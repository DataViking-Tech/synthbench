"""Distributional similarity metrics."""

from __future__ import annotations

import numpy as np
from scipy.spatial.distance import jensenshannon


def jensen_shannon_divergence(
    p: dict[str, float], q: dict[str, float]
) -> float:
    """Compute Jensen-Shannon divergence between two distributions.

    Both distributions must be over the same set of keys (options).
    Returns JSD in [0, 1] (using base-2 log, so max is 1.0).

    Args:
        p: First distribution (e.g., human).
        q: Second distribution (e.g., model).

    Returns:
        JSD value. Lower means more similar (0 = identical).
    """
    keys = sorted(set(p) | set(q))
    p_vec = np.array([p.get(k, 0.0) for k in keys], dtype=np.float64)
    q_vec = np.array([q.get(k, 0.0) for k in keys], dtype=np.float64)

    # Ensure valid distributions (non-negative, sum > 0)
    p_vec = np.maximum(p_vec, 0.0)
    q_vec = np.maximum(q_vec, 0.0)

    p_sum = p_vec.sum()
    q_sum = q_vec.sum()
    if p_sum == 0 or q_sum == 0:
        return 1.0

    p_vec /= p_sum
    q_vec /= q_sum

    # scipy's jensenshannon returns the *distance* (sqrt of divergence)
    # We want the divergence itself (JSD), so we square it.
    jsd = jensenshannon(p_vec, q_vec, base=2) ** 2
    return float(jsd)
