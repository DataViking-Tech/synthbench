"""Refusal calibration metric (P_refuse)."""

from __future__ import annotations

import re

# Patterns that indicate an LLM-style refusal when explicit refusal field is unavailable
_REFUSAL_PATTERNS = [
    re.compile(r"\bI cannot\b", re.IGNORECASE),
    re.compile(r"\bI can't\b", re.IGNORECASE),
    re.compile(r"\bI don't\b", re.IGNORECASE),
    re.compile(r"\bAs an AI\b", re.IGNORECASE),
    re.compile(r"\bI'm not able to\b", re.IGNORECASE),
    re.compile(r"\bI am not able to\b", re.IGNORECASE),
]


def refusal_calibration(
    provider_refusal_rates: list[float],
    human_refusal_rates: list[float],
) -> float:
    """Compute refusal calibration: P_refuse = 1 - mean(|R_provider - R_human|).

    Measures whether the provider's refusal rate matches human refusal patterns.
    A provider that never refuses when humans sometimes do (or vice versa) gets
    a lower score.

    Args:
        provider_refusal_rates: Per-question refusal rates from the provider.
            Each value in [0, 1].
        human_refusal_rates: Per-question refusal rates from human data.
            Each value in [0, 1].

    Returns:
        P_refuse in [0, 1]. Higher = better calibrated refusals.
        Returns 1.0 if no questions provided.
    """
    if not provider_refusal_rates or not human_refusal_rates:
        return 1.0

    n = min(len(provider_refusal_rates), len(human_refusal_rates))
    total_diff = sum(
        abs(provider_refusal_rates[i] - human_refusal_rates[i]) for i in range(n)
    )
    mean_diff = total_diff / n

    return max(0.0, min(1.0, 1.0 - mean_diff))


def detect_refusal(text: str) -> bool:
    """Detect refusal from response text using common LLM refusal patterns.

    For providers without an explicit refusal field, this heuristic checks
    the raw response text for common refusal phrases.

    Args:
        text: Raw response text from the provider.

    Returns:
        True if the text appears to be a refusal.
    """
    return any(p.search(text) for p in _REFUSAL_PATTERNS)


def extract_human_refusal_rate(human_distribution: dict[str, float]) -> float:
    """Extract refusal rate from a human response distribution.

    Looks for option keys that indicate refusal (e.g., "Refused",
    "Don't know/Refused"). Returns the combined probability mass of
    refusal-like options.

    Args:
        human_distribution: Human response distribution for a question.

    Returns:
        Refusal rate in [0, 1].
    """
    refusal_keys = [
        k
        for k in human_distribution
        if isinstance(k, str)
        and (
            re.search(r"\brefused?\b", k, re.IGNORECASE)
            or re.search(r"\bdon'?t know\b", k, re.IGNORECASE)
        )
    ]
    return sum(human_distribution.get(k, 0.0) for k in refusal_keys)


def refusal_rate(dist: dict[str, float]) -> float:
    """Extract the explicit "Refused" option probability from a distribution.

    OpinionsQA includes "Refused" as an explicit answer option in 677 of 684
    questions. This function reads that option directly — no text parsing.

    Args:
        dist: Response distribution mapping option text to probability.

    Returns:
        Probability mass on the "Refused" option, or 0.0 if absent.
    """
    return dist.get("Refused", 0.0)


def p_refuse(
    model_dist: dict[str, float],
    human_dist: dict[str, float],
) -> float | None:
    """Per-question refusal calibration via the explicit "Refused" option.

    P_refuse_q = 1.0 - |refusal_rate(model) - refusal_rate(human)|

    For questions where neither distribution contains a "Refused" option,
    returns None (exclude from aggregate).

    Args:
        model_dist: Model response distribution for one question.
        human_dist: Human response distribution for one question.

    Returns:
        P_refuse in [0, 1], or None if the question has no "Refused" option.
    """
    has_refused = "Refused" in model_dist or "Refused" in human_dist
    if not has_refused:
        return None
    return 1.0 - abs(refusal_rate(model_dist) - refusal_rate(human_dist))
