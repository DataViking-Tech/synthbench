"""Benchmark runner — orchestrates dataset, provider, and metrics."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections import Counter
from dataclasses import dataclass, field

from synthbench.datasets.base import Question
from synthbench.datasets import Dataset
from synthbench.datasets.opinionsqa import wave_year
from synthbench.metrics import (
    jensen_shannon_divergence,
    kendall_tau_b,
    parity_score,
    synthbench_parity_score,
    refusal_calibration,
    extract_human_refusal_rate,
    conditioning_fidelity,
)
from synthbench.providers.base import Distribution, PersonaSpec, Provider, Response
from synthbench.stats import bootstrap_ci, question_set_hash


def _sha256_of(s: str) -> str:
    """Return ``sha256:<hex>`` digest of a UTF-8 string."""
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def _provider_reproducibility_hashes(provider: Provider) -> dict[str, str]:
    """Derive Tier-3 reproducibility hashes for a provider.

    ``model_revision_hash`` identifies the provider + model pair the run
    was executed against (``provider.name`` already encodes both). The
    hash is stable across runs against the same deployment, and changes
    whenever the provider class name or configured model identifier
    changes — which is what Tier-3 validators expect.

    ``prompt_template_hash`` identifies the literal prompt surface the
    provider sends to the model. Providers that don't issue a prompt
    (baselines) report an empty template; we emit an all-zero digest
    so the field is still a non-empty string the validator will accept.
    """
    template = getattr(provider, "prompt_template_source", "") or ""
    return {
        "model_revision_hash": _sha256_of(provider.name),
        "prompt_template_hash": _sha256_of(template),
    }


def _normalize_model_dist(
    model_dist: dict[str, float], options: list[str]
) -> dict[str, float]:
    """Renormalize a model distribution so its mass over declared options sums to 1.

    Raw model distributions are built from valid-option counts divided by
    total samples, where "total" includes refusals and parse failures. That
    denominator leaves the valid-option mass below 1 whenever any sample was
    refused or unparseable. Downstream validation (tier 2 per-question
    recompute) re-derives JSD and Kendall's tau from the stored
    distribution, so any drift between the published distribution and the
    published metrics trips the gate.

    We renormalize the distribution over the declared options before
    computing metrics so the two stay internally consistent. Refusal mass
    is already captured separately via ``model_refusal_rate`` / p_refuse,
    so it's not being silently dropped — just removed from the conditional
    answer distribution that p_dist and p_rank operate on. If every sample
    was refused or unparseable (total mass == 0), fall back to a uniform
    distribution: a rare degenerate case, but the published file still
    needs to be a valid probability vector.
    """
    total = sum(model_dist.get(opt, 0.0) for opt in options)
    if total > 0:
        return {opt: model_dist.get(opt, 0.0) / total for opt in options}
    if options:
        uniform = 1.0 / len(options)
        return {opt: uniform for opt in options}
    return {}


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
    temporal_year: int = 0
    token_usage: dict | None = None
    """Summed token usage across samples for this question.

    Shape: {"input_tokens": int, "output_tokens": int, "call_count": int}.
    None when the provider did not report usage for any sample.
    """
    raw_sample: dict | None = None
    """One preserved raw response (text + selected option) for submission audits.

    Shape: ``{"raw_text": str, "selected_option": str}``. ``None`` when the
    provider didn't return raw text (e.g. native distribution providers that
    expose probabilities but no per-sample strings). See ``raw_responses``
    in :mod:`synthbench.validation` for the Tier-3 audit use case.
    """


def _aggregate_token_usage(responses: list[Response]) -> dict | None:
    """Sum input/output tokens across sample responses.

    Returns None if no response carried usage data; otherwise returns
    {"input_tokens": int, "output_tokens": int, "call_count": int}.
    """
    input_tot = 0
    output_tot = 0
    calls = 0
    any_usage = False
    for r in responses:
        usage = (r.metadata or {}).get("usage")
        if usage is None:
            continue
        any_usage = True
        input_tot += usage.get("input_tokens", 0) or 0
        output_tot += usage.get("output_tokens", 0) or 0
        calls += 1
    if not any_usage:
        return None
    return {
        "input_tokens": input_tot,
        "output_tokens": output_tot,
        "call_count": calls,
    }


@dataclass
class DemographicGroupResult:
    """Results for a single demographic group evaluation."""

    attribute: str
    group: str
    p_dist: float
    p_cond: float
    n_questions: int


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
    demographic_breakdown: dict[str, list[DemographicGroupResult]] = field(
        default_factory=dict
    )

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
    def temporal_breakdown(self) -> dict[int, dict[str, float]]:
        """Per-year P_dist scores for temporal contamination analysis.

        Groups questions by survey wave year and computes P_dist for each.
        Returns {year: {"p_dist": ..., "mean_jsd": ..., "n_questions": ...}}.
        """
        by_year: dict[int, list[QuestionResult]] = {}
        for q in self.questions:
            if q.temporal_year > 0:
                by_year.setdefault(q.temporal_year, []).append(q)

        result: dict[int, dict[str, float]] = {}
        for year in sorted(by_year):
            qs = by_year[year]
            mean_jsd = sum(q.jsd for q in qs) / len(qs)
            mean_tau = sum(q.kendall_tau for q in qs) / len(qs)
            result[year] = {
                "p_dist": round(1.0 - mean_jsd, 6),
                "p_rank": round((1.0 + mean_tau) / 2.0, 6),
                "mean_jsd": round(mean_jsd, 6),
                "n_questions": len(qs),
            }
        return result

    @property
    def q_set_hash(self) -> str:
        """SHA256 hash of sorted question keys for reproducibility."""
        return question_set_hash([q.key for q in self.questions])

    @property
    def total_parse_failures(self) -> int:
        """Total parse failures across all questions."""
        return sum(q.n_parse_failures for q in self.questions)


logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """Run a benchmark: load data, query provider, compute metrics."""

    BATCH_SIZE = 10
    """Questions per batch when using batch_get_distribution."""

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
        self._concurrency = concurrency
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

        # Use batched evaluation when provider supports it
        use_batch = self.provider.supports_distribution and hasattr(
            self.provider, "batch_get_distribution"
        )

        if use_batch:
            results = await self._run_batched(questions, progress_callback)
        else:
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
                **_provider_reproducibility_hashes(self.provider),
            },
            elapsed_seconds=elapsed,
        )

    async def _evaluate_question(self, question: Question) -> QuestionResult:
        """Sample the provider and compute metrics for one question."""
        model_refusal_rate = 0.0
        token_usage: dict | None = None
        raw_sample: dict | None = None

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
            if dist.metadata:
                token_usage = dist.metadata.get("usage")
                sampled = dist.metadata.get("raw_sample")
                if isinstance(sampled, dict) and sampled.get("raw_text"):
                    raw_sample = {
                        "raw_text": str(sampled["raw_text"]),
                        "selected_option": str(sampled.get("selected_option", "")),
                    }
        else:
            (
                responses,
                refusals,
                parse_fails,
                token_usage,
                raw_sample,
            ) = await self._collect_samples_with_refusals(question)
            counts = Counter(responses)
            total = len(responses) + refusals
            model_dist = {
                opt: counts.get(opt, 0) / max(total, 1) for opt in question.options
            }
            model_refusal_rate = refusals / max(total, 1)
            n_samples = total
            n_parse_failures = parse_fails

        model_dist = _normalize_model_dist(model_dist, question.options)
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
            temporal_year=wave_year(question.survey),
            token_usage=token_usage,
            raw_sample=raw_sample,
        )

    async def _run_batched(
        self,
        questions: list[Question],
        progress_callback=None,
    ) -> list[QuestionResult]:
        """Evaluate questions in batches using provider batch_get_distribution.

        Groups questions into batches of BATCH_SIZE, runs batches concurrently
        (limited by the concurrency semaphore), and collects results.
        """
        batch_size = self.BATCH_SIZE
        batches = [
            questions[i : i + batch_size] for i in range(0, len(questions), batch_size)
        ]

        total = len(questions)
        all_results: list[QuestionResult | None] = [None] * total
        done_count = 0

        async def process_batch(batch_idx: int, batch: list[Question]):
            nonlocal done_count
            async with self._semaphore:
                texts = [q.text for q in batch]
                opts_list = [q.options for q in batch]
                dists = await self.provider.batch_get_distribution(
                    texts, opts_list, n_samples=self.samples_per_question
                )

                start_idx = batch_idx * batch_size
                for j, (q, dist) in enumerate(zip(batch, dists)):
                    qr = self._build_question_result(q, dist)
                    all_results[start_idx + j] = qr
                    done_count += 1
                    if progress_callback:
                        progress_callback(done_count, total, qr)

        tasks = [process_batch(i, batch) for i, batch in enumerate(batches)]
        await asyncio.gather(*tasks)

        return [r for r in all_results if r is not None]

    def _build_question_result(
        self, question: Question, dist: Distribution
    ) -> QuestionResult:
        """Build a QuestionResult from a question and its model distribution."""
        model_dist = dict(zip(question.options, dist.probabilities))
        model_dist = _normalize_model_dist(model_dist, question.options)
        model_refusal_rate = dist.refusal_probability
        n_samples = dist.n_samples or self.samples_per_question
        token_usage = dist.metadata.get("usage") if dist.metadata else None

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
            n_parse_failures=0,
            model_refusal_rate=model_refusal_rate,
            human_refusal_rate=human_refusal_rate,
            temporal_year=wave_year(question.survey),
            token_usage=token_usage,
        )

    async def _collect_samples_with_refusals(
        self, question: Question, persona: PersonaSpec | None = None
    ) -> tuple[list[str], int, int, dict | None, dict | None]:
        """Call the provider samples_per_question times, tracking refusals.

        Returns (selected_options, refusal_count, parse_failure_count,
        token_usage, raw_sample). token_usage is the summed per-sample
        usage dict, or None if no sample reported usage. raw_sample is
        the first non-refusal response preserved for Tier-3 auditing, or
        None if every sample was a refusal / parse failure.
        """

        async def _one_sample():
            async with self._semaphore:
                resp = await self.provider.respond(
                    question.text, question.options, persona=persona
                )
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
        token_usage = _aggregate_token_usage(results)

        # Preserve the first non-refusal raw response as an audit sample.
        raw_sample: dict | None = None
        for r in results:
            if r.refusal:
                continue
            if r.raw_text and r.selected_option in valid_options:
                raw_sample = {
                    "raw_text": r.raw_text,
                    "selected_option": r.selected_option,
                }
                break

        return selected, refusals, parse_failures, token_usage, raw_sample

    async def _sample_distribution(
        self, question: Question, persona: PersonaSpec | None = None
    ) -> dict[str, float]:
        """Get model response distribution for a question, optionally with persona."""
        if self.provider.supports_distribution:
            dist = await self.provider.get_distribution(
                question.text,
                question.options,
                persona=persona,
                n_samples=self.samples_per_question,
            )
            model_dist = dict(zip(question.options, dist.probabilities))
        else:
            (
                responses,
                _refusals,
                _fails,
                _usage,
                _raw,
            ) = await self._collect_samples_with_refusals(question, persona=persona)
            total = len(responses) + _refusals
            counts = Counter(responses)
            model_dist = {
                opt: counts.get(opt, 0) / max(total, 1) for opt in question.options
            }

        return _normalize_model_dist(model_dist, question.options)

    async def run_with_demographics(
        self,
        demographics: list[str],
        n: int | None = None,
        progress_callback=None,
        question_keys: list[str] | None = None,
    ) -> BenchmarkResult:
        """Run benchmark with persona-conditioned demographic evaluation.

        For each demographic attribute, evaluates per-group alignment by
        running conditioned queries with demographic personas and comparing
        against group-specific human distributions.

        Args:
            demographics: List of demographic attributes (e.g., ["AGE", "POLIDEOLOGY"]).
            n: Number of questions to evaluate.
            progress_callback: Optional progress callback.
            question_keys: Optional pinned question set.

        Returns:
            BenchmarkResult enriched with group_scores, conditioned_scores,
            default_scores, and demographic_breakdown.
        """
        t0 = time.monotonic()

        # 1. Run unconditioned baseline
        baseline = await self.run(
            n=n, progress_callback=progress_callback, question_keys=question_keys
        )

        # Build lookup: question_key -> (Question, unconditioned model dist)
        questions = self.dataset.load(n=n)
        if question_keys is not None:
            from synthbench.suites import filter_questions_by_suite

            questions = filter_questions_by_suite(questions, question_keys)

        question_by_key = {q.key: q for q in questions}
        unconditioned_dists = {
            qr.key: qr.model_distribution for qr in baseline.questions
        }

        # 2. Run per-attribute demographic evaluation
        all_group_scores: dict[str, float] = {}
        all_conditioned_scores: dict[str, float] = {}
        all_default_scores: dict[str, float] = {}
        demographic_breakdown: dict[str, list[DemographicGroupResult]] = {}

        for attr in demographics:
            demo_dists = self.dataset.load_demographic_distributions(attr)
            if not demo_dists:
                logger.warning(
                    "No demographic data for attribute '%s' in dataset '%s' — skipping.",
                    attr,
                    self.dataset.name,
                )
                continue

            # Collect all groups across questions for this attribute
            all_groups: set[str] = set()
            for _qkey, gdata in demo_dists.items():
                all_groups.update(gdata.keys())

            attr_results: list[DemographicGroupResult] = []

            for group in sorted(all_groups):
                # Find questions with both baseline data and group-specific data
                common_keys = [
                    k
                    for k in unconditioned_dists
                    if k in demo_dists and group in demo_dists[k]
                ]
                if not common_keys:
                    continue

                persona = PersonaSpec(
                    demographics={attr: group}, attribute=attr, group=group
                )

                conditioned_jsd_total = 0.0
                unconditioned_jsd_total = 0.0
                p_cond_total = 0.0

                for qkey in common_keys:
                    question = question_by_key.get(qkey)
                    if question is None:
                        continue

                    group_human = demo_dists[qkey][group]
                    unconditioned_model = unconditioned_dists[qkey]

                    # Run conditioned evaluation
                    conditioned_model = await self._sample_distribution(
                        question, persona=persona
                    )

                    # Compute JSDs
                    conditioned_jsd_total += jensen_shannon_divergence(
                        group_human, conditioned_model
                    )
                    unconditioned_jsd_total += jensen_shannon_divergence(
                        group_human, unconditioned_model
                    )
                    p_cond_total += conditioning_fidelity(
                        conditioned_model, unconditioned_model, group_human
                    )

                n_q = len(common_keys)
                group_p_dist = 1.0 - conditioned_jsd_total / n_q
                group_p_cond = p_cond_total / n_q

                label = f"{attr}:{group}"
                all_group_scores[label] = group_p_dist
                all_conditioned_scores[label] = group_p_dist
                all_default_scores[label] = 1.0 - unconditioned_jsd_total / n_q

                attr_results.append(
                    DemographicGroupResult(
                        attribute=attr,
                        group=group,
                        p_dist=group_p_dist,
                        p_cond=group_p_cond,
                        n_questions=n_q,
                    )
                )

            if attr_results:
                demographic_breakdown[attr] = attr_results

        elapsed = time.monotonic() - t0

        baseline.group_scores = all_group_scores
        baseline.conditioned_scores = all_conditioned_scores
        baseline.default_scores = all_default_scores
        baseline.demographic_breakdown = demographic_breakdown
        baseline.elapsed_seconds = elapsed

        return baseline
