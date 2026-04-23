"""World Values Survey (Wave 7) dataset loader.

Loads survey questions with ground-truth distributions from WVS Wave 7
(2017-2022). Covers 64 countries, 290+ questions on social values, political
orientation, economic priorities, and religious beliefs.

WVS microdata requires registration at https://worldvaluessurvey.org, so this
adapter expects a pre-aggregated CSV produced from the SPSS/CSV microdata.
See ``_try_download`` for the expected format and setup instructions.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from synthbench.datasets.base import Dataset, DatasetDownloadError, Question

_WVS_URL = "https://worldvaluessurvey.org/WVSDocumentationWV7.jsp"

# Expected CSV columns in the pre-aggregated input file.
_REQUIRED_COLUMNS = ("question_id", "question_text", "country", "option", "count")


def _default_cache_dir() -> Path:
    return Path.home() / ".synthbench" / "data" / "wvs"


class WVSDataset(Dataset):
    """World Values Survey Wave 7: cross-national opinion data."""

    # WVS microdata requires registration and explicit agreement to terms
    # that restrict redistribution of the underlying data. The ``gated``
    # tier (sb-sj6) satisfies those terms: per-question distributions ship
    # behind a JWT-authenticated Worker, so only identified visitors reach
    # them. Anonymous visitors see the sign-in gate.
    redistribution_policy = "gated"
    license_url = "https://worldvaluessurvey.org/WVSDocumentationWV7.jsp"
    citation = "World Values Survey Association — WVS Wave 7 (2017-2022)"

    def __init__(
        self,
        data_dir: Path | str | None = None,
        country: str | None = None,
    ):
        self._data_dir = Path(data_dir) if data_dir else _default_cache_dir()
        self._country = country

    @property
    def name(self) -> str:
        if self._country:
            return f"wvs ({self._country})"
        return "wvs"

    def info(self) -> dict:
        return {
            "name": "WVS7",
            "source": "World Values Survey, Wave 7 (2017-2022)",
            "url": _WVS_URL,
            "license": "Academic use; registration required",
            "country_filter": self._country,
        }

    def load(self, n: int | None = None) -> list[Question]:
        cache_path = self._data_dir / "questions.json"

        if cache_path.exists():
            questions = self._load_cached(cache_path)
        else:
            questions = self._build_from_raw()

        if self._country:
            questions = [q for q in questions if q.survey.endswith(self._country)]

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
                survey=q.get("survey", "WVS7"),
                topic=q.get("topic", ""),
            )
            for q in data["questions"]
        ]

    def _save_cache(self, questions: list[Question]) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "dataset": "wvs",
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
        raw_path = self._data_dir / "raw" / "wvs7_aggregated.csv"
        if not raw_path.exists():
            self._raise_setup_instructions(raw_path)

        questions = _aggregate_from_csv(raw_path, country_filter=self._country)
        self._save_cache(questions)
        return questions

    def _raise_setup_instructions(self, raw_path: Path) -> None:
        raise DatasetDownloadError(
            "World Values Survey Wave 7 data requires manual setup.\n\n"
            "Steps:\n"
            f"  1. Visit: {_WVS_URL}\n"
            "  2. Register for free academic access\n"
            "  3. Download the WV7 microdata (SPSS or CSV)\n"
            "  4. Aggregate into a CSV with columns:\n"
            f"       {', '.join(_REQUIRED_COLUMNS)}\n"
            "     One row per (question_id, country, option) with a count of\n"
            "     respondents who chose that option in that country.\n"
            f"  5. Save the aggregated file as:\n     {raw_path}\n"
            "  6. Re-run synthbench\n"
        )


def _aggregate_from_csv(
    path: Path,
    country_filter: str | None = None,
) -> list[Question]:
    """Aggregate per-country option counts into Question distributions.

    If *country_filter* is given, ground truth is that country's distribution.
    Otherwise counts are summed across all countries (population-weighted by
    sample size).
    """
    # {qid: {"text": str, "options": [opt,...],
    #         "counts": {country: {opt: count}}}}
    by_question: dict[str, dict] = {}

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in _REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise DatasetDownloadError(
                f"WVS aggregated CSV at {path} is missing columns: {missing}.\n"
                f"Expected columns: {', '.join(_REQUIRED_COLUMNS)}"
            )
        for row in reader:
            qid = (row.get("question_id") or "").strip()
            text = (row.get("question_text") or "").strip()
            country = (row.get("country") or "").strip()
            option = (row.get("option") or "").strip()
            count_raw = (row.get("count") or "").strip()
            if not qid or not text or not country or not option:
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
            entry["counts"][country][option] += count

    questions: list[Question] = []
    for qid in sorted(by_question):
        entry = by_question[qid]
        options: list[str] = entry["options"]
        counts: dict[str, dict[str, float]] = entry["counts"]

        if country_filter is not None:
            if country_filter not in counts:
                continue
            dist_counts = counts[country_filter]
            survey = f"WVS7:{country_filter}"
            totals = {opt: dist_counts.get(opt, 0.0) for opt in options}
        else:
            survey = "WVS7"
            totals = {opt: 0.0 for opt in options}
            for cdist in counts.values():
                for opt, c in cdist.items():
                    totals[opt] = totals.get(opt, 0.0) + c

        total = sum(totals.values())
        if total <= 0:
            continue
        dist = {opt: totals[opt] / total for opt in options if totals[opt] > 0}
        if not dist:
            continue

        questions.append(
            Question(
                key=f"WVS_{qid}",
                text=entry["text"],
                options=[o for o in options if o in dist],
                human_distribution=dist,
                survey=survey,
            )
        )

    return questions
