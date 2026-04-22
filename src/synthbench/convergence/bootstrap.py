"""Multinomial sub-sampling primitives.

The aggregate ``human_distribution`` on a Question is the population proportion
vector. Drawing n responses from an i.i.d. population with that distribution is
a multinomial draw. This module provides the narrow primitives -- actual curve
computation lives in :mod:`synthbench.convergence.curves`.
"""

from __future__ import annotations

import numpy as np


def bootstrap_sample(
    distribution: dict[str, float],
    n: int,
    rng: np.random.Generator | None = None,
) -> dict[str, int]:
    """Draw a multinomial sample of size ``n`` from ``distribution``.

    Args:
        distribution: Option -> probability. Need not be exactly normalized --
            zero-sum inputs return an empty count vector.
        n: Number of responses to draw. Must be non-negative.
        rng: Optional numpy ``Generator`` for reproducibility. If omitted, a
            fresh default generator is used (non-deterministic).

    Returns:
        Option -> integer count. Counts sum to ``n`` when the input has positive
        mass; sum to 0 for an empty / zero-mass distribution.
    """
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    if rng is None:
        rng = np.random.default_rng()

    keys = list(distribution.keys())
    if not keys or n == 0:
        return {k: 0 for k in keys}

    probs = np.array([max(0.0, distribution[k]) for k in keys], dtype=np.float64)
    total = probs.sum()
    if total <= 0.0:
        return {k: 0 for k in keys}
    probs /= total

    counts = rng.multinomial(n, probs)
    return {k: int(c) for k, c in zip(keys, counts)}


def empirical_distribution(sample: dict[str, int]) -> dict[str, float]:
    """Normalize a count vector into an empirical distribution.

    Zero-total samples return a dict with the same keys but zero probabilities,
    preserving key alignment for downstream JSD.
    """
    total = sum(sample.values())
    if total <= 0:
        return {k: 0.0 for k in sample}
    return {k: v / total for k, v in sample.items()}
