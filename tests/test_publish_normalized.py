"""Tests for normalized_sps annotation in publish.py."""

from __future__ import annotations

from synthbench.publish import _annotate_normalized_sps


def _base_baselines() -> dict:
    return {
        "ceiling": {
            "opinionsqa": {"overall": {"mean": 0.9995}},
            "subpop": {"overall": {"mean": 0.9954}},
        }
    }


def test_raw_llm_normalizes_to_zero():
    entries = [
        {
            "model": "Claude Haiku 4.5",
            "dataset": "opinionsqa",
            "framework": "raw",
            "sps": 0.815,
        },
    ]
    _annotate_normalized_sps(entries, _base_baselines())
    assert entries[0]["normalized_sps"] == 0.0


def test_product_normalization_uses_matching_raw_base():
    entries = [
        {
            "model": "Claude Haiku 4.5",
            "dataset": "opinionsqa",
            "framework": "raw",
            "sps": 0.815,
        },
        {
            "model": "SynthPanel (Haiku 4.5)",
            "dataset": "opinionsqa",
            "framework": "product",
            "sps": 0.829,
        },
    ]
    _annotate_normalized_sps(entries, _base_baselines())
    expected = (0.829 - 0.815) / (0.9995 - 0.815)
    assert abs(entries[1]["normalized_sps"] - expected) < 1e-5


def test_product_without_known_base_is_skipped():
    entries = [
        {
            "model": "SynthPanel Ensemble (3-model)",
            "dataset": "opinionsqa",
            "framework": "product",
            "sps": 0.835,
        },
    ]
    _annotate_normalized_sps(entries, _base_baselines())
    assert "normalized_sps" not in entries[0]


def test_baseline_rows_are_skipped():
    entries = [
        {
            "model": "Random Baseline",
            "dataset": "opinionsqa",
            "framework": "baseline",
            "sps": 0.76,
        },
        {
            "model": "Majority Baseline",
            "dataset": "opinionsqa",
            "framework": "baseline",
            "sps": 0.70,
        },
    ]
    _annotate_normalized_sps(entries, _base_baselines())
    assert all("normalized_sps" not in e for e in entries)


def test_missing_ceiling_skips_dataset():
    entries = [
        {
            "model": "Claude Haiku 4.5",
            "dataset": "globalopinionqa",
            "framework": "raw",
            "sps": 0.72,
        },
        {
            "model": "SynthPanel (Haiku 4.5)",
            "dataset": "globalopinionqa",
            "framework": "product",
            "sps": 0.73,
        },
    ]
    baselines = {"ceiling": {}}  # no ceiling for globalopinionqa
    _annotate_normalized_sps(entries, baselines)
    assert all("normalized_sps" not in e for e in entries)


def test_product_without_matching_raw_on_same_dataset_is_skipped():
    # Raw LLM for Haiku 4.5 exists on opinionsqa but not on subpop; the product
    # row on subpop should NOT borrow the opinionsqa raw baseline.
    entries = [
        {
            "model": "Claude Haiku 4.5",
            "dataset": "opinionsqa",
            "framework": "raw",
            "sps": 0.815,
        },
        {
            "model": "SynthPanel (Haiku 4.5)",
            "dataset": "subpop",
            "framework": "product",
            "sps": 0.77,
        },
    ]
    _annotate_normalized_sps(entries, _base_baselines())
    assert entries[0]["normalized_sps"] == 0.0
    assert "normalized_sps" not in entries[1]


def test_clamps_to_range_when_sps_exceeds_ceiling():
    entries = [
        {
            "model": "Claude Haiku 4.5",
            "dataset": "opinionsqa",
            "framework": "raw",
            "sps": 0.815,
        },
        {
            "model": "SynthPanel (Haiku 4.5)",
            "dataset": "opinionsqa",
            "framework": "product",
            "sps": 1.2,
        },
    ]
    _annotate_normalized_sps(entries, _base_baselines())
    assert entries[1]["normalized_sps"] <= 1.05


def test_non_positive_range_skipped():
    # If the raw baseline already matches or exceeds the ceiling, skip to avoid
    # divide-by-zero or upside-down percentages.
    entries = [
        {
            "model": "Claude Haiku 4.5",
            "dataset": "opinionsqa",
            "framework": "raw",
            "sps": 0.9995,
        },
        {
            "model": "SynthPanel (Haiku 4.5)",
            "dataset": "opinionsqa",
            "framework": "product",
            "sps": 0.999,
        },
    ]
    _annotate_normalized_sps(entries, _base_baselines())
    assert "normalized_sps" not in entries[1]
