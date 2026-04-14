"""Tests for the NTIA Internet Use Survey dataset loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from synthbench.datasets.ntia import (
    DEMOGRAPHIC_ATTRIBUTES,
    NTIADataset,
    _parse_prop,
    _question_key,
    _render_text,
)


# A compact fixture mirroring the real NTIA Analyze Table schema. Only the
# columns the adapter reads are populated; others are left blank so the
# test catches regressions where missing values are misparsed as 0.0.
_FIXTURE_HEADER = [
    "dataset",
    "variable",
    "description",
    "universe",
    "usProp",
    "usPropSE",
    "usCount",
    "usCountSE",
    "age314Prop",
    "age314PropSE",
    "age314Count",
    "age314CountSE",
    "age1524Prop",
    "age1524PropSE",
    "age1524Count",
    "age1524CountSE",
    "age2544Prop",
    "age2544PropSE",
    "age2544Count",
    "age2544CountSE",
    "age4564Prop",
    "age4564PropSE",
    "age4564Count",
    "age4564CountSE",
    "age65pProp",
    "age65pPropSE",
    "age65pCount",
    "age65pCountSE",
    "workEmployedProp",
    "workEmployedPropSE",
    "workEmployedCount",
    "workEmployedCountSE",
    "workUnemployedProp",
    "workUnemployedPropSE",
    "workUnemployedCount",
    "workUnemployedCountSE",
    "workNILFProp",
    "workNILFPropSE",
    "workNILFCount",
    "workNILFCountSE",
    "incomeU25Prop",
    "incomeU25PropSE",
    "incomeU25Count",
    "incomeU25CountSE",
    "income2549Prop",
    "income2549PropSE",
    "income2549Count",
    "income2549CountSE",
    "income5074Prop",
    "income5074PropSE",
    "income5074Count",
    "income5074CountSE",
    "income7599Prop",
    "income7599PropSE",
    "income7599Count",
    "income7599CountSE",
    "income100pProp",
    "income100pPropSE",
    "income100pCount",
    "income100pCountSE",
    "edNoDiplomaProp",
    "edNoDiplomaPropSE",
    "edNoDiplomaCount",
    "edNoDiplomaCountSE",
    "edHSGradProp",
    "edHSGradPropSE",
    "edHSGradCount",
    "edHSGradCountSE",
    "edSomeCollegeProp",
    "edSomeCollegePropSE",
    "edSomeCollegeCount",
    "edSomeCollegeCountSE",
    "edCollegeGradProp",
    "edCollegeGradPropSE",
    "edCollegeGradCount",
    "edCollegeGradCountSE",
    "sexMaleProp",
    "sexMalePropSE",
    "sexMaleCount",
    "sexMaleCountSE",
    "sexFemaleProp",
    "sexFemalePropSE",
    "sexFemaleCount",
    "sexFemaleCountSE",
    "raceWhiteProp",
    "raceWhitePropSE",
    "raceWhiteCount",
    "raceWhiteCountSE",
    "raceBlackProp",
    "raceBlackPropSE",
    "raceBlackCount",
    "raceBlackCountSE",
    "raceHispanicProp",
    "raceHispanicPropSE",
    "raceHispanicCount",
    "raceHispanicCountSE",
    "raceAsianProp",
    "raceAsianPropSE",
    "raceAsianCount",
    "raceAsianCountSE",
    "raceAmIndianProp",
    "raceAmIndianPropSE",
    "raceAmIndianCount",
    "raceAmIndianCountSE",
    "raceOtherProp",
    "raceOtherPropSE",
    "raceOtherCount",
    "raceOtherCountSE",
    "disabilityNoProp",
    "disabilityNoPropSE",
    "disabilityNoCount",
    "disabilityNoCountSE",
    "disabilityYesProp",
    "disabilityYesPropSE",
    "disabilityYesCount",
    "disabilityYesCountSE",
    "metroNoProp",
    "metroNoPropSE",
    "metroNoCount",
    "metroNoCountSE",
    "metroYesProp",
    "metroYesPropSE",
    "metroYesCount",
    "metroYesCountSE",
    "metroUnknownProp",
    "metroUnknownPropSE",
    "metroUnknownCount",
    "metroUnknownCountSE",
    "scChldHomeNoProp",
    "scChldHomeNoPropSE",
    "scChldHomeNoCount",
    "scChldHomeNoCountSE",
    "scChldHomeYesProp",
    "scChldHomeYesPropSE",
    "scChldHomeYesCount",
    "scChldHomeYesCountSE",
    "veteranNoProp",
    "veteranNoPropSE",
    "veteranNoCount",
    "veteranNoCountSE",
    "veteranYesProp",
    "veteranYesPropSE",
    "veteranYesCount",
    "veteranYesCountSE",
]


def _fill(**kwargs) -> list[str]:
    """Produce one CSV data row aligned with _FIXTURE_HEADER."""
    row = []
    for col in _FIXTURE_HEADER:
        row.append(str(kwargs.get(col, "")))
    return row


def _write_fixture(cache_dir: Path) -> Path:
    import csv

    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / "analyze-table.csv"
    rows = [
        # Structural identity row — must be filtered out.
        _fill(
            dataset="Nov 2023",
            variable="isHouseholder",
            description="Household Reference Person",
            universe="",
            usProp="1.000000",
        ),
        # Real Nov 2023 question.
        _fill(
            dataset="Nov 2023",
            variable="internetUser",
            description="Uses the Internet (Any Location)",
            universe="isAdult",
            usProp="0.900000",
            age1524Prop="0.950000",
            age65pProp="0.780000",
            incomeU25Prop="0.800000",
            income100pProp="0.980000",
            edCollegeGradProp="0.970000",
            sexMaleProp="0.905000",
            sexFemaleProp="0.895000",
        ),
        # Wave filter should exclude this one.
        _fill(
            dataset="Nov 2021",
            variable="internetUser",
            description="Uses the Internet (Any Location)",
            universe="isAdult",
            usProp="0.850000",
        ),
        # Missing usProp → skipped.
        _fill(
            dataset="Nov 2023",
            variable="homeIOTUser",
            description="Interacts with Household Equipment Using the Internet",
            universe="adultInternetUser",
            usProp="",
        ),
    ]

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(_FIXTURE_HEADER)
        writer.writerows(rows)
    return path


class TestParseProp:
    def test_valid_float(self):
        assert _parse_prop("0.5") == 0.5

    def test_empty_is_none(self):
        assert _parse_prop("") is None
        assert _parse_prop("   ") is None

    def test_none_is_none(self):
        assert _parse_prop(None) is None

    def test_out_of_range_is_none(self):
        assert _parse_prop("1.5") is None
        assert _parse_prop("-0.1") is None

    def test_nonnumeric_is_none(self):
        assert _parse_prop("NA") is None


class TestQuestionKey:
    def test_dataset_space_becomes_underscore(self):
        assert _question_key("Nov 2023", "internetUser", "isAdult") == (
            "NTIA_Nov_2023_internetUser_isAdult"
        )

    def test_empty_universe_becomes_all(self):
        assert _question_key("Nov 2023", "isHouseholder", "") == (
            "NTIA_Nov_2023_isHouseholder_all"
        )


class TestRenderText:
    def test_universe_phrase_appended(self):
        text = _render_text("Uses the Internet at Home", "isAdult")
        assert text == "Uses the Internet at Home (among adults)?"

    def test_no_universe_still_ends_with_question_mark(self):
        assert _render_text("Something", "") == "Something?"

    def test_unknown_universe_ignored(self):
        # Unknown universe codes fall through without a phrase rather than
        # leaking raw identifiers like "isMadeUp" into user-facing text.
        assert _render_text("Something", "isMadeUp") == "Something?"


class TestLoad:
    def test_load_filters_to_default_wave(self, tmp_path: Path):
        _write_fixture(tmp_path)
        ds = NTIADataset(data_dir=tmp_path)

        questions = ds.load()

        # isHouseholder filtered, Nov 2021 filtered by wave, homeIOTUser
        # filtered by missing usProp → only internetUser Nov 2023 remains.
        assert len(questions) == 1
        q = questions[0]
        assert q.key == "NTIA_Nov_2023_internetUser_isAdult"
        assert q.options == ["Yes", "No"]
        assert q.survey == "NTIA Nov 2023"
        assert q.human_distribution["Yes"] == pytest.approx(0.9)
        assert q.human_distribution["No"] == pytest.approx(0.1)
        assert "among adults" in q.text

    def test_load_respects_n_limit(self, tmp_path: Path):
        _write_fixture(tmp_path)
        ds = NTIADataset(data_dir=tmp_path)

        assert ds.load(n=0) == []

    def test_dataset_filter_none_loads_all_waves(self, tmp_path: Path):
        _write_fixture(tmp_path)
        ds = NTIADataset(data_dir=tmp_path, dataset_filter="")

        # Empty string filter disables the wave filter (see __init__).
        # But the default behavior without filter should be wave-restricted.
        # Here we pass an empty string which the adapter treats as "no filter"
        # only when _dataset_filter is falsy — check both waves now appear.
        questions = ds.load()
        assert len(questions) == 2
        assert {q.survey for q in questions} == {"NTIA Nov 2023", "NTIA Nov 2021"}

    def test_explicit_wave_filter(self, tmp_path: Path):
        _write_fixture(tmp_path)
        ds = NTIADataset(data_dir=tmp_path, dataset_filter="Nov 2021")

        questions = ds.load()
        assert len(questions) == 1
        assert questions[0].survey == "NTIA Nov 2021"


class TestDemographicDistributions:
    def test_age_distributions(self, tmp_path: Path):
        _write_fixture(tmp_path)
        ds = NTIADataset(data_dir=tmp_path)

        demo = ds.load_demographic_distributions("AGE")

        qkey = "NTIA_Nov_2023_internetUser_isAdult"
        assert qkey in demo
        # Three age groups were populated in the fixture; the two missing
        # ones (age314, age2544, age4564) must be absent, not zero-filled.
        assert set(demo[qkey]) == {"15-24", "65+"}
        assert demo[qkey]["15-24"] == {
            "Yes": pytest.approx(0.95),
            "No": pytest.approx(0.05),
        }
        assert demo[qkey]["65+"] == {
            "Yes": pytest.approx(0.78),
            "No": pytest.approx(0.22),
        }

    def test_income_distributions(self, tmp_path: Path):
        _write_fixture(tmp_path)
        ds = NTIADataset(data_dir=tmp_path)

        demo = ds.load_demographic_distributions("INCOME")

        qkey = "NTIA_Nov_2023_internetUser_isAdult"
        assert demo[qkey]["Under $25K"]["Yes"] == pytest.approx(0.80)
        assert demo[qkey]["$100K+"]["Yes"] == pytest.approx(0.98)

    def test_lowercase_attribute(self, tmp_path: Path):
        _write_fixture(tmp_path)
        ds = NTIADataset(data_dir=tmp_path)

        # case-insensitive
        demo = ds.load_demographic_distributions("income")
        assert demo  # not empty

    def test_unknown_attribute_raises(self, tmp_path: Path):
        _write_fixture(tmp_path)
        ds = NTIADataset(data_dir=tmp_path)

        with pytest.raises(ValueError, match="Unknown NTIA demographic attribute"):
            ds.load_demographic_distributions("FAVORITE_COLOR")


class TestInfo:
    def test_info_exposes_wave_and_license(self):
        ds = NTIADataset(data_dir=Path("/nonexistent"))
        info = ds.info()
        assert info["name"] == "NTIA Internet Use Survey"
        assert "Public domain" in info["license"]
        assert info["wave"] == NTIADataset.DEFAULT_WAVE
        assert info["demographics"] == len(DEMOGRAPHIC_ATTRIBUTES)


class TestRegistry:
    def test_ntia_registered_in_DATASETS(self):
        from synthbench.datasets import DATASETS

        assert "ntia" in DATASETS
        assert DATASETS["ntia"] is NTIADataset


class TestSaveCache:
    def test_roundtrip_shape(self, tmp_path: Path):
        _write_fixture(tmp_path)
        ds = NTIADataset(data_dir=tmp_path)
        questions = ds.load()

        out = ds.save_cache(questions, path=tmp_path / "q.json")
        assert out.exists()

        import json

        data = json.loads(out.read_text())
        assert data["dataset"] == "ntia"
        assert data["n_questions"] == len(questions)
        assert data["wave"] == NTIADataset.DEFAULT_WAVE
