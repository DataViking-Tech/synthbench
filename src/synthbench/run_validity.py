"""Detect invalid benchmark runs (e.g. uniform-distribution API-failure garbage).

An "invalid" run is one whose per-question ``model_distribution`` fields are
overwhelmingly perfectly uniform (``{A: 0.25, B: 0.25, ...}`` for a 4-option
question), coupled with near-zero refusal activity. This is the signature of
a silent API failure — provider returned empty distributions, model alias
missed, budget exhaustion, synthpanel fallback — that still parsed cleanly
but produced no usable signal.

Existing ``parse_failure_rate`` tracking does NOT catch this class: the run
parses fine, it just contains pure noise. Publishing such runs to the
leaderboard inflates scores with fake results and undermines credibility.

The detector is intentionally strict — we would rather miss borderline cases
than false-flag a legitimate run with coincidentally-flat distributions.

Usage::

    from synthbench.run_validity import is_invalid_run

    invalid, reason, metrics = is_invalid_run(result_data)
    if invalid:
        print(f"skip: {reason}")
"""

from __future__ import annotations

from typing import Any, Mapping


# Per-question uniformity cutoff: a distribution is "uniform" if the maximum
# absolute deviation from the expected uniform value (1/n) is below this.
# 0.01 allows for trivial float rounding noise (e.g. 0.333 vs 0.3333) but
# excludes any real signal from a sampled distribution over 30+ samples.
UNIFORMITY_EPSILON = 0.01

# A run is invalid if at least this fraction of its questions have uniform
# distributions. Start strict (80%) — real runs with even weak signal fall
# well below this floor. Haiku-quality-or-better on SubPOP/GOQA produces
# ~0% uniform questions; the bad example (sb-knd reproducer) sits at exactly
# 80%. Using >= (not >) so the reproducer-profile is caught on the boundary.
UNIFORM_FRACTION_THRESHOLD = 0.8

# A run must also show negligible refusal signal — a model that truly refuses
# most questions is not "API failure garbage", it's a legitimate safety
# response pattern. A legitimate refusing model hits refusal_rate ~0.3+ (see
# check_missing_refusals thresholds in anomaly.py). The bad example shows
# mean ~0.012 (a single spurious 1.0 blip across 200 questions), so 0.05 is
# a comfortable gap between garbage and genuine refusal behaviour.
REFUSAL_RATE_THRESHOLD = 0.05

# Minimum number of questions required to evaluate validity. Very short runs
# (< 10 questions) don't give us enough statistical power to distinguish
# "uniform garbage" from "coincidentally flat but real" signal. Skip silently.
MIN_QUESTIONS_FOR_VALIDITY = 10


def uniformity_score(dist: Mapping[str, float] | None) -> float:
    """Return the maximum absolute deviation from perfect uniformity.

    ``0.0`` means the distribution is perfectly uniform (every bucket
    equals ``1/n``); larger values mean less uniform. An empty/missing
    distribution returns ``1.0`` (maximally non-uniform by convention —
    we don't flag it as uniform garbage).

    Examples
    --------
    >>> uniformity_score({"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25})
    0.0
    >>> round(uniformity_score({"A": 0.5, "B": 0.5}), 2)
    0.0
    >>> round(uniformity_score({"A": 1.0, "B": 0.0}), 2)
    0.5
    """
    if not dist:
        return 1.0
    n = len(dist)
    if n == 0:
        return 1.0
    expected = 1.0 / n
    try:
        return max(abs(float(v) - expected) for v in dist.values())
    except (TypeError, ValueError):
        return 1.0


def _per_question(data: Mapping[str, Any]) -> list[dict]:
    pq = data.get("per_question") if isinstance(data, Mapping) else None
    return list(pq) if isinstance(pq, list) else []


def compute_uniformity_metrics(
    data: Mapping[str, Any],
    *,
    uniformity_epsilon: float = UNIFORMITY_EPSILON,
) -> dict:
    """Summarise the uniformity / refusal profile of a run's per-question data.

    Returns a dict with keys:

    * ``n_questions``: total per-question entries
    * ``n_uniform_questions``: count whose ``model_distribution`` is within
      ``uniformity_epsilon`` of perfect uniformity
    * ``uniform_fraction``: ratio in ``[0, 1]`` (``0.0`` if n_questions == 0)
    * ``refusal_rate``: mean per-question ``model_refusal_rate`` (``0.0`` if
      missing or empty)

    Pure function: no I/O, no mutation of ``data``.
    """
    pq = _per_question(data)
    n_questions = len(pq)
    n_uniform = 0
    refusals: list[float] = []
    for q in pq:
        if not isinstance(q, Mapping):
            continue
        md = q.get("model_distribution")
        if uniformity_score(md) < uniformity_epsilon:
            n_uniform += 1
        r = q.get("model_refusal_rate")
        if isinstance(r, (int, float)):
            refusals.append(float(r))

    uniform_fraction = (n_uniform / n_questions) if n_questions else 0.0
    refusal_rate = (sum(refusals) / len(refusals)) if refusals else 0.0

    return {
        "n_questions": n_questions,
        "n_uniform_questions": n_uniform,
        "uniform_fraction": uniform_fraction,
        "refusal_rate": refusal_rate,
    }


def is_invalid_run(
    data: Mapping[str, Any],
    *,
    uniformity_epsilon: float = UNIFORMITY_EPSILON,
    uniform_fraction_threshold: float = UNIFORM_FRACTION_THRESHOLD,
    refusal_rate_threshold: float = REFUSAL_RATE_THRESHOLD,
    min_questions: int = MIN_QUESTIONS_FOR_VALIDITY,
) -> tuple[bool, str, dict]:
    """Classify a single run as invalid (API-failure garbage) or valid.

    Returns ``(is_invalid, reason, metrics)``. ``reason`` is an empty string
    when the run is valid. ``metrics`` is the dict returned by
    :func:`compute_uniformity_metrics` (always present, useful for
    downstream reporting even on valid runs).

    A run is flagged invalid when ALL of the following hold:

    1. ``n_questions >= min_questions`` (skip trivially small runs)
    2. ``uniform_fraction > uniform_fraction_threshold`` — the bulk of
       questions are perfectly uniform
    3. ``refusal_rate <= refusal_rate_threshold`` — the uniformity is not
       explained by legitimate refusals

    Any other state is treated as valid: low-uniformity runs, runs with
    genuine refusal patterns, and runs too small to evaluate all pass
    through untouched.
    """
    metrics = compute_uniformity_metrics(data, uniformity_epsilon=uniformity_epsilon)
    n = metrics["n_questions"]
    if n < min_questions:
        return False, "", metrics

    if metrics["uniform_fraction"] < uniform_fraction_threshold:
        return False, "", metrics

    if metrics["refusal_rate"] > refusal_rate_threshold:
        # Uniform-looking distribution explained by real refusals — not garbage.
        return False, "", metrics

    reason = (
        f"uniform-garbage: {metrics['n_uniform_questions']}/{n} questions "
        f"({metrics['uniform_fraction']:.1%}) have uniform model_distribution "
        f"with mean refusal_rate {metrics['refusal_rate']:.3f}"
    )
    return True, reason, metrics


def run_identity(data: Mapping[str, Any]) -> dict:
    """Return a minimal identity block for an invalid run (for reporting).

    Pulls ``provider``, ``dataset``, ``samples_per_question``, and
    ``n_evaluated`` from ``config`` plus the top-level ``timestamp``.
    Missing fields degrade to ``None`` rather than raising.
    """
    cfg = data.get("config") if isinstance(data, Mapping) else None
    cfg = cfg if isinstance(cfg, Mapping) else {}
    return {
        "provider": cfg.get("provider"),
        "dataset": cfg.get("dataset"),
        "samples_per_question": cfg.get("samples_per_question"),
        "n_evaluated": cfg.get("n_evaluated"),
        "timestamp": data.get("timestamp"),
    }
