"""Tests for the GSS dataset loader."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from synthbench.datasets.gss import (
    DatasetDownloadError,
    GSSDataset,
    _aggregate_from_csv,
)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["question_id", "question_text", "year", "option", "count"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)


class TestAggregateFromCsv:
    def test_sums_across_years_when_no_filter(self, tmp_path: Path):
        csv_path = tmp_path / "gss_aggregated.csv"
        _write_csv(
            csv_path,
            [
                {
                    "question_id": "SPKATH",
                    "question_text": "Allow speech?",
                    "year": "2018",
                    "option": "Yes",
                    "count": 400,
                },
                {
                    "question_id": "SPKATH",
                    "question_text": "Allow speech?",
                    "year": "2018",
                    "option": "No",
                    "count": 600,
                },
                {
                    "question_id": "SPKATH",
                    "question_text": "Allow speech?",
                    "year": "2022",
                    "option": "Yes",
                    "count": 700,
                },
                {
                    "question_id": "SPKATH",
                    "question_text": "Allow speech?",
                    "year": "2022",
                    "option": "No",
                    "count": 300,
                },
            ],
        )

        questions = _aggregate_from_csv(csv_path)
        assert len(questions) == 1
        q = questions[0]
        assert q.key == "GSS_SPKATH"
        assert q.survey == "GSS"
        assert q.human_distribution["Yes"] == pytest.approx(1100 / 2000)
        assert q.human_distribution["No"] == pytest.approx(900 / 2000)

    def test_year_filter_uses_only_that_year(self, tmp_path: Path):
        csv_path = tmp_path / "gss_aggregated.csv"
        _write_csv(
            csv_path,
            [
                {
                    "question_id": "SPKATH",
                    "question_text": "Q?",
                    "year": "2018",
                    "option": "Yes",
                    "count": 400,
                },
                {
                    "question_id": "SPKATH",
                    "question_text": "Q?",
                    "year": "2018",
                    "option": "No",
                    "count": 600,
                },
                {
                    "question_id": "SPKATH",
                    "question_text": "Q?",
                    "year": "2022",
                    "option": "Yes",
                    "count": 700,
                },
                {
                    "question_id": "SPKATH",
                    "question_text": "Q?",
                    "year": "2022",
                    "option": "No",
                    "count": 300,
                },
            ],
        )

        questions = _aggregate_from_csv(csv_path, year_filter="2022")
        assert len(questions) == 1
        q = questions[0]
        assert q.survey == "GSS:2022"
        assert q.human_distribution["Yes"] == pytest.approx(0.7)
        assert q.human_distribution["No"] == pytest.approx(0.3)

    def test_year_filter_skips_questions_without_that_year(self, tmp_path: Path):
        csv_path = tmp_path / "gss_aggregated.csv"
        _write_csv(
            csv_path,
            [
                {
                    "question_id": "Q1",
                    "question_text": "A?",
                    "year": "2018",
                    "option": "Yes",
                    "count": 10,
                },
                {
                    "question_id": "Q2",
                    "question_text": "B?",
                    "year": "2022",
                    "option": "Yes",
                    "count": 10,
                },
            ],
        )

        questions = _aggregate_from_csv(csv_path, year_filter="2018")
        assert [q.key for q in questions] == ["GSS_Q1"]

    def test_rejects_csv_missing_columns(self, tmp_path: Path):
        path = tmp_path / "bad.csv"
        path.write_text("question_id,option\nQ1,Yes\n")
        with pytest.raises(DatasetDownloadError, match="missing columns"):
            _aggregate_from_csv(path)


class TestGSSDataset:
    def test_load_builds_from_raw_csv_and_caches(self, tmp_path: Path):
        raw = tmp_path / "raw" / "gss_aggregated.csv"
        _write_csv(
            raw,
            [
                {
                    "question_id": "Q1",
                    "question_text": "A?",
                    "year": "2020",
                    "option": "Yes",
                    "count": 1,
                },
                {
                    "question_id": "Q1",
                    "question_text": "A?",
                    "year": "2020",
                    "option": "No",
                    "count": 3,
                },
            ],
        )

        ds = GSSDataset(data_dir=tmp_path)
        first = ds.load()
        assert len(first) == 1
        assert first[0].human_distribution == {"Yes": 0.25, "No": 0.75}

        # Second load should hit the cache — delete raw to prove it.
        raw.unlink()
        second = GSSDataset(data_dir=tmp_path).load()
        assert len(second) == 1
        assert second[0].human_distribution == {"Yes": 0.25, "No": 0.75}

    def test_load_raises_when_raw_missing(self, tmp_path: Path):
        ds = GSSDataset(data_dir=tmp_path)
        with pytest.raises(DatasetDownloadError, match="manual setup"):
            ds.load()

    def test_n_parameter_truncates(self, tmp_path: Path):
        raw = tmp_path / "raw" / "gss_aggregated.csv"
        _write_csv(
            raw,
            [
                {
                    "question_id": f"Q{i}",
                    "question_text": f"Q{i}?",
                    "year": "2020",
                    "option": "Yes",
                    "count": 5,
                }
                for i in range(4)
            ],
        )

        ds = GSSDataset(data_dir=tmp_path)
        assert len(ds.load(n=2)) == 2

    def test_year_constructor_arg_filters_cached_questions(self, tmp_path: Path):
        raw = tmp_path / "raw" / "gss_aggregated.csv"
        _write_csv(
            raw,
            [
                {
                    "question_id": "Q1",
                    "question_text": "A?",
                    "year": "2018",
                    "option": "Yes",
                    "count": 10,
                },
                {
                    "question_id": "Q1",
                    "question_text": "A?",
                    "year": "2022",
                    "option": "Yes",
                    "count": 10,
                },
                {
                    "question_id": "Q2",
                    "question_text": "B?",
                    "year": "2018",
                    "option": "Yes",
                    "count": 10,
                },
            ],
        )

        ds = GSSDataset(data_dir=tmp_path, year=2022)
        questions = ds.load()
        assert [q.key for q in questions] == ["GSS_Q1"]
        assert questions[0].survey == "GSS:2022"

    def test_info_reports_year_filter(self, tmp_path: Path):
        ds = GSSDataset(data_dir=tmp_path, year=2021)
        info = ds.info()
        assert info["name"] == "GSS"
        assert info["year_filter"] == "2021"

    def test_name_includes_year_when_filtered(self, tmp_path: Path):
        assert GSSDataset(data_dir=tmp_path).name == "gss"
        assert GSSDataset(data_dir=tmp_path, year=2020).name == "gss (2020)"
