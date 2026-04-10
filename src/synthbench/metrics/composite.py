"""Composite parity score combining distributional and ranking metrics."""

from __future__ import annotations


def parity_score(
    jsd: float,
    tau: float,
    jsd_weight: float = 0.5,
    tau_weight: float = 0.5,
) -> float:
    """Compute composite parity score from JSD and Kendall's tau.

    Converts both metrics to a [0, 1] scale where 1 = perfect parity,
    then takes a weighted average.

    - JSD contribution: (1 - jsd), since JSD=0 means identical distributions
    - Tau contribution: (tau + 1) / 2, mapping [-1, 1] → [0, 1]

    Args:
        jsd: Jensen-Shannon divergence (0 to 1).
        tau: Kendall's tau-b (-1 to 1).
        jsd_weight: Weight for the JSD component.
        tau_weight: Weight for the tau component.

    Returns:
        Parity score in [0, 1]. Higher = better match to human distributions.
    """
    jsd_score = 1.0 - max(0.0, min(1.0, jsd))
    tau_score = (max(-1.0, min(1.0, tau)) + 1.0) / 2.0

    total_weight = jsd_weight + tau_weight
    return (jsd_weight * jsd_score + tau_weight * tau_score) / total_weight
