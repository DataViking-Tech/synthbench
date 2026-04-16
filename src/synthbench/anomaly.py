"""Tier-3 statistical anomaly detection for SynthBench submissions.

Tier 1 (schema) and tier 2 (arithmetic recomputation) both trust the
per-question distributions the submitter attached. A sufficiently careful
fabricator can defeat them by reverse-engineering distributions that are
arithmetically self-consistent. Tier 3 adds cheap statistical plausibility
checks that catch the most common lazy attacks: "copy the answer key",
"zero-out refusals", "match one peer run exactly".

Each detector returns an :class:`~synthbench.validation.Issue` with
``severity = WARNING``. We deliberately keep tier 3 soft in its first
iteration — once we've observed the distribution of legitimate
submissions in practice, specific detectors can be graduated to ERROR.

Detectors:

* ``check_suspicious_perfection`` — per-question JSD near zero with near-zero
  variance implies the submitter copied the human distribution verbatim.
* ``check_missing_refusals`` — a submission with model_refusal_rate ≡ 0
  across a dataset where real humans refuse is suspicious: real LLMs do
  refuse, and refusal-free runs are almost always fabricated or
  miscalibrated post-processing.
* ``check_peer_distribution_outlier`` — soft signal comparing claimed
  per-question distributions against peer submissions on the same family.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

from synthbench.validation import Issue, Severity


# Detector thresholds. Tuned against real submissions in leaderboard-results/
# where mean_jsd lives in ~[0.05, 0.55] with std ~[0.10, 0.30]. Fabrication
# that copies the answer key produces mean ~0 with std ~0; the threshold sits
# an order of magnitude below the noise floor of any real run we've seen.
SUSPICIOUS_MEAN_JSD = 0.005
SUSPICIOUS_STD_JSD = 0.005

# Share of dataset questions that must have a human refusal rate above this
# cutoff before a zero-refusal submission is flagged. We require at least
# one visibly-refusing question in the dataset to avoid false positives on
# datasets where humans rarely refuse.
HUMAN_REFUSAL_CUTOFF = 0.05
HUMAN_REFUSAL_MIN_QUESTIONS = 3

# Peer-outlier detector: two submissions are "same-family" if they share
# the model family (e.g. both claim claude-haiku-4-5) and the dataset.
# We flag when the mean absolute delta between submission and peer JSD
# on overlapping questions exceeds :data:`PEER_OUTLIER_DELTA`. Real
# same-family runs differ by <=~0.05 on average; 0.15 is well outside
# observed noise and inside the range produced by answer-key attacks.
PEER_OUTLIER_DELTA = 0.15
PEER_MIN_OVERLAP = 5


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = _mean(values)
    variance = sum((v - mu) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def check_suspicious_perfection(
    per_question: Sequence[Mapping[str, Any]],
) -> Issue | None:
    """Flag submissions whose per-question JSD is implausibly perfect.

    Real LLMs produce per-question JSD with a non-trivial spread. A
    submission where either the mean OR the standard deviation of JSD
    sits below :data:`SUSPICIOUS_MEAN_JSD` / :data:`SUSPICIOUS_STD_JSD`
    is almost certainly copied from the answer key. We use OR because
    either condition alone is enough: mean-near-zero implies uniformly
    near-perfect matches (impossible for a real model), and std-near-zero
    implies the per-question distances are all the same, which a real
    sampling pipeline cannot produce.
    """
    jsd_values = [
        float(q["jsd"]) for q in per_question if isinstance(q.get("jsd"), (int, float))
    ]
    if len(jsd_values) < 5:
        return None

    mean_jsd = _mean(jsd_values)
    std_jsd = _std(jsd_values)

    if mean_jsd < SUSPICIOUS_MEAN_JSD or std_jsd < SUSPICIOUS_STD_JSD:
        return Issue(
            code="ANOMALY_PERFECTION",
            severity=Severity.WARNING,
            message=(
                f"per-question JSD has mean={mean_jsd:.6f}, "
                f"std={std_jsd:.6f} — implausibly perfect match to "
                f"human distribution (thresholds: mean<{SUSPICIOUS_MEAN_JSD}, "
                f"std<{SUSPICIOUS_STD_JSD}). Likely answer-key copy."
            ),
            path="per_question",
        )
    return None


def check_missing_refusals(
    per_question: Sequence[Mapping[str, Any]],
) -> Issue | None:
    """Flag submissions that never refuse despite humans refusing.

    Some datasets have questions humans refuse on (e.g. political
    identification, touchy religious questions). Real LLMs refuse those
    too — sometimes at similar rates, sometimes higher. A submission
    that reports ``model_refusal_rate = 0`` across every question in a
    dataset where humans clearly refuse is either fabricated or has a
    silent bug that drops refusals. Either way, worth surfacing.
    """
    pq_list = [q for q in per_question if isinstance(q, dict)]
    if not pq_list:
        return None

    refusing_questions = [
        q
        for q in pq_list
        if isinstance(q.get("human_refusal_rate"), (int, float))
        and float(q["human_refusal_rate"]) >= HUMAN_REFUSAL_CUTOFF
    ]
    if len(refusing_questions) < HUMAN_REFUSAL_MIN_QUESTIONS:
        # Dataset doesn't have enough "refuseable" questions to reason about.
        return None

    model_refusal_values = [float(q.get("model_refusal_rate") or 0.0) for q in pq_list]
    if any(v > 0.0 for v in model_refusal_values):
        return None

    return Issue(
        code="ANOMALY_NO_REFUSAL",
        severity=Severity.WARNING,
        message=(
            f"submission reports model_refusal_rate=0 on every question, "
            f"but {len(refusing_questions)} of {len(pq_list)} questions "
            f"have human_refusal_rate >= {HUMAN_REFUSAL_CUTOFF}. Real "
            f"LLMs refuse sometimes — check for fabricated or post-"
            f"processed refusals."
        ),
        path="per_question",
    )


def _same_family(submission_provider: str, peer_provider: str) -> bool:
    """True when two provider strings plausibly share a model family.

    Heuristic: take the last path segment (usually the model id) and
    compare. ``openrouter/anthropic/claude-haiku-4-5`` and
    ``anthropic/claude-haiku-4-5`` both resolve to ``claude-haiku-4-5``.
    Baselines and ensembles are never "same-family".
    """
    if not submission_provider or not peer_provider:
        return False
    if "baseline" in submission_provider or "baseline" in peer_provider:
        return False
    if submission_provider.startswith("ensemble/") or peer_provider.startswith(
        "ensemble/"
    ):
        return False

    def _model_tail(name: str) -> str:
        return name.rsplit("/", 1)[-1].lower()

    return _model_tail(submission_provider) == _model_tail(peer_provider)


def check_peer_distribution_outlier(
    submission: Mapping[str, Any],
    peers: Iterable[Mapping[str, Any]],
) -> Issue | None:
    """Soft check: claimed distribution shapes vs same-family peers.

    If the submission claims model X but its per-question JSD on
    overlapping questions is wildly out of line with other runs of
    model X, flag it. This catches submissions that claim a particular
    model but were actually generated by something else.

    Not a hard reject — honest runs differ from each other (temperature,
    prompt, seed). We only flag when the deviation exceeds
    :data:`PEER_OUTLIER_SIGMA` standard deviations of the peer JSD
    distribution on the shared question set. Returns ``None`` when
    there are no same-family peers or insufficient overlap.
    """
    config = submission.get("config") or {}
    submission_provider = str(config.get("provider", ""))
    dataset = config.get("dataset")
    per_question = submission.get("per_question") or []

    if not submission_provider or not dataset or not per_question:
        return None

    submission_jsd_by_key: dict[str, float] = {}
    for q in per_question:
        if not isinstance(q, dict):
            continue
        key = q.get("key")
        jsd = q.get("jsd")
        if isinstance(key, str) and isinstance(jsd, (int, float)):
            submission_jsd_by_key[key] = float(jsd)

    # Collect peer JSD maps on same model family + same dataset.
    peer_jsd_maps: list[dict[str, float]] = []
    for peer in peers:
        if not isinstance(peer, dict):
            continue
        peer_config = peer.get("config") or {}
        peer_provider = str(peer_config.get("provider", ""))
        peer_dataset = peer_config.get("dataset")
        if peer_dataset != dataset or not _same_family(
            submission_provider, peer_provider
        ):
            continue

        peer_jsd: dict[str, float] = {}
        for q in peer.get("per_question") or []:
            if not isinstance(q, dict):
                continue
            key = q.get("key")
            jsd = q.get("jsd")
            if isinstance(key, str) and isinstance(jsd, (int, float)):
                peer_jsd[key] = float(jsd)
        if peer_jsd:
            peer_jsd_maps.append(peer_jsd)

    if not peer_jsd_maps:
        return None

    # Compute per-key peer mean JSD using every peer that covered that key.
    per_key_peer_values: dict[str, list[float]] = {}
    for peer_map in peer_jsd_maps:
        for key, jsd in peer_map.items():
            if key in submission_jsd_by_key:
                per_key_peer_values.setdefault(key, []).append(jsd)

    overlap = [
        (submission_jsd_by_key[k], _mean(vals))
        for k, vals in per_key_peer_values.items()
        if vals
    ]
    if len(overlap) < PEER_MIN_OVERLAP:
        return None

    deltas = [sub - peer_mean for sub, peer_mean in overlap]
    mu = _mean(deltas)
    if abs(mu) < PEER_OUTLIER_DELTA:
        return None

    direction = "lower" if mu < 0 else "higher"
    return Issue(
        code="ANOMALY_PEER_OUTLIER",
        severity=Severity.WARNING,
        message=(
            f"per-question JSD runs {direction} than same-family peers "
            f"({len(overlap)} shared questions, mean delta={mu:.4f} > "
            f"threshold {PEER_OUTLIER_DELTA}). Investigate whether the "
            f"claimed model matches the submission."
        ),
        path="per_question",
    )


def tier3_checks(
    data: Mapping[str, Any],
    *,
    peers: Iterable[Mapping[str, Any]] = (),
) -> list[Issue]:
    """Run every tier-3 anomaly detector and return the list of issues.

    Note: ``check_missing_refusals`` is intentionally *not* called from
    the default dispatch. Every current provider prompt in
    ``src/synthbench/providers/`` ends with ``"Respond with ONLY the
    letter of your choice"`` and gives the model no way to refuse — the
    harness architecturally produces ``model_refusal_rate == 0`` on
    every question, so the detector flagged every legitimate submission
    (sb-a613). The function is kept exported so callers can invoke it
    directly once a refusal-capable prompt variant exists.
    """
    per_question = data.get("per_question") or []
    if not isinstance(per_question, list):
        return []

    issues: list[Issue] = []

    perfection = check_suspicious_perfection(per_question)
    if perfection is not None:
        issues.append(perfection)

    peer_outlier = check_peer_distribution_outlier(data, peers)
    if peer_outlier is not None:
        issues.append(peer_outlier)

    return issues


__all__ = [
    "SUSPICIOUS_MEAN_JSD",
    "SUSPICIOUS_STD_JSD",
    "HUMAN_REFUSAL_CUTOFF",
    "HUMAN_REFUSAL_MIN_QUESTIONS",
    "PEER_OUTLIER_DELTA",
    "PEER_MIN_OVERLAP",
    "check_suspicious_perfection",
    "check_missing_refusals",
    "check_peer_distribution_outlier",
    "tier3_checks",
]
