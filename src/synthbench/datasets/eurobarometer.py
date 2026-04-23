"""Eurobarometer Consumer Modules dataset loader.

Loads consumer-opinion survey questions from the European Commission's
Eurobarometer programme (Standard, Flash, and Special Consumer Conditions
modules). Eurobarometer surveys field quarterly across EU member states and
provide a cross-cultural benchmark of consumer attitudes, expectations, and
behaviour.

Demographics captured: age, sex, education, employment, country.

Data source: GESIS (ZACAT) microdata archive — https://www.gesis.org/eurobarometer-data-service/
License: GESIS terms of use; re-distribution of microdata is restricted so the
adapter does not auto-download. Pre-process the SPSS (.sav) exports locally
and drop them into the expected directory layout described below.

The adapter reuses the same ``info.csv`` + ``{ATTR}_data.json`` layout as the
OpinionsQA / PewTech adapters so existing preprocessing scripts can be
adapted with minimal effort.
"""

from __future__ import annotations

import csv
import json
from ast import literal_eval
from pathlib import Path

from synthbench.datasets.base import Dataset, DatasetDownloadError, Question

_GESIS_URL = "https://www.gesis.org/eurobarometer-data-service/"

# Demographic attributes stored per survey as ``<ATTR>_data.json``.
DEMOGRAPHIC_ATTRIBUTES = [
    "AGE",
    "SEX",
    "EDUCATION",
    "EMPLOYMENT",
    "COUNTRY",
]


def _default_cache_dir() -> Path:
    return Path.home() / ".synthbench" / "data" / "eurobarometer"


class EurobarometerConsumerDataset(Dataset):
    """Eurobarometer Consumer Modules: cross-EU consumer opinion questions."""

    # GESIS terms of use permit redistribution for research use with
    # attribution. Per-question distributions ship to the ``gated`` R2 tier
    # (sb-sj6): signed-in researchers can see them; anonymous visitors hit
    # the sign-in gate.
    redistribution_policy = "gated"
    license_url = "https://www.gesis.org/eurobarometer-data-service/about-eurobarometer"
    citation = "European Commission / GESIS — Eurobarometer Consumer Modules"

    DEMOGRAPHIC_ATTRIBUTES = DEMOGRAPHIC_ATTRIBUTES

    def __init__(self, data_dir: Path | str | None = None):
        self._data_dir = Path(data_dir) if data_dir else _default_cache_dir()

    @property
    def name(self) -> str:
        return "eurobarometer"

    def info(self) -> dict:
        return {
            "name": "Eurobarometer Consumer Modules",
            "source": "European Commission / GESIS Eurobarometer Data Service",
            "url": _GESIS_URL,
            "license": "GESIS terms of use (microdata redistribution restricted)",
            "demographics": list(DEMOGRAPHIC_ATTRIBUTES),
            "coverage": "EU member states, biannual+flash fielding",
            "topics": [
                "consumer conditions",
                "cross-border purchasing",
                "digital services",
                "sustainability attitudes",
                "price perception",
            ],
        }

    def load(self, n: int | None = None) -> list[Question]:
        cache_path = self._data_dir / "questions.json"

        if cache_path.exists():
            questions = self._load_cached(cache_path)
        else:
            questions = self._download_and_process()

        if n is not None:
            questions = questions[:n]
        return questions

    def load_demographic_distributions(
        self,
        attribute: str,
    ) -> dict[str, dict[str, dict[str, float]]]:
        """Load per-group human distributions for a demographic attribute.

        Args:
            attribute: One of ``AGE``, ``SEX``, ``EDUCATION``, ``EMPLOYMENT``,
                ``COUNTRY``.

        Returns:
            ``{question_key: {group_name: {option: probability}}}``
        """
        raw_dir = self._data_dir / "raw"
        surveys_dir = _find_surveys_dir(raw_dir)
        if surveys_dir is None:
            return {}

        result: dict[str, dict[str, dict[str, float]]] = {}

        for survey_dir in sorted(surveys_dir.iterdir()):
            if not survey_dir.is_dir():
                continue
            attr_path = survey_dir / f"{attribute}_data.json"
            if not attr_path.exists():
                continue

            with open(attr_path) as f:
                data = json.load(f)

            for qkey, entry in data.items():
                if not isinstance(entry, dict):
                    continue

                groups: dict[str, dict[str, float]] = {}
                for sub_key, counts in entry.items():
                    if sub_key in ("MC_options", "question_text", "nan"):
                        continue
                    if not isinstance(counts, dict):
                        continue

                    total = sum(float(v) for v in counts.values())
                    if total <= 0:
                        continue
                    groups[sub_key] = {
                        opt: float(val) / total for opt, val in counts.items()
                    }

                if groups:
                    result[qkey] = groups

        return result

    def _load_cached(self, path: Path) -> list[Question]:
        with open(path) as f:
            data = json.load(f)
        return [
            Question(
                key=q["key"],
                text=q["text"],
                options=[str(o) for o in q["options"]],
                human_distribution={
                    str(k): float(v) for k, v in q["human_distribution"].items()
                },
                survey=q.get("survey", ""),
                topic=q.get("topic", ""),
            )
            for q in data["questions"]
        ]

    def _save_cache(self, questions: list[Question]) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "dataset": "eurobarometer",
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
        cache_path = self._data_dir / "questions.json"
        with open(cache_path, "w") as f:
            json.dump(data, f, indent=2)

    def _download_and_process(self) -> list[Question]:
        raw_dir = self._data_dir / "raw"
        if not raw_dir.exists():
            raise DatasetDownloadError(
                "Eurobarometer microdata must be set up manually.\n\n"
                "Steps:\n"
                f"  1. Visit: {_GESIS_URL}\n"
                "  2. Create a free GESIS account and accept the Eurobarometer "
                "terms of use\n"
                "  3. Download Consumer Conditions / Standard EB waves of "
                "interest as SPSS (.sav)\n"
                "  4. Pre-process each survey into the following layout:\n"
                f"     {raw_dir}/<survey_id>/\n"
                "       info.csv         - columns: key, question, references\n"
                "       NONE_data.json   - overall counts "
                '{key: {"<option>": count}}\n'
                "       {ATTR}_data.json - per-group counts for "
                f"{', '.join(DEMOGRAPHIC_ATTRIBUTES)}\n"
                "  5. Re-run synthbench.\n"
            )

        surveys_dir = _find_surveys_dir(raw_dir)
        if surveys_dir is None:
            raise DatasetDownloadError(
                f"No survey subdirectories found under {raw_dir}.\n"
                f"See {_GESIS_URL} for data download and preprocessing guidance."
            )

        questions = _process_surveys(surveys_dir)
        self._save_cache(questions)
        return questions

    def available_surveys(self) -> list[str]:
        """Return sorted list of survey ids discovered in the raw directory."""
        surveys_dir = _find_surveys_dir(self._data_dir / "raw")
        if surveys_dir is None:
            return []
        return sorted(p.name for p in surveys_dir.iterdir() if p.is_dir())


def _find_surveys_dir(raw_dir: Path) -> Path | None:
    """Return the directory containing per-survey subdirectories."""
    if not raw_dir.exists():
        return None

    # Prefer a ``surveys/`` subdirectory if it exists; otherwise use raw_dir
    # itself provided it directly contains survey folders.
    nested = raw_dir / "surveys"
    if nested.is_dir():
        return nested

    for child in raw_dir.iterdir():
        if child.is_dir() and (child / "info.csv").exists():
            return raw_dir
    return None


def _process_surveys(surveys_dir: Path) -> list[Question]:
    questions: list[Question] = []

    for survey_dir in sorted(surveys_dir.iterdir()):
        if not survey_dir.is_dir():
            continue

        info_path = survey_dir / "info.csv"
        if not info_path.exists():
            continue

        dist_by_key = _load_survey_distributions(survey_dir)
        survey_id = survey_dir.name

        for row in _read_csv(info_path):
            qkey = row.get("key", "")
            if not qkey:
                continue

            refs_raw = row.get("references", "")
            try:
                refs = literal_eval(refs_raw) if refs_raw else []
            except (ValueError, SyntaxError):
                refs = [r.strip() for r in refs_raw.split(",") if r.strip()]

            if not refs:
                continue
            refs = [str(r) for r in refs]

            question_text = row.get("question", qkey)
            human_dist = dist_by_key.get(qkey, {})
            if not human_dist:
                continue

            questions.append(
                Question(
                    key=f"{survey_id}:{qkey}",
                    text=question_text,
                    options=refs,
                    human_distribution=human_dist,
                    survey=survey_id,
                    topic=row.get("topic", ""),
                )
            )

    return questions


def _load_survey_distributions(survey_dir: Path) -> dict[str, dict[str, float]]:
    """Load aggregated human response distributions for one Eurobarometer survey.

    Prefers ``NONE_data.json`` (overall population). Falls back to summing
    sub-groups from the first available demographic ``*_data.json``.
    Returns ``{question_key: {option: count}}`` (unnormalized — renormalized
    in ``Question.__post_init__``).
    """
    none_path = survey_dir / "NONE_data.json"
    json_path = None
    if none_path.exists():
        json_path = none_path
    else:
        for p in sorted(survey_dir.glob("*_data.json")):
            json_path = p
            break

    if json_path is None:
        return {}

    with open(json_path) as f:
        data = json.load(f)

    result: dict[str, dict[str, float]] = {}
    for qkey, entry in data.items():
        if not isinstance(entry, dict):
            continue
        totals: dict[str, float] = {}
        for sub_key, counts in entry.items():
            if sub_key in ("MC_options", "question_text"):
                continue
            if not isinstance(counts, dict):
                continue
            for option, val in counts.items():
                totals[str(option)] = totals.get(str(option), 0.0) + float(val)
        if totals:
            result[qkey] = totals
    return result


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)
