"""Tests for Human Ceiling, Temporal Drift Floor, and Ensemble Bootstrap CIs.

Verifies the split-half multinomial bootstrap implementation against the
methodology writeup (hq-wisp-vuom1):
- Ceiling approaches 1.0 as n grows (JSD converges to 0 between half-samples
  drawn from the same distribution).
- Bootstrap CIs are reproducible under fixed seed.
- Quality flag follows Cochran n=400 rule-of-thumb.
"""

from __future__ import annotations

import pytest

from synthbench.baselines import (
    CeilingResult,
    aggregate_ceilings,
    compute_ceiling,
    compute_ceiling_jsd,
    compute_ceiling_tau,
    compute_opinionsqa_subgroup_ceilings,
    compute_temporal_drift,
    ensemble_bootstrap_ci,
)
from synthbench.metrics.distributional import jensen_shannon_divergence


# ---------------------------------------------------------------------------
# compute_ceiling
# ---------------------------------------------------------------------------


def test_ceiling_increases_with_n():
    """As n grows, split-half JSD shrinks, so ceiling -> 1.0."""
    small = compute_ceiling_jsd({"A": 50, "B": 30, "C": 20}, n_bootstrap=200)
    large = compute_ceiling_jsd({"A": 50000, "B": 30000, "C": 20000}, n_bootstrap=200)
    assert large.mean > small.mean
    assert large.mean > 0.999
    # Small-n ceiling should be notably lower
    assert small.mean < 0.995


def test_ceiling_reproducible_under_seed():
    """Same seed -> bit-identical ceiling."""
    counts = {"A": 500, "B": 300, "C": 200}
    r1 = compute_ceiling_jsd(counts, n_bootstrap=100, seed=42)
    r2 = compute_ceiling_jsd(counts, n_bootstrap=100, seed=42)
    assert r1.mean == r2.mean
    assert r1.ci_low == r2.ci_low
    assert r1.ci_high == r2.ci_high


def test_ceiling_different_seeds_differ():
    """Different seeds -> different bootstrap realizations."""
    counts = {"A": 500, "B": 300, "C": 200}
    r1 = compute_ceiling_jsd(counts, n_bootstrap=100, seed=42)
    r2 = compute_ceiling_jsd(counts, n_bootstrap=100, seed=7)
    # Means should be close but not identical
    assert abs(r1.mean - r2.mean) < 0.01
    assert r1.mean != r2.mean or r1.ci_low != r2.ci_low


def test_ceiling_ci_brackets_mean():
    """95% CI should bracket the point estimate."""
    r = compute_ceiling_jsd({"A": 200, "B": 100, "C": 100}, n_bootstrap=500)
    assert r.ci_low <= r.mean <= r.ci_high


def test_ceiling_quality_flags():
    """n >= 400 -> high; 200 <= n < 400 -> medium; n < 200 -> low."""
    high = compute_ceiling_jsd({"A": 300, "B": 200}, n_bootstrap=50)
    assert high.quality_flag == "high"

    medium = compute_ceiling_jsd({"A": 150, "B": 100}, n_bootstrap=50)
    assert medium.quality_flag == "medium"

    low = compute_ceiling_jsd({"A": 50, "B": 50}, n_bootstrap=50)
    assert low.quality_flag == "low"


def test_ceiling_empty_raises():
    with pytest.raises(ValueError):
        compute_ceiling_jsd({}, n_bootstrap=10)


def test_ceiling_zero_counts_raises():
    with pytest.raises(ValueError):
        compute_ceiling_jsd({"A": 0, "B": 0}, n_bootstrap=10)


def test_ceiling_single_category():
    """Degenerate: all mass on one option — JSD between halves is always 0."""
    r = compute_ceiling_jsd({"A": 1000}, n_bootstrap=100)
    assert r.mean == pytest.approx(1.0, abs=1e-9)


def test_ceiling_n_effective_matches_total():
    counts = {"A": 500, "B": 300, "C": 200}
    r = compute_ceiling_jsd(counts, n_bootstrap=50)
    assert r.n_effective == 1000


def test_ceiling_method_string_includes_bootstrap_count():
    r = compute_ceiling_jsd({"A": 100, "B": 100}, n_bootstrap=250)
    assert "250" in r.method


def test_tau_ceiling_agreement_metric():
    """Kendall tau is an agreement metric; ceiling is mean(tau) directly."""
    r = compute_ceiling_tau({"A": 500, "B": 300, "C": 200}, n_bootstrap=100)
    # Distinct probabilities -> tau should be near +1
    assert r.mean > 0.9
    assert r.ci_low <= r.mean <= r.ci_high


def test_ceiling_custom_metric():
    """compute_ceiling accepts any metric(p, q) -> float."""

    def l1(p: dict, q: dict) -> float:
        keys = set(p) | set(q)
        return sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys) / 2

    r = compute_ceiling(
        {"A": 500, "B": 500}, metric=l1, n_bootstrap=50, is_distance=True
    )
    assert 0.0 <= r.mean <= 1.0


# ---------------------------------------------------------------------------
# aggregate_ceilings
# ---------------------------------------------------------------------------


def test_aggregate_ceilings_weighted_mean():
    a = CeilingResult(
        mean=0.90, ci_low=0.85, ci_high=0.95, n_effective=1000, quality_flag="high"
    )
    b = CeilingResult(
        mean=0.70, ci_low=0.65, ci_high=0.75, n_effective=3000, quality_flag="high"
    )
    agg = aggregate_ceilings([a, b])
    assert agg is not None
    # Weighted by n_effective: (0.9*1000 + 0.7*3000) / 4000 = 0.75
    assert agg.mean == pytest.approx(0.75, abs=1e-6)
    assert agg.n_effective == 4000
    assert agg.quality_flag == "high"


def test_aggregate_ceilings_worst_flag_wins():
    high = CeilingResult(0.9, 0.85, 0.95, 1000, "high")
    low = CeilingResult(0.6, 0.55, 0.65, 100, "low")
    agg = aggregate_ceilings([high, low])
    assert agg.quality_flag == "low"


def test_aggregate_ceilings_empty_returns_none():
    assert aggregate_ceilings([]) is None


def test_aggregate_ceilings_explicit_weights():
    a = CeilingResult(0.9, 0.85, 0.95, 1000, "high")
    b = CeilingResult(0.7, 0.65, 0.75, 1000, "high")
    agg = aggregate_ceilings([a, b], weights=[3.0, 1.0])
    assert agg is not None
    # (0.9*3 + 0.7*1)/4 = 0.85
    assert agg.mean == pytest.approx(0.85, abs=1e-6)


# ---------------------------------------------------------------------------
# ensemble_bootstrap_ci
# ---------------------------------------------------------------------------


def test_ensemble_bootstrap_ci_not_zero_with_data():
    """Real ensemble data should produce non-zero CI width."""
    per_question = [{"parity": 0.1 + 0.7 * (i % 17) / 17.0} for i in range(500)]
    lo, hi = ensemble_bootstrap_ci(per_question, n_bootstrap=200)
    assert hi > lo
    assert hi - lo > 0.01  # Meaningful width


def test_ensemble_bootstrap_ci_reproducible():
    per_question = [{"parity": 0.5 + 0.1 * (i % 7 - 3)} for i in range(100)]
    lo1, hi1 = ensemble_bootstrap_ci(per_question, seed=42)
    lo2, hi2 = ensemble_bootstrap_ci(per_question, seed=42)
    assert lo1 == lo2
    assert hi1 == hi2


def test_ensemble_bootstrap_ci_empty():
    assert ensemble_bootstrap_ci([]) == (0.0, 0.0)


def test_ensemble_bootstrap_ci_skips_missing_keys():
    per_question = [
        {"parity": 0.8},
        {"parity": None},
        {"parity": 0.6},
        {},  # no parity key at all
    ]
    lo, hi = ensemble_bootstrap_ci(per_question, n_bootstrap=50)
    # Should still produce a finite CI over the 2 valid values
    assert 0.0 <= lo <= hi <= 1.0


def test_ensemble_bootstrap_ci_constant_values():
    """All identical scores -> zero-width CI at that value."""
    per_question = [{"parity": 0.75}] * 50
    lo, hi = ensemble_bootstrap_ci(per_question, n_bootstrap=50)
    assert lo == pytest.approx(0.75, abs=1e-9)
    assert hi == pytest.approx(0.75, abs=1e-9)


# ---------------------------------------------------------------------------
# compute_temporal_drift
# ---------------------------------------------------------------------------


def test_temporal_drift_identical_distributions_zero_drift():
    per_question = [
        {
            "key": "ABORTION_W26",
            "human_distribution": {"legal": 0.5, "illegal": 0.5},
            "temporal_year": 2017,
        },
        {
            "key": "ABORTION_W32",
            "human_distribution": {"legal": 0.5, "illegal": 0.5},
            "temporal_year": 2018,
        },
    ]
    out = compute_temporal_drift(per_question)
    assert out["n_pairs"] == 1
    assert out["n_stems"] == 1
    assert out["mean_drift"] == pytest.approx(0.0, abs=1e-6)


def test_temporal_drift_divergent_distributions_nonzero():
    per_question = [
        {
            "key": "ABORTION_W26",
            "human_distribution": {"legal": 0.8, "illegal": 0.2},
            "temporal_year": 2017,
        },
        {
            "key": "ABORTION_W54",
            "human_distribution": {"legal": 0.2, "illegal": 0.8},
            "temporal_year": 2020,
        },
    ]
    out = compute_temporal_drift(per_question)
    assert out["mean_drift"] > 0.1
    assert "3" in out["by_year_gap"]
    assert out["by_year_gap"]["3"]["n_pairs"] == 1


def test_temporal_drift_no_repeats():
    per_question = [
        {
            "key": "UNIQUE_ONE_W26",
            "human_distribution": {"A": 0.5, "B": 0.5},
            "temporal_year": 2017,
        },
        {
            "key": "UNIQUE_TWO_W32",
            "human_distribution": {"A": 0.5, "B": 0.5},
            "temporal_year": 2018,
        },
    ]
    out = compute_temporal_drift(per_question)
    assert out["n_pairs"] == 0
    assert out["n_stems"] == 0


def test_temporal_drift_survey_fallback_when_no_year():
    """If temporal_year is missing, infer year from survey field via WAVE_YEAR_MAP."""
    per_question = [
        {
            "key": "ABORTION_W26",
            "human_distribution": {"A": 0.5, "B": 0.5},
            "survey": "ATP W26",
        },
        {
            "key": "ABORTION_W32",
            "human_distribution": {"A": 0.4, "B": 0.6},
            "survey": "ATP W32",
        },
    ]
    out = compute_temporal_drift(per_question)
    # W26 -> 2017, W32 -> 2018, gap = 1
    assert "1" in out["by_year_gap"]
    assert out["n_pairs"] == 1


def test_temporal_drift_matches_case_insensitive_stems():
    """Pew sometimes uses SATLIFEA vs SATLIFEa for the same trend item across
    waves — case-normalize the stem so these pair up."""
    per_question = [
        {
            "key": "SATLIFEA_W32",
            "human_distribution": {"Satisfied": 0.7, "Dissatisfied": 0.3},
            "temporal_year": 2018,
        },
        {
            "key": "SATLIFEa_W50",  # lowercase variant
            "human_distribution": {"Satisfied": 0.65, "Dissatisfied": 0.35},
            "temporal_year": 2020,
        },
    ]
    out = compute_temporal_drift(per_question)
    assert out["n_stems"] == 1
    assert out["n_pairs"] == 1
    assert out["mean_drift"] > 0.0


def test_temporal_drift_reproducible():
    """Bootstrap CI uses fixed seed (42)."""
    per_question = [
        {
            "key": f"Q{i}_W{wave}",
            "human_distribution": {"A": 0.5 + 0.01 * wave, "B": 0.5 - 0.01 * wave},
            "temporal_year": 2017 + wave,
        }
        for i in range(3)
        for wave in (26, 32, 41)
    ]
    out1 = compute_temporal_drift(per_question)
    out2 = compute_temporal_drift(per_question)
    assert out1["mean_drift"] == out2["mean_drift"]
    assert out1["ci_low"] == out2["ci_low"]
    assert out1["ci_high"] == out2["ci_high"]


# ---------------------------------------------------------------------------
# Integration: JSD between half-samples is small but non-zero
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# compute_opinionsqa_subgroup_ceilings
# ---------------------------------------------------------------------------


def _write_synthetic_wave(
    base,
    wave: int,
    attribute: str,
    *,
    groups: dict[str, int],
    mc_options: list[str],
    n_questions: int = 3,
) -> None:
    """Write a synthetic Pew ATP wave fixture with a single attribute file.

    ``groups`` maps group label -> total n per question. Option counts are
    split roughly evenly across ``mc_options``.
    """
    import json

    wave_dir = base / f"American_Trends_Panel_W{wave}"
    wave_dir.mkdir(parents=True, exist_ok=True)
    payload: dict = {}
    for q in range(n_questions):
        key = f"TESTQ{q}_W{wave}"
        entry: dict = {
            "MC_options": mc_options,
            "question_text": f"Test question {q}",
        }
        for group, n in groups.items():
            k = len(mc_options)
            base_count = n // k
            remainder = n - base_count * k
            counts = {opt: float(base_count) for opt in mc_options}
            # Put the remainder on the first option so the total matches n.
            counts[mc_options[0]] += float(remainder)
            entry[group] = counts
        payload[key] = entry

    with open(wave_dir / f"{attribute}_data.json", "w") as f:
        json.dump(payload, f)


def test_subgroup_ceilings_returns_none_when_missing(tmp_path):
    # No human_resp directory — returns None.
    assert compute_opinionsqa_subgroup_ceilings(data_dir=str(tmp_path)) is None


def test_subgroup_ceilings_computes_per_wave_attribute_group(tmp_path, monkeypatch):
    """Synthetic fixture: two waves × one attribute × two groups each."""
    human_resp = tmp_path / "raw" / "human_resp"
    human_resp.mkdir(parents=True)

    mc = ["Agree", "Disagree", "Refused"]
    _write_synthetic_wave(
        human_resp,
        wave=26,
        attribute="EDUCATION",
        groups={"College graduate": 800, "High school graduate": 450},
        mc_options=mc,
    )
    _write_synthetic_wave(
        human_resp,
        wave=32,
        attribute="EDUCATION",
        groups={"College graduate": 600, "High school graduate": 100},
        mc_options=mc,
    )

    # Restrict PEW_WAVES so the function only visits our fixture waves.
    monkeypatch.setattr("synthbench.datasets.opinionsqa.PEW_WAVES", [26, 32])

    out = compute_opinionsqa_subgroup_ceilings(data_dir=str(tmp_path), n_bootstrap=100)
    assert out is not None
    assert out["granularity"] == "wave_attribute_group"
    assert out["n_subgroups"] == 4  # 2 waves × 2 groups
    # Every row has wave/attribute/group identifiers.
    rows = out["per_subgroup"]
    keys = {(r["wave"], r["attribute"], r["group"]) for r in rows}
    assert ("ATP W26", "EDUCATION", "College graduate") in keys
    assert ("ATP W32", "EDUCATION", "High school graduate") in keys
    # Distribution keys are emitted.
    for k in ("min", "p25", "median", "p75", "max"):
        assert k in out["distribution"]
    assert 0.0 <= out["distribution"]["min"] <= out["distribution"]["max"] <= 1.0
    # Median also surfaced as the reference ceiling for P_sub.
    assert out["subgroup_ceiling_for_psub"] == out["distribution"]["median"]


def test_subgroup_ceilings_worst_5_are_lowest(tmp_path, monkeypatch):
    human_resp = tmp_path / "raw" / "human_resp"
    human_resp.mkdir(parents=True)

    mc = ["A", "B", "C"]
    # Six groups with varying n. Smaller n -> lower ceiling.
    _write_synthetic_wave(
        human_resp,
        wave=26,
        attribute="EDUCATION",
        groups={
            "G1_big": 5000,
            "G2_big": 4500,
            "G3_mid": 800,
            "G4_mid": 700,
            "G5_small": 90,
            "G6_small": 60,
        },
        mc_options=mc,
    )
    monkeypatch.setattr("synthbench.datasets.opinionsqa.PEW_WAVES", [26])

    out = compute_opinionsqa_subgroup_ceilings(data_dir=str(tmp_path), n_bootstrap=100)
    assert out is not None
    assert len(out["worst_5_subgroups"]) == 5
    worst_means = [r["ceiling"]["mean"] for r in out["worst_5_subgroups"]]
    # Worst-5 list is sorted ascending by ceiling mean.
    assert worst_means == sorted(worst_means)
    # The 5 smallest-n groups dominate the worst list (G6_small is worst).
    assert out["worst_5_subgroups"][0]["group"] == "G6_small"


def test_subgroup_ceilings_quality_flag_downgrade_for_small_n(tmp_path, monkeypatch):
    """Groups with n<200 (Cochran) must still be emitted but flagged 'low'."""
    human_resp = tmp_path / "raw" / "human_resp"
    human_resp.mkdir(parents=True)

    mc = ["Yes", "No"]
    _write_synthetic_wave(
        human_resp,
        wave=26,
        attribute="RACE",
        groups={"Big": 800, "Small": 80},  # small < 200 -> low flag
        mc_options=mc,
    )
    monkeypatch.setattr("synthbench.datasets.opinionsqa.PEW_WAVES", [26])

    out = compute_opinionsqa_subgroup_ceilings(data_dir=str(tmp_path), n_bootstrap=100)
    assert out is not None

    flags = {
        (r["attribute"], r["group"]): r["ceiling"]["quality_flag"]
        for r in out["per_subgroup"]
    }
    assert flags[("RACE", "Big")] == "high"
    assert flags[("RACE", "Small")] == "low"
    # Quality breakdown totals equal n_subgroups.
    total = sum(out["quality_breakdown"].values())
    assert total == out["n_subgroups"]


def test_subgroup_ceilings_handles_cross_cut_nested_files(tmp_path, monkeypatch):
    """Cross-cut files like POLPARTY_SEX nest one level deeper; labels flatten."""
    import json

    human_resp = tmp_path / "raw" / "human_resp"
    wave_dir = human_resp / "American_Trends_Panel_W26"
    wave_dir.mkdir(parents=True)

    mc = ["Yes", "No"]
    payload = {
        "Q_W26": {
            "MC_options": mc,
            "question_text": "Cross-cut test",
            "Democrat": {
                "Female": {"Yes": 200.0, "No": 300.0},
                "Male": {"Yes": 180.0, "No": 260.0},
            },
            "Republican": {
                "Female": {"Yes": 150.0, "No": 260.0},
                "Male": {"Yes": 140.0, "No": 240.0},
            },
        }
    }
    with open(wave_dir / "POLPARTY_SEX_data.json", "w") as f:
        json.dump(payload, f)
    monkeypatch.setattr("synthbench.datasets.opinionsqa.PEW_WAVES", [26])

    out = compute_opinionsqa_subgroup_ceilings(data_dir=str(tmp_path), n_bootstrap=50)
    assert out is not None
    groups = {r["group"] for r in out["per_subgroup"]}
    # Compound labels flatten to "<outer> × <inner>".
    assert "Democrat × Female" in groups
    assert "Republican × Male" in groups
    # All four cross-cut cells emitted.
    assert len(groups) == 4


def test_subgroup_ceilings_skips_aggregate_none_data(tmp_path, monkeypatch):
    """NONE_data.json is the wave-aggregate and must NOT be included."""
    human_resp = tmp_path / "raw" / "human_resp"
    wave_dir = human_resp / "American_Trends_Panel_W26"
    wave_dir.mkdir(parents=True)

    import json

    mc = ["Yes", "No"]
    # Only NONE_data.json present -> no per-subgroup files -> no rows.
    payload = {
        "Q_W26": {
            "MC_options": mc,
            "question_text": "Q",
            "Democrat": {"Yes": 400.0, "No": 400.0},
        }
    }
    with open(wave_dir / "NONE_data.json", "w") as f:
        json.dump(payload, f)
    monkeypatch.setattr("synthbench.datasets.opinionsqa.PEW_WAVES", [26])

    out = compute_opinionsqa_subgroup_ceilings(data_dir=str(tmp_path), n_bootstrap=50)
    assert out is None


def test_multinomial_half_sample_jsd_shape():
    """Sanity: JSD between two half-samples of the same distribution is small."""
    import numpy as np

    rng = np.random.default_rng(0)
    p = [0.5, 0.3, 0.2]
    n = 1000
    keys = ["A", "B", "C"]

    draws = []
    for _ in range(50):
        a = rng.multinomial(n, p)
        b = rng.multinomial(n, p)
        dist_a = {k: float(a[i]) / n for i, k in enumerate(keys)}
        dist_b = {k: float(b[i]) / n for i, k in enumerate(keys)}
        draws.append(jensen_shannon_divergence(dist_a, dist_b))

    mean_jsd = sum(draws) / len(draws)
    # JSD should be small (well under 0.01) for n=1000
    assert mean_jsd < 0.01
    assert mean_jsd > 0.0
