"""Michigan Consumer Sentiment dataset loader.

Loads questions from the University of Michigan Survey of Consumers — a monthly
US telephone survey that anchors the widely-cited Index of Consumer Sentiment
(ICS) and Index of Consumer Expectations (ICE).

The Survey Research Center publishes summary tables per question as time series,
with demographic breakdowns across age, income, education, and political
affiliation. This adapter aggregates those monthly tables into overall and
per-subgroup response distributions so synthetic respondents can be evaluated
against real population behavior.

Data source: https://data.sca.isr.umich.edu/
License: Publicly available for research; cite the Survey Research Center,
University of Michigan.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from synthbench.datasets.base import Dataset, DatasetDownloadError, Question

_SCA_ARCHIVE_URL = "https://data.sca.isr.umich.edu/"

# Demographic attributes exposed by the SCA public data archive that the
# benchmark cares about. Names align with the CSV file prefixes the adapter
# looks for and with the attribute names runner.py passes through.
DEMOGRAPHIC_ATTRIBUTES = [
    "AGE",
    "INCOME",
    "EDUCATION",
    "POLPARTY",
]


# Core Survey of Consumers question set.  Each entry pins the question text
# and the discrete response categories the SCA publishes for that question.
# Keys match the SCA variable mnemonic (PAGO, BUS12, …) so raw CSV files can
# key off the filename.  Options are listed in the order SCA publishes them.
QUESTION_METADATA: dict[str, dict] = {
    # --- Personal finances -------------------------------------------------
    "PAGO": {
        "text": (
            "We are interested in how people are getting along financially these days. "
            "Would you say that you (and your family living there) are better off or "
            "worse off financially than you were a year ago?"
        ),
        "options": ["Better", "Same", "Worse"],
        "topic": "personal_finances",
    },
    "PEXP": {
        "text": (
            "Now looking ahead — do you think that a year from now you (and your family "
            "living there) will be better off financially, or worse off, or just about "
            "the same as now?"
        ),
        "options": ["Better", "Same", "Worse"],
        "topic": "personal_finances",
    },
    # --- Business conditions ----------------------------------------------
    "BUS12": {
        "text": (
            "Now turning to business conditions in the country as a whole — do you think "
            "that during the next twelve months we'll have good times financially, or "
            "bad times, or what?"
        ),
        "options": ["Good", "Uncertain", "Bad"],
        "topic": "business_conditions",
    },
    "BUS5": {
        "text": (
            "Looking ahead, which would you say is more likely — that in the country as "
            "a whole we'll have continuous good times during the next five years or so, "
            "or that we will have periods of widespread unemployment or depression, or "
            "what?"
        ),
        "options": ["Good", "Uncertain", "Bad"],
        "topic": "business_conditions",
    },
    # --- Buying conditions ------------------------------------------------
    "DUR": {
        "text": (
            "About the big things people buy for their homes — such as furniture, a "
            "refrigerator, stove, television, and things like that. Generally speaking, "
            "do you think now is a good or bad time for people to buy major household "
            "items?"
        ),
        "options": ["Good", "Pro-Con", "Bad"],
        "topic": "buying_conditions",
    },
    "HOM": {
        "text": (
            "Generally speaking, do you think now is a good time or a bad time to buy "
            "a house?"
        ),
        "options": ["Good", "Pro-Con", "Bad"],
        "topic": "buying_conditions",
    },
    "CAR": {
        "text": (
            "Speaking now of the automobile market — do you think the next 12 months or "
            "so will be a good time or a bad time to buy a vehicle, such as a car, "
            "pickup, van, or sport utility vehicle?"
        ),
        "options": ["Good", "Pro-Con", "Bad"],
        "topic": "buying_conditions",
    },
    # --- Inflation & expectations -----------------------------------------
    "PX1": {
        "text": (
            "During the next 12 months, do you think that prices in general will go up, "
            "or go down, or stay where they are now?"
        ),
        "options": ["Go up", "Stay the same", "Go down"],
        "topic": "inflation_expectations",
    },
    "PX5": {
        "text": (
            "What about the outlook for prices over the next 5 to 10 years? Do you "
            "think prices will be higher, about the same, or lower, 5 to 10 years from "
            "now?"
        ),
        "options": ["Higher", "About the same", "Lower"],
        "topic": "inflation_expectations",
    },
    # --- Employment & income ----------------------------------------------
    "UNEMP": {
        "text": (
            "How about people out of work during the coming 12 months — do you think "
            "that there will be more unemployment than now, about the same, or less?"
        ),
        "options": ["More", "About the same", "Less"],
        "topic": "labor_market",
    },
    "RATEX": {
        "text": (
            "No one can say for sure, but what do you think will happen to interest "
            "rates for borrowing money during the next 12 months — will they go up, "
            "stay the same, or go down?"
        ),
        "options": ["Go up", "Stay the same", "Go down"],
        "topic": "interest_rates",
    },
    "INEX": {
        "text": (
            "During the next 12 months, do you expect your (family) income to be higher "
            "or lower than during the past year?"
        ),
        "options": ["Higher", "About the same", "Lower"],
        "topic": "personal_finances",
    },
    # --- Government policy -------------------------------------------------
    "GOVT": {
        "text": (
            "As to the economic policy of the government — I mean steps taken to fight "
            "inflation or unemployment — would you say the government is doing a good "
            "job, only fair, or a poor job?"
        ),
        "options": ["Good", "Only fair", "Poor"],
        "topic": "government_policy",
    },
    # --- Stock market expectations ----------------------------------------
    "STK12": {
        "text": (
            "Considering all the different investments people might make in stocks, "
            "what do you think the chances are that a one-year investment in a diver"
            "sified portfolio of stocks will increase in value — would you say almost "
            "certain, very probable, fairly probable, not very probable, or not at all "
            "probable?"
        ),
        "options": [
            "Almost certain",
            "Very probable",
            "Fairly probable",
            "Not very probable",
            "Not at all probable",
        ],
        "topic": "financial_markets",
    },
}


def _default_cache_dir() -> Path:
    return Path.home() / ".synthbench" / "data" / "michigan"


def _normalize_options(options: list) -> list[str]:
    """Coerce option values to strings (consistent with GOQA adapter)."""
    return [str(o) for o in options]


class MichiganSentimentDataset(Dataset):
    """University of Michigan Survey of Consumers monthly questions."""

    # SRC terms: "Publicly available for research; cite the Survey Research
    # Center, University of Michigan." Research-use + attribution-required
    # distribution fits the ``gated`` tier (sb-sj6) — redistribution is
    # scoped to identifiable researchers via the sign-in gate, with full
    # attribution on every artifact.
    redistribution_policy = "gated"
    license_url = "https://data.sca.isr.umich.edu/terms.php"
    citation = "Survey Research Center, University of Michigan — Surveys of Consumers"

    DEMOGRAPHIC_ATTRIBUTES = DEMOGRAPHIC_ATTRIBUTES

    def __init__(self, data_dir: Path | str | None = None):
        self._data_dir = Path(data_dir) if data_dir else _default_cache_dir()

    @property
    def name(self) -> str:
        return "michigan"

    def info(self) -> dict:
        return {
            "name": "Michigan Consumer Sentiment",
            "source": "University of Michigan Survey Research Center",
            "url": _SCA_ARCHIVE_URL,
            "n_questions": len(QUESTION_METADATA),
            "demographics": len(DEMOGRAPHIC_ATTRIBUTES),
            "cadence": "monthly",
            "license": "public (cite SRC, University of Michigan)",
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
        """Load per-group distributions for a demographic attribute.

        Aggregates monthly time-series rows into a single distribution per
        (question, group) pair by averaging across all available months.

        Returns:
            {question_key: {group_name: {option: probability}}}
        """
        attr = attribute.upper()
        if attr not in DEMOGRAPHIC_ATTRIBUTES:
            return {}

        demo_cache = self._data_dir / f"demo_{attr}.json"
        if demo_cache.exists():
            with open(demo_cache) as f:
                return json.load(f)

        raw_dir = self._data_dir / "raw"
        if not raw_dir.exists():
            return {}

        result = self._aggregate_demographic(raw_dir, attr)
        self._save_demo_cache(attr, result)
        return result

    # ------------------------------------------------------------------ #
    # Internal: cache I/O
    # ------------------------------------------------------------------ #

    def _load_cached(self, path: Path) -> list[Question]:
        with open(path) as f:
            data = json.load(f)
        return [
            Question(
                key=q["key"],
                text=q["text"],
                options=_normalize_options(q["options"]),
                human_distribution={
                    str(k): float(v) for k, v in q["human_distribution"].items()
                },
                survey=q.get("survey", "SCA"),
                topic=q.get("topic", ""),
            )
            for q in data["questions"]
        ]

    def _save_cache(self, questions: list[Question]) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "dataset": "michigan",
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

    def _save_demo_cache(
        self, attribute: str, data: dict[str, dict[str, dict[str, float]]]
    ) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        with open(self._data_dir / f"demo_{attribute}.json", "w") as f:
            json.dump(data, f, indent=2)

    # ------------------------------------------------------------------ #
    # Internal: raw data processing
    # ------------------------------------------------------------------ #

    def _download_and_process(self) -> list[Question]:
        raw_dir = self._data_dir / "raw"
        if not raw_dir.exists():
            self._raise_manual_setup(raw_dir)

        questions = self._aggregate_overall(raw_dir)
        if not questions:
            self._raise_manual_setup(raw_dir)

        self._save_cache(questions)
        return questions

    def _raise_manual_setup(self, raw_dir: Path) -> None:
        raise DatasetDownloadError(
            "Michigan Consumer Sentiment data requires manual setup.\n\n"
            "The Survey Research Center does not expose a single bulk download, "
            "so the adapter reads CSV tables that you export from the archive.\n\n"
            "Steps:\n"
            f"  1. Visit: {_SCA_ARCHIVE_URL}\n"
            "  2. For each question of interest, export the time-series table\n"
            "     with demographic breakdowns (age, income, education, party).\n"
            f"  3. Save CSVs under: {raw_dir}\n"
            "       overall/{QKEY}.csv    - monthly overall response percentages\n"
            "       {ATTR}/{QKEY}.csv     - monthly per-group percentages\n"
            "                               where ATTR ∈ {AGE, INCOME, EDUCATION, POLPARTY}\n"
            "     Each CSV: first column 'date' (YYYY-MM), remaining columns are\n"
            "     the response options for that question (e.g. Better, Same, Worse)\n"
            "     containing percentages (0-100) or counts.\n"
            f"     Recognized question keys: {', '.join(sorted(QUESTION_METADATA))}\n"
            "  4. Re-run synthbench."
        )

    def _aggregate_overall(self, raw_dir: Path) -> list[Question]:
        """Build Question objects from overall/{QKEY}.csv tables.

        Averages each option's percentage across every month in the file.
        """
        overall_dir = raw_dir / "overall"
        if not overall_dir.is_dir():
            return []

        questions: list[Question] = []
        for qkey, meta in QUESTION_METADATA.items():
            csv_path = overall_dir / f"{qkey}.csv"
            if not csv_path.is_file():
                continue

            dist = _average_csv_distribution(csv_path, meta["options"])
            if not dist:
                continue

            questions.append(
                Question(
                    key=qkey,
                    text=meta["text"],
                    options=list(meta["options"]),
                    human_distribution=dist,
                    survey="SCA",
                    topic=meta.get("topic", ""),
                )
            )
        return questions

    def _aggregate_demographic(
        self,
        raw_dir: Path,
        attribute: str,
    ) -> dict[str, dict[str, dict[str, float]]]:
        """Read {ATTR}/{QKEY}.csv files and average per (question, group).

        The demographic CSV layout stacks months for every subgroup, with a
        'group' column identifying the subpopulation (e.g., '18-34', '$50-75K',
        'Democrat').  The adapter averages all rows within a group.
        """
        attr_dir = raw_dir / attribute
        if not attr_dir.is_dir():
            return {}

        result: dict[str, dict[str, dict[str, float]]] = {}
        for qkey, meta in QUESTION_METADATA.items():
            csv_path = attr_dir / f"{qkey}.csv"
            if not csv_path.is_file():
                continue

            per_group = _average_csv_distribution_by_group(csv_path, meta["options"])
            if per_group:
                result[qkey] = per_group

        return result


# ---------------------------------------------------------------------- #
# CSV parsing helpers
# ---------------------------------------------------------------------- #


def _average_csv_distribution(
    csv_path: Path,
    options: list[str],
) -> dict[str, float]:
    """Return option→mean distribution averaged across every row in csv_path.

    Missing option columns are skipped. Each row is treated as one month of
    response percentages (or counts — values are normalized per row).
    """
    sums = [0.0] * len(options)
    count = 0

    for row in _read_csv_rows(csv_path):
        values = _extract_option_values(row, options)
        if values is None:
            continue
        total = sum(values)
        if total <= 0:
            continue
        for i, v in enumerate(values):
            sums[i] += v / total
        count += 1

    if count == 0:
        return {}
    return {opt: sums[i] / count for i, opt in enumerate(options)}


def _average_csv_distribution_by_group(
    csv_path: Path,
    options: list[str],
) -> dict[str, dict[str, float]]:
    """Aggregate a demographic CSV into {group: {option: mean_pct}}.

    CSV layout:
      date, group, <option_1>, <option_2>, ...
    """
    sums: dict[str, list[float]] = defaultdict(lambda: [0.0] * len(options))
    counts: dict[str, int] = defaultdict(int)

    for row in _read_csv_rows(csv_path):
        group = (row.get("group") or row.get("Group") or "").strip()
        if not group:
            continue
        values = _extract_option_values(row, options)
        if values is None:
            continue
        total = sum(values)
        if total <= 0:
            continue
        bucket = sums[group]
        for i, v in enumerate(values):
            bucket[i] += v / total
        counts[group] += 1

    result: dict[str, dict[str, float]] = {}
    for group, bucket in sums.items():
        n = counts[group]
        if n == 0:
            continue
        result[group] = {opt: bucket[i] / n for i, opt in enumerate(options)}
    return result


def _extract_option_values(
    row: dict[str, str],
    options: list[str],
) -> list[float] | None:
    """Pull numeric option values from a CSV row, matching headers case-insensitively."""
    # Build case-insensitive lookup once per row
    lower_row = {k.strip().lower(): v for k, v in row.items() if k}

    values: list[float] = []
    for opt in options:
        raw = lower_row.get(opt.strip().lower())
        if raw is None or raw == "":
            return None
        try:
            values.append(float(raw))
        except (ValueError, TypeError):
            return None
    return values


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)
