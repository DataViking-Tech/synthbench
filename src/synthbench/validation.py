"""Submission validation pipeline for SynthBench leaderboard entries.

Runs authenticity checks on result JSON files to catch fabricated or
inflated scores before they reach the public leaderboard. Organized into
tiers of increasing cost:

* Tier 1 — schema + statistical plausibility (cheap, always on in CI).
* Tier 2 — aggregate ↔ per-question recomputation (pure arithmetic).
* Tier 3/4 — reproducibility + attestation (out of scope here; see the
  submitter documentation for the manual workflow).

Returns structured :class:`ValidationReport` objects rather than raising,
so callers (CLI, CI scripts) can decide how to surface findings.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping

from synthbench.metrics.composite import synthbench_parity_score
from synthbench.metrics.distributional import jensen_shannon_divergence
from synthbench.metrics.ranking import kendall_tau_b
from synthbench.metrics.refusal import refusal_calibration
from synthbench.stats import question_set_hash

# Tolerances for numerical comparison. Distributions are serialized to 4
# decimal places; metrics are rounded to 6. Small errors in the input
# distributions compound through JSD and Kendall's tau, so per-question
# recompute needs to survive ~5e-3 noise. The tolerances below still catch
# any fabrication that meaningfully inflates scores (typical threshold of
# concern is >1% SPS drift — orders of magnitude above the tolerance).
#
# PER-QUESTION TAU SPECIFICALLY: 4-decimal rounding can collapse two distinct
# probabilities to the same value, introducing a tie that wasn't in the
# unrounded input. Kendall's tau-b adjusts for ties in the denominator
# (sqrt((N0-T1)(N0-T2))), so a single rounding-induced tie shifts tau-b by
# ~0.01–0.02 on small-option distributions (e.g. 3/√75 = 0.3464 vs 3/√70 =
# 0.3586 on a 6-option question). We widen the per-question recompute
# tolerance to absorb this artifact without weakening fabrication detection
# — real fabrication deltas are typically >0.1.
DISTRIBUTION_SUM_TOLERANCE = 5e-3
METRIC_RECOMPUTE_TOLERANCE = 3e-2
AGGREGATE_RECOMPUTE_TOLERANCE = 1e-2

# Raw-response sample requirements (tier 3). Submissions must ship raw model
# text for at least this share of questions so that anomaly reviewers can
# spot-check provider output. Length bounds are loose — real model outputs
# range from a single option letter ("A") up to multi-paragraph reasoning,
# but *every* sample being <=1 char or >=10,000 chars is a strong fabrication
# signal.
RAW_RESPONSE_MIN_COVERAGE = 0.10
RAW_RESPONSE_MIN_LENGTH = 1
RAW_RESPONSE_MAX_LENGTH = 10_000
RAW_RESPONSE_SHORT_FRACTION_LIMIT = 0.95
RAW_RESPONSE_LONG_FRACTION_LIMIT = 0.95

# Reproducibility metadata fields required on new submissions. Missing
# fields are WARNINGS in tier 3 (not ERRORS in tier 1) so existing
# leaderboard files remain valid until we re-generate them.
REQUIRED_REPRODUCIBILITY = (
    "seed",
    "model_revision_hash",
    "prompt_template_hash",
    "framework_version",
    "submitted_at",
)


class Severity(str, Enum):
    """Issue severity. ERROR fails the run; WARNING is informational."""

    ERROR = "error"
    WARNING = "warning"


@dataclass
class Issue:
    """A single validation finding."""

    code: str
    severity: Severity
    message: str
    path: str = ""

    def format(self) -> str:
        loc = f" [{self.path}]" if self.path else ""
        return f"{self.severity.value.upper()}: {self.code}{loc} — {self.message}"


@dataclass
class ValidationReport:
    """Aggregate result of running validators against one submission."""

    source: str = ""
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors

    def extend(self, issues: Iterable[Issue]) -> None:
        self.issues.extend(issues)

    def format(self) -> str:
        header = f"Validation report: {self.source}"
        if not self.issues:
            return f"{header}\n  OK — no issues."
        lines = [header]
        for issue in self.issues:
            lines.append(f"  {issue.format()}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tier 1: schema + statistical plausibility
# ---------------------------------------------------------------------------

# Top-level fields every submission must carry.
REQUIRED_TOP_LEVEL = ("benchmark", "version", "config", "aggregate", "per_question")
REQUIRED_CONFIG = ("dataset", "provider")
REQUIRED_AGGREGATE = (
    "mean_jsd",
    "mean_kendall_tau",
    "composite_parity",
    "n_questions",
)
REQUIRED_PER_QUESTION = (
    "key",
    "human_distribution",
    "model_distribution",
    "jsd",
    "kendall_tau",
)


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _check_type(
    value: Any, expected: type | tuple[type, ...], path: str, code: str
) -> Issue | None:
    if not isinstance(value, expected):
        return Issue(
            code=code,
            severity=Severity.ERROR,
            message=f"expected {expected}, got {type(value).__name__}",
            path=path,
        )
    return None


def _validate_schema(data: Any) -> list[Issue]:
    """Check the top-level shape and required fields of a submission."""

    issues: list[Issue] = []

    if not isinstance(data, dict):
        issues.append(
            Issue(
                code="SCHEMA_ROOT",
                severity=Severity.ERROR,
                message="result file must decode to a JSON object",
            )
        )
        return issues

    benchmark = data.get("benchmark")
    if benchmark != "synthbench":
        issues.append(
            Issue(
                code="SCHEMA_BENCHMARK",
                severity=Severity.ERROR,
                message=f"'benchmark' must be 'synthbench' (got {benchmark!r})",
                path="benchmark",
            )
        )

    for key in REQUIRED_TOP_LEVEL:
        if key not in data:
            issues.append(
                Issue(
                    code="SCHEMA_MISSING",
                    severity=Severity.ERROR,
                    message=f"missing required top-level key '{key}'",
                    path=key,
                )
            )

    config = data.get("config")
    if isinstance(config, dict):
        for key in REQUIRED_CONFIG:
            if key not in config:
                issues.append(
                    Issue(
                        code="SCHEMA_MISSING",
                        severity=Severity.ERROR,
                        message=f"missing required config key '{key}'",
                        path=f"config.{key}",
                    )
                )
    elif config is not None:
        issues.append(
            Issue(
                code="SCHEMA_TYPE",
                severity=Severity.ERROR,
                message="'config' must be an object",
                path="config",
            )
        )

    aggregate = data.get("aggregate")
    if isinstance(aggregate, dict):
        for key in REQUIRED_AGGREGATE:
            if key not in aggregate:
                issues.append(
                    Issue(
                        code="SCHEMA_MISSING",
                        severity=Severity.ERROR,
                        message=f"missing required aggregate key '{key}'",
                        path=f"aggregate.{key}",
                    )
                )
    elif aggregate is not None:
        issues.append(
            Issue(
                code="SCHEMA_TYPE",
                severity=Severity.ERROR,
                message="'aggregate' must be an object",
                path="aggregate",
            )
        )

    per_question = data.get("per_question")
    if per_question is None:
        pass  # already reported above
    elif not isinstance(per_question, list):
        issues.append(
            Issue(
                code="SCHEMA_TYPE",
                severity=Severity.ERROR,
                message="'per_question' must be a list",
                path="per_question",
            )
        )
    else:
        for idx, q in enumerate(per_question):
            if not isinstance(q, dict):
                issues.append(
                    Issue(
                        code="SCHEMA_TYPE",
                        severity=Severity.ERROR,
                        message="per-question entry must be an object",
                        path=f"per_question[{idx}]",
                    )
                )
                continue
            for key in REQUIRED_PER_QUESTION:
                if key not in q:
                    issues.append(
                        Issue(
                            code="SCHEMA_MISSING",
                            severity=Severity.ERROR,
                            message=f"missing '{key}' on per-question entry",
                            path=f"per_question[{idx}].{key}",
                        )
                    )
    return issues


def _validate_bounds(data: Mapping[str, Any]) -> list[Issue]:
    """Check SPS/sub-metric bounds, parse_failure_rate, n_questions."""

    issues: list[Issue] = []
    aggregate = data.get("aggregate") or {}
    scores = data.get("scores") or {}

    # SPS + related must live in [0, 1].
    sps_bounded = (
        "composite_parity",
        "mean_jsd",
        "median_jsd",
    )
    for key in sps_bounded:
        val = aggregate.get(key)
        if val is None:
            continue
        if not _is_number(val):
            issues.append(
                Issue(
                    code="BOUNDS_TYPE",
                    severity=Severity.ERROR,
                    message=f"'{key}' must be numeric",
                    path=f"aggregate.{key}",
                )
            )
            continue
        if not (0.0 <= val <= 1.0):
            issues.append(
                Issue(
                    code="BOUNDS_RANGE",
                    severity=Severity.ERROR,
                    message=f"'{key}'={val} outside [0, 1]",
                    path=f"aggregate.{key}",
                )
            )

    # Kendall's tau lives in [-1, 1].
    tau = aggregate.get("mean_kendall_tau")
    if tau is not None:
        if not _is_number(tau):
            issues.append(
                Issue(
                    code="BOUNDS_TYPE",
                    severity=Severity.ERROR,
                    message="'mean_kendall_tau' must be numeric",
                    path="aggregate.mean_kendall_tau",
                )
            )
        elif not (-1.0 <= tau <= 1.0):
            issues.append(
                Issue(
                    code="BOUNDS_RANGE",
                    severity=Severity.ERROR,
                    message=f"'mean_kendall_tau'={tau} outside [-1, 1]",
                    path="aggregate.mean_kendall_tau",
                )
            )

    for key, val in scores.items():
        if not _is_number(val):
            continue
        if not (0.0 <= val <= 1.0):
            issues.append(
                Issue(
                    code="BOUNDS_RANGE",
                    severity=Severity.ERROR,
                    message=f"scores.{key}={val} outside [0, 1]",
                    path=f"scores.{key}",
                )
            )

    config = data.get("config") or {}
    pfr = config.get("parse_failure_rate")
    if pfr is not None:
        if not _is_number(pfr):
            issues.append(
                Issue(
                    code="BOUNDS_TYPE",
                    severity=Severity.ERROR,
                    message="'parse_failure_rate' must be numeric",
                    path="config.parse_failure_rate",
                )
            )
        elif not (0.0 <= pfr <= 1.0):
            issues.append(
                Issue(
                    code="BOUNDS_RANGE",
                    severity=Severity.ERROR,
                    message=f"'parse_failure_rate'={pfr} outside [0, 1]",
                    path="config.parse_failure_rate",
                )
            )

    n_q_agg = aggregate.get("n_questions")
    if n_q_agg is not None and not (isinstance(n_q_agg, int) and n_q_agg >= 0):
        issues.append(
            Issue(
                code="BOUNDS_RANGE",
                severity=Severity.ERROR,
                message=f"'n_questions'={n_q_agg} must be non-negative int",
                path="aggregate.n_questions",
            )
        )
    return issues


def _validate_distributions(data: Mapping[str, Any]) -> list[Issue]:
    """Check that per-question distributions are proper probability vectors."""

    issues: list[Issue] = []
    per_question = data.get("per_question") or []
    for idx, q in enumerate(per_question):
        if not isinstance(q, dict):
            continue
        for field_name in ("human_distribution", "model_distribution"):
            dist = q.get(field_name)
            if dist is None:
                continue
            if not isinstance(dist, dict):
                issues.append(
                    Issue(
                        code="DIST_TYPE",
                        severity=Severity.ERROR,
                        message=f"'{field_name}' must be a mapping",
                        path=f"per_question[{idx}].{field_name}",
                    )
                )
                continue
            total = 0.0
            for option, weight in dist.items():
                if not _is_number(weight):
                    issues.append(
                        Issue(
                            code="DIST_TYPE",
                            severity=Severity.ERROR,
                            message=(f"non-numeric weight for option {option!r}"),
                            path=f"per_question[{idx}].{field_name}",
                        )
                    )
                    total = float("nan")
                    break
                if weight < -DISTRIBUTION_SUM_TOLERANCE:
                    issues.append(
                        Issue(
                            code="DIST_NEGATIVE",
                            severity=Severity.ERROR,
                            message=(
                                f"negative probability for option {option!r}: {weight}"
                            ),
                            path=f"per_question[{idx}].{field_name}",
                        )
                    )
                total += float(weight)
            if total == total and abs(total - 1.0) > DISTRIBUTION_SUM_TOLERANCE:
                issues.append(
                    Issue(
                        code="DIST_SUM",
                        severity=Severity.ERROR,
                        message=(
                            f"distribution sums to {total:.6f}, expected 1.0 "
                            f"(±{DISTRIBUTION_SUM_TOLERANCE})"
                        ),
                        path=f"per_question[{idx}].{field_name}",
                    )
                )
    return issues


def _validate_question_set_hash(
    data: Mapping[str, Any],
    expected_hash: str | None,
) -> list[Issue]:
    """Verify that reported and recomputed question-set hashes match.

    Also cross-checks against a known-good hash for the dataset, when
    one is supplied by the caller.
    """

    issues: list[Issue] = []
    per_question = data.get("per_question") or []
    if not isinstance(per_question, list):
        return issues

    keys = [q.get("key") for q in per_question if isinstance(q, dict)]
    if len(keys) != len(per_question) or any(k is None for k in keys):
        return issues

    recomputed = question_set_hash(keys)

    config = data.get("config") or {}
    aggregate = data.get("aggregate") or {}
    reported = config.get("question_set_hash") or aggregate.get("question_set_hash")

    if reported is not None and reported != recomputed:
        issues.append(
            Issue(
                code="QSET_HASH",
                severity=Severity.ERROR,
                message=(
                    f"question_set_hash {reported} does not match recomputed "
                    f"{recomputed}"
                ),
                path="config.question_set_hash",
            )
        )

    if expected_hash is not None and recomputed != expected_hash:
        issues.append(
            Issue(
                code="QSET_HASH_DATASET",
                severity=Severity.ERROR,
                message=(
                    f"question set hash {recomputed} does not match the "
                    f"canonical dataset hash {expected_hash}"
                ),
                path="per_question",
            )
        )
    return issues


def _validate_counts(data: Mapping[str, Any]) -> list[Issue]:
    """Cross-check aggregate.n_questions vs len(per_question)."""

    issues: list[Issue] = []
    aggregate = data.get("aggregate") or {}
    per_question = data.get("per_question") or []
    reported = aggregate.get("n_questions")
    actual = len(per_question) if isinstance(per_question, list) else 0
    if isinstance(reported, int) and reported != actual:
        issues.append(
            Issue(
                code="COUNT_MISMATCH",
                severity=Severity.ERROR,
                message=(
                    f"aggregate.n_questions={reported} disagrees with "
                    f"len(per_question)={actual}"
                ),
                path="aggregate.n_questions",
            )
        )
    return issues


def _validate_parse_failure_plausibility(
    data: Mapping[str, Any],
) -> list[Issue]:
    """Warn when reported parse-failure rates look implausibly clean.

    A legitimate run on a non-trivial dataset with >=500 samples that
    never encounters a single parse failure is suspicious — not wrong,
    just worth flagging for manual review.
    """

    issues: list[Issue] = []
    per_question = data.get("per_question") or []
    if not isinstance(per_question, list) or not per_question:
        return issues

    config = data.get("config") or {}
    provider = str(config.get("provider", ""))
    if "baseline" in provider or provider.startswith("ensemble/"):
        return issues

    total_samples = 0
    total_failures = 0
    for q in per_question:
        if not isinstance(q, dict):
            continue
        n_samples = q.get("n_samples", 0) or 0
        n_parse_failures = q.get("n_parse_failures", 0) or 0
        if _is_number(n_samples):
            total_samples += int(n_samples)
        if _is_number(n_parse_failures):
            total_failures += int(n_parse_failures)

    if total_samples >= 500 and total_failures == 0 and len(per_question) >= 50:
        issues.append(
            Issue(
                code="PARSE_SUSPICIOUS",
                severity=Severity.WARNING,
                message=(
                    f"zero parse failures across {total_samples} samples on "
                    f"{len(per_question)} questions — verify parse pipeline"
                ),
                path="per_question",
            )
        )
    return issues


# ---------------------------------------------------------------------------
# Tier 2: recomputation verification
# ---------------------------------------------------------------------------


def _close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def _recompute_per_question(q: Mapping[str, Any]) -> tuple[float, float]:
    """Recompute (JSD, Kendall's tau) from the distributions in a question."""

    human = q.get("human_distribution") or {}
    model = q.get("model_distribution") or {}
    return (
        jensen_shannon_divergence(human, model),
        kendall_tau_b(human, model),
    )


def _validate_per_question_metrics(data: Mapping[str, Any]) -> list[Issue]:
    """Recompute each question's JSD / tau and compare to reported values."""

    issues: list[Issue] = []
    per_question = data.get("per_question") or []
    for idx, q in enumerate(per_question):
        if not isinstance(q, dict):
            continue
        reported_jsd = q.get("jsd")
        reported_tau = q.get("kendall_tau")
        if not _is_number(reported_jsd) or not _is_number(reported_tau):
            continue
        try:
            recomputed_jsd, recomputed_tau = _recompute_per_question(q)
        except Exception as exc:
            issues.append(
                Issue(
                    code="RECOMPUTE_ERROR",
                    severity=Severity.ERROR,
                    message=f"failed to recompute metrics: {exc}",
                    path=f"per_question[{idx}]",
                )
            )
            continue

        if not _close(recomputed_jsd, float(reported_jsd), METRIC_RECOMPUTE_TOLERANCE):
            issues.append(
                Issue(
                    code="PER_Q_JSD",
                    severity=Severity.ERROR,
                    message=(
                        f"reported jsd={reported_jsd}, recomputed {recomputed_jsd:.6f}"
                    ),
                    path=f"per_question[{idx}].jsd",
                )
            )
        if not _close(recomputed_tau, float(reported_tau), METRIC_RECOMPUTE_TOLERANCE):
            issues.append(
                Issue(
                    code="PER_Q_TAU",
                    severity=Severity.ERROR,
                    message=(
                        f"reported kendall_tau={reported_tau}, recomputed "
                        f"{recomputed_tau:.6f}"
                    ),
                    path=f"per_question[{idx}].kendall_tau",
                )
            )
    return issues


def _validate_aggregate_recomputation(data: Mapping[str, Any]) -> list[Issue]:
    """Recompute mean JSD, mean tau, composite_parity, SPS components.

    The tolerance here is looser than per-question because published
    files round to 6 decimals, which compounds over hundreds of terms.
    """

    issues: list[Issue] = []
    aggregate = data.get("aggregate") or {}
    scores = data.get("scores") or {}
    per_question = data.get("per_question") or []
    if not isinstance(per_question, list) or not per_question:
        return issues

    jsd_vals = [q.get("jsd") for q in per_question if isinstance(q, dict)]
    tau_vals = [q.get("kendall_tau") for q in per_question if isinstance(q, dict)]
    jsd_vals = [float(v) for v in jsd_vals if _is_number(v)]
    tau_vals = [float(v) for v in tau_vals if _is_number(v)]
    if not jsd_vals or not tau_vals or len(jsd_vals) != len(tau_vals):
        return issues

    n = len(jsd_vals)
    recomputed_mean_jsd = sum(jsd_vals) / n
    recomputed_mean_tau = sum(tau_vals) / n
    recomputed_p_dist = 1.0 - recomputed_mean_jsd
    recomputed_p_rank = (1.0 + recomputed_mean_tau) / 2.0

    reported_mean_jsd = aggregate.get("mean_jsd")
    reported_mean_tau = aggregate.get("mean_kendall_tau")
    reported_composite = aggregate.get("composite_parity")

    if _is_number(reported_mean_jsd) and not _close(
        float(reported_mean_jsd), recomputed_mean_jsd, AGGREGATE_RECOMPUTE_TOLERANCE
    ):
        issues.append(
            Issue(
                code="AGG_MEAN_JSD",
                severity=Severity.ERROR,
                message=(
                    f"aggregate.mean_jsd={reported_mean_jsd} does not match "
                    f"recomputed {recomputed_mean_jsd:.6f}"
                ),
                path="aggregate.mean_jsd",
            )
        )
    if _is_number(reported_mean_tau) and not _close(
        float(reported_mean_tau), recomputed_mean_tau, AGGREGATE_RECOMPUTE_TOLERANCE
    ):
        issues.append(
            Issue(
                code="AGG_MEAN_TAU",
                severity=Severity.ERROR,
                message=(
                    f"aggregate.mean_kendall_tau={reported_mean_tau} does not "
                    f"match recomputed {recomputed_mean_tau:.6f}"
                ),
                path="aggregate.mean_kendall_tau",
            )
        )

    # composite_parity is equivalent to either (a) a two-metric parity blend
    # of JSD + tau, or (b) the full SPS mean. We accept either convention
    # because the code base has historically used both.
    parity_two = 0.5 * recomputed_p_dist + 0.5 * recomputed_p_rank
    if _is_number(reported_composite):
        reported = float(reported_composite)
        sps_components: dict[str, float] = {
            "p_dist": recomputed_p_dist,
            "p_rank": recomputed_p_rank,
        }
        refuse_vals: list[float] = []
        human_refuse_vals: list[float] = []
        for q in per_question:
            if not isinstance(q, dict):
                continue
            m = q.get("model_refusal_rate")
            h = q.get("human_refusal_rate")
            if _is_number(m) and _is_number(h):
                refuse_vals.append(float(m))
                human_refuse_vals.append(float(h))
        if refuse_vals and len(refuse_vals) == len(human_refuse_vals):
            sps_components["p_refuse"] = refusal_calibration(
                refuse_vals, human_refuse_vals
            )
        parity_sps = synthbench_parity_score(sps_components)

        if not any(
            _close(reported, candidate, AGGREGATE_RECOMPUTE_TOLERANCE)
            for candidate in (parity_two, parity_sps)
        ):
            issues.append(
                Issue(
                    code="AGG_COMPOSITE",
                    severity=Severity.ERROR,
                    message=(
                        f"aggregate.composite_parity={reported} matches neither "
                        f"the 2-metric blend ({parity_two:.6f}) nor the SPS "
                        f"mean ({parity_sps:.6f})"
                    ),
                    path="aggregate.composite_parity",
                )
            )

    # scores.p_dist / p_rank cross-check
    for key, expected in (
        ("p_dist", recomputed_p_dist),
        ("p_rank", recomputed_p_rank),
    ):
        reported = scores.get(key)
        if _is_number(reported) and not _close(
            float(reported), expected, AGGREGATE_RECOMPUTE_TOLERANCE
        ):
            issues.append(
                Issue(
                    code="SCORES_SUB",
                    severity=Severity.ERROR,
                    message=(
                        f"scores.{key}={reported} disagrees with recomputed "
                        f"{expected:.6f}"
                    ),
                    path=f"scores.{key}",
                )
            )
    return issues


# ---------------------------------------------------------------------------
# Tier 3: raw-response samples + reproducibility metadata
# ---------------------------------------------------------------------------


def _validate_raw_responses(data: Mapping[str, Any]) -> list[Issue]:
    """Check for raw model output samples attached to the submission.

    A legitimate submission carries a ``raw_responses`` list where each
    entry looks like::

        {"key": "Q_001", "raw_text": "...", "selected_option": "A"}

    At least :data:`RAW_RESPONSE_MIN_COVERAGE` share of questions must
    have a sample. Each sample's raw text must be a non-empty string
    within length bounds, and its selected option must agree with the
    top option of the reported ``model_distribution`` (ties allowed).

    Missing or malformed raw samples surface as WARNINGS so existing
    leaderboard files without the field still validate. Once the
    ecosystem has migrated, the bead plans to graduate this to ERROR.
    """
    issues: list[Issue] = []
    per_question = data.get("per_question") or []
    if not isinstance(per_question, list) or not per_question:
        return issues

    raw_responses = data.get("raw_responses")
    if raw_responses is None:
        issues.append(
            Issue(
                code="RAW_RESPONSES_MISSING",
                severity=Severity.WARNING,
                message=(
                    "submission has no 'raw_responses' field — required "
                    "for Tier-3 integrity review once schema version "
                    "graduates (see SUBMISSIONS.md)"
                ),
                path="raw_responses",
            )
        )
        return issues

    if not isinstance(raw_responses, list):
        issues.append(
            Issue(
                code="RAW_RESPONSES_TYPE",
                severity=Severity.WARNING,
                message="'raw_responses' must be a list of samples",
                path="raw_responses",
            )
        )
        return issues

    # Coverage check: fraction of questions that carry a sample.
    total_questions = len(per_question)
    min_required = max(1, int(math.ceil(total_questions * RAW_RESPONSE_MIN_COVERAGE)))
    if len(raw_responses) < min_required:
        issues.append(
            Issue(
                code="RAW_RESPONSES_COVERAGE",
                severity=Severity.WARNING,
                message=(
                    f"raw_responses has {len(raw_responses)} entries but "
                    f"{total_questions} questions require at least "
                    f"{min_required} samples "
                    f"({RAW_RESPONSE_MIN_COVERAGE:.0%} coverage)"
                ),
                path="raw_responses",
            )
        )

    # Per-sample shape, length, and mode-agreement checks.
    model_dist_by_key: dict[str, Mapping[str, Any]] = {}
    for q in per_question:
        if not isinstance(q, dict):
            continue
        key = q.get("key")
        dist = q.get("model_distribution")
        if isinstance(key, str) and isinstance(dist, dict):
            model_dist_by_key[key] = dist

    lengths: list[int] = []
    for idx, sample in enumerate(raw_responses):
        if not isinstance(sample, dict):
            issues.append(
                Issue(
                    code="RAW_RESPONSES_SHAPE",
                    severity=Severity.WARNING,
                    message="raw_responses entry must be an object",
                    path=f"raw_responses[{idx}]",
                )
            )
            continue
        key = sample.get("key")
        raw_text = sample.get("raw_text")
        selected = sample.get("selected_option")

        if not isinstance(key, str) or not key:
            issues.append(
                Issue(
                    code="RAW_RESPONSES_SHAPE",
                    severity=Severity.WARNING,
                    message="raw_responses entry missing string 'key'",
                    path=f"raw_responses[{idx}].key",
                )
            )
            continue
        if not isinstance(raw_text, str) or not raw_text.strip():
            issues.append(
                Issue(
                    code="RAW_RESPONSES_EMPTY",
                    severity=Severity.WARNING,
                    message="raw_text is missing or empty",
                    path=f"raw_responses[{idx}].raw_text",
                )
            )
            continue

        length = len(raw_text)
        lengths.append(length)
        if length > RAW_RESPONSE_MAX_LENGTH:
            issues.append(
                Issue(
                    code="RAW_RESPONSES_LENGTH",
                    severity=Severity.WARNING,
                    message=(
                        f"raw_text length {length} exceeds {RAW_RESPONSE_MAX_LENGTH}"
                    ),
                    path=f"raw_responses[{idx}].raw_text",
                )
            )

        # Mode-agreement: the selected option should be in the top set of
        # the reported model_distribution. We accept any option that is
        # tied for the max probability (within 1e-6).
        dist = model_dist_by_key.get(key)
        if dist is not None and isinstance(selected, str) and dist:
            numeric_items = [
                (opt, float(val)) for opt, val in dist.items() if _is_number(val)
            ]
            if numeric_items:
                top = max(p for _, p in numeric_items)
                top_opts = {opt for opt, p in numeric_items if abs(p - top) <= 1e-6}
                if selected not in top_opts:
                    issues.append(
                        Issue(
                            code="RAW_RESPONSES_MODE",
                            severity=Severity.WARNING,
                            message=(
                                f"selected_option {selected!r} not in top-"
                                f"probability set {sorted(top_opts)} of "
                                f"model_distribution for {key}"
                            ),
                            path=f"raw_responses[{idx}].selected_option",
                        )
                    )

    # Length-distribution sanity: catch the "all 1-char" / "all 10k-char"
    # fabricator that doesn't bother writing plausible model output.
    if lengths:
        short = sum(1 for length in lengths if length <= RAW_RESPONSE_MIN_LENGTH)
        long_ = sum(1 for length in lengths if length >= RAW_RESPONSE_MAX_LENGTH)
        n = len(lengths)
        if short / n >= RAW_RESPONSE_SHORT_FRACTION_LIMIT:
            issues.append(
                Issue(
                    code="RAW_RESPONSES_LENGTH_SHORT",
                    severity=Severity.WARNING,
                    message=(
                        f"{short}/{n} raw_responses are <= "
                        f"{RAW_RESPONSE_MIN_LENGTH} char(s) — suspiciously "
                        f"short for natural model output"
                    ),
                    path="raw_responses",
                )
            )
        if long_ / n >= RAW_RESPONSE_LONG_FRACTION_LIMIT:
            issues.append(
                Issue(
                    code="RAW_RESPONSES_LENGTH_LONG",
                    severity=Severity.WARNING,
                    message=(
                        f"{long_}/{n} raw_responses are >= "
                        f"{RAW_RESPONSE_MAX_LENGTH} chars — suspicious"
                    ),
                    path="raw_responses",
                )
            )

    return issues


def _validate_reproducibility_metadata(data: Mapping[str, Any]) -> list[Issue]:
    """Warn when reproducibility metadata fields are missing or malformed.

    Submissions should carry a ``reproducibility`` block containing
    :data:`REQUIRED_REPRODUCIBILITY` fields. Each missing or blank field
    surfaces a separate warning so the reviewer sees exactly which
    piece of metadata needs to be filled in.
    """
    issues: list[Issue] = []
    repro = data.get("reproducibility")

    if repro is None:
        issues.append(
            Issue(
                code="REPRO_MISSING",
                severity=Severity.WARNING,
                message=(
                    "submission has no 'reproducibility' block — required "
                    "for Tier-3 spot-check auditing (see SUBMISSIONS.md)"
                ),
                path="reproducibility",
            )
        )
        return issues

    if not isinstance(repro, dict):
        issues.append(
            Issue(
                code="REPRO_TYPE",
                severity=Severity.WARNING,
                message="'reproducibility' must be an object",
                path="reproducibility",
            )
        )
        return issues

    for field_name in REQUIRED_REPRODUCIBILITY:
        if field_name not in repro:
            issues.append(
                Issue(
                    code="REPRO_FIELD_MISSING",
                    severity=Severity.WARNING,
                    message=f"reproducibility.{field_name} is required",
                    path=f"reproducibility.{field_name}",
                )
            )
            continue
        value = repro[field_name]
        if field_name == "seed":
            if value is not None and not isinstance(value, (int, float)):
                issues.append(
                    Issue(
                        code="REPRO_FIELD_TYPE",
                        severity=Severity.WARNING,
                        message="reproducibility.seed must be numeric or null",
                        path="reproducibility.seed",
                    )
                )
        elif not isinstance(value, str) or not value.strip():
            issues.append(
                Issue(
                    code="REPRO_FIELD_EMPTY",
                    severity=Severity.WARNING,
                    message=(
                        f"reproducibility.{field_name} must be a non-empty string"
                    ),
                    path=f"reproducibility.{field_name}",
                )
            )
    return issues


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def validate_submission(
    data: Any,
    *,
    source: str = "<memory>",
    expected_question_hash: str | None = None,
    tier1: bool = True,
    tier2: bool = True,
    tier3: bool = False,
    peers: Iterable[Mapping[str, Any]] = (),
) -> ValidationReport:
    """Run the configured tiers of validation against a submission.

    Args:
        data: Decoded submission JSON (typically a ``dict``).
        source: Human-readable identifier used in the report header.
        expected_question_hash: Optional canonical question-set hash; when
            supplied, the submission's keys must hash to this value.
        tier1: When ``True``, run tier 1 (schema + plausibility).
        tier2: When ``True``, run tier 2 (recomputation). Tier 2 is only
            useful when the schema gate passes, so it is skipped if tier 1
            surfaces any errors.
        tier3: When ``True``, run tier 3 (statistical anomaly detection,
            raw-response samples, reproducibility metadata). Tier 3
            issues are WARNINGS by default — enable ``--strict`` at the
            CLI to fail the run on any warning.
        peers: Optional iterable of peer submission dicts used by the
            peer-distribution outlier detector. Ignored outside tier 3.
    """

    report = ValidationReport(source=source)

    if tier1:
        report.extend(_validate_schema(data))
        if report.errors:
            return report
        mapping: Mapping[str, Any] = data  # type: ignore[assignment]
        report.extend(_validate_bounds(mapping))
        report.extend(_validate_distributions(mapping))
        report.extend(_validate_counts(mapping))
        report.extend(_validate_question_set_hash(mapping, expected_question_hash))
        report.extend(_validate_parse_failure_plausibility(mapping))

    if tier2 and not report.errors and isinstance(data, dict):
        report.extend(_validate_per_question_metrics(data))
        report.extend(_validate_aggregate_recomputation(data))

    if tier3 and isinstance(data, dict):
        # Import here to avoid a module-load cycle: anomaly.py imports
        # Issue/Severity from this module.
        from synthbench.anomaly import tier3_checks

        mapping: Mapping[str, Any] = data  # type: ignore[assignment]
        report.extend(_validate_raw_responses(mapping))
        report.extend(_validate_reproducibility_metadata(mapping))
        report.extend(tier3_checks(mapping, peers=peers))

    return report


def validate_file(
    path: str | Path,
    *,
    expected_question_hash: str | None = None,
    tier1: bool = True,
    tier2: bool = True,
    tier3: bool = False,
    peers: Iterable[Mapping[str, Any]] = (),
) -> ValidationReport:
    """Load a JSON file and validate it. Errors are wrapped as report issues."""

    import json

    p = Path(path)
    report = ValidationReport(source=str(p))
    try:
        data = json.loads(p.read_text())
    except FileNotFoundError:
        report.issues.append(
            Issue(
                code="IO_MISSING",
                severity=Severity.ERROR,
                message=f"file not found: {p}",
            )
        )
        return report
    except json.JSONDecodeError as exc:
        report.issues.append(
            Issue(
                code="IO_DECODE",
                severity=Severity.ERROR,
                message=f"invalid JSON: {exc}",
            )
        )
        return report

    return validate_submission(
        data,
        source=str(p),
        expected_question_hash=expected_question_hash,
        tier1=tier1,
        tier2=tier2,
        tier3=tier3,
        peers=peers,
    )
