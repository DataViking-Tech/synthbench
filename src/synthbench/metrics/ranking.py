"""Ranking agreement metrics."""

from __future__ import annotations

from scipy.stats import kendalltau


def kendall_tau_b(
    p: dict[str, float], q: dict[str, float]
) -> float:
    """Compute Kendall's tau-b rank correlation between two distributions.

    Measures whether the model ranks options in the same order as humans.
    Returns tau in [-1, 1]. Higher means better agreement.
    +1 = perfect agreement, 0 = no correlation, -1 = perfect reversal.

    With fewer than 2 comparable options, returns 0.0.

    Args:
        p: First distribution (e.g., human).
        q: Second distribution (e.g., model).

    Returns:
        Kendall's tau-b correlation coefficient.
    """
    keys = sorted(set(p) | set(q))
    if len(keys) < 2:
        return 0.0

    p_vals = [p.get(k, 0.0) for k in keys]
    q_vals = [q.get(k, 0.0) for k in keys]

    tau, _pvalue = kendalltau(p_vals, q_vals, variant="b")

    # kendalltau returns nan for constant inputs
    if tau != tau:  # NaN check
        return 0.0

    return float(tau)
