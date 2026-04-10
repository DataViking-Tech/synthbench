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
from synthbench.stats import bootstrap_ci, question_set_hash


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
        """P_cond score. None if no conditioning data.

        Uses score-diff fallback until the pipeline provides full
        distributions for the JSD-based conditioning_fidelity().
        """
        if not self.conditioned_scores or not self.default_scores:
            return None
        common = set(self.conditioned_scores) & set(self.default_scores)
        if not common:
            return 0.0
        improvements = [
            max(0.0, self.conditioned_scores[g] - self.default_scores[g])
            for g in common
        ]
        return sum(improvements) / len(improvements)

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

    @property
    def per_metric_ci(self) -> dict[str, tuple[float, float]]:
        """Bootstrap 95% CIs for each SPS component metric.

        Returns {metric_name: (ci_lower, ci_upper)}.
        Requires at least 5 questions for bootstrap to work.
        """
        if len(self.questions) < 5:
            return {}

        def _mean(data: list[float]) -> float:
            return sum(data) / len(data) if data else 0.0

        cis: dict[str, tuple[float, float]] = {}

        # P_dist CI from per-question JSD values
        jsd_vals = [q.jsd for q in self.questions]
        r = bootstrap_ci(jsd_vals, _mean, seed=42)
        cis["p_dist"] = (round(1.0 - r.ci_upper, 6), round(1.0 - r.ci_lower, 6))

        # P_rank CI from per-question tau values
        tau_vals = [q.kendall_tau for q in self.questions]
        r = bootstrap_ci(tau_vals, _mean, seed=43)
        cis["p_rank"] = (
            round((1.0 + r.ci_lower) / 2.0, 6),
            round((1.0 + r.ci_upper) / 2.0, 6),
        )

        # P_refuse CI from per-question refusal diffs
        refuse_diffs = [
            abs(q.model_refusal_rate - q.human_refusal_rate) for q in self.questions
        ]
        r = bootstrap_ci(refuse_diffs, _mean, seed=44)
        cis["p_refuse"] = (round(1.0 - r.ci_upper, 6), round(1.0 - r.ci_lower, 6))

        # SPS CI from per-question parity scores
        parity_vals = [q.parity for q in self.questions]
        r = bootstrap_ci(parity_vals, _mean, seed=45)
        cis["sps"] = (round(r.ci_lower, 6), round(r.ci_upper, 6))

        return cis

    @property
    def q_set_hash(self) -> str:
        """SHA256 hash of sorted question keys for reproducibility."""
        return question_set_hash([q.key for q in self.questions])

    @property
    def total_parse_failures(self) -> int:
        """Total parse failures across all questions."""
        return sum(q.n_parse_failures for q in self.questions)


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
        question_keys: list[str] | None = None,
    ) -> BenchmarkResult:
        t0 = time.monotonic()
        questions = self.dataset.load(n=n)

        # Filter by pinned question set if provided
        if question_keys is not None:
            from synthbench.suites import filter_questions_by_suite

            questions = filter_questions_by_suite(questions, question_keys)

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
                question.text,
                question.options,
                n_samples=self.samples_per_question,
            )
            model_dist = dict(zip(question.options, dist.probabilities))
            model_refusal_rate = dist.refusal_probability
            n_samples = dist.n_samples or self.samples_per_question
            n_parse_failures = 0
        else:
            (
                responses,
                refusals,
                parse_fails,
            ) = await self._collect_samples_with_refusals(question)
            counts = Counter(responses)
            total = len(responses) + refusals
            model_dist = {
                opt: counts.get(opt, 0) / max(total, 1) for opt in question.options
            }
            model_refusal_rate = refusals / max(total, 1)
            n_samples = total
            n_parse_failures = parse_fails

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
    ) -> tuple[list[str], int, int]:
        """Call the provider samples_per_question times, tracking refusals.

        Returns (selected_options, refusal_count, parse_failure_count).
        """

        async def _one_sample():
            async with self._semaphore:
                resp = await self.provider.respond(question.text, question.options)
                return resp

        tasks = [_one_sample() for _ in range(self.samples_per_question)]
        results = await asyncio.gather(*tasks)

        selected = [r.selected_option for r in results if not r.refusal]
        refusals = sum(1 for r in results if r.refusal)
        valid_options = set(question.options)
        parse_failures = sum(
            1
            for r in results
            if not r.refusal and r.selected_option not in valid_options
        )
        return selected, refusals, parse_failures
