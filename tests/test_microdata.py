"""Microdata + real-sampling convergence tests.

Covers:
  * GSS microdata loader (long-form CSV ingestion + filter)
  * Real-sampling curve shape vs. bootstrap floor
  * compare CLI/orchestration emits both curves
  * Redistribution policy surfaces correctly on real/compare payloads
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from click.testing import CliRunner

from synthbench.cli import main
from synthbench.convergence.curves import compute_curve
from synthbench.convergence.real_sampling import (
    compute_real_curve,
    respondent_distribution,
    subsample_distribution,
)
from synthbench.datasets.base import Dataset, MicrodataNotAvailable, MicrodataRow
from synthbench.datasets.gss import DatasetDownloadError, GSSDataset

FIXTURE_CSV = Path(__file__).parent / "fixtures" / "microdata" / "gss_microdata.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _install_microdata(data_dir: Path) -> None:
    target = data_dir / "microdata" / "gss_microdata.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE_CSV, target)


def _seed_aggregate_questions(data_dir: Path) -> None:
    """Drop a tiny aggregate cache so dataset.load() works alongside microdata."""
    raw = data_dir / "raw" / "gss_aggregated.csv"
    raw.parent.mkdir(parents=True, exist_ok=True)
    with open(raw, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["question_id", "question_text", "year", "option", "count"])
        for opt, count in [("Yes", 75), ("No", 45)]:
            w.writerow(["SPKATH", "Allow speech?", "2018", opt, count])
            w.writerow(["SPKATH", "Allow speech?", "2022", opt, count])
        for opt, count in [
            ("StronglyAgree", 40),
            ("Agree", 30),
            ("Disagree", 20),
            ("StronglyDisagree", 10),
        ]:
            w.writerow(["ABANY", "Abortion?", "2018", opt, count])
            w.writerow(["ABANY", "Abortion?", "2022", opt, count])


# ---------------------------------------------------------------------------
# Microdata shape
# ---------------------------------------------------------------------------


def test_load_microdata_returns_rows_with_expected_shape(tmp_path: Path):
    _install_microdata(tmp_path)
    rows = GSSDataset(data_dir=tmp_path).load_microdata()

    assert len(rows) == 120  # 60 respondents per year × 2 years
    assert all(isinstance(r, MicrodataRow) for r in rows)
    sample = rows[0]
    assert sample.respondent_id and "@" in sample.respondent_id
    assert sample.survey_wave.startswith("GSS:")
    assert set(sample.responses).issubset({"GSS_SPKATH", "GSS_ABANY"})
    # Subgroup labels round-tripped from the CSV's subgroup_* columns.
    assert sample.subgroup.get("age_band") in {"18-29", "30-44", "45-64", "65+"}


def test_load_microdata_filters_by_year(tmp_path: Path):
    _install_microdata(tmp_path)
    rows = GSSDataset(data_dir=tmp_path, year=2022).load_microdata()
    assert len(rows) == 60
    assert all(r.survey_wave == "GSS:2022" for r in rows)


def test_load_microdata_for_question_accepts_bare_or_prefixed_key(tmp_path: Path):
    _install_microdata(tmp_path)
    ds = GSSDataset(data_dir=tmp_path)
    bare = ds.load_microdata_for_question("SPKATH")
    prefixed = ds.load_microdata_for_question("GSS_SPKATH")
    assert len(bare) == 120
    assert len(prefixed) == 120


def test_load_microdata_n_truncates(tmp_path: Path):
    _install_microdata(tmp_path)
    rows = GSSDataset(data_dir=tmp_path).load_microdata(n=25)
    assert len(rows) == 25


def test_load_microdata_raises_when_missing(tmp_path: Path):
    ds = GSSDataset(data_dir=tmp_path)
    with pytest.raises(DatasetDownloadError, match="microdata requires manual setup"):
        ds.load_microdata()


def test_load_microdata_rejects_csv_missing_columns(tmp_path: Path):
    target = tmp_path / "microdata" / "gss_microdata.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("respondent_id,question_id\nR1,SPKATH\n")
    with pytest.raises(DatasetDownloadError, match="missing columns"):
        GSSDataset(data_dir=tmp_path).load_microdata()


# ---------------------------------------------------------------------------
# Default Dataset.load_microdata raises MicrodataNotAvailable
# ---------------------------------------------------------------------------


def test_default_load_microdata_raises_not_available():
    class _Aggregate(Dataset):
        @property
        def name(self):
            return "fixture_agg"

        def load(self, n=None):
            return []

        def info(self):
            return {}

    with pytest.raises(MicrodataNotAvailable):
        _Aggregate().load_microdata()


# ---------------------------------------------------------------------------
# Real-sampling primitives
# ---------------------------------------------------------------------------


def _toy_rows(n_yes: int, n_no: int) -> list[MicrodataRow]:
    rows: list[MicrodataRow] = []
    for i in range(n_yes):
        rows.append(
            MicrodataRow(
                respondent_id=f"y{i}",
                survey_wave="X",
                responses={"Q": "Yes"},
            )
        )
    for i in range(n_no):
        rows.append(
            MicrodataRow(
                respondent_id=f"n{i}",
                survey_wave="X",
                responses={"Q": "No"},
            )
        )
    return rows


def test_respondent_distribution_normalizes_eligible_respondents():
    rows = _toy_rows(30, 70)
    dist = respondent_distribution(rows, "Q")
    assert dist == {"Yes": 0.3, "No": 0.7}


def test_respondent_distribution_empty_when_question_unanswered():
    rows = _toy_rows(5, 5)
    assert respondent_distribution(rows, "OTHER") == {}


def test_subsample_returns_none_when_pool_smaller_than_n():
    rows = _toy_rows(5, 5)
    rng = np.random.default_rng(0)
    assert subsample_distribution(rows, "Q", n=20, rng=rng) is None


def test_subsample_without_replacement_caps_at_pool_proportions():
    """Drawing the entire pool exactly recovers the population counts."""
    rows = _toy_rows(40, 60)
    rng = np.random.default_rng(0)
    counts = subsample_distribution(rows, "Q", n=100, rng=rng)
    assert counts == {"Yes": 40, "No": 60}


def test_compute_real_curve_skips_sample_sizes_exceeding_pool():
    rows = _toy_rows(10, 10)
    curve = compute_real_curve(
        rows,
        question_key="Q",
        sample_sizes=(5, 50),
        B=10,
        rng=0,
    )
    # Only n=5 fits the pool; n=50 silently dropped.
    assert [p.n for p in curve] == [5]


# ---------------------------------------------------------------------------
# Curve shape: real differs from bootstrap (the marketable claim)
# ---------------------------------------------------------------------------


def test_real_sampling_curve_differs_from_bootstrap(tmp_path: Path):
    """Real sampling and aggregate bootstrap should not produce identical curves.

    The aggregate distribution collapses inter-wave drift in the GSS fixture
    (2018 vs 2022 differ on SPKATH). Real sub-sampling carries that
    heterogeneity into each replicate, so the curve mean is not the
    idealized 1/sqrt(n) floor.
    """
    _install_microdata(tmp_path)
    rows = GSSDataset(data_dir=tmp_path).load_microdata()
    full = respondent_distribution(rows, "GSS_SPKATH")

    real = compute_real_curve(
        rows,
        question_key="GSS_SPKATH",
        sample_sizes=(20, 50),
        B=200,
        rng=7,
    )
    boot = compute_curve(full, sample_sizes=(20, 50), B=200, rng=7)

    real_means = [p.jsd_mean for p in real]
    boot_means = [p.jsd_mean for p in boot]
    assert real_means != boot_means
    # And both curves should descend with n in expectation.
    assert real_means[0] > real_means[-1]
    assert boot_means[0] > boot_means[-1]


# ---------------------------------------------------------------------------
# CLI integration: real + compare
# ---------------------------------------------------------------------------


@pytest.fixture
def gss_with_microdata(tmp_path: Path, monkeypatch):
    """Patch GSSDataset to use a temp data_dir wired to the fixture microdata."""
    _install_microdata(tmp_path)
    _seed_aggregate_questions(tmp_path)

    class _PatchedGSS(GSSDataset):
        def __init__(self, data_dir=None, year=None):
            super().__init__(data_dir=tmp_path, year=year)

    from synthbench.datasets import DATASETS

    patched = dict(DATASETS)
    patched["gss"] = _PatchedGSS
    monkeypatch.setattr("synthbench.datasets.DATASETS", patched)
    monkeypatch.setattr("synthbench.convergence.cli_report.DATASETS", patched)
    monkeypatch.setattr("synthbench.datasets.policy.DATASETS", patched)
    return tmp_path


def test_cli_real_emits_curve(gss_with_microdata, tmp_path: Path):
    out = tmp_path / "real.json"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "convergence",
            "real",
            "--dataset",
            "gss",
            "--question",
            "SPKATH",
            "--output",
            str(out),
            "--bootstraps",
            "30",
            "--sample-sizes",
            "20,50,100",
            "--seed",
            "3",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text())
    assert payload["mode"] == "real"
    assert payload["question_key"] == "GSS_SPKATH"
    assert payload["redistribution_policy"] == "full"
    assert payload["n_respondents"] == 120
    assert {p["n"] for p in payload["real_curve"]} == {20, 50, 100}


def test_cli_real_errors_when_microdata_missing(tmp_path, monkeypatch):
    """opinionsqa has no microdata adapter; CLI must surface a clean error."""
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "convergence",
            "real",
            "--dataset",
            "opinionsqa",
            "--question",
            "any-key",
        ],
    )
    assert result.exit_code != 0
    assert (
        "does not provide microdata" in result.output or "no question" in result.output
    )


def test_compare_produces_both_curves(gss_with_microdata, tmp_path: Path):
    out = tmp_path / "compare.json"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "convergence",
            "compare",
            "--dataset",
            "gss",
            "--question",
            "SPKATH",
            "--output",
            str(out),
            "--bootstraps",
            "30",
            "--sample-sizes",
            "20,50",
            "--seed",
            "11",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text())
    assert payload["mode"] == "compare"
    assert {p["n"] for p in payload["bootstrap_curve"]} == {20, 50}
    assert {p["n"] for p in payload["real_curve"]} == {20, 50}
    assert {d["n"] for d in payload["delta_jsd_mean"]} == {20, 50}


# ---------------------------------------------------------------------------
# License compliance: redistribution_policy surfaces from the adapter
# ---------------------------------------------------------------------------


def test_redistribution_policy_enforced_for_gated_datasets(
    gss_with_microdata, tmp_path: Path, monkeypatch
):
    """When the adapter declares ``gated``, the payload reflects it.

    The real/compare CLI is built on the same policy_for() lookup the
    bootstrap CLI uses, so flipping the underlying adapter's policy must
    propagate to the emitted artifact metadata.
    """
    from synthbench.datasets import DATASETS

    monkeypatch.setattr(DATASETS["gss"], "redistribution_policy", "gated")
    monkeypatch.setattr(
        DATASETS["gss"], "license_url", "https://example.test/gated-license"
    )

    from synthbench.convergence.cli_report import run_compare

    payload = run_compare(
        dataset_name="gss",
        question_key="SPKATH",
        bootstraps=10,
        sample_sizes="20",
        seed=1,
    )
    assert payload["redistribution_policy"] == "gated"
    assert payload["license_url"] == "https://example.test/gated-license"
