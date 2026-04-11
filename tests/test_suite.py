"""Tests for the suite runner module."""

from __future__ import annotations

import json

import pytest

from synthbench.suite import (
    load_suite_config,
    check_suite,
    find_existing_results,
    format_check,
    format_summary,
    _gap_key,
    _compute_variance_stats,
    HIGH_CV_THRESHOLD,
)


class TestLoadSuiteConfig:
    def test_standard_loads(self):
        runs = load_suite_config("standard")
        assert isinstance(runs, list)
        assert len(runs) == 7

    def test_standard_run_fields(self):
        runs = load_suite_config("standard")
        for run in runs:
            assert "dataset" in run
            assert "samples" in run
            assert "label" in run
            assert "repeats" in run
            assert isinstance(run["repeats"], int)
            assert run["repeats"] > 0

    def test_standard_labels(self):
        runs = load_suite_config("standard")
        labels = [r["label"] for r in runs]
        assert "OpinionsQA Full" in labels
        assert "OpinionsQA Consumer" in labels
        assert "OpinionsQA Political" in labels
        assert "OpinionsQA Neutral" in labels
        assert "GlobalOpinionQA" in labels
        assert "SubPOP" in labels
        assert "OpinionsQA Replicate" in labels

    def test_standard_datasets(self):
        runs = load_suite_config("standard")
        datasets = {r["dataset"] for r in runs}
        assert "opinionsqa" in datasets
        assert "globalopinionqa" in datasets
        assert "subpop" in datasets

    def test_standard_topics(self):
        runs = load_suite_config("standard")
        topics = [r.get("topic") for r in runs]
        assert "consumer" in topics
        assert "political" in topics
        assert "neutral" in topics

    def test_nonexistent_suite_raises(self):
        with pytest.raises(FileNotFoundError):
            load_suite_config("nonexistent_suite_xyz")


class TestGapKey:
    def test_basic(self):
        key = _gap_key("openrouter/haiku", "opinionsqa", None, 50)
        assert key == "openrouter/haiku|opinionsqa|all|50"

    def test_with_topic(self):
        key = _gap_key("openrouter/haiku", "opinionsqa", "consumer", 50)
        assert key == "openrouter/haiku|opinionsqa|consumer|50"

    def test_different_samples_different_keys(self):
        k1 = _gap_key("prov", "ds", None, 30)
        k2 = _gap_key("prov", "ds", None, 50)
        assert k1 != k2


class TestFindExistingResults:
    def test_empty_dir(self, tmp_path):
        results = find_existing_results(tmp_path, "test-provider")
        assert results == {}

    def test_nonexistent_dir(self, tmp_path):
        results = find_existing_results(tmp_path / "nope", "test-provider")
        assert results == {}

    def test_finds_matching_results(self, tmp_path):
        result = {
            "benchmark": "synthbench",
            "config": {
                "provider": "test-prov",
                "dataset": "opinionsqa",
                "topic_filter": None,
                "samples_per_question": 50,
                "n_evaluated": 100,
            },
            "scores": {"sps": 0.75},
        }
        (tmp_path / "r1.json").write_text(json.dumps(result))
        (tmp_path / "r2.json").write_text(json.dumps(result))

        found = find_existing_results(tmp_path, "test-prov")
        key = _gap_key("test-prov", "opinionsqa", None, 50)
        assert key in found
        assert len(found[key]) == 2

    def test_ignores_other_providers(self, tmp_path):
        result = {
            "benchmark": "synthbench",
            "config": {
                "provider": "other-prov",
                "dataset": "opinionsqa",
                "samples_per_question": 50,
            },
            "scores": {"sps": 0.5},
        }
        (tmp_path / "r.json").write_text(json.dumps(result))

        found = find_existing_results(tmp_path, "test-prov")
        assert found == {}

    def test_ignores_non_synthbench(self, tmp_path):
        (tmp_path / "r.json").write_text(json.dumps({"not": "synthbench"}))
        found = find_existing_results(tmp_path, "test-prov")
        assert found == {}

    def test_ignores_malformed_json(self, tmp_path):
        (tmp_path / "bad.json").write_text("{broken json")
        found = find_existing_results(tmp_path, "test-prov")
        assert found == {}

    def test_topic_filter_matching(self, tmp_path):
        for topic in ["consumer", "political"]:
            result = {
                "benchmark": "synthbench",
                "config": {
                    "provider": "test-prov",
                    "dataset": "opinionsqa",
                    "topic_filter": topic,
                    "samples_per_question": 50,
                },
                "scores": {"sps": 0.7},
            }
            (tmp_path / f"r_{topic}.json").write_text(json.dumps(result))

        found = find_existing_results(tmp_path, "test-prov")
        assert len(found) == 2
        assert _gap_key("test-prov", "opinionsqa", "consumer", 50) in found
        assert _gap_key("test-prov", "opinionsqa", "political", 50) in found


class TestCheckSuite:
    def _make_result(self, provider, dataset, topic=None, samples=50, sps=0.7):
        return {
            "benchmark": "synthbench",
            "config": {
                "provider": provider,
                "dataset": dataset,
                "topic_filter": topic,
                "samples_per_question": samples,
                "n_evaluated": 100,
            },
            "scores": {"sps": sps},
        }

    def test_all_missing(self, tmp_path):
        annotated = check_suite("test-prov", tmp_path)
        assert len(annotated) == 7
        assert all(a["status"] == "missing" for a in annotated)

    def test_done_with_enough_repeats(self, tmp_path):
        # Write 3 results for opinionsqa full (samples=50, no topic)
        for j in range(3):
            result = self._make_result("test-prov", "opinionsqa", sps=0.7 + j * 0.01)
            (tmp_path / f"r{j}.json").write_text(json.dumps(result))

        annotated = check_suite("test-prov", tmp_path)
        oqa_full = [a for a in annotated if a["label"] == "OpinionsQA Full"][0]
        assert oqa_full["status"] == "done"
        assert oqa_full["n_existing"] == 3

    def test_partial_with_some_repeats(self, tmp_path):
        # Write 1 result for opinionsqa full (need 3)
        result = self._make_result("test-prov", "opinionsqa", sps=0.7)
        (tmp_path / "r1.json").write_text(json.dumps(result))

        annotated = check_suite("test-prov", tmp_path)
        oqa_full = [a for a in annotated if a["label"] == "OpinionsQA Full"][0]
        assert oqa_full["status"] == "partial"
        assert oqa_full["n_existing"] == 1

    def test_repeats_override(self, tmp_path):
        # Write 1 result — with override=1, should be "done"
        result = self._make_result("test-prov", "opinionsqa", sps=0.7)
        (tmp_path / "r1.json").write_text(json.dumps(result))

        annotated = check_suite("test-prov", tmp_path, repeats_override=1)
        oqa_full = [a for a in annotated if a["label"] == "OpinionsQA Full"][0]
        assert oqa_full["status"] == "done"

    def test_sps_stats_computed(self, tmp_path):
        for j in range(3):
            result = self._make_result("test-prov", "opinionsqa", sps=0.70 + j * 0.01)
            (tmp_path / f"r{j}.json").write_text(json.dumps(result))

        annotated = check_suite("test-prov", tmp_path)
        oqa_full = [a for a in annotated if a["label"] == "OpinionsQA Full"][0]
        assert "sps_mean" in oqa_full
        assert "sps_std" in oqa_full
        assert abs(oqa_full["sps_mean"] - 0.71) < 0.001


class TestComputeVarianceStats:
    def test_empty(self):
        stats = _compute_variance_stats([])
        assert stats["mean"] == 0.0
        assert stats["std"] == 0.0
        assert not stats["high_variance"]

    def test_single_value(self):
        stats = _compute_variance_stats([0.75])
        assert stats["mean"] == 0.75
        assert stats["std"] == 0.0
        assert stats["cv"] == 0.0
        assert not stats["high_variance"]

    def test_low_variance(self):
        stats = _compute_variance_stats([0.750, 0.751, 0.749])
        assert stats["cv"] < HIGH_CV_THRESHOLD
        assert not stats["high_variance"]

    def test_high_variance(self):
        stats = _compute_variance_stats([0.50, 0.70, 0.90])
        assert stats["cv"] > HIGH_CV_THRESHOLD
        assert stats["high_variance"]


class TestFormatCheck:
    def test_format_missing(self):
        annotated = [
            {
                "label": "Test Run",
                "status": "missing",
                "n_existing": 0,
                "repeats_needed": 3,
            }
        ]
        output = format_check(annotated, "test-prov")
        assert "[MISSING]" in output
        assert "1 missing" in output

    def test_format_done(self):
        annotated = [
            {
                "label": "Test Run",
                "status": "done",
                "n_existing": 3,
                "repeats_needed": 3,
                "sps_mean": 0.75,
                "sps_std": 0.01,
            }
        ]
        output = format_check(annotated, "test-prov")
        assert "[DONE]" in output
        assert "3/3" in output
        assert "1 done" in output

    def test_format_partial(self):
        annotated = [
            {
                "label": "Test Run",
                "status": "partial",
                "n_existing": 1,
                "repeats_needed": 3,
                "sps_mean": 0.75,
                "sps_std": 0.0,
            }
        ]
        output = format_check(annotated, "test-prov")
        assert "[PARTIAL 1/3]" in output
        assert "1 partial" in output


class TestFormatSummary:
    def test_format_completed(self):
        summaries = [
            {
                "label": "Test Run",
                "status": "completed",
                "repeats_needed": 3,
                "n_existing": 0,
                "n_completed": 3,
                "sps_values": [0.7, 0.71, 0.72],
                "mean": 0.71,
                "std": 0.01,
                "cv": 0.014,
                "high_variance": False,
            }
        ]
        output = format_summary(summaries, "test-prov")
        assert "DONE" in output
        assert "1 completed" in output

    def test_format_high_variance_flagged(self):
        summaries = [
            {
                "label": "Volatile Run",
                "status": "completed",
                "repeats_needed": 3,
                "n_existing": 0,
                "n_completed": 3,
                "sps_values": [0.5, 0.7, 0.9],
                "mean": 0.7,
                "std": 0.2,
                "cv": 0.286,
                "high_variance": True,
            }
        ]
        output = format_summary(summaries, "test-prov")
        assert "High variance" in output
        assert "Volatile Run" in output
