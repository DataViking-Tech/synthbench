"""Composite parity score combining distributional and ranking metrics."""

from __future__ import annotations

# The 5 Phase-1 SPS metrics in canonical order
SPS_METRICS = ("p_dist", "p_rank", "p_cond", "p_sub", "p_refuse")


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


def synthbench_parity_score(
    metrics: dict[str, float],
    weights: dict[str, float] | None = None,
) -> float:
    """Compute the SynthBench Parity Score (SPS) from available component metrics.

    Equal-weighted mean of available metrics (0.20 each in Phase 1 when all 5
    are present). When a metric can't be computed, it is excluded and the
    remaining metrics are reweighted to sum to 1.0.

    Args:
        metrics: Mapping of metric name to score. Keys should be from
            SPS_METRICS (p_dist, p_rank, p_cond, p_sub, p_refuse).
            Only present keys are included in the average.
        weights: Optional custom weights per metric. If None, equal weights.

    Returns:
        SPS in [0, 1]. Higher = better overall parity.
        Returns 0.0 if no metrics provided.
    """
    available = {k: v for k, v in metrics.items() if k in SPS_METRICS}
    if not available:
        return 0.0

    if weights is None:
        # Equal weighting across available metrics
        return sum(available.values()) / len(available)

    # Custom weights — only use weights for available metrics, then renormalize
    weighted_sum = sum(weights.get(k, 0.0) * v for k, v in available.items())
    total_weight = sum(weights.get(k, 0.0) for k in available)
    if total_weight == 0.0:
        return 0.0
    return weighted_sum / total_weight
