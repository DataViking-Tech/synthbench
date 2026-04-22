"""Tests for bootstrap convergence curves."""

from __future__ import annotations

import json

import numpy as np
import pytest
from click.testing import CliRunner

from synthbench.cli import main
from synthbench.convergence import (
    CurvePoint,
    bootstrap_sample,
    compute_curve,
    empirical_distribution,
    find_convergence_n,
)
from synthbench.convergence.cli_report import (
    build_payload,
    compute_reports,
    run_bootstrap,
)
from synthbench.datasets.base import Dataset, Question


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

UNIFORM_FOUR = {"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}
SKEWED_FOUR = {"a": 0.6, "b": 0.2, "c": 0.15, "d": 0.05}


@pytest.fixture
def fixture_question() -> Question:
    """Small deterministic distribution for curve-shape tests."""
    return Question(
        key="FIXTURE_UNIFORM4",
        text="A synthetic uniform four-option question.",
        options=["a", "b", "c", "d"],
        human_distribution=dict(UNIFORM_FOUR),
        survey="fixture",
    )


@pytest.fixture
def fixture_questions(fixture_question: Question) -> list[Question]:
    return [
        fixture_question,
        Question(
            key="FIXTURE_SKEWED4",
            text="A synthetic skewed four-option question.",
            options=["a", "b", "c", "d"],
            human_distribution=dict(SKEWED_FOUR),
            survey="fixture",
        ),
    ]


# ---------------------------------------------------------------------------
# bootstrap.py
# ---------------------------------------------------------------------------


def test_bootstrap_sample_sums_to_n():
    rng = np.random.default_rng(0)
    sample = bootstrap_sample(UNIFORM_FOUR, 100, rng)
    assert sum(sample.values()) == 100
    assert set(sample) == set(UNIFORM_FOUR)


def test_bootstrap_sample_zero_n_returns_zero_counts():
    sample = bootstrap_sample(UNIFORM_FOUR, 0, np.random.default_rng(0))
    assert sample == {k: 0 for k in UNIFORM_FOUR}


def test_empirical_distribution_normalizes():
    emp = empirical_distribution({"a": 3, "b": 1})
    assert emp == {"a": 0.75, "b": 0.25}


def test_empirical_distribution_zero_total():
    emp = empirical_distribution({"a": 0, "b": 0})
    assert emp == {"a": 0.0, "b": 0.0}


# ---------------------------------------------------------------------------
# curves.py: required "monotonic decreasing in expectation"
# ---------------------------------------------------------------------------


def test_curve_monotonic_decreasing_in_expectation():
    """On a uniform distribution, bootstrap JSD must trend down as n grows.

    Monotonic in expectation means: averaged over B bootstraps, jsd_mean at
    small n exceeds jsd_mean at large n, even though individual bootstraps
    can blip up or down. We use widely separated sample sizes (20 vs 5000)
    so the trend dominates Monte Carlo noise at B=500.
    """
    curve = compute_curve(
        UNIFORM_FOUR,
        sample_sizes=(20, 50, 200, 1000, 5000),
        B=500,
        rng=42,
    )
    means = [p.jsd_mean for p in curve]
    assert means[0] > means[-1], (
        f"Expected jsd_mean to decrease with n, got curve {means}"
    )
    # Endpoint should match the ~1/sqrt(n) floor: at n=5000 over a uniform
    # 4-way distribution, mean JSD is comfortably below 0.01.
    assert curve[-1].jsd_mean < 0.01, (
        f"n=5000 should have settled well below 0.01, got {curve[-1].jsd_mean}"
    )
    # p10 <= mean <= p90 at every point
    for p in curve:
        assert p.jsd_p10 <= p.jsd_mean <= p.jsd_p90


def test_curve_identical_when_seeded():
    a = compute_curve(UNIFORM_FOUR, sample_sizes=(100, 500), B=50, rng=7)
    b = compute_curve(UNIFORM_FOUR, sample_sizes=(100, 500), B=50, rng=7)
    assert [p.jsd_mean for p in a] == [p.jsd_mean for p in b]


# ---------------------------------------------------------------------------
# thresholds.py
# ---------------------------------------------------------------------------


def _synthetic_curve(values: list[float]) -> list[CurvePoint]:
    return [
        CurvePoint(n=(i + 1) * 100, jsd_mean=v, jsd_p10=v, jsd_p90=v, bootstrap_B=1)
        for i, v in enumerate(values)
    ]


def test_convergence_n_returns_smallest_stable_n():
    """Smallest n where mean < epsilon AND next 2 sample points stay flat."""
    # Still falling at index 1 (0.03 -> 0.015 drops 0.015 > delta=0.005),
    # so index 1 is disqualified. Index 2 = 0.015 is below 0.02 and the next
    # two drops are within delta. Expected n = 300.
    curve = _synthetic_curve([0.05, 0.03, 0.015, 0.013, 0.012, 0.011])
    assert find_convergence_n(curve, epsilon=0.02, delta=0.005) == 300


def test_convergence_n_none_when_never_stable():
    # All points above epsilon
    curve = _synthetic_curve([0.1, 0.09, 0.08, 0.07])
    assert find_convergence_n(curve, epsilon=0.02) is None


def test_convergence_n_none_when_curve_too_short_for_tail():
    # Below epsilon, but only one follow-up point — can't evaluate "next 2"
    curve = _synthetic_curve([0.05, 0.01, 0.009])
    assert find_convergence_n(curve, epsilon=0.02) is None


# ---------------------------------------------------------------------------
# cli_report.py: policy gating
# ---------------------------------------------------------------------------


def test_curve_respects_redistribution_policy(fixture_questions, monkeypatch):
    """Switching policy rewrites the payload without re-running bootstraps."""
    reports = compute_reports(
        fixture_questions,
        sample_sizes=(100, 500, 1000),
        B=30,
        rng=11,
    )

    from synthbench.convergence import cli_report
    from synthbench.datasets.policy import DatasetPolicy

    def make_stub(tier):
        def stub(_name):
            return DatasetPolicy(
                name="fixture",
                redistribution_policy=tier,
                license_url=None,
                citation=None,
            )

        return stub

    # full: questions + summary intact
    monkeypatch.setattr(cli_report, "policy_for", make_stub("full"))
    payload = build_payload(
        "fixture",
        reports,
        sample_sizes=(100, 500, 1000),
        B=30,
        epsilon=0.02,
        delta=0.005,
    )
    assert payload["redistribution_policy"] == "full"
    assert len(payload["questions"]) == 2
    assert payload["questions"][0]["human_distribution"]
    assert payload["summary"]["n_questions"] == 2

    # gated: still ships per-question (gated routes to R2 at publish time)
    monkeypatch.setattr(cli_report, "policy_for", make_stub("gated"))
    payload = build_payload(
        "fixture",
        reports,
        sample_sizes=(100, 500, 1000),
        B=30,
        epsilon=0.02,
        delta=0.005,
    )
    assert payload["redistribution_policy"] == "gated"
    assert len(payload["questions"]) == 2

    # aggregates_only: questions stripped, summary preserved
    monkeypatch.setattr(cli_report, "policy_for", make_stub("aggregates_only"))
    payload = build_payload(
        "fixture",
        reports,
        sample_sizes=(100, 500, 1000),
        B=30,
        epsilon=0.02,
        delta=0.005,
    )
    assert payload["redistribution_policy"] == "aggregates_only"
    assert payload["questions"] == []
    assert payload["summary"]["n_questions"] == 2
    assert "suppressed" in payload

    # citation_only: both suppressed
    monkeypatch.setattr(cli_report, "policy_for", make_stub("citation_only"))
    payload = build_payload(
        "fixture",
        reports,
        sample_sizes=(100, 500, 1000),
        B=30,
        epsilon=0.02,
        delta=0.005,
    )
    assert payload["redistribution_policy"] == "citation_only"
    assert payload["questions"] == []
    assert payload["summary"] is None
    assert "suppressed" in payload


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------


class _FixtureDataset(Dataset):
    """Tiny in-memory dataset registered under an ephemeral name for the CLI test."""

    redistribution_policy = "full"
    license_url = "https://example.test/license"
    citation = "Fixture dataset for tests."

    @property
    def name(self) -> str:
        return "fixture_bootstrap"

    def load(self, n: int | None = None):
        qs = [
            Question(
                key="F_UNIFORM4",
                text="Uniform four-option fixture.",
                options=["a", "b", "c", "d"],
                human_distribution=dict(UNIFORM_FOUR),
                survey="fixture",
            ),
            Question(
                key="F_SKEWED4",
                text="Skewed four-option fixture.",
                options=["a", "b", "c", "d"],
                human_distribution=dict(SKEWED_FOUR),
                survey="fixture",
            ),
        ]
        return qs if n is None else qs[:n]

    def info(self) -> dict:
        return {"name": self.name, "n_questions": 2}


@pytest.fixture
def registered_fixture_dataset(monkeypatch):
    from synthbench.datasets import DATASETS

    patched = dict(DATASETS)
    patched["fixture_bootstrap"] = _FixtureDataset
    monkeypatch.setattr("synthbench.datasets.DATASETS", patched)
    monkeypatch.setattr("synthbench.convergence.cli_report.DATASETS", patched)
    monkeypatch.setattr("synthbench.datasets.policy.DATASETS", patched)
    return patched


def test_cli_bootstrap_produces_json_and_plot(registered_fixture_dataset, tmp_path):
    """--output writes JSON; --plot writes a sibling PDF (when matplotlib available)."""
    matplotlib = pytest.importorskip("matplotlib")
    del matplotlib  # only needed for the availability check

    out_json = tmp_path / "fixture.json"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "convergence",
            "bootstrap",
            "--dataset",
            "fixture_bootstrap",
            "--output",
            str(out_json),
            "--bootstraps",
            "30",
            "--sample-sizes",
            "50,200,1000",
            "--plot",
            "--seed",
            "3",
        ],
    )
    assert result.exit_code == 0, result.output

    assert out_json.exists()
    payload = json.loads(out_json.read_text())
    assert payload["dataset"] == "fixture_bootstrap"
    assert payload["redistribution_policy"] == "full"
    assert payload["parameters"]["bootstrap_B"] == 30
    assert payload["parameters"]["sample_sizes"] == [50, 200, 1000]
    assert len(payload["questions"]) == 2
    q = payload["questions"][0]
    assert {"key", "text", "human_distribution", "curve", "convergence_n"} <= set(q)
    assert len(q["curve"]) == 3
    assert {"n", "jsd_mean", "jsd_p10", "jsd_p90", "bootstrap_B"} <= set(q["curve"][0])

    pdf = out_json.with_suffix(".pdf")
    assert pdf.exists()
    assert pdf.stat().st_size > 0


def test_cli_bootstrap_unknown_dataset_errors():
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["convergence", "bootstrap", "--dataset", "nonexistent_dataset_xyz"],
    )
    assert result.exit_code != 0
    assert "unknown dataset" in result.output


def test_run_bootstrap_filters_to_single_question(registered_fixture_dataset, tmp_path):
    payload, _ = run_bootstrap(
        dataset_name="fixture_bootstrap",
        question_key="F_SKEWED4",
        output=None,
        bootstraps=20,
        sample_sizes="100,500",
        seed=5,
    )
    assert len(payload["questions"]) == 1
    assert payload["questions"][0]["key"] == "F_SKEWED4"


def test_run_bootstrap_plot_requires_output(registered_fixture_dataset):
    with pytest.raises(ValueError, match="--plot requires --output"):
        run_bootstrap(
            dataset_name="fixture_bootstrap",
            output=None,
            plot=True,
            bootstraps=10,
            sample_sizes="100",
            seed=1,
        )


def test_run_bootstrap_unknown_question_errors(registered_fixture_dataset):
    with pytest.raises(ValueError, match="no question with key"):
        run_bootstrap(
            dataset_name="fixture_bootstrap",
            question_key="does-not-exist",
            bootstraps=10,
            sample_sizes="100",
            seed=1,
        )
