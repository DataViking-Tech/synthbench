"""Convergence curve computation over a single aggregate distribution.

For each sample size n, draw B bootstrap samples from the aggregate
distribution, compute JSD(empirical_sample, full_distribution), and summarize
as {mean, p10, p90}. Plotting the mean against n yields the characteristic
~1/sqrt(n) curve that an idealized i.i.d. sampler would produce -- the
theoretical floor real samples must beat.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from synthbench.convergence.bootstrap import (
    bootstrap_sample,
    empirical_distribution,
)
from synthbench.metrics.distributional import jensen_shannon_divergence

DEFAULT_SAMPLE_SIZES: tuple[int, ...] = (
    20,
    50,
    100,
    200,
    500,
    1000,
    2000,
    5000,
    10000,
)
DEFAULT_BOOTSTRAP_B: int = 500


@dataclass(frozen=True)
class CurvePoint:
    """One sample-size slice of a convergence curve."""

    n: int
    jsd_mean: float
    jsd_p10: float
    jsd_p90: float
    bootstrap_B: int

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "jsd_mean": self.jsd_mean,
            "jsd_p10": self.jsd_p10,
            "jsd_p90": self.jsd_p90,
            "bootstrap_B": self.bootstrap_B,
        }


def compute_curve(
    distribution: dict[str, float],
    sample_sizes: Sequence[int] = DEFAULT_SAMPLE_SIZES,
    B: int = DEFAULT_BOOTSTRAP_B,
    rng: np.random.Generator | int | None = None,
) -> list[CurvePoint]:
    """Compute the bootstrap convergence curve for one distribution.

    Args:
        distribution: Aggregate human distribution (option -> probability).
        sample_sizes: Sample sizes n to evaluate. Must all be positive.
        B: Bootstrap replicates per sample size. Must be positive.
        rng: Optional seed or numpy Generator for reproducibility. An int is
            passed to ``np.random.default_rng``; a Generator is used as-is.

    Returns:
        One :class:`CurvePoint` per entry in ``sample_sizes``, in the order
        given. Empty distributions produce an empty list.
    """
    if B < 1:
        raise ValueError(f"B must be >= 1, got {B}")
    for n in sample_sizes:
        if n < 1:
            raise ValueError(f"sample_sizes must be positive, got {n}")

    if not distribution:
        return []

    if isinstance(rng, np.random.Generator):
        gen = rng
    else:
        gen = np.random.default_rng(rng)

    curve: list[CurvePoint] = []
    for n in sample_sizes:
        jsds = np.empty(B, dtype=np.float64)
        for b in range(B):
            sample = bootstrap_sample(distribution, n, gen)
            emp = empirical_distribution(sample)
            jsds[b] = jensen_shannon_divergence(emp, distribution)
        curve.append(
            CurvePoint(
                n=int(n),
                jsd_mean=float(np.mean(jsds)),
                jsd_p10=float(np.percentile(jsds, 10)),
                jsd_p90=float(np.percentile(jsds, 90)),
                bootstrap_B=int(B),
            )
        )
    return curve


def curve_to_dicts(curve: Iterable[CurvePoint]) -> list[dict]:
    """Helper to JSON-serialize a curve."""
    return [p.to_dict() for p in curve]
