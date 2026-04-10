"""Conditioning fidelity metric (P_cond)."""

from __future__ import annotations


def conditioning_fidelity(
    conditioned_scores: dict[str, float],
    default_scores: dict[str, float],
) -> float:
    """Compute conditioning fidelity: P_cond = mean(max(0, cond - default)).

    Measures how much persona conditioning improves alignment with the
    target demographic. The improvement is floored at 0 per group —
    if conditioning makes alignment worse, the provider gets no credit
    for that group.

    Args:
        conditioned_scores: Mapping of group name to alignment score
            (e.g., P_dist) when persona conditioning is applied.
        default_scores: Mapping of group name to alignment score
            when no persona conditioning is applied (default prompt).

    Returns:
        P_cond in [0, 1]. Higher = conditioning provides more improvement.
        Returns 0.0 if no common groups found.
    """
    common_groups = set(conditioned_scores) & set(default_scores)
    if not common_groups:
        return 0.0

    improvements = [
        max(0.0, conditioned_scores[g] - default_scores[g])
        for g in common_groups
    ]

    return sum(improvements) / len(improvements)
