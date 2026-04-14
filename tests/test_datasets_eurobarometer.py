"""Tests for the Eurobarometer Consumer Modules dataset adapter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from synthbench.datasets import DATASETS, EurobarometerConsumerDataset
from synthbench.datasets.eurobarometer import (
    DEMOGRAPHIC_ATTRIBUTES,
    DatasetDownloadError,
)


def _write_survey(
    root: Path,
    survey_id: str,
    info_rows: list[dict[str, str]],
    none_data: dict,
    demo_data: dict[str, dict] | None = None,
) -> None:
    survey_dir = root / survey_id
    survey_dir.mkdir(parents=True)

    info_path = survey_dir / "info.csv"
    with open(info_path, "w", newline="") as f:
        import csv

        writer = csv.DictWriter(f, fieldnames=list(info_rows[0].keys()))
        writer.writeheader()
        writer.writerows(info_rows)

    with open(survey_dir / "NONE_data.json", "w") as f:
        json.dump(none_data, f)

    if demo_data:
        for attr, data in demo_data.items():
            with open(survey_dir / f"{attr}_data.json", "w") as f:
                json.dump(data, f)


class TestRegistry:
    def test_adapter_is_registered(self):
        assert "eurobarometer" in DATASETS
        assert DATASETS["eurobarometer"] is EurobarometerConsumerDataset

    def test_info_contains_expected_keys(self, tmp_path: Path):
        ds = EurobarometerConsumerDataset(data_dir=tmp_path)
        info = ds.info()
        assert info["name"] == "Eurobarometer Consumer Modules"
        assert "GESIS" in info["source"]
        assert set(info["demographics"]) == set(DEMOGRAPHIC_ATTRIBUTES)

    def test_name_is_stable(self, tmp_path: Path):
        assert EurobarometerConsumerDataset(data_dir=tmp_path).name == "eurobarometer"


class TestLoadingFromRaw:
    def test_load_processes_raw_surveys(self, tmp_path: Path):
        raw = tmp_path / "raw"
        _write_survey(
            raw,
            "EB98.1",
            info_rows=[
                {
                    "key": "QA1",
                    "question": "How would you judge the current situation in (OUR COUNTRY) economy?",
                    "references": "['Very good', 'Rather good', 'Rather bad', 'Very bad']",
                }
            ],
            none_data={
                "QA1": {
                    "counts": {
                        "Very good": 50,
                        "Rather good": 250,
                        "Rather bad": 400,
                        "Very bad": 300,
                    }
                }
            },
        )

        ds = EurobarometerConsumerDataset(data_dir=tmp_path)
        questions = ds.load()
        assert len(questions) == 1

        q = questions[0]
        assert q.key == "EB98.1:QA1"
        assert q.survey == "EB98.1"
        assert q.options == ["Very good", "Rather good", "Rather bad", "Very bad"]
        assert pytest.approx(sum(q.human_distribution.values()), rel=1e-6) == 1.0
        assert set(q.human_distribution) == set(q.options)

    def test_load_caches_questions_json(self, tmp_path: Path):
        raw = tmp_path / "raw"
        _write_survey(
            raw,
            "EB98.1",
            info_rows=[
                {
                    "key": "QA1",
                    "question": "Judgement?",
                    "references": "['Yes', 'No']",
                }
            ],
            none_data={"QA1": {"counts": {"Yes": 1, "No": 1}}},
        )

        ds = EurobarometerConsumerDataset(data_dir=tmp_path)
        ds.load()
        assert (tmp_path / "questions.json").exists()

        # Second call should hit the cache (no raw access needed).
        ds2 = EurobarometerConsumerDataset(data_dir=tmp_path)
        qs = ds2.load()
        assert len(qs) == 1
        assert qs[0].options == ["Yes", "No"]

    def test_load_applies_n_limit(self, tmp_path: Path):
        raw = tmp_path / "raw"
        _write_survey(
            raw,
            "EB98.1",
            info_rows=[
                {"key": f"Q{i}", "question": f"Q{i}?", "references": "['A', 'B']"}
                for i in range(5)
            ],
            none_data={f"Q{i}": {"counts": {"A": 1, "B": 1}} for i in range(5)},
        )

        ds = EurobarometerConsumerDataset(data_dir=tmp_path)
        assert len(ds.load(n=3)) == 3

    def test_missing_raw_raises_with_setup_instructions(self, tmp_path: Path):
        ds = EurobarometerConsumerDataset(data_dir=tmp_path)
        with pytest.raises(DatasetDownloadError) as exc:
            ds.load()
        assert "GESIS" in str(exc.value)


class TestDemographicDistributions:
    def test_load_demographic_distributions(self, tmp_path: Path):
        raw = tmp_path / "raw"
        _write_survey(
            raw,
            "EB98.1",
            info_rows=[
                {"key": "QA1", "question": "Judgement?", "references": "['Yes', 'No']"}
            ],
            none_data={"QA1": {"counts": {"Yes": 1, "No": 1}}},
            demo_data={
                "COUNTRY": {
                    "QA1": {
                        "France": {"Yes": 60, "No": 40},
                        "Germany": {"Yes": 30, "No": 70},
                    }
                }
            },
        )

        ds = EurobarometerConsumerDataset(data_dir=tmp_path)
        demo = ds.load_demographic_distributions("COUNTRY")
        assert "QA1" in demo
        assert pytest.approx(demo["QA1"]["France"]["Yes"]) == 0.6
        assert pytest.approx(demo["QA1"]["Germany"]["No"]) == 0.7

    def test_missing_raw_dir_returns_empty(self, tmp_path: Path):
        ds = EurobarometerConsumerDataset(data_dir=tmp_path)
        assert ds.load_demographic_distributions("AGE") == {}


class TestCachedLoadNormalization:
    def test_cached_options_coerced_to_strings(self, tmp_path: Path):
        cache_path = tmp_path / "questions.json"
        cache_path.write_text(
            json.dumps(
                {
                    "dataset": "eurobarometer",
                    "version": "1.0",
                    "n_questions": 1,
                    "questions": [
                        {
                            "key": "EB98.1:QA1",
                            "text": "Likert?",
                            "options": [1, 2, 3, 4],
                            "human_distribution": {1: 0.25, 2: 0.25, 3: 0.25, 4: 0.25},
                            "survey": "EB98.1",
                        }
                    ],
                }
            )
        )
        ds = EurobarometerConsumerDataset(data_dir=tmp_path)
        questions = ds.load()
        assert len(questions) == 1
        q = questions[0]
        assert q.options == ["1", "2", "3", "4"]
        assert all(isinstance(o, str) for o in q.options)
        assert all(isinstance(k, str) for k in q.human_distribution)
