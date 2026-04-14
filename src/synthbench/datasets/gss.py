"""General Social Survey (GSS) dataset loader.

Loads questions from NORC's General Social Survey (1972-present). Covers US
social attitudes on work, gender roles, race, spending priorities, and
confidence in institutions.

GSS microdata is public at https://gss.norc.org, but the raw SPSS/STATA files
are large and require aggregation. This adapter reads a pre-aggregated CSV
produced from the microdata; see ``_try_download`` for setup instructions.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from synthbench.datasets.base import Dataset, Question

_GSS_URL = "https://gss.norc.org/Get-The-Data"

# Expected CSV columns in the pre-aggregated input file.
_REQUIRED_COLUMNS = ("question_id", "question_text", "year", "option", "count")


def _default_cache_dir() -> Path:
    return Path.home() / ".synthbench" / "data" / "gss"


class GSSDataset(Dataset):
    """General Social Survey: US social attitudes from 1972 to present."""

    def __init__(
        self,
        data_dir: Path | str | None = None,
        year: int | str | None = None,
    ):
        self._data_dir = Path(data_dir) if data_dir else _default_cache_dir()
        self._year = str(year) if year is not None else None

    @property
    def name(self) -> str:
        if self._year:
            return f"gss ({self._year})"
        return "gss"

    def info(self) -> dict:
        return {
            "name": "GSS",
            "source": "NORC General Social Survey",
            "url": _GSS_URL,
            "license": "Public domain (NORC)",
            "year_filter": self._year,
        }

    def load(self, n: int | None = None) -> list[Question]:
        cache_path = self._data_dir / "questions.json"

        if cache_path.exists():
            questions = self._load_cached(cache_path)
        else:
            questions = self._build_from_raw()

        if self._year:
            questions = [q for q in questions if q.survey.endswith(self._year)]

        if n is not None:
            questions = questions[:n]
        return questions

    def _load_cached(self, path: Path) -> list[Question]:
        with open(path) as f:
            data = json.load(f)
        return [
            Question(
                key=q["key"],
                text=q["text"],
                options=q["options"],
                human_distribution=q["human_distribution"],
                survey=q.get("survey", "GSS"),
                topic=q.get("topic", ""),
            )
            for q in data["questions"]
        ]

    def _save_cache(self, questions: list[Question]) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "dataset": "gss",
            "version": "1.0",
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
        with open(self._data_dir / "questions.json", "w") as f:
            json.dump(data, f, indent=2)

    def _build_from_raw(self) -> list[Question]:
        raw_path = self._data_dir / "raw" / "gss_aggregated.csv"
        if not raw_path.exists():
            self._raise_setup_instructions(raw_path)

        questions = _aggregate_from_csv(raw_path, year_filter=self._year)
        self._save_cache(questions)
        return questions

    def _raise_setup_instructions(self, raw_path: Path) -> None:
        raise DatasetDownloadError(
            "General Social Survey data requires manual setup.\n\n"
            "Steps:\n"
            f"  1. Visit: {_GSS_URL}\n"
            "  2. Download the GSS cumulative data file (STATA or SPSS format)\n"
            "  3. Aggregate into a CSV with columns:\n"
            f"       {', '.join(_REQUIRED_COLUMNS)}\n"
            "     One row per (question_id, year, option) with the respondent\n"
            "     count for that option in that survey year.\n"
            f"  4. Save the aggregated file as:\n     {raw_path}\n"
            "  5. Re-run synthbench\n"
        )


def _aggregate_from_csv(
    path: Path,
    year_filter: str | None = None,
) -> list[Question]:
    """Aggregate per-year option counts into Question distributions.

    If *year_filter* is given, ground truth is that year's distribution.
    Otherwise counts are summed across all years (cumulative distribution).
    """
    by_question: dict[str, dict] = {}

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in _REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise DatasetDownloadError(
                f"GSS aggregated CSV at {path} is missing columns: {missing}.\n"
                f"Expected columns: {', '.join(_REQUIRED_COLUMNS)}"
            )
        for row in reader:
            qid = (row.get("question_id") or "").strip()
            text = (row.get("question_text") or "").strip()
            year = (row.get("year") or "").strip()
            option = (row.get("option") or "").strip()
            count_raw = (row.get("count") or "").strip()
            if not qid or not text or not year or not option:
                continue
            try:
                count = float(count_raw)
            except ValueError:
                continue
            if count <= 0:
                continue

            entry = by_question.setdefault(
                qid,
                {
                    "text": text,
                    "options": [],
                    "option_set": set(),
                    "counts": defaultdict(lambda: defaultdict(float)),
                },
            )
            if option not in entry["option_set"]:
                entry["options"].append(option)
                entry["option_set"].add(option)
            entry["counts"][year][option] += count

    questions: list[Question] = []
    for qid in sorted(by_question):
        entry = by_question[qid]
        options: list[str] = entry["options"]
        counts: dict[str, dict[str, float]] = entry["counts"]

        if year_filter is not None:
            if year_filter not in counts:
                continue
            dist_counts = counts[year_filter]
            survey = f"GSS:{year_filter}"
            totals = {opt: dist_counts.get(opt, 0.0) for opt in options}
        else:
            survey = "GSS"
            totals = {opt: 0.0 for opt in options}
            for ydist in counts.values():
                for opt, c in ydist.items():
                    totals[opt] = totals.get(opt, 0.0) + c

        total = sum(totals.values())
        if total <= 0:
            continue
        dist = {opt: totals[opt] / total for opt in options if totals[opt] > 0}
        if not dist:
            continue

        questions.append(
            Question(
                key=f"GSS_{qid}",
                text=entry["text"],
                options=[o for o in options if o in dist],
                human_distribution=dist,
                survey=survey,
            )
        )

    return questions


class DatasetDownloadError(Exception):
    """Raised when required GSS data files are missing."""
