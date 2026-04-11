"""Tests for cross-model convergence contamination detection."""

from __future__ import annotations

import json

import pytest

from synthbench.contamination import (
    convergence_analysis,
    convergence_to_json,
    format_convergence_report,
    load_result_distributions,
)


def _write_result(tmp_path, name: str, provider: str, per_question: list[dict]) -> str:
    """Write a minimal synthbench result JSON file and return the path."""
    data = {
        "benchmark": "synthbench",
        "version": "0.1.0",
        "config": {
            "dataset": "opinionsqa",
            "provider": provider,
            "n_evaluated": len(per_question),
        },
        "scores": {"sps": 0.5},
        "aggregate": {},
        "per_question": per_question,
    }
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(data))
    return path


def _make_question(key: str, text: str, dist: dict[str, float]) -> dict:
    return {
        "key": key,
        "text": text,
        "options": list(dist.keys()),
        "human_distribution": {k: 0.25 for k in dist},
        "model_distribution": dist,
        "jsd": 0.1,
        "kendall_tau": 0.5,
        "parity": 0.6,
        "n_samples": 30,
    }


class TestLoadResultDistributions:
    def test_loads_valid_file(self, tmp_path):
        q = _make_question("Q1", "Test?", {"A": 0.5, "B": 0.5})
        path = _write_result(tmp_path, "r1", "model-a", [q])
        provider, dists, texts = load_result_distributions(path)
        assert provider == "model-a"
        assert "Q1" in dists
        assert dists["Q1"] == {"A": 0.5, "B": 0.5}
        assert texts["Q1"] == "Test?"

    def test_rejects_non_synthbench(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"benchmark": "other"}))
        with pytest.raises(ValueError, match="Not a synthbench"):
            load_result_distributions(path)


class TestConvergenceAnalysis:
    def test_identical_distributions_high_risk(self, tmp_path):
        """When all models produce identical distributions, contamination_risk = 1.0."""
        dist = {"A": 0.6, "B": 0.3, "C": 0.1}
        q = _make_question("Q1", "Same?", dist)

        f1 = _write_result(tmp_path, "r1", "model-a", [q])
        f2 = _write_result(tmp_path, "r2", "model-b", [q])
        f3 = _write_result(tmp_path, "r3", "model-c", [q])

        analysis = convergence_analysis([f1, f2, f3])

        assert analysis.n_models == 3
        assert analysis.n_questions == 1
        assert analysis.questions[0].contamination_risk == pytest.approx(1.0)
        assert analysis.questions[0].mean_std == pytest.approx(0.0)

    def test_divergent_distributions_low_risk(self, tmp_path):
        """When models produce very different distributions, risk is low."""
        q1 = _make_question("Q1", "Div?", {"A": 1.0, "B": 0.0})
        q2 = _make_question("Q1", "Div?", {"A": 0.0, "B": 1.0})

        f1 = _write_result(tmp_path, "r1", "model-a", [q1])
        f2 = _write_result(tmp_path, "r2", "model-b", [q2])

        analysis = convergence_analysis([f1, f2])

        assert analysis.n_questions == 1
        q = analysis.questions[0]
        # std of [1.0, 0.0] = 0.5, std of [0.0, 1.0] = 0.5
        # mean_std = 0.5, contamination_risk = 1 - (0.5/0.5) = 0.0
        assert q.contamination_risk == pytest.approx(0.0)
        assert q.mean_std == pytest.approx(0.5)

    def test_min_models_filter(self, tmp_path):
        """Questions appearing in fewer than min_models files are excluded."""
        q_shared = _make_question("Q1", "Shared", {"A": 0.5, "B": 0.5})
        q_unique = _make_question("Q2", "Unique", {"A": 0.8, "B": 0.2})

        f1 = _write_result(tmp_path, "r1", "model-a", [q_shared, q_unique])
        f2 = _write_result(tmp_path, "r2", "model-b", [q_shared])
        f3 = _write_result(tmp_path, "r3", "model-c", [q_shared])

        analysis = convergence_analysis([f1, f2, f3], min_models=3)

        assert analysis.n_questions == 1
        assert analysis.questions[0].key == "Q1"

    def test_needs_at_least_2_files(self, tmp_path):
        q = _make_question("Q1", "Solo", {"A": 1.0})
        f1 = _write_result(tmp_path, "r1", "model-a", [q])

        with pytest.raises(ValueError, match="at least 2"):
            convergence_analysis([f1])

    def test_risk_categories(self, tmp_path):
        """Verify high/medium/low risk bucketing."""
        # High risk: identical
        q_same = _make_question("Q_HIGH", "Same", {"A": 0.8, "B": 0.2})
        # Medium risk: moderate divergence
        q_med_a = _make_question("Q_MED", "Med", {"A": 0.7, "B": 0.3})
        q_med_b = _make_question("Q_MED", "Med", {"A": 0.5, "B": 0.5})
        # Low risk: strong divergence
        q_low_a = _make_question("Q_LOW", "Low", {"A": 1.0, "B": 0.0})
        q_low_b = _make_question("Q_LOW", "Low", {"A": 0.0, "B": 1.0})

        f1 = _write_result(tmp_path, "r1", "model-a", [q_same, q_med_a, q_low_a])
        f2 = _write_result(tmp_path, "r2", "model-b", [q_same, q_med_b, q_low_b])

        analysis = convergence_analysis([f1, f2])

        assert analysis.n_questions == 3
        assert analysis.high_risk_count >= 1
        assert analysis.low_risk_count >= 1

    def test_duplicate_provider_names(self, tmp_path):
        """Multiple files from same provider get deduplicated names."""
        q = _make_question("Q1", "Dup", {"A": 0.5, "B": 0.5})
        f1 = _write_result(tmp_path, "r1", "model-a", [q])
        f2 = _write_result(tmp_path, "r2", "model-a", [q])

        analysis = convergence_analysis([f1, f2])
        assert analysis.n_models == 2
        assert len(set(analysis.model_names)) == 2

    def test_partial_overlap(self, tmp_path):
        """Questions not in all files still get analyzed if >= min_models."""
        q1 = _make_question("Q1", "Both", {"A": 0.5, "B": 0.5})
        q2 = _make_question("Q2", "Only A", {"A": 0.9, "B": 0.1})
        q3 = _make_question("Q3", "Only B", {"A": 0.1, "B": 0.9})

        f1 = _write_result(tmp_path, "r1", "model-a", [q1, q2])
        f2 = _write_result(tmp_path, "r2", "model-b", [q1, q3])

        analysis = convergence_analysis([f1, f2], min_models=2)
        # Only Q1 is in both
        assert analysis.n_questions == 1
        assert analysis.questions[0].key == "Q1"


class TestFormatAndSerialize:
    def test_format_report_contains_key_sections(self, tmp_path):
        dist = {"A": 0.5, "B": 0.5}
        q = _make_question("Q1", "Test question text", dist)
        f1 = _write_result(tmp_path, "r1", "model-a", [q])
        f2 = _write_result(tmp_path, "r2", "model-b", [q])

        analysis = convergence_analysis([f1, f2])
        report = format_convergence_report(analysis)

        assert "Cross-Model Convergence Analysis" in report
        assert "Risk Distribution" in report
        assert "model-a" in report
        assert "model-b" in report
        assert "Highest Contamination Risk" in report

    def test_json_serialization_roundtrip(self, tmp_path):
        dist = {"A": 0.5, "B": 0.5}
        q = _make_question("Q1", "Test?", dist)
        f1 = _write_result(tmp_path, "r1", "model-a", [q])
        f2 = _write_result(tmp_path, "r2", "model-b", [q])

        analysis = convergence_analysis([f1, f2])
        data = convergence_to_json(analysis)

        assert data["type"] == "contamination_convergence"
        assert data["n_models"] == 2
        assert data["n_questions"] == 1
        assert len(data["per_question"]) == 1
        assert "contamination_risk" in data["per_question"][0]
        # Verify it's JSON-serializable
        json.dumps(data)
