"""Real-sampling convergence curves over individual-level microdata.

Sibling to :mod:`synthbench.convergence.curves` (bootstrap from aggregates).

Where ``bootstrap.py`` draws multinomial samples from a collapsed aggregate
distribution -- the idealized i.i.d. floor -- this module sub-samples actual
respondents *without replacement* from the dataset's microdata. The resulting
curve carries the population heterogeneity that aggregate bootstrapping
discards: rare-cell variance, inter-wave drift, and the long tail of options
that any one respondent can't reach.

The output schema (``CurvePoint``) deliberately mirrors ``curves.compute_curve``
so the same plotting / threshold / payload code can render either curve. The
two curves only differ in *how the per-replicate sample is drawn*.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from synthbench.convergence.bootstrap import empirical_distribution
from synthbench.convergence.curves import (
    DEFAULT_BOOTSTRAP_B,
    DEFAULT_SAMPLE_SIZES,
    CurvePoint,
)
from synthbench.datasets.base import MicrodataRow
from synthbench.metrics.distributional import jensen_shannon_divergence


def respondent_distribution(
    rows: Sequence[MicrodataRow],
    question_key: str,
) -> dict[str, float]:
    """Aggregate microdata rows into the empirical distribution for one question.

    Respondents who did not answer the question contribute nothing. An empty
    return value is possible if no respondent answered the question.
    """
    counts: dict[str, int] = {}
    for r in rows:
        opt = r.responses.get(question_key)
        if opt is None:
            continue
        counts[opt] = counts.get(opt, 0) + 1
    total = sum(counts.values())
    if total == 0:
        return {}
    return {k: v / total for k, v in counts.items()}


def subsample_distribution(
    rows: Sequence[MicrodataRow],
    question_key: str,
    n: int,
    rng: np.random.Generator,
) -> dict[str, int] | None:
    """Sub-sample ``n`` respondents (without replacement) and tally answers.

    Only respondents who answered ``question_key`` are eligible. Returns
    ``None`` when the eligible pool is smaller than ``n`` -- the caller
    should treat this as "n too large for this question" and skip the point
    rather than silently degrade to a smaller sample.
    """
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    eligible = [i for i, r in enumerate(rows) if question_key in r.responses]
    if n == 0:
        return {}
    if len(eligible) < n:
        return None

    chosen = rng.choice(len(eligible), size=n, replace=False)
    counts: dict[str, int] = {}
    for idx in chosen:
        opt = rows[eligible[int(idx)]].responses[question_key]
        counts[opt] = counts.get(opt, 0) + 1
    return counts


def compute_real_curve(
    rows: Sequence[MicrodataRow],
    question_key: str,
    sample_sizes: Sequence[int] = DEFAULT_SAMPLE_SIZES,
    B: int = DEFAULT_BOOTSTRAP_B,
    rng: np.random.Generator | int | None = None,
) -> list[CurvePoint]:
    """Real-sampling convergence curve for one question.

    For each ``n`` in ``sample_sizes``, draw ``B`` respondent sub-samples
    (without replacement) from the eligible pool, normalize each into an
    empirical distribution, and compute JSD vs. the full-population
    distribution. Sample sizes that exceed the eligible pool are skipped so
    the curve never silently shrinks below the requested ``n``.

    Returns one :class:`CurvePoint` per *evaluable* sample size, in input
    order. Returns ``[]`` when no respondent answered the question.
    """
    if B < 1:
        raise ValueError(f"B must be >= 1, got {B}")
    for n in sample_sizes:
        if n < 1:
            raise ValueError(f"sample_sizes must be positive, got {n}")

    full = respondent_distribution(rows, question_key)
    if not full:
        return []

    if isinstance(rng, np.random.Generator):
        gen = rng
    else:
        gen = np.random.default_rng(rng)

    curve: list[CurvePoint] = []
    for n in sample_sizes:
        jsds: list[float] = []
        for _ in range(B):
            sample = subsample_distribution(rows, question_key, n, gen)
            if sample is None:
                # Pool too small for this n; abandon further replicates so we
                # don't waste cycles on a sample size we can't service.
                break
            emp = empirical_distribution(sample)
            jsds.append(jensen_shannon_divergence(emp, full))
        if not jsds:
            continue
        arr = np.asarray(jsds, dtype=np.float64)
        curve.append(
            CurvePoint(
                n=int(n),
                jsd_mean=float(np.mean(arr)),
                jsd_p10=float(np.percentile(arr, 10)),
                jsd_p90=float(np.percentile(arr, 90)),
                bootstrap_B=int(len(jsds)),
            )
        )
    return curve


__all__ = [
    "respondent_distribution",
    "subsample_distribution",
    "compute_real_curve",
]
