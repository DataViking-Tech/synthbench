"""Tests for the WVS dataset loader."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from synthbench.datasets.wvs import (
    DatasetDownloadError,
    WVSDataset,
    _aggregate_from_csv,
)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["question_id", "question_text", "country", "option", "count"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)


class TestAggregateFromCsv:
    def test_sums_across_countries_when_no_filter(self, tmp_path: Path):
        csv_path = tmp_path / "wvs7_aggregated.csv"
        _write_csv(
            csv_path,
            [
                {
                    "question_id": "Q1",
                    "question_text": "Do you trust?",
                    "country": "USA",
                    "option": "Yes",
                    "count": 60,
                },
                {
                    "question_id": "Q1",
                    "question_text": "Do you trust?",
                    "country": "USA",
                    "option": "No",
                    "count": 40,
                },
                {
                    "question_id": "Q1",
                    "question_text": "Do you trust?",
                    "country": "JPN",
                    "option": "Yes",
                    "count": 30,
                },
                {
                    "question_id": "Q1",
                    "question_text": "Do you trust?",
                    "country": "JPN",
                    "option": "No",
                    "count": 70,
                },
            ],
        )

        questions = _aggregate_from_csv(csv_path)
        assert len(questions) == 1
        q = questions[0]
        assert q.key == "WVS_Q1"
        assert q.survey == "WVS7"
        # Pooled: 90 Yes, 110 No
        assert q.human_distribution["Yes"] == pytest.approx(90 / 200)
        assert q.human_distribution["No"] == pytest.approx(110 / 200)

    def test_country_filter_uses_only_that_country(self, tmp_path: Path):
        csv_path = tmp_path / "wvs7_aggregated.csv"
        _write_csv(
            csv_path,
            [
                {
                    "question_id": "Q1",
                    "question_text": "Trust?",
                    "country": "USA",
                    "option": "Yes",
                    "count": 60,
                },
                {
                    "question_id": "Q1",
                    "question_text": "Trust?",
                    "country": "USA",
                    "option": "No",
                    "count": 40,
                },
                {
                    "question_id": "Q1",
                    "question_text": "Trust?",
                    "country": "JPN",
                    "option": "Yes",
                    "count": 30,
                },
                {
                    "question_id": "Q1",
                    "question_text": "Trust?",
                    "country": "JPN",
                    "option": "No",
                    "count": 70,
                },
            ],
        )

        questions = _aggregate_from_csv(csv_path, country_filter="JPN")
        assert len(questions) == 1
        q = questions[0]
        assert q.survey == "WVS7:JPN"
        assert q.human_distribution["Yes"] == pytest.approx(0.3)
        assert q.human_distribution["No"] == pytest.approx(0.7)

    def test_country_filter_skips_questions_without_that_country(self, tmp_path: Path):
        csv_path = tmp_path / "wvs7_aggregated.csv"
        _write_csv(
            csv_path,
            [
                {
                    "question_id": "Q1",
                    "question_text": "A?",
                    "country": "USA",
                    "option": "Yes",
                    "count": 10,
                },
                {
                    "question_id": "Q2",
                    "question_text": "B?",
                    "country": "JPN",
                    "option": "Yes",
                    "count": 10,
                },
            ],
        )

        questions = _aggregate_from_csv(csv_path, country_filter="USA")
        keys = [q.key for q in questions]
        assert keys == ["WVS_Q1"]

    def test_rejects_csv_missing_columns(self, tmp_path: Path):
        path = tmp_path / "bad.csv"
        path.write_text("question_id,option\nQ1,Yes\n")
        with pytest.raises(DatasetDownloadError, match="missing columns"):
            _aggregate_from_csv(path)

    def test_zero_and_invalid_counts_are_dropped(self, tmp_path: Path):
        csv_path = tmp_path / "wvs7_aggregated.csv"
        _write_csv(
            csv_path,
            [
                {
                    "question_id": "Q1",
                    "question_text": "T?",
                    "country": "USA",
                    "option": "Yes",
                    "count": 10,
                },
                {
                    "question_id": "Q1",
                    "question_text": "T?",
                    "country": "USA",
                    "option": "No",
                    "count": 0,
                },
                {
                    "question_id": "Q1",
                    "question_text": "T?",
                    "country": "USA",
                    "option": "Maybe",
                    "count": "abc",
                },
            ],
        )

        questions = _aggregate_from_csv(csv_path)
        assert len(questions) == 1
        assert questions[0].options == ["Yes"]
        assert questions[0].human_distribution == {"Yes": 1.0}


class TestWVSDataset:
    def test_load_builds_from_raw_csv_and_caches(self, tmp_path: Path):
        raw = tmp_path / "raw" / "wvs7_aggregated.csv"
        _write_csv(
            raw,
            [
                {
                    "question_id": "Q1",
                    "question_text": "Trust?",
                    "country": "USA",
                    "option": "Yes",
                    "count": 1,
                },
                {
                    "question_id": "Q1",
                    "question_text": "Trust?",
                    "country": "USA",
                    "option": "No",
                    "count": 3,
                },
            ],
        )

        ds = WVSDataset(data_dir=tmp_path)
        first = ds.load()
        assert len(first) == 1
        assert first[0].human_distribution == {"Yes": 0.25, "No": 0.75}

        # Second load should hit the cache — delete raw to prove it.
        raw.unlink()
        second = WVSDataset(data_dir=tmp_path).load()
        assert len(second) == 1
        assert second[0].human_distribution == {"Yes": 0.25, "No": 0.75}

    def test_load_raises_when_raw_missing(self, tmp_path: Path):
        ds = WVSDataset(data_dir=tmp_path)
        with pytest.raises(DatasetDownloadError, match="manual setup"):
            ds.load()

    def test_n_parameter_truncates(self, tmp_path: Path):
        raw = tmp_path / "raw" / "wvs7_aggregated.csv"
        _write_csv(
            raw,
            [
                {
                    "question_id": f"Q{i}",
                    "question_text": f"T{i}?",
                    "country": "USA",
                    "option": "Yes",
                    "count": 5,
                }
                for i in range(3)
            ],
        )

        ds = WVSDataset(data_dir=tmp_path)
        questions = ds.load(n=2)
        assert len(questions) == 2

    def test_country_constructor_arg_filters_cached_questions(self, tmp_path: Path):
        raw = tmp_path / "raw" / "wvs7_aggregated.csv"
        _write_csv(
            raw,
            [
                {
                    "question_id": "Q1",
                    "question_text": "T?",
                    "country": "USA",
                    "option": "Yes",
                    "count": 10,
                },
                {
                    "question_id": "Q1",
                    "question_text": "T?",
                    "country": "JPN",
                    "option": "Yes",
                    "count": 10,
                },
                {
                    "question_id": "Q2",
                    "question_text": "U?",
                    "country": "USA",
                    "option": "Yes",
                    "count": 10,
                },
            ],
        )

        ds = WVSDataset(data_dir=tmp_path, country="JPN")
        questions = ds.load()
        assert [q.key for q in questions] == ["WVS_Q1"]
        assert questions[0].survey == "WVS7:JPN"

    def test_info_reports_country_filter(self, tmp_path: Path):
        ds = WVSDataset(data_dir=tmp_path, country="ESP")
        info = ds.info()
        assert info["name"] == "WVS7"
        assert info["country_filter"] == "ESP"

    def test_name_includes_country_when_filtered(self, tmp_path: Path):
        assert WVSDataset(data_dir=tmp_path).name == "wvs"
        assert WVSDataset(data_dir=tmp_path, country="DEU").name == "wvs (DEU)"
