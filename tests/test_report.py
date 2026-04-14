"""Tests for score card generation."""

from __future__ import annotations

import json

import pytest

from synthbench.runner import BenchmarkResult, QuestionResult
from synthbench.report import normalize_distribution, to_json, to_markdown


@pytest.fixture
def sample_result():
    questions = [
        QuestionResult(
            key="Q1",
            text="Do you support X?",
            options=["Yes", "No"],
            human_distribution={"Yes": 0.6, "No": 0.4},
            model_distribution={"Yes": 0.7, "No": 0.3},
            jsd=0.015,
            kendall_tau=1.0,
            parity=0.95,
            n_samples=30,
        ),
        QuestionResult(
            key="Q2",
            text="How do you feel about Y?",
            options=["Good", "Neutral", "Bad"],
            human_distribution={"Good": 0.3, "Neutral": 0.4, "Bad": 0.3},
            model_distribution={"Good": 0.5, "Neutral": 0.3, "Bad": 0.2},
            jsd=0.08,
            kendall_tau=0.67,
            parity=0.78,
            n_samples=30,
        ),
    ]
    return BenchmarkResult(
        provider_name="test/mock",
        dataset_name="test",
        questions=questions,
        config={"samples_per_question": 30, "n_evaluated": 2},
        elapsed_seconds=5.2,
    )


def test_to_json_structure(sample_result):
    data = to_json(sample_result)
    assert data["benchmark"] == "synthbench"
    assert "version" in data
    assert "timestamp" in data
    assert data["config"]["provider"] == "test/mock"
    assert data["aggregate"]["n_questions"] == 2
    assert len(data["per_question"]) == 2


def test_to_json_has_scores(sample_result):
    data = to_json(sample_result)
    assert "scores" in data
    scores = data["scores"]
    assert "sps" in scores
    assert "p_dist" in scores
    assert "p_rank" in scores
    assert "p_refuse" in scores


def test_to_json_per_question_has_refusal(sample_result):
    data = to_json(sample_result)
    for q in data["per_question"]:
        assert "model_refusal_rate" in q
        assert "human_refusal_rate" in q


def test_to_json_round_trip(sample_result):
    data = to_json(sample_result)
    serialized = json.dumps(data)
    parsed = json.loads(serialized)
    assert parsed["aggregate"]["mean_jsd"] == data["aggregate"]["mean_jsd"]


def test_to_markdown_contains_scores(sample_result):
    md = to_markdown(sample_result)
    assert "SynthBench Score Card" in md
    assert "test/mock" in md
    assert "Mean JSD" in md
    assert "SPS" in md
    assert "P_dist" in md
    assert "P_rank" in md
    assert "P_refuse" in md


class TestNormalizeDistribution:
    """Distribution normalization at publish time (sb-7bg)."""

    def test_already_normalized_preserved(self):
        result = normalize_distribution({"A": 0.6, "B": 0.4})
        assert abs(sum(result.values()) - 1.0) < 5e-3
        assert result["A"] == 0.6
        assert result["B"] == 0.4

    def test_parse_failure_drop_renormalized(self):
        # Simulates runner output when some samples fail to parse:
        # sum is 1 - refusal_rate (0.7), and we need to renormalize to 1.0.
        result = normalize_distribution({"A": 0.5, "B": 0.2})
        assert abs(sum(result.values()) - 1.0) < 5e-3
        # Ratio preserved: A was 2.5× B, still 2.5× B after normalization.
        assert result["A"] / result["B"] == pytest.approx(2.5, rel=1e-3)

    def test_floating_point_drift_corrected(self):
        # 1/3 rounded to 4 decimals is 0.3333; three of them sum to 0.9999.
        result = normalize_distribution({"A": 0.3333, "B": 0.3333, "C": 0.3333})
        assert abs(sum(result.values()) - 1.0) < 5e-3

    def test_all_zero_fallback_to_uniform(self):
        # Total refusal: every sample failed to parse. Uniform keeps
        # downstream math defined (validator requires sum=1.0).
        result = normalize_distribution({"A": 0.0, "B": 0.0, "C": 0.0})
        assert abs(sum(result.values()) - 1.0) < 5e-3
        assert result["A"] == result["B"] == result["C"]

    def test_empty_distribution_stays_empty(self):
        assert normalize_distribution({}) == {}

    def test_negative_clamped_to_zero(self):
        result = normalize_distribution({"A": 0.6, "B": -0.1, "C": 0.4})
        assert result["B"] == 0.0
        assert abs(sum(result.values()) - 1.0) < 5e-3


def test_to_json_model_distribution_sums_to_one():
    """Regression for sb-7bg: published distributions must sum to 1.0."""
    # Runner-style un-normalized dist (parse failures dropped 30% of mass).
    q = QuestionResult(
        key="Q1",
        text="?",
        options=["Yes", "No"],
        human_distribution={"Yes": 0.5, "No": 0.5},
        model_distribution={"Yes": 0.5, "No": 0.2},
        jsd=0.0,
        kendall_tau=1.0,
        parity=1.0,
        n_samples=30,
        n_parse_failures=9,
        model_refusal_rate=0.3,
    )
    result = BenchmarkResult(
        provider_name="test/mock",
        dataset_name="test",
        questions=[q],
        config={"samples_per_question": 30, "n_evaluated": 1},
    )
    data = to_json(result)
    md = data["per_question"][0]["model_distribution"]
    assert abs(sum(md.values()) - 1.0) < 5e-3
