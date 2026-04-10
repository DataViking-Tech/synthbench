"""Benchmark runner — orchestrates dataset, provider, and metrics."""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from dataclasses import dataclass, field

from synthbench.datasets.base import Question
from synthbench.datasets import Dataset
from synthbench.metrics import (
    jensen_shannon_divergence,
    kendall_tau_b,
    parity_score,
    synthbench_parity_score,
    refusal_calibration,
    extract_human_refusal_rate,
)
from synthbench.providers.base import Provider


@dataclass
class QuestionResult:
    """Metrics for a single question."""

    key: str
    text: str
    options: list[str]
    human_distribution: dict[str, float]
    model_distribution: dict[str, float]
    jsd: float
    kendall_tau: float
    parity: float
    n_samples: int
    n_parse_failures: int = 0
    model_refusal_rate: float = 0.0
    human_refusal_rate: float = 0.0


@dataclass
class BenchmarkResult:
    """Full benchmark run results."""

    provider_name: str
    dataset_name: str
    questions: list[QuestionResult]
    config: dict = field(default_factory=dict)
    elapsed_seconds: float = 0.0
    group_scores: dict[str, float] = field(default_factory=dict)
    conditioned_scores: dict[str, float] = field(default_factory=dict)
    default_scores: dict[str, float] = field(default_factory=dict)

    @property
    def mean_jsd(self) -> float:
        if not self.questions:
            return 0.0
        return sum(q.jsd for q in self.questions) / len(self.questions)

    @property
    def median_jsd(self) -> float:
        if not self.questions:
            return 0.0
        vals = sorted(q.jsd for q in self.questions)
        mid = len(vals) // 2
        if len(vals) % 2 == 0:
            return (vals[mid - 1] + vals[mid]) / 2
        return vals[mid]

    @property
    def mean_kendall_tau(self) -> float:
        if not self.questions:
            return 0.0
        return sum(q.kendall_tau for q in self.questions) / len(self.questions)

    @property
    def composite_parity(self) -> float:
        return parity_score(self.mean_jsd, self.mean_kendall_tau)

    @property
    def p_dist(self) -> float:
        """P_dist = 1 - mean(JSD). Distributional parity [0, 1]."""
        return 1.0 - self.mean_jsd

    @property
    def p_rank(self) -> float:
        """P_rank = (1 + mean(tau)) / 2. Rank-order parity [0, 1]."""
        return (1.0 + self.mean_kendall_tau) / 2.0

    @property
    def p_refuse(self) -> float:
        """P_refuse = 1 - mean(|R_provider - R_human|). Refusal calibration [0, 1]."""
        if not self.questions:
            return 1.0
        return refusal_calibration(
            [q.model_refusal_rate for q in self.questions],
            [q.human_refusal_rate for q in self.questions],
        )

    @property
    def p_sub(self) -> float | None:
        """P_sub = 1 - CV(group_scores). None if no group data available."""
        if not self.group_scores:
            return None
        from synthbench.metrics import subgroup_consistency
        return subgroup_consistency(self.group_scores)

    @property
    def p_cond(self) -> float | None:
        """P_cond = mean(max(0, cond - default)). None if no conditioning data."""
        if not self.conditioned_scores or not self.default_scores:
            return None
        from synthbench.metrics import conditioning_fidelity
        return conditioning_fidelity(self.conditioned_scores, self.default_scores)

    @property
    def sps_components(self) -> dict[str, float]:
        """All available SPS component scores."""
        components: dict[str, float] = {
            "p_dist": self.p_dist,
            "p_rank": self.p_rank,
            "p_refuse": self.p_refuse,
        }
        if self.p_sub is not None:
            components["p_sub"] = self.p_sub
        if self.p_cond is not None:
            components["p_cond"] = self.p_cond
        return components

    @property
    def sps(self) -> float:
        """SynthBench Parity Score — equal-weighted mean of available metrics."""
        return synthbench_parity_score(self.sps_components)


class BenchmarkRunner:
    """Run a benchmark: load data, query provider, compute metrics."""

    def __init__(
        self,
        dataset: Dataset,
        provider: Provider,
        samples_per_question: int = 30,
        concurrency: int = 10,
    ):
        self.dataset = dataset
        self.provider = provider
        self.samples_per_question = samples_per_question
        self._semaphore = asyncio.Semaphore(concurrency)

    async def run(
        self,
        n: int | None = None,
        progress_callback=None,
    ) -> BenchmarkResult:
        t0 = time.monotonic()
        questions = self.dataset.load(n=n)

        results = []
        for i, question in enumerate(questions):
            qr = await self._evaluate_question(question)
            results.append(qr)
            if progress_callback:
                progress_callback(i + 1, len(questions), qr)

        elapsed = time.monotonic() - t0

        return BenchmarkResult(
            provider_name=self.provider.name,
            dataset_name=self.dataset.name,
            questions=results,
            config={
                "samples_per_question": self.samples_per_question,
                "n_requested": n,
                "n_evaluated": len(results),
            },
            elapsed_seconds=elapsed,
        )

    async def _evaluate_question(self, question: Question) -> QuestionResult:
        """Sample the provider and compute metrics for one question."""
        model_refusal_rate = 0.0

        if self.provider.supports_distribution:
            dist = await self.provider.get_distribution(
                question.text, question.options,
                n_samples=self.samples_per_question,
            )
            model_dist = dict(zip(question.options, dist.probabilities))
            model_refusal_rate = dist.refusal_probability
            n_samples = dist.n_samples or self.samples_per_question
            n_parse_failures = 0
        else:
            responses, refusals = await self._collect_samples_with_refusals(question)
            counts = Counter(responses)
            total = len(responses) + refusals
            model_dist = {
                opt: counts.get(opt, 0) / max(total, 1) for opt in question.options
            }
            model_refusal_rate = refusals / max(total, 1)
            n_samples = total
            n_parse_failures = 0

        human_refusal_rate = extract_human_refusal_rate(question.human_distribution)

        jsd = jensen_shannon_divergence(question.human_distribution, model_dist)
        tau = kendall_tau_b(question.human_distribution, model_dist)
        par = parity_score(jsd, tau)

        return QuestionResult(
            key=question.key,
            text=question.text,
            options=question.options,
            human_distribution=question.human_distribution,
            model_distribution=model_dist,
            jsd=jsd,
            kendall_tau=tau,
            parity=par,
            n_samples=n_samples,
            n_parse_failures=n_parse_failures,
            model_refusal_rate=model_refusal_rate,
            human_refusal_rate=human_refusal_rate,
        )

    async def _collect_samples_with_refusals(
        self, question: Question
    ) -> tuple[list[str], int]:
        """Call the provider samples_per_question times, tracking refusals.

        Returns (selected_options, refusal_count).
        """

        async def _one_sample():
            async with self._semaphore:
                resp = await self.provider.respond(question.text, question.options)
                return resp

        tasks = [_one_sample() for _ in range(self.samples_per_question)]
        results = await asyncio.gather(*tasks)

        selected = [r.selected_option for r in results if not r.refusal]
        refusals = sum(1 for r in results if r.refusal)
        return selected, refusals
