"""Bootstrap convergence analysis over aggregate human distributions.

Given a Question with a known ``human_distribution``, this module computes a
theoretical ~1/sqrt(n) convergence curve by multinomial subsampling:

  curve(n) = distribution over B bootstrap samples of
             JSD(empirical_sample_of_size_n, full_distribution)

Three layers:

* :mod:`synthbench.convergence.bootstrap` -- multinomial sub-sampling primitives
* :mod:`synthbench.convergence.curves`    -- curve computation
  (n -> JSD_mean / JSD_p10 / JSD_p90) across sample sizes
* :mod:`synthbench.convergence.thresholds` -- "convergence n" finder: smallest
  n at which the curve stabilizes below epsilon with a flat tail

The output is the theoretical lower bound an idealized i.i.d. sampler from the
aggregate distribution would achieve. It is NOT an estimate of real-population
convergence (population heterogeneity requires microdata; see the microdata
bead). Treat this curve as the floor everything else gets compared to.
"""

from __future__ import annotations

from synthbench.convergence.bootstrap import (
    bootstrap_sample,
    empirical_distribution,
)
from synthbench.convergence.curves import (
    DEFAULT_BOOTSTRAP_B,
    DEFAULT_SAMPLE_SIZES,
    CurvePoint,
    compute_curve,
)
from synthbench.convergence.thresholds import (
    DEFAULT_DELTA,
    DEFAULT_EPSILON,
    find_convergence_n,
)

__all__ = [
    "bootstrap_sample",
    "empirical_distribution",
    "compute_curve",
    "CurvePoint",
    "DEFAULT_SAMPLE_SIZES",
    "DEFAULT_BOOTSTRAP_B",
    "find_convergence_n",
    "DEFAULT_EPSILON",
    "DEFAULT_DELTA",
]
