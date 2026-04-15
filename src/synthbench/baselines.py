"""Human Ceiling, Temporal Drift Floor, and Ensemble Bootstrap CI baselines.

Implements the split-half multinomial bootstrap ceiling described in the
methodology writeup (hq-wisp-vuom1):

1. compute_ceiling() — pure function. Given raw category counts, draws two
   independent half-samples from Multinomial(n/2, p_hat), applies a distance
   metric between them, and reports (1 - mean(distance)) as the ceiling.

2. compute_temporal_drift() — JSD between same-wording questions across Pew
   ATP waves. Reports mean drift per year-gap + CI. A new baseline-adjacent
   metric that quantifies how real-world opinions shift year-over-year.

3. ensemble_bootstrap_ci() — resamples per-question scores with replacement
   B=1000 times to produce percentile CIs for deterministic ensemble runs
   (previously reported CI_lower = CI_upper = 0.000).

Citations (per data scientist):
- Santurkar et al. 2023 (OpinionsQA, arxiv:2303.17548)
- Durmus et al. 2023 (GlobalOpinionQA, arxiv:2306.16388)
- Suh et al. (SubPOP, ACL 2025, arxiv:2502.16761)
- Spearman-Brown prophecy (1910)
- Efron (1979) bootstrap
- Lin (1991) Jensen-Shannon divergence
- Cochran (1977) Sampling Techniques
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

import numpy as np
from scipy.special import rel_entr

from synthbench.metrics.distributional import jensen_shannon_divergence
from synthbench.metrics.ranking import kendall_tau_b

_LOG2 = float(np.log(2.0))

QualityFlag = Literal["high", "medium", "low"]


@dataclass
class CeilingResult:
    """Result of a split-half ceiling computation."""

    mean: float
    ci_low: float
    ci_high: float
    n_effective: int
    quality_flag: QualityFlag
    method: str = "multinomial_bootstrap_1000"

    def to_dict(self) -> dict:
        return {
            "mean": round(self.mean, 6),
            "ci_low": round(self.ci_low, 6),
            "ci_high": round(self.ci_high, 6),
            "n_effective": self.n_effective,
            "quality_flag": self.quality_flag,
            "method": self.method,
        }


def _quality_flag(n: int) -> QualityFlag:
    """Classify raw subpop sample size per Cochran (1977) and methodology writeup."""
    if n >= 400:
        return "high"
    if n >= 200:
        return "medium"
    return "low"


def compute_ceiling(
    counts: dict[str, int],
    metric: Callable[[dict[str, float], dict[str, float]], float],
    n_bootstrap: int = 1000,
    seed: int = 42,
    is_distance: bool = True,
) -> CeilingResult:
    """Split-half ceiling via multinomial bootstrap.

    Given observed counts c = [c_1, ..., c_k] with total n, treats p_hat = c/n
    as the multinomial MLE. Draws two independent half-samples of size
    floor(n/2) from Multinomial(n/2, p_hat), computes the metric between the
    two empirical distributions, and repeats B times.

    For distance metrics (JSD, where lower = better), ceiling = 1 - mean(d).
    For agreement metrics (Kendall tau, where higher = better), ceiling =
    mean(tau) directly — pass is_distance=False.

    Args:
        counts: option -> count from real human data. Integer-valued.
        metric: callable(p, q) -> float, where p/q are dict[option, probability].
        n_bootstrap: number of bootstrap replicates (default 1000).
        seed: RNG seed for reproducibility (default 42).
        is_distance: If True, ceiling = 1 - mean(metric). If False, ceiling =
            mean(metric) (useful for rank agreement like Kendall tau).

    Returns:
        CeilingResult with mean, 95% CI, effective n, quality flag, method.

    Raises:
        ValueError: if counts is empty or all zero.
    """
    keys = sorted(counts.keys())
    if not keys:
        raise ValueError("counts is empty")

    c_vec = np.array([float(counts[k]) for k in keys], dtype=np.float64)
    n_total = int(c_vec.sum())
    if n_total <= 0:
        raise ValueError(f"counts sum to {n_total}, must be positive")

    p_hat = c_vec / n_total
    n_half = n_total // 2

    # Degenerate case: n too small to split
    if n_half < 1:
        return CeilingResult(
            mean=0.0,
            ci_low=0.0,
            ci_high=0.0,
            n_effective=n_total,
            quality_flag=_quality_flag(n_total),
            method=f"multinomial_bootstrap_{n_bootstrap}",
        )

    rng = np.random.default_rng(seed)

    if metric is jensen_shannon_divergence:
        # Fast path: vectorize both the multinomial draws and the JSD metric.
        # `size=(n_bootstrap, 2)` preserves the interleaved A/B draw order of
        # the original per-iteration loop, so the RNG bit-stream — and thus
        # every realized draw — is identical to calling rng.multinomial twice
        # per step. This keeps seed=42 reproducibility bit-exact vs. the
        # dict-based path (see sb-dkz).
        distances = _multinomial_bootstrap_jsd(p_hat, n_half, n_bootstrap, rng)
    else:
        distances = np.empty(n_bootstrap, dtype=np.float64)
        for b in range(n_bootstrap):
            # Two independent half-samples from Multinomial(n/2, p_hat)
            draw_a = rng.multinomial(n_half, p_hat)
            draw_b = rng.multinomial(n_half, p_hat)

            # Normalize to probabilities for the metric
            dist_a = {keys[i]: float(draw_a[i]) / n_half for i in range(len(keys))}
            dist_b = {keys[i]: float(draw_b[i]) / n_half for i in range(len(keys))}

            distances[b] = float(metric(dist_a, dist_b))

    mean_d = float(distances.mean())
    lo_arr, hi_arr = np.percentile(distances, [2.5, 97.5])
    lo = float(lo_arr)
    hi = float(hi_arr)

    if is_distance:
        # Ceiling = 1 - mean(distance); CI flips direction
        ceiling_mean = 1.0 - mean_d
        ceiling_lo = 1.0 - hi
        ceiling_hi = 1.0 - lo
    else:
        # Agreement metric: ceiling = mean(metric) directly
        ceiling_mean = mean_d
        ceiling_lo = lo
        ceiling_hi = hi

    return CeilingResult(
        mean=ceiling_mean,
        ci_low=ceiling_lo,
        ci_high=ceiling_hi,
        n_effective=n_total,
        quality_flag=_quality_flag(n_total),
        method=f"multinomial_bootstrap_{n_bootstrap}",
    )


def _multinomial_bootstrap_jsd(
    p_hat: np.ndarray,
    n_half: int,
    n_bootstrap: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Vectorized split-half JSD bootstrap (base-2), bit-compatible with
    the per-iteration loop using two sequential ``rng.multinomial(n_half,
    p_hat)`` calls at the same seed.

    ``size=(n_bootstrap, 2)`` materializes the draws in the same interleaved
    A, B, A, B, ... order the original loop consumed, so the RNG state is
    advanced identically. The returned JSD values match the dict-based
    ``jensen_shannon_divergence(p, q)`` computation to ~1e-16 (floating-point
    noise only), which is well under the 6-decimal rounding applied in
    ``CeilingResult.to_dict``.
    """
    draws = rng.multinomial(n_half, p_hat, size=(n_bootstrap, 2))
    p = draws[:, 0].astype(np.float64) / n_half
    q = draws[:, 1].astype(np.float64) / n_half
    m = 0.5 * (p + q)
    jsd_nats = 0.5 * (rel_entr(p, m).sum(axis=-1) + rel_entr(q, m).sum(axis=-1))
    return jsd_nats / _LOG2


def compute_ceiling_jsd(
    counts: dict[str, int], n_bootstrap: int = 1000, seed: int = 42
) -> CeilingResult:
    """Convenience wrapper for JSD-based ceiling (P_dist)."""
    return compute_ceiling(
        counts, jensen_shannon_divergence, n_bootstrap, seed, is_distance=True
    )


def compute_ceiling_tau(
    counts: dict[str, int], n_bootstrap: int = 1000, seed: int = 42
) -> CeilingResult:
    """Convenience wrapper for Kendall tau-based ceiling (P_rank)."""
    return compute_ceiling(counts, kendall_tau_b, n_bootstrap, seed, is_distance=False)


def aggregate_ceilings(
    ceilings: list[CeilingResult],
    weights: list[float] | None = None,
) -> CeilingResult | None:
    """Aggregate per-subpop/per-wave ceilings into a single summary.

    Weighted mean of the point estimate; weighted CI bounds (keeps the range
    interpretable without mis-implying independence across subpops). Method
    string reflects aggregation.

    Args:
        ceilings: non-empty list of CeilingResult objects to combine.
        weights: optional weights (e.g., n_questions per wave). If None,
            weights by n_effective of each result.

    Returns:
        Aggregated CeilingResult, or None if input is empty.
    """
    if not ceilings:
        return None

    if weights is None:
        weights = [float(c.n_effective) for c in ceilings]
    if len(weights) != len(ceilings):
        raise ValueError("weights and ceilings must have same length")

    w_sum = float(sum(weights))
    if w_sum <= 0:
        return None

    mean = sum(c.mean * w for c, w in zip(ceilings, weights)) / w_sum
    lo = sum(c.ci_low * w for c, w in zip(ceilings, weights)) / w_sum
    hi = sum(c.ci_high * w for c, w in zip(ceilings, weights)) / w_sum
    n_eff = int(sum(c.n_effective for c in ceilings))

    # Aggregate quality flag = worst tier present
    flags = {c.quality_flag for c in ceilings}
    if "low" in flags:
        agg_flag: QualityFlag = "low"
    elif "medium" in flags:
        agg_flag = "medium"
    else:
        agg_flag = "high"

    return CeilingResult(
        mean=mean,
        ci_low=lo,
        ci_high=hi,
        n_effective=n_eff,
        quality_flag=agg_flag,
        method=f"aggregate_of_{len(ceilings)}_subpops",
    )


def compute_temporal_drift(
    per_question_data: list[dict],
) -> dict:
    """Temporal drift floor for OpinionsQA: JSD between same-wording questions
    across Pew ATP waves.

    Pew repeats ~15-20% of questions across waves for trend tracking. This
    quantifies how much real opinions shift year-over-year on repeated items.
    Useful framing for P_refuse and longitudinal claims; strictly separate
    from the Human Ceiling itself.

    Identifies repeated questions by stripping the wave suffix (e.g.
    "TRUST_W32" -> "TRUST") and pairing distributions across waves.

    Args:
        per_question_data: list of dicts with at least keys
            'key', 'human_distribution', and either 'temporal_year' (from
            publish) or 'survey' (so the wave year can be extracted).

    Returns:
        dict with:
            mean_drift: overall mean JSD across repeated-question pairs
            ci_low, ci_high: 95% percentile CI via bootstrap over pairs
            n_pairs: total number of cross-wave pairs compared
            n_stems: number of question stems observed in 2+ waves
            by_year_gap: dict mapping year-gap (int) -> mean JSD and count
            method: description string
    """
    from synthbench.datasets.opinionsqa import WAVE_YEAR_MAP, wave_year

    # Group entries by key stem (strip "_W##" suffix). Pew sometimes assigns
    # wave-specific keys to same-wording repeats — this groups them only when
    # the underlying key (e.g., HARASS4) is reused across waves, which is
    # Pew's convention for true trend-tracking questions. Text-based matching
    # produces false positives because Pew questions often share generic
    # preambles ("Please choose the statement that comes closer to your own
    # views.") that aren't semantically equivalent.
    stems: dict[str, list[dict]] = {}
    for q in per_question_data:
        key = q.get("key", "")
        if not key or "_W" not in key:
            continue
        stem = key.rsplit("_W", 1)[0]
        year = q.get("temporal_year")
        if year is None or year == 0:
            survey = q.get("survey", "")
            year = wave_year(survey) if survey else 0
            if not year:
                try:
                    wave_num = int(key.rsplit("_W", 1)[1])
                    year = WAVE_YEAR_MAP.get(wave_num, 0)
                except (ValueError, IndexError):
                    year = 0
        if not year:
            continue
        dist = q.get("human_distribution", {})
        if not dist:
            continue
        # Case-normalize stem: Pew sometimes uses SATLIFEA vs SATLIFEa for
        # the same underlying trend item across waves.
        stems.setdefault(stem.upper(), []).append({"year": int(year), "dist": dist})

    # Compute JSD between every pair of waves for each repeated stem
    pair_jsds: list[tuple[int, float]] = []  # (year_gap, jsd)
    n_stems_repeated = 0
    for stem, entries in stems.items():
        if len(entries) < 2:
            continue
        n_stems_repeated += 1
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                year_gap = abs(entries[i]["year"] - entries[j]["year"])
                jsd = jensen_shannon_divergence(entries[i]["dist"], entries[j]["dist"])
                pair_jsds.append((year_gap, jsd))

    if not pair_jsds:
        return {
            "mean_drift": 0.0,
            "ci_low": 0.0,
            "ci_high": 0.0,
            "n_pairs": 0,
            "n_stems": 0,
            "by_year_gap": {},
            "method": "cross_wave_jsd_on_repeated_stems",
        }

    jsds = np.array([p[1] for p in pair_jsds], dtype=np.float64)
    mean_drift = float(jsds.mean())

    # Bootstrap CI over pairs
    rng = np.random.default_rng(42)
    n_boot = 1000
    boot_means = np.empty(n_boot, dtype=np.float64)
    n = len(jsds)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boot_means[b] = float(jsds[idx].mean())
    ci_low = float(np.percentile(boot_means, 2.5))
    ci_high = float(np.percentile(boot_means, 97.5))

    # By year-gap breakdown
    by_gap: dict[int, list[float]] = {}
    for gap, jsd in pair_jsds:
        by_gap.setdefault(gap, []).append(jsd)
    by_year_gap = {
        str(gap): {
            "mean_jsd": round(float(np.mean(vals)), 6),
            "n_pairs": len(vals),
        }
        for gap, vals in sorted(by_gap.items())
    }

    return {
        "mean_drift": round(mean_drift, 6),
        "ci_low": round(ci_low, 6),
        "ci_high": round(ci_high, 6),
        "n_pairs": len(pair_jsds),
        "n_stems": n_stems_repeated,
        "by_year_gap": by_year_gap,
        "method": "cross_wave_jsd_on_repeated_stems",
    }


def ensemble_bootstrap_ci(
    per_question: list[dict],
    metric_key: str = "parity",
    n_bootstrap: int = 1000,
    seed: int = 42,
) -> tuple[float, float]:
    """Bootstrap CI for a deterministic ensemble run by resampling
    per-question scores with replacement.

    Ensemble entries currently emit CI_lower = CI_upper = 0.000 because the
    arithmetic blend has no replicate variance. This function recovers a real
    CI by bootstrapping over the per-question score distribution.

    Args:
        per_question: list of per-question dicts from an ensemble result.
        metric_key: which per-question score to resample. Defaults to 'parity'
            (matches the aggregate SPS / composite_parity).
        n_bootstrap: number of bootstrap replicates (default 1000).
        seed: RNG seed for reproducibility (default 42).

    Returns:
        (ci_lower, ci_upper) as 95% percentile CI. (0.0, 0.0) if no data.
    """
    values = [
        float(q[metric_key]) for q in per_question if q.get(metric_key) is not None
    ]
    if not values:
        return (0.0, 0.0)

    arr = np.array(values, dtype=np.float64)
    n = len(arr)
    rng = np.random.default_rng(seed)
    boot_means = np.empty(n_bootstrap, dtype=np.float64)
    for b in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        boot_means[b] = float(arr[idx].mean())
    ci_low = float(np.percentile(boot_means, 2.5))
    ci_high = float(np.percentile(boot_means, 97.5))
    return (ci_low, ci_high)


# ---------------------------------------------------------------------------
# Per-dataset ceiling protocols
# ---------------------------------------------------------------------------


def _counts_from_probs(probs: dict[str, float], n: int) -> dict[str, int]:
    """Convert a probability distribution to integer counts for a given n.

    Uses round-half-to-even; adjusts the largest bucket to guarantee the
    counts sum to n (deterministic for fixed input).
    """
    if n <= 0 or not probs:
        return {}
    items = list(probs.items())
    raw = [(k, p * n) for k, p in items]
    counts = {k: int(round(v)) for k, v in raw}
    diff = n - sum(counts.values())
    if diff != 0 and counts:
        # Adjust the bucket with the largest fractional part
        frac = sorted(raw, key=lambda kv: kv[1] - int(kv[1]), reverse=(diff > 0))
        if frac:
            counts[frac[0][0]] += diff
    return counts


def compute_opinionsqa_ceiling(
    data_dir: str | None = None, n_bootstrap: int = 1000
) -> dict | None:
    """Compute OpinionsQA ceiling from raw NONE_data.json counts (within-wave).

    Returns a dict suitable for emission into leaderboard.json, or None if
    raw data is not available on disk. Default n_bootstrap=1000 (the full
    bootstrap budget); the vectorized JSD fast path in ``compute_ceiling``
    keeps publish-time cost negligible at this B (sb-dkz).
    """
    from pathlib import Path

    from synthbench.datasets.opinionsqa import (
        PEW_WAVES,
        WAVE_YEAR_MAP,
        _default_cache_dir,
    )

    data_path = Path(data_dir) if data_dir else _default_cache_dir()
    human_resp = data_path / "raw" / "human_resp"
    if not human_resp.is_dir():
        return None

    import json

    wave_ceilings: list[CeilingResult] = []
    wave_weights: list[float] = []
    wave_details: list[dict] = []

    for wave in PEW_WAVES:
        wave_dir = human_resp / f"American_Trends_Panel_W{wave}"
        none_path = wave_dir / "NONE_data.json"
        if not none_path.exists():
            continue

        with open(none_path) as f:
            data = json.load(f)

        per_q_ceilings: list[CeilingResult] = []
        for _qkey, entry in data.items():
            if not isinstance(entry, dict):
                continue
            # Sum counts across sub_keys (political parties), per option
            totals: dict[str, float] = {}
            for sub_key, counts in entry.items():
                if sub_key in ("MC_options", "question_text"):
                    continue
                if not isinstance(counts, dict):
                    continue
                for option, val in counts.items():
                    totals[option] = totals.get(option, 0.0) + float(val)
            if not totals:
                continue
            int_counts = {k: int(round(v)) for k, v in totals.items() if v > 0}
            if sum(int_counts.values()) < 10:
                continue
            try:
                r = compute_ceiling_jsd(int_counts, n_bootstrap=n_bootstrap)
                per_q_ceilings.append(r)
            except ValueError:
                continue

        if per_q_ceilings:
            agg = aggregate_ceilings(per_q_ceilings)
            if agg is not None:
                wave_ceilings.append(agg)
                wave_weights.append(float(len(per_q_ceilings)))
                wave_details.append(
                    {
                        "wave": f"ATP W{wave}",
                        "year": WAVE_YEAR_MAP.get(wave, 0),
                        "n_questions": len(per_q_ceilings),
                        "ceiling": agg.to_dict(),
                    }
                )

    if not wave_ceilings:
        return None

    overall = aggregate_ceilings(wave_ceilings, weights=wave_weights)
    return {
        "dataset": "opinionsqa",
        "overall": overall.to_dict() if overall else None,
        "per_wave": wave_details,
        "protocol": "within_wave_split_half_multinomial_bootstrap",
        "n_bootstrap": n_bootstrap,
    }


def compute_opinionsqa_subgroup_ceilings(
    data_dir: str | None = None, n_bootstrap: int = 1000
) -> dict | None:
    """Compute per-(wave, attribute, group) ceilings for OpinionsQA.

    The aggregate ceiling from compute_opinionsqa_ceiling() is wave-level (n
    ~= 4000-5000 per wave) and overstates the achievable ceiling for P_sub,
    which is measured at (wave × attribute × group) granularity where
    subgroup sizes are 50-500. This function computes the ceiling at the
    same granularity as the metric it bounds.

    Aggregates per-question ceilings into one ceiling per (wave, attribute,
    group), then emits the distribution (min/p25/median/p75/max) plus the
    five worst subgroups by name.

    Quality flags follow Cochran (1977): high n≥400, medium 200≤n<400,
    low n<200. Small subgroups are retained but flagged so callers can
    filter if needed.

    Returns None if raw data is not on disk.
    """
    from pathlib import Path

    from synthbench.datasets.opinionsqa import (
        PEW_WAVES,
        WAVE_YEAR_MAP,
        _default_cache_dir,
    )

    data_path = Path(data_dir) if data_dir else _default_cache_dir()
    human_resp = data_path / "raw" / "human_resp"
    if not human_resp.is_dir():
        return None

    import json

    # Per-subgroup files shipped by Pew ATP. NONE_data.json is excluded
    # because it is the wave-aggregate (not a subgroup).
    ATTRIBUTE_FILES = [
        "EDUCATION",
        "POLPARTY",
        "POLIDEOLOGY",
        "RACE",
        "SEX",
        "INCOME",
        "AGE",
        "CREGION",
        "POLPARTY_SEX",
        "POLPARTY_RACE",
        "RACE_SEX",
    ]

    per_subgroup_rows: list[dict] = []

    for wave in PEW_WAVES:
        wave_dir = human_resp / f"American_Trends_Panel_W{wave}"
        if not wave_dir.is_dir():
            continue
        year = WAVE_YEAR_MAP.get(wave, 0)
        wave_label = f"ATP W{wave}"

        for attr in ATTRIBUTE_FILES:
            path = wave_dir / f"{attr}_data.json"
            if not path.exists():
                continue

            with open(path) as f:
                data = json.load(f)

            # Bucket per-question ceilings by subgroup key. Cross-cut files
            # (e.g. POLPARTY_SEX) ship one level of nesting — leaves are the
            # option-count dicts we care about; branches become compound
            # group labels like "Democrat × Female".
            def _iter_subgroups(obj, prefix: str = ""):
                for sub_key, sub_val in obj.items():
                    if sub_key in ("MC_options", "question_text"):
                        continue
                    if not isinstance(sub_val, dict):
                        continue
                    inner_vals = list(sub_val.values())
                    if inner_vals and all(isinstance(v, dict) for v in inner_vals):
                        # Nested cross-cut: recurse one level.
                        label = f"{prefix}{sub_key} × "
                        yield from _iter_subgroups(sub_val, prefix=label)
                    else:
                        yield f"{prefix}{sub_key}", sub_val

            group_ceilings: dict[str, list[CeilingResult]] = {}
            for _qkey, entry in data.items():
                if not isinstance(entry, dict):
                    continue
                for group_label, counts in _iter_subgroups(entry):
                    int_counts: dict[str, int] = {}
                    for k, v in counts.items():
                        try:
                            fv = float(v)
                        except (TypeError, ValueError):
                            continue
                        if fv > 0:
                            int_counts[k] = int(round(fv))
                    if sum(int_counts.values()) < 10:
                        continue
                    try:
                        r = compute_ceiling_jsd(int_counts, n_bootstrap=n_bootstrap)
                    except ValueError:
                        continue
                    group_ceilings.setdefault(group_label, []).append(r)

            for group, results in sorted(group_ceilings.items()):
                agg = aggregate_ceilings(results)
                if agg is None:
                    continue
                per_subgroup_rows.append(
                    {
                        "wave": wave_label,
                        "year": year,
                        "attribute": attr,
                        "group": group,
                        "n_questions": len(results),
                        "ceiling": agg.to_dict(),
                    }
                )

    if not per_subgroup_rows:
        return None

    values = np.array(
        [row["ceiling"]["mean"] for row in per_subgroup_rows], dtype=np.float64
    )
    distribution = {
        "min": round(float(values.min()), 6),
        "p25": round(float(np.percentile(values, 25)), 6),
        "median": round(float(np.percentile(values, 50)), 6),
        "p75": round(float(np.percentile(values, 75)), 6),
        "max": round(float(values.max()), 6),
    }

    worst_5 = sorted(per_subgroup_rows, key=lambda r: r["ceiling"]["mean"])[:5]

    quality_breakdown: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for row in per_subgroup_rows:
        flag = row["ceiling"]["quality_flag"]
        quality_breakdown[flag] = quality_breakdown.get(flag, 0) + 1

    return {
        "dataset": "opinionsqa",
        "granularity": "wave_attribute_group",
        "distribution": distribution,
        "subgroup_ceiling_for_psub": distribution["median"],
        "worst_5_subgroups": worst_5,
        "quality_breakdown": quality_breakdown,
        "n_subgroups": len(per_subgroup_rows),
        "per_subgroup": per_subgroup_rows,
        "protocol": "per_subgroup_split_half_multinomial_bootstrap",
        "n_bootstrap": n_bootstrap,
        "note": (
            "P_sub is a per-(wave, attribute, group) metric; the wave-aggregate "
            "ceiling overstates achievable headroom at subgroup granularity. "
            "Use the median subgroup ceiling (subgroup_ceiling_for_psub) as the "
            "reference for P_sub, and the distribution to characterize spread."
        ),
    }


def compute_subpop_ceiling(
    data_dir: str | None = None,
    n_per_subpop: int = 500,
    n_bootstrap: int = 1000,
) -> dict | None:
    """Compute SubPOP ceiling per (attribute, group) subpopulation.

    SubPOP ships probabilities without raw counts. We approximate counts by
    rounding probs * n_per_subpop. Pew ATP subpops typically have
    n ~= 300-800 respondents; the methodology writeup recommends flagging
    ceilings as "medium" quality when n is inferred.

    Returns a dict suitable for leaderboard.json, or None if raw data is
    unavailable.
    """
    from pathlib import Path

    from synthbench.datasets.subpop import _default_cache_dir

    data_path = Path(data_dir) if data_dir else _default_cache_dir()
    raw_path = data_path / "raw_rows.json"
    if not raw_path.exists():
        return None

    import json

    with open(raw_path) as f:
        rows = json.load(f)

    # Group by (attribute, group)
    subpop_ceilings: dict[tuple[str, str], list[CeilingResult]] = {}
    for row in rows:
        attr = row.get("attribute", "")
        group = row.get("group", "")
        options = row.get("options", [])
        responses = row.get("responses", [])
        if not attr or not group or len(options) != len(responses):
            continue
        probs = {opt: float(p) for opt, p in zip(options, responses)}
        counts = _counts_from_probs(probs, n_per_subpop)
        if sum(counts.values()) < 10:
            continue
        try:
            r = compute_ceiling_jsd(counts, n_bootstrap=n_bootstrap)
            subpop_ceilings.setdefault((attr, group), []).append(r)
        except ValueError:
            continue

    if not subpop_ceilings:
        return None

    per_subpop: list[dict] = []
    all_ceilings: list[CeilingResult] = []
    all_weights: list[float] = []
    for (attr, group), results in sorted(subpop_ceilings.items()):
        agg = aggregate_ceilings(results)
        if agg is None:
            continue
        # Downgrade flag: n is inferred, so cap at "medium"
        if agg.quality_flag == "high":
            agg = CeilingResult(
                mean=agg.mean,
                ci_low=agg.ci_low,
                ci_high=agg.ci_high,
                n_effective=agg.n_effective,
                quality_flag="medium",
                method=agg.method + "_inferred_n",
            )
        per_subpop.append(
            {
                "attribute": attr,
                "group": group,
                "n_questions": len(results),
                "ceiling": agg.to_dict(),
            }
        )
        all_ceilings.append(agg)
        all_weights.append(float(len(results)))

    overall = aggregate_ceilings(all_ceilings, weights=all_weights)
    return {
        "dataset": "subpop",
        "overall": overall.to_dict() if overall else None,
        "per_subpop": per_subpop,
        "protocol": "per_subpop_split_half_multinomial_bootstrap",
        "n_bootstrap": n_bootstrap,
        "n_per_subpop_assumed": n_per_subpop,
        "note": (
            "SubPOP ships probabilities without raw counts; counts inferred "
            f"at n={n_per_subpop} per subpop (typical Pew ATP subgroup size). "
            "Quality flag capped at 'medium' due to inferred n."
        ),
    }


def compute_globalopinionqa_ceiling(
    data_dir: str | None = None,
    n_per_country: int = 1000,
    n_bootstrap: int = 1000,
) -> dict | None:
    """Compute GlobalOpinionQA ceiling per-country with regional aggregates.

    Weighted by actual (country, question) coverage, not hypothetical coverage.
    Typical Pew Global Attitudes n per country = 1000-1500.
    """
    from pathlib import Path

    from synthbench.datasets.globalopinionqa import _default_cache_dir

    data_path = Path(data_dir) if data_dir else _default_cache_dir()
    cache_path = data_path / "questions.json"
    if not cache_path.exists():
        return None

    import json

    with open(cache_path) as f:
        payload = json.load(f)
    questions = payload.get("questions", [])
    if not questions:
        return None

    country_ceilings: dict[str, list[CeilingResult]] = {}
    for q in questions:
        options = q.get("options", [])
        selections = q.get("selections", {})
        if not options or not selections:
            continue
        for country, probs in selections.items():
            if len(probs) != len(options):
                continue
            dist = {str(opt): float(p) for opt, p in zip(options, probs)}
            counts = _counts_from_probs(dist, n_per_country)
            if sum(counts.values()) < 10:
                continue
            try:
                r = compute_ceiling_jsd(counts, n_bootstrap=n_bootstrap)
                country_ceilings.setdefault(country, []).append(r)
            except ValueError:
                continue

    if not country_ceilings:
        return None

    per_country: list[dict] = []
    all_ceilings: list[CeilingResult] = []
    all_weights: list[float] = []
    for country, results in sorted(country_ceilings.items()):
        agg = aggregate_ceilings(results)
        if agg is None:
            continue
        # Flag as inferred n
        if agg.quality_flag == "high":
            agg = CeilingResult(
                mean=agg.mean,
                ci_low=agg.ci_low,
                ci_high=agg.ci_high,
                n_effective=agg.n_effective,
                quality_flag="medium",
                method=agg.method + "_inferred_n",
            )
        per_country.append(
            {
                "country": country,
                "n_questions": len(results),
                "ceiling": agg.to_dict(),
            }
        )
        all_ceilings.append(agg)
        # Weight aggregate by actual (country, question) coverage
        all_weights.append(float(len(results)))

    overall = aggregate_ceilings(all_ceilings, weights=all_weights)
    return {
        "dataset": "globalopinionqa",
        "overall": overall.to_dict() if overall else None,
        "per_country": per_country,
        "protocol": "per_country_split_half_multinomial_bootstrap",
        "n_bootstrap": n_bootstrap,
        "n_per_country_assumed": n_per_country,
        "note": (
            "GlobalOpinionQA ships country probabilities without raw counts; "
            f"counts inferred at n={n_per_country} per country (typical Pew "
            "Global Attitudes survey size). Aggregate weighted by actual "
            "(country, question) coverage."
        ),
    }
