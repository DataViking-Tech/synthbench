"""Tests for the GlobalOpinionQA dataset loader."""

from __future__ import annotations

import json
from pathlib import Path

from synthbench.datasets.globalopinionqa import (
    GlobalOpinionQADataset,
    _normalize_options,
)


class TestNormalizeOptions:
    def test_floats_become_strings(self):
        assert _normalize_options([0.0, 1.0, 2.0]) == ["0.0", "1.0", "2.0"]

    def test_ints_become_strings(self):
        assert _normalize_options([1, 2, 3]) == ["1", "2", "3"]

    def test_strings_pass_through(self):
        assert _normalize_options(["Yes", "No"]) == ["Yes", "No"]

    def test_mixed_types_coerced(self):
        assert _normalize_options(["Yes", 1.0, 2]) == ["Yes", "1.0", "2"]


class TestLoadCachedNormalizesOptions:
    def test_numeric_options_stringified(self, tmp_path: Path):
        """Regression: cached rows with numeric options must load as strings.

        Before the fix, a cache row whose ``options`` were floats (Likert
        scales) loaded straight into the Question dataclass, and downstream
        serializers emitted a ``per_question.options`` list of floats. That
        broke the site's run-detail page, which called ``String.replace`` on
        each option (sb-cym).
        """
        cache_dir = tmp_path / "goqa"
        cache_dir.mkdir()
        cache_path = cache_dir / "questions.json"
        cache_path.write_text(
            json.dumps(
                {
                    "dataset": "globalopinionqa",
                    "version": "1.0",
                    "n_questions": 1,
                    "questions": [
                        {
                            "key": "GOQA_0_deadbeef",
                            "text": "Likert scale question?",
                            "options": [0.0, 1.0, 2.0, 3.0, 4.0],
                            "selections": {
                                "USA": [0.2, 0.2, 0.2, 0.2, 0.2],
                            },
                            "survey": "",
                        }
                    ],
                }
            )
        )

        ds = GlobalOpinionQADataset(data_dir=cache_dir)
        questions = ds.load()

        assert len(questions) == 1
        q = questions[0]
        assert q.options == ["0.0", "1.0", "2.0", "3.0", "4.0"]
        assert all(isinstance(o, str) for o in q.options)
        assert set(q.human_distribution.keys()) == set(q.options)
        assert all(isinstance(k, str) for k in q.human_distribution)

    def test_string_options_unchanged(self, tmp_path: Path):
        cache_dir = tmp_path / "goqa"
        cache_dir.mkdir()
        cache_path = cache_dir / "questions.json"
        cache_path.write_text(
            json.dumps(
                {
                    "dataset": "globalopinionqa",
                    "version": "1.0",
                    "n_questions": 1,
                    "questions": [
                        {
                            "key": "GOQA_1_cafebabe",
                            "text": "Approve or disapprove?",
                            "options": ["Approve", "Disapprove"],
                            "selections": {"USA": [0.6, 0.4]},
                            "survey": "",
                        }
                    ],
                }
            )
        )

        ds = GlobalOpinionQADataset(data_dir=cache_dir)
        questions = ds.load()

        assert len(questions) == 1
        assert questions[0].options == ["Approve", "Disapprove"]
