"""Benchmark runner — orchestrates dataset, provider, and metrics."""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from dataclasses import dataclass, field

from synthbench.datasets.base import Question
from synthbench.datasets import Dataset
from synthbench.metrics import jensen_shannon_divergence, kendall_tau_b, parity_score
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


@dataclass
class BenchmarkResult:
    """Full benchmark run results."""

    provider_name: str
    dataset_name: str
    questions: list[QuestionResult]
    config: dict = field(default_factory=dict)
    elapsed_seconds: float = 0.0

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
        responses = await self._collect_samples(question)

        # Build empirical distribution
        counts = Counter(responses)
        total = len(responses)
        model_dist = {
            opt: counts.get(opt, 0) / total for opt in question.options
        }

        # Count parse failures (responses that fell back to first option
        # but we can't distinguish from legitimate first-option choices,
        # so this is approximate)
        n_parse_failures = 0

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
            n_samples=total,
            n_parse_failures=n_parse_failures,
        )

    async def _collect_samples(self, question: Question) -> list[str]:
        """Call the provider samples_per_question times, with concurrency limit."""

        async def _one_sample():
            async with self._semaphore:
                resp = await self.provider.respond(question.text, question.options)
                return resp.selected_option

        tasks = [_one_sample() for _ in range(self.samples_per_question)]
        return await asyncio.gather(*tasks)
