"""NTIA Internet Use Survey dataset loader.

Loads binary Yes/No survey measures from NTIA's Internet Use Survey — the
Computer & Internet Use Supplement to the U.S. Census Current Population
Survey (CPS). NTIA publishes pre-computed summary statistics ("Analyze
Table") as a single public-domain CSV covering waves 1994-2023.

Each question has the form "Does this condition apply?" (e.g. "Uses the
Internet (Any Location)", "Anyone in Household Uses a Desktop, Laptop, or
Tablet at Home"). The ground-truth distribution is the population
proportion answering Yes vs. No.

Source: https://www.ntia.gov/page/download-ntia-internet-use-survey-datasets
License: Public domain (U.S. Government work)
"""

from __future__ import annotations

import csv
import json
import urllib.request
from collections import defaultdict
from pathlib import Path

from synthbench.datasets.base import Dataset, Question

_ANALYZE_TABLE_URL = (
    "https://www.ntia.gov/sites/default/files/"
    "data_central_downloads/datasets/ntia-analyze-table.csv"
)

# Universe rows are structural identifiers (usProp always 1.0), not questions.
_UNIVERSE_MARKERS = {"isHouseholder", "isPerson", "isAdult"}

# Demographic attribute → ordered list of (column_prefix, group_label) pairs.
# The Analyze Table uses fixed column prefixes like "age314Prop" for the
# 3-14 age band. Each attribute partitions the population into exhaustive
# groups summing to the universe.
_DEMOGRAPHIC_GROUPS: dict[str, list[tuple[str, str]]] = {
    "AGE": [
        ("age314", "3-14"),
        ("age1524", "15-24"),
        ("age2544", "25-44"),
        ("age4564", "45-64"),
        ("age65p", "65+"),
    ],
    "EMPLOYMENT": [
        ("workEmployed", "Employed"),
        ("workUnemployed", "Unemployed"),
        ("workNILF", "Not in Labor Force"),
    ],
    "INCOME": [
        ("incomeU25", "Under $25K"),
        ("income2549", "$25K-$50K"),
        ("income5074", "$50K-$75K"),
        ("income7599", "$75K-$100K"),
        ("income100p", "$100K+"),
    ],
    "EDUCATION": [
        ("edNoDiploma", "No Diploma"),
        ("edHSGrad", "HS Grad"),
        ("edSomeCollege", "Some College"),
        ("edCollegeGrad", "College Grad"),
    ],
    "SEX": [
        ("sexMale", "Male"),
        ("sexFemale", "Female"),
    ],
    "RACE": [
        ("raceWhite", "White"),
        ("raceBlack", "Black"),
        ("raceHispanic", "Hispanic"),
        ("raceAsian", "Asian"),
        ("raceAmIndian", "American Indian"),
        ("raceOther", "Other"),
    ],
    "DISABILITY": [
        ("disabilityNo", "No Disability"),
        ("disabilityYes", "Disability"),
    ],
    "GEOGRAPHY": [
        ("metroNo", "Non-Metro"),
        ("metroYes", "Metro"),
        ("metroUnknown", "Metro Unknown"),
    ],
    "SCHOOLCHILD": [
        ("scChldHomeNo", "No School-Age Child at Home"),
        ("scChldHomeYes", "School-Age Child at Home"),
    ],
    "VETERAN": [
        ("veteranNo", "Non-Veteran"),
        ("veteranYes", "Veteran"),
    ],
}

DEMOGRAPHIC_ATTRIBUTES = list(_DEMOGRAPHIC_GROUPS)


def _default_cache_dir() -> Path:
    return Path.home() / ".synthbench" / "data" / "ntia"


def _parse_prop(val: str | None) -> float | None:
    """Parse a proportion cell. Empty/whitespace cells → None (missing)."""
    if val is None:
        return None
    s = val.strip()
    if not s:
        return None
    try:
        p = float(s)
    except ValueError:
        return None
    if p < 0.0 or p > 1.0:
        return None
    return p


def _question_key(dataset: str, variable: str, universe: str) -> str:
    """Build a stable key from (dataset, variable, universe)."""
    ds_slug = dataset.replace(" ", "_")
    u_slug = universe or "all"
    return f"NTIA_{ds_slug}_{variable}_{u_slug}"


def _render_text(description: str, universe: str) -> str:
    """Produce a human-readable question text from the description.

    Appends universe context when present so the question is unambiguous
    outside the raw CSV, e.g. ``"Uses the Internet at Home (among adults)"``.
    """
    base = description.strip() or "(no description)"
    universe_phrase = {
        "isPerson": "among persons ages 3+",
        "isAdult": "among adults",
        "isHouseholder": "among householders",
        "adultInternetUser": "among adult internet users",
        "internetAnywhere": "among households with internet anywhere",
        "internetAtHome": "among households with home internet",
        "noInternetAtHome": "among households without home internet",
    }.get(universe)
    if universe_phrase:
        return f"{base} ({universe_phrase})?"
    return f"{base}?"


class NTIADataset(Dataset):
    """NTIA Internet Use Survey: CPS supplement on US internet use.

    Redistribution: ``full``. U.S. Government works are not subject to
    copyright (17 USC 105); NTIA explicitly publishes the Internet Use Survey
    Analyze Table for public use without restriction. This is the only
    adapter currently tiered as ``full``.

    Args:
        data_dir: Local cache directory. Defaults to ``~/.synthbench/data/ntia``.
        dataset_filter: Survey wave to load (e.g. ``"Nov 2023"``). When set,
            only questions from that wave are returned. When None, loads all
            waves available in the Analyze Table.
    """

    redistribution_policy = "full"
    license_url = "https://www.ntia.gov/page/download-ntia-internet-use-survey-datasets"
    citation = "NTIA Internet Use Survey (U.S. Government work, 17 USC 105)"

    DEMOGRAPHIC_ATTRIBUTES = DEMOGRAPHIC_ATTRIBUTES

    # Latest-known wave at time of writing. Used as the default filter when
    # no explicit dataset_filter is supplied so `synthbench run` on a fresh
    # install produces the ~80-question "current" survey rather than the
    # full 700+-row historical set.
    DEFAULT_WAVE = "Nov 2023"

    def __init__(
        self,
        data_dir: Path | str | None = None,
        dataset_filter: str | None = None,
    ):
        self._data_dir = Path(data_dir) if data_dir else _default_cache_dir()
        self._dataset_filter = (
            dataset_filter if dataset_filter is not None else self.DEFAULT_WAVE
        )

    @property
    def name(self) -> str:
        if self._dataset_filter:
            return f"ntia ({self._dataset_filter})"
        return "ntia"

    def info(self) -> dict:
        return {
            "name": "NTIA Internet Use Survey",
            "source": "NTIA Computer & Internet Use Supplement to CPS",
            "url": _ANALYZE_TABLE_URL,
            "license": "Public domain (U.S. Government work)",
            "wave": self._dataset_filter,
            "demographics": len(DEMOGRAPHIC_ATTRIBUTES),
            "waves_available": [
                "Nov 1994",
                "Oct 1997",
                "Dec 1998",
                "Aug 2000",
                "Sep 2001",
                "Oct 2003",
                "Oct 2007",
                "Oct 2009",
                "Oct 2010",
                "Jul 2011",
                "Oct 2012",
                "Jul 2013",
                "Jul 2015",
                "Nov 2017",
                "Nov 2019",
                "Nov 2021",
                "Nov 2023",
            ],
        }

    def load(self, n: int | None = None) -> list[Question]:
        """Load binary Yes/No questions for the selected wave."""
        rows = self._load_rows()
        questions = self._rows_to_questions(rows)

        if n is not None:
            questions = questions[:n]
        return questions

    # ------------------------------------------------------------------ #
    # Demographic distributions
    # ------------------------------------------------------------------ #

    def load_demographic_distributions(
        self,
        attribute: str,
    ) -> dict[str, dict[str, dict[str, float]]]:
        """Load per-group Yes/No distributions for a demographic attribute.

        Args:
            attribute: One of the NTIA demographic attribute names
                (e.g. ``"AGE"``, ``"INCOME"``, ``"GEOGRAPHY"``).

        Returns:
            ``{question_key: {group_name: {"Yes": prob, "No": 1 - prob}}}``
        """
        attr = attribute.upper()
        if attr not in _DEMOGRAPHIC_GROUPS:
            raise ValueError(
                f"Unknown NTIA demographic attribute: {attribute!r}. "
                f"Expected one of {DEMOGRAPHIC_ATTRIBUTES}."
            )

        rows = self._load_rows()
        groups = _DEMOGRAPHIC_GROUPS[attr]
        result: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)

        for row in rows:
            variable = row.get("variable", "").strip('"')
            if variable in _UNIVERSE_MARKERS:
                continue
            dataset = row.get("dataset", "").strip('"')
            universe = row.get("universe", "").strip('"')
            if self._dataset_filter and dataset != self._dataset_filter:
                continue

            qkey = _question_key(dataset, variable, universe)
            for col_prefix, group_label in groups:
                p = _parse_prop(row.get(f"{col_prefix}Prop"))
                if p is None:
                    continue
                result[qkey][group_label] = {"Yes": p, "No": 1.0 - p}

        return {k: v for k, v in result.items() if v}

    # ------------------------------------------------------------------ #
    # Internal: load / download / cache raw CSV rows
    # ------------------------------------------------------------------ #

    def _load_rows(self) -> list[dict[str, str]]:
        """Load raw CSV rows, downloading the Analyze Table if missing."""
        cache_path = self._data_dir / "analyze-table.csv"
        if not cache_path.exists():
            self._download(cache_path)

        with open(cache_path, newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    def _download(self, dest: Path) -> None:
        """Download the NTIA Analyze Table CSV (public domain)."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            with urllib.request.urlopen(_ANALYZE_TABLE_URL) as resp:  # noqa: S310
                data = resp.read()
        except Exception as e:
            raise DatasetDownloadError(
                f"Failed to download NTIA Analyze Table from {_ANALYZE_TABLE_URL}: {e}\n"
                "Download the CSV manually and place it at:\n"
                f"  {dest}\n"
                "See https://www.ntia.gov/page/download-ntia-internet-use-survey-datasets"
            ) from e
        dest.write_bytes(data)

    def _rows_to_questions(self, rows: list[dict[str, str]]) -> list[Question]:
        """Convert Analyze Table rows into Question objects."""
        questions: list[Question] = []
        for row in rows:
            variable = row.get("variable", "").strip('"')
            if not variable or variable in _UNIVERSE_MARKERS:
                continue
            dataset = row.get("dataset", "").strip('"')
            if self._dataset_filter and dataset != self._dataset_filter:
                continue

            us_prop = _parse_prop(row.get("usProp"))
            if us_prop is None:
                continue

            description = row.get("description", "").strip('"').strip()
            universe = row.get("universe", "").strip('"')
            qkey = _question_key(dataset, variable, universe)

            questions.append(
                Question(
                    key=qkey,
                    text=_render_text(description, universe),
                    options=["Yes", "No"],
                    human_distribution={"Yes": us_prop, "No": 1.0 - us_prop},
                    survey=f"NTIA {dataset}",
                )
            )
        return questions

    def save_cache(self, questions: list[Question], path: Path | None = None) -> Path:
        """Serialize processed questions to JSON. Provided for symmetry with
        the other adapters; not used on the hot path because the raw CSV is
        small (~2MB) and already cached locally."""
        path = path or (self._data_dir / "questions.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "dataset": "ntia",
            "version": "1.0",
            "wave": self._dataset_filter,
            "n_questions": len(questions),
            "questions": [
                {
                    "key": q.key,
                    "text": q.text,
                    "options": q.options,
                    "human_distribution": q.human_distribution,
                    "survey": q.survey,
                    "topic": q.topic,
                }
                for q in questions
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path


class DatasetDownloadError(Exception):
    """Raised when the Analyze Table cannot be fetched."""
