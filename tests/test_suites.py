"""Tests for pinned question suites."""

from __future__ import annotations

import json

import pytest

from synthbench.suites import (
    load_suite,
    filter_questions_by_suite,
    AVAILABLE_SUITES,
    SUITE_DIR,
)
from synthbench.datasets.base import Question


class TestLoadSuite:
    def test_smoke_loads(self):
        keys = load_suite("smoke")
        assert keys is not None
        assert len(keys) == 28
        assert all(isinstance(k, str) for k in keys)

    def test_core_loads(self):
        keys = load_suite("core")
        assert keys is not None
        assert len(keys) == 200
        assert all(isinstance(k, str) for k in keys)

    def test_full_returns_none(self):
        result = load_suite("full")
        assert result is None

    def test_unknown_suite_raises(self):
        with pytest.raises(ValueError, match="Unknown suite"):
            load_suite("nonexistent")

    def test_available_suites_constant(self):
        assert "smoke" in AVAILABLE_SUITES
        assert "core" in AVAILABLE_SUITES
        assert "full" in AVAILABLE_SUITES

    def test_suite_json_files_valid(self):
        for name in ("smoke", "core"):
            path = SUITE_DIR / f"{name}.json"
            assert path.exists(), f"Missing suite file: {path}"
            with open(path) as f:
                data = json.load(f)
            assert "keys" in data
            assert "suite" in data
            assert data["suite"] == name
            assert len(data["keys"]) == data["n_keys"]

    def test_no_duplicate_keys_in_suites(self):
        for name in ("smoke", "core"):
            keys = load_suite(name)
            assert len(keys) == len(set(keys)), f"Duplicate keys in {name}"


class TestFilterQuestionsBySuite:
    def test_filters_and_orders(self):
        qs = [
            Question(
                key="Q3", text="Q3?", options=["A"], human_distribution={"A": 1.0}
            ),
            Question(
                key="Q1", text="Q1?", options=["A"], human_distribution={"A": 1.0}
            ),
            Question(
                key="Q2", text="Q2?", options=["A"], human_distribution={"A": 1.0}
            ),
        ]
        filtered = filter_questions_by_suite(qs, ["Q2", "Q1"])
        assert len(filtered) == 2
        assert filtered[0].key == "Q2"
        assert filtered[1].key == "Q1"

    def test_missing_keys_skipped(self):
        qs = [
            Question(
                key="Q1", text="Q1?", options=["A"], human_distribution={"A": 1.0}
            ),
        ]
        filtered = filter_questions_by_suite(qs, ["Q1", "Q_MISSING"])
        assert len(filtered) == 1
        assert filtered[0].key == "Q1"

    def test_empty_suite_returns_empty(self):
        qs = [
            Question(
                key="Q1", text="Q1?", options=["A"], human_distribution={"A": 1.0}
            ),
        ]
        filtered = filter_questions_by_suite(qs, [])
        assert len(filtered) == 0
