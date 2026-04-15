"""Tests for run_validity: detection of uniform-distribution garbage runs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from synthbench.run_validity import (
    REFUSAL_RATE_THRESHOLD,
    UNIFORM_FRACTION_THRESHOLD,
    UNIFORMITY_EPSILON,
    compute_uniformity_metrics,
    is_invalid_run,
    run_identity,
    uniformity_score,
)

LEADERBOARD_DIR = Path(__file__).resolve().parent.parent / "leaderboard-results"
BAD_RUN = (
    LEADERBOARD_DIR / "subpop_synthpanel_claude-haiku-4-5-20251001_20260411_073013.json"
)
GOOD_RUN_GLOB = "globalopinionqa_openrouter_anthropic_claude-haiku-4-5_*.json"


def _make_result(
    per_question: list[dict],
    *,
    provider: str = "test/provider",
    dataset: str = "opinionsqa",
) -> dict:
    return {
        "benchmark": "synthbench",
        "timestamp": "2026-04-15T00:00:00Z",
        "config": {
            "provider": provider,
            "dataset": dataset,
            "samples_per_question": 30,
            "n_evaluated": len(per_question),
        },
        "per_question": per_question,
    }


def _uniform_q(key: str, n_options: int = 4, refusal: float = 0.0) -> dict:
    prob = 1.0 / n_options
    dist = {f"opt{i}": prob for i in range(n_options)}
    return {
        "key": key,
        "model_distribution": dist,
        "model_refusal_rate": refusal,
    }


def _healthy_q(key: str, refusal: float = 0.0) -> dict:
    return {
        "key": key,
        "model_distribution": {"A": 0.6, "B": 0.25, "C": 0.1, "D": 0.05},
        "model_refusal_rate": refusal,
    }


class TestUniformityScore:
    def test_perfectly_uniform_four_options(self):
        assert uniformity_score({"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}) == 0.0

    def test_perfectly_uniform_three_options(self):
        # 1/3 with float rounding
        dist = {"A": 1 / 3, "B": 1 / 3, "C": 1 / 3}
        assert uniformity_score(dist) < 1e-9

    def test_skewed_distribution(self):
        # A=0.5, B=0.5 on 2 options is uniform
        assert uniformity_score({"A": 0.5, "B": 0.5}) == pytest.approx(0.0)
        # A=1.0, B=0.0 is maximally non-uniform for n=2: |1.0-0.5|=0.5
        assert uniformity_score({"A": 1.0, "B": 0.0}) == pytest.approx(0.5)

    def test_empty_dist_is_not_uniform(self):
        # Missing/empty distributions return 1.0 so they don't trigger the
        # invalid-run detector (we don't want to confuse "missing" with "uniform").
        assert uniformity_score(None) == 1.0
        assert uniformity_score({}) == 1.0

    def test_bad_values_are_not_uniform(self):
        # Non-numeric values shouldn't crash and shouldn't be flagged uniform.
        assert uniformity_score({"A": "oops", "B": 0.5}) == 1.0


class TestComputeUniformityMetrics:
    def test_all_uniform_run(self):
        pq = [_uniform_q(f"Q{i}") for i in range(20)]
        metrics = compute_uniformity_metrics(_make_result(pq))
        assert metrics == {
            "n_questions": 20,
            "n_uniform_questions": 20,
            "uniform_fraction": 1.0,
            "refusal_rate": 0.0,
        }

    def test_healthy_run(self):
        pq = [_healthy_q(f"Q{i}") for i in range(20)]
        metrics = compute_uniformity_metrics(_make_result(pq))
        assert metrics["n_uniform_questions"] == 0
        assert metrics["uniform_fraction"] == 0.0

    def test_mixed_run(self):
        pq = [_uniform_q(f"U{i}") for i in range(8)]
        pq += [_healthy_q(f"H{i}") for i in range(2)]
        metrics = compute_uniformity_metrics(_make_result(pq))
        assert metrics["n_uniform_questions"] == 8
        assert metrics["n_questions"] == 10
        assert metrics["uniform_fraction"] == pytest.approx(0.8)

    def test_refusal_rate_averaged(self):
        pq = [_uniform_q(f"Q{i}", refusal=0.3) for i in range(10)]
        metrics = compute_uniformity_metrics(_make_result(pq))
        assert metrics["refusal_rate"] == pytest.approx(0.3)

    def test_missing_per_question_is_empty(self):
        metrics = compute_uniformity_metrics({"benchmark": "synthbench"})
        assert metrics["n_questions"] == 0
        assert metrics["uniform_fraction"] == 0.0

    def test_non_numeric_refusal_skipped(self):
        pq = [_uniform_q("Q0")]
        pq[0]["model_refusal_rate"] = "nan"  # type: ignore[assignment]
        metrics = compute_uniformity_metrics(_make_result(pq))
        assert metrics["refusal_rate"] == 0.0


class TestIsInvalidRun:
    def test_bad_sb_knd_reproducer_flagged(self):
        """Real-world fixture from the sb-knd bug report must be flagged."""
        if not BAD_RUN.exists():
            pytest.skip(f"Fixture missing: {BAD_RUN}")
        data = json.loads(BAD_RUN.read_text())
        invalid, reason, metrics = is_invalid_run(data)
        assert invalid is True
        assert reason.startswith("uniform-garbage:")
        # Sanity: the real run has ~160/200 uniform questions
        assert metrics["n_uniform_questions"] >= int(0.75 * metrics["n_questions"])

    def test_healthy_goqa_haiku_not_flagged(self):
        """A known-good haiku run must pass through untouched."""
        matches = sorted(LEADERBOARD_DIR.glob(GOOD_RUN_GLOB))
        if not matches:
            pytest.skip(f"No fixture matching {GOOD_RUN_GLOB}")
        data = json.loads(matches[0].read_text())
        invalid, reason, metrics = is_invalid_run(data)
        assert invalid is False, f"False positive on good run: {reason}"
        assert reason == ""

    def test_all_healthy_synthetic(self):
        pq = [_healthy_q(f"Q{i}") for i in range(30)]
        invalid, reason, _ = is_invalid_run(_make_result(pq))
        assert invalid is False
        assert reason == ""

    def test_all_uniform_synthetic_flagged(self):
        pq = [_uniform_q(f"Q{i}") for i in range(30)]
        invalid, reason, metrics = is_invalid_run(_make_result(pq))
        assert invalid is True
        assert "30/30" in reason
        assert metrics["uniform_fraction"] == 1.0

    def test_uniform_but_refusing_not_flagged(self):
        """A run with uniform-looking dists that ARE legitimate refusals
        (refusal_rate > threshold) should not be flagged."""
        pq = [_uniform_q(f"Q{i}", refusal=0.9) for i in range(30)]
        invalid, reason, _ = is_invalid_run(_make_result(pq))
        assert invalid is False
        assert reason == ""

    def test_small_run_skipped(self):
        """Runs below min_questions threshold pass through silently."""
        pq = [_uniform_q(f"Q{i}") for i in range(5)]
        invalid, reason, _ = is_invalid_run(_make_result(pq))
        assert invalid is False
        assert reason == ""

    def test_below_uniform_fraction_threshold(self):
        # 70% uniform — below the 80% floor — should not fire.
        pq = [_uniform_q(f"U{i}") for i in range(14)]
        pq += [_healthy_q(f"H{i}") for i in range(6)]
        invalid, _reason, metrics = is_invalid_run(_make_result(pq))
        assert invalid is False
        assert metrics["uniform_fraction"] == pytest.approx(0.7)

    def test_threshold_constants_sane(self):
        assert 0.0 < UNIFORMITY_EPSILON < 0.1
        assert 0.5 <= UNIFORM_FRACTION_THRESHOLD <= 0.95
        assert 0.0 <= REFUSAL_RATE_THRESHOLD <= 0.05


class TestRunIdentity:
    def test_extracts_config_fields(self):
        data = _make_result([_healthy_q("Q0")], provider="prov/x", dataset="gss")
        ident = run_identity(data)
        assert ident["provider"] == "prov/x"
        assert ident["dataset"] == "gss"
        assert ident["samples_per_question"] == 30
        assert ident["timestamp"] == "2026-04-15T00:00:00Z"

    def test_missing_config_degrades_gracefully(self):
        ident = run_identity({"benchmark": "synthbench"})
        assert ident["provider"] is None
        assert ident["dataset"] is None
