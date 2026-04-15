"""Tests for per-question text rehydration at publish time (sb-x2k).

Historical ``leaderboard-results/*.json`` carry per-question ``text`` fields
sliced at 120 characters by the old report writer (removed in sb-5o1).
Regenerating every run would be prohibitive, so publish.py rehydrates from a
committed ``data/question-text-registries/<dataset>.json`` fixture. These
tests lock in that behavior and protect against silent regressions.
"""

from __future__ import annotations

import json
from pathlib import Path

from synthbench.publish import (
    _load_question_text_registry,
    _rehydrate_question_text,
)


def _write_registry(root: Path, dataset: str, mapping: dict[str, str]) -> None:
    reg_dir = root / "data" / "question-text-registries"
    reg_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "dataset": dataset,
        "n_questions": len(mapping),
        "questions": mapping,
    }
    (reg_dir / f"{dataset}.json").write_text(json.dumps(payload))


def test_load_registry_missing_directory_returns_empty(tmp_path: Path) -> None:
    assert _load_question_text_registry(tmp_path) == {}


def test_load_registry_reads_committed_fixture(tmp_path: Path) -> None:
    _write_registry(tmp_path, "opinionsqa", {"K1": "full text one", "K2": "full text two"})
    registry = _load_question_text_registry(tmp_path)
    assert registry == {"opinionsqa": {"K1": "full text one", "K2": "full text two"}}


def test_load_registry_ignores_malformed_files(tmp_path: Path) -> None:
    reg_dir = tmp_path / "data" / "question-text-registries"
    reg_dir.mkdir(parents=True)
    (reg_dir / "bad.json").write_text("{not json")
    _write_registry(tmp_path, "opinionsqa", {"K": "ok"})
    registry = _load_question_text_registry(tmp_path)
    assert "opinionsqa" in registry
    assert registry["opinionsqa"]["K"] == "ok"


def test_rehydrate_replaces_truncated_text() -> None:
    result = {
        "config": {"dataset": "opinionsqa"},
        "per_question": [
            {"key": "K1", "text": "Short question trun"},  # truncated
            {"key": "K2", "text": "Already full length."},
        ],
    }
    registry = {
        "opinionsqa": {
            "K1": "Short question truncated at 120 would stop mid-word here.",
            "K2": "Already full length.",
        }
    }
    _rehydrate_question_text(result, registry)
    assert result["per_question"][0]["text"].endswith("mid-word here.")
    # Registry equal-length text doesn't overwrite — guards against corrupted
    # registries clobbering good data with an accidental shorter value.
    assert result["per_question"][1]["text"] == "Already full length."


def test_rehydrate_noop_when_registry_lacks_dataset() -> None:
    result = {
        "config": {"dataset": "unknown"},
        "per_question": [{"key": "K1", "text": "short"}],
    }
    _rehydrate_question_text(result, {"opinionsqa": {"K1": "full"}})
    assert result["per_question"][0]["text"] == "short"


def test_rehydrate_skips_rows_without_key() -> None:
    result = {
        "config": {"dataset": "opinionsqa"},
        "per_question": [{"text": "orphan", "key": None}, {"key": "K1", "text": "t"}],
    }
    _rehydrate_question_text(result, {"opinionsqa": {"K1": "full text"}})
    assert result["per_question"][0]["text"] == "orphan"
    assert result["per_question"][1]["text"] == "full text"


def test_rehydrate_never_shortens_text() -> None:
    """A shorter registry value must not overwrite an already-long row."""
    result = {
        "config": {"dataset": "opinionsqa"},
        "per_question": [{"key": "K1", "text": "A" * 200}],
    }
    _rehydrate_question_text(result, {"opinionsqa": {"K1": "B" * 50}})
    assert result["per_question"][0]["text"] == "A" * 200
