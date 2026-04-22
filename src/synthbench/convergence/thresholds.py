"""Find the smallest sample size at which a convergence curve has stabilized.

"Convergence n" is the smallest n such that:
  1. jsd_mean(n) falls below epsilon, AND
  2. the curve has flattened -- no subsequent n within the next two sample
     points lowers jsd_mean by more than delta.

Requires at least two points after the candidate n to evaluate the flat tail,
so curves shorter than that can only return None.
"""

from __future__ import annotations

from typing import Iterable

from synthbench.convergence.curves import CurvePoint

DEFAULT_EPSILON: float = 0.02
DEFAULT_DELTA: float = 0.005


def find_convergence_n(
    curve: Iterable[CurvePoint],
    epsilon: float = DEFAULT_EPSILON,
    delta: float = DEFAULT_DELTA,
) -> int | None:
    """Return the smallest n where the curve stabilizes below epsilon.

    Args:
        curve: Sequence of :class:`CurvePoint` ordered by increasing n.
        epsilon: JSD mean ceiling. Point qualifies only if jsd_mean < epsilon.
        delta: Maximum allowed drop in jsd_mean across the next two sample
            points. A larger drop means the curve is still descending.

    Returns:
        The n at the first qualifying point, or None if no such point exists.
    """
    points = list(curve)
    for i, point in enumerate(points):
        if point.jsd_mean >= epsilon:
            continue
        tail = points[i + 1 : i + 3]
        if len(tail) < 2:
            return None
        drops = [point.jsd_mean - later.jsd_mean for later in tail]
        if max(drops) > delta:
            continue
        return point.n
    return None
