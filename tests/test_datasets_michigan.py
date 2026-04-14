"""Tests for the Michigan Consumer Sentiment dataset loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from synthbench.datasets.michigan import (
    DEMOGRAPHIC_ATTRIBUTES,
    QUESTION_METADATA,
    DatasetDownloadError,
    MichiganSentimentDataset,
    _average_csv_distribution,
    _average_csv_distribution_by_group,
)


# --------------------------------------------------------------------- #
# Registry wiring
# --------------------------------------------------------------------- #


def test_registered_in_datasets_registry():
    from synthbench.datasets import DATASETS, MichiganSentimentDataset as Exported

    assert DATASETS["michigan"] is Exported
    assert Exported is MichiganSentimentDataset


def test_info_metadata():
    ds = MichiganSentimentDataset(data_dir="/tmp/michigan_does_not_exist")
    info = ds.info()
    assert info["name"] == "Michigan Consumer Sentiment"
    assert info["cadence"] == "monthly"
    assert info["n_questions"] == len(QUESTION_METADATA)
    assert info["demographics"] == len(DEMOGRAPHIC_ATTRIBUTES)


def test_demographic_attributes_match_bead_spec():
    # sb-michigan requires age, income, education, political party.
    assert set(DEMOGRAPHIC_ATTRIBUTES) == {"AGE", "INCOME", "EDUCATION", "POLPARTY"}


# --------------------------------------------------------------------- #
# Cache load path
# --------------------------------------------------------------------- #


class TestLoadCached:
    def test_roundtrip_string_options(self, tmp_path: Path):
        cache_dir = tmp_path / "michigan"
        cache_dir.mkdir()
        (cache_dir / "questions.json").write_text(
            json.dumps(
                {
                    "dataset": "michigan",
                    "version": "1.0",
                    "n_questions": 1,
                    "questions": [
                        {
                            "key": "PAGO",
                            "text": "Better or worse?",
                            "options": ["Better", "Same", "Worse"],
                            "human_distribution": {
                                "Better": 0.3,
                                "Same": 0.4,
                                "Worse": 0.3,
                            },
                            "survey": "SCA",
                            "topic": "personal_finances",
                        }
                    ],
                }
            )
        )

        ds = MichiganSentimentDataset(data_dir=cache_dir)
        questions = ds.load()

        assert len(questions) == 1
        q = questions[0]
        assert q.key == "PAGO"
        assert q.options == ["Better", "Same", "Worse"]
        assert all(isinstance(v, float) for v in q.human_distribution.values())
        assert abs(sum(q.human_distribution.values()) - 1.0) < 1e-6

    def test_numeric_options_coerced_to_strings(self, tmp_path: Path):
        # Defensive: if a future cache writer emits numeric option labels, the
        # loader should stringify them so downstream serializers stay happy
        # (same invariant enforced for GlobalOpinionQA in sb-cym).
        cache_dir = tmp_path / "michigan"
        cache_dir.mkdir()
        (cache_dir / "questions.json").write_text(
            json.dumps(
                {
                    "dataset": "michigan",
                    "version": "1.0",
                    "n_questions": 1,
                    "questions": [
                        {
                            "key": "STK12",
                            "text": "Probability?",
                            "options": [1, 2, 3, 4, 5],
                            "human_distribution": {
                                "1": 0.1,
                                "2": 0.2,
                                "3": 0.4,
                                "4": 0.2,
                                "5": 0.1,
                            },
                        }
                    ],
                }
            )
        )

        ds = MichiganSentimentDataset(data_dir=cache_dir)
        q = ds.load()[0]
        assert q.options == ["1", "2", "3", "4", "5"]
        assert all(isinstance(o, str) for o in q.options)

    def test_load_n_truncates(self, tmp_path: Path):
        cache_dir = tmp_path / "michigan"
        cache_dir.mkdir()
        (cache_dir / "questions.json").write_text(
            json.dumps(
                {
                    "dataset": "michigan",
                    "version": "1.0",
                    "n_questions": 3,
                    "questions": [
                        {
                            "key": f"Q{i}",
                            "text": "x",
                            "options": ["A", "B"],
                            "human_distribution": {"A": 0.5, "B": 0.5},
                        }
                        for i in range(3)
                    ],
                }
            )
        )

        ds = MichiganSentimentDataset(data_dir=cache_dir)
        assert len(ds.load(n=2)) == 2


# --------------------------------------------------------------------- #
# Missing data path
# --------------------------------------------------------------------- #


class TestMissingData:
    def test_no_cache_and_no_raw_raises_with_instructions(self, tmp_path: Path):
        ds = MichiganSentimentDataset(data_dir=tmp_path / "empty")
        with pytest.raises(DatasetDownloadError) as excinfo:
            ds.load()
        msg = str(excinfo.value)
        assert "data.sca.isr.umich.edu" in msg
        assert "overall" in msg
        assert "AGE" in msg

    def test_demographic_missing_returns_empty(self, tmp_path: Path):
        ds = MichiganSentimentDataset(data_dir=tmp_path / "empty")
        assert ds.load_demographic_distributions("AGE") == {}

    def test_demographic_unknown_attribute_returns_empty(self, tmp_path: Path):
        ds = MichiganSentimentDataset(data_dir=tmp_path / "empty")
        assert ds.load_demographic_distributions("FAVORITE_COLOR") == {}


# --------------------------------------------------------------------- #
# Raw CSV aggregation
# --------------------------------------------------------------------- #


class TestOverallAggregation:
    def test_monthly_rows_averaged(self, tmp_path: Path):
        raw_dir = tmp_path / "michigan" / "raw" / "overall"
        raw_dir.mkdir(parents=True)
        csv_path = raw_dir / "PAGO.csv"
        csv_path.write_text(
            "date,Better,Same,Worse\n"
            "2024-01,30,40,30\n"
            "2024-02,40,30,30\n"
            "2024-03,20,50,30\n"
        )

        dist = _average_csv_distribution(csv_path, ["Better", "Same", "Worse"])
        assert abs(sum(dist.values()) - 1.0) < 1e-6
        # Means: (0.30+0.40+0.20)/3 = 0.30, (0.40+0.30+0.50)/3 = 0.40, 0.30
        assert abs(dist["Better"] - 0.30) < 1e-6
        assert abs(dist["Same"] - 0.40) < 1e-6
        assert abs(dist["Worse"] - 0.30) < 1e-6

    def test_download_and_process_end_to_end(self, tmp_path: Path):
        base = tmp_path / "michigan"
        overall = base / "raw" / "overall"
        overall.mkdir(parents=True)
        (overall / "PAGO.csv").write_text(
            "date,Better,Same,Worse\n2024-01,25,50,25\n2024-02,35,40,25\n"
        )
        (overall / "BUS12.csv").write_text(
            "date,Good,Uncertain,Bad\n2024-01,50,20,30\n"
        )

        ds = MichiganSentimentDataset(data_dir=base)
        questions = ds.load()

        keys = {q.key for q in questions}
        assert keys == {"PAGO", "BUS12"}

        pago = next(q for q in questions if q.key == "PAGO")
        assert pago.options == ["Better", "Same", "Worse"]
        assert abs(pago.human_distribution["Better"] - 0.30) < 1e-6
        assert pago.topic == "personal_finances"
        assert pago.survey == "SCA"

        # Second load should hit the cache — delete raw dir, still works.
        import shutil

        shutil.rmtree(base / "raw")
        reloaded = MichiganSentimentDataset(data_dir=base).load()
        assert {q.key for q in reloaded} == {"PAGO", "BUS12"}

    def test_row_normalization_handles_counts(self, tmp_path: Path):
        # Counts instead of percentages should also normalize correctly.
        raw_dir = tmp_path / "overall"
        raw_dir.mkdir()
        csv_path = raw_dir / "BUS12.csv"
        csv_path.write_text(
            "date,Good,Uncertain,Bad\n2024-01,200,100,200\n2024-02,150,50,300\n"
        )

        dist = _average_csv_distribution(csv_path, ["Good", "Uncertain", "Bad"])
        assert abs(sum(dist.values()) - 1.0) < 1e-6

    def test_malformed_rows_skipped(self, tmp_path: Path):
        raw_dir = tmp_path / "overall"
        raw_dir.mkdir()
        csv_path = raw_dir / "PAGO.csv"
        csv_path.write_text(
            "date,Better,Same,Worse\n"
            "2024-01,30,40,30\n"
            "2024-02,bad,data,here\n"  # skipped
            "2024-03,,40,30\n"  # skipped
            "2024-04,40,30,30\n"
        )
        dist = _average_csv_distribution(csv_path, ["Better", "Same", "Worse"])
        # Two usable rows → (0.30+0.40)/2 = 0.35 Better
        assert abs(dist["Better"] - 0.35) < 1e-6


class TestDemographicAggregation:
    def test_group_rows_averaged_independently(self, tmp_path: Path):
        csv_path = tmp_path / "PAGO.csv"
        csv_path.write_text(
            "date,group,Better,Same,Worse\n"
            "2024-01,18-34,40,40,20\n"
            "2024-02,18-34,60,20,20\n"
            "2024-01,55+,20,50,30\n"
            "2024-02,55+,30,40,30\n"
        )

        groups = _average_csv_distribution_by_group(
            csv_path, ["Better", "Same", "Worse"]
        )
        assert set(groups) == {"18-34", "55+"}
        assert abs(groups["18-34"]["Better"] - 0.50) < 1e-6
        assert abs(groups["55+"]["Better"] - 0.25) < 1e-6
        for gd in groups.values():
            assert abs(sum(gd.values()) - 1.0) < 1e-6

    def test_load_demographic_distributions_end_to_end(self, tmp_path: Path):
        base = tmp_path / "michigan"
        (base / "raw" / "overall").mkdir(parents=True)
        (base / "raw" / "overall" / "PAGO.csv").write_text(
            "date,Better,Same,Worse\n2024-01,30,40,30\n"
        )
        (base / "raw" / "POLPARTY").mkdir(parents=True)
        (base / "raw" / "POLPARTY" / "PAGO.csv").write_text(
            "date,group,Better,Same,Worse\n"
            "2024-01,Democrat,50,30,20\n"
            "2024-01,Republican,10,40,50\n"
            "2024-01,Independent,30,40,30\n"
        )

        ds = MichiganSentimentDataset(data_dir=base)
        demo = ds.load_demographic_distributions("POLPARTY")

        assert "PAGO" in demo
        assert set(demo["PAGO"]) == {"Democrat", "Republican", "Independent"}
        assert abs(demo["PAGO"]["Democrat"]["Better"] - 0.50) < 1e-6
        assert abs(demo["PAGO"]["Republican"]["Worse"] - 0.50) < 1e-6

        # Second call should hit the demo cache.
        import shutil

        shutil.rmtree(base / "raw" / "POLPARTY")
        again = ds.load_demographic_distributions("POLPARTY")
        assert again == demo

    def test_demographic_case_insensitive(self, tmp_path: Path):
        base = tmp_path / "michigan"
        (base / "raw" / "AGE").mkdir(parents=True)
        (base / "raw" / "AGE" / "PAGO.csv").write_text(
            "date,group,Better,Same,Worse\n2024-01,18-34,40,40,20\n"
        )
        ds = MichiganSentimentDataset(data_dir=base)
        demo_upper = ds.load_demographic_distributions("AGE")
        # Hit the cache so force a fresh instance to re-read with lowercase
        base2 = tmp_path / "michigan2"
        (base2 / "raw" / "AGE").mkdir(parents=True)
        (base2 / "raw" / "AGE" / "PAGO.csv").write_text(
            "date,group,Better,Same,Worse\n2024-01,18-34,40,40,20\n"
        )
        ds2 = MichiganSentimentDataset(data_dir=base2)
        demo_lower = ds2.load_demographic_distributions("age")
        assert demo_upper == demo_lower
