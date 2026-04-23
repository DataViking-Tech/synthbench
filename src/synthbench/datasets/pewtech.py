"""PewTech dataset loader.

Loads technology-focused survey questions from Pew Research Center's
Internet & Technology surveys (American Trends Panel).

Covers: tech adoption, digital privacy, social media attitudes, AI opinions.

Data source: https://www.pewresearch.org/internet/datasets/
"""

from __future__ import annotations

import csv
import json
from ast import literal_eval
from pathlib import Path

from synthbench.datasets.base import Dataset, DatasetDownloadError, Question

# Pew Internet & Technology team publications page.
_PEW_DATASETS_URL = "https://www.pewresearch.org/internet/datasets/"

# Technology-focused ATP wave numbers.  Unlike OpinionsQA (waves 26-92,
# broad topic coverage), these target surveys published by Pew's
# Internet & Technology team covering tech adoption, digital privacy,
# social media attitudes, and AI opinions.
#
# The adapter processes ANY waves found in the data directory, so this
# list is advisory — it tells users which waves to download.
TECH_WAVES = [86, 87, 91, 95, 98, 100, 103, 107, 110, 113]

# Same demographic attributes as OpinionsQA (Pew ATP standard).
DEMOGRAPHIC_ATTRIBUTES = [
    "AGE",
    "CREGION",
    "EDUCATION",
    "INCOME",
    "POLIDEOLOGY",
    "POLPARTY",
    "RACE",
    "SEX",
]


def _default_cache_dir() -> Path:
    return Path.home() / ".synthbench" / "data" / "pewtech"


class PewTechDataset(Dataset):
    """Pew Internet & Technology: tech-focused survey questions from ATP."""

    # Pew ATP datasets require registration and agreement to Pew's terms
    # (restricting redistribution). The ``gated`` tier (sb-sj6) satisfies
    # those terms: per-question distributions ship behind a JWT-
    # authenticated Worker, so only identified visitors reach them.
    # Anonymous visitors see the sign-in gate.
    redistribution_policy = "gated"
    license_url = "https://www.pewresearch.org/internet/datasets/"
    citation = "Pew Research Center — Internet & Technology (American Trends Panel)"

    def __init__(self, data_dir: Path | str | None = None):
        self._data_dir = Path(data_dir) if data_dir else _default_cache_dir()

    @property
    def name(self) -> str:
        return "pewtech"

    def info(self) -> dict:
        return {
            "name": "PewTech",
            "source": "Pew Research Center Internet & Technology",
            "url": _PEW_DATASETS_URL,
            "n_waves": len(TECH_WAVES),
            "demographics": len(DEMOGRAPHIC_ATTRIBUTES),
            "topics": [
                "tech adoption",
                "digital privacy",
                "social media",
                "AI attitudes",
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

    def _load_cached(self, path: Path) -> list[Question]:
        with open(path) as f:
            data = json.load(f)
        return [
            Question(
                key=q["key"],
                text=q["text"],
                options=q["options"],
                human_distribution=q["human_distribution"],
                survey=q.get("survey", ""),
                topic=q.get("topic", ""),
            )
            for q in data["questions"]
        ]

    def _save_cache(self, questions: list[Question]) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "dataset": "pewtech",
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
        """Process raw Pew ATP data from the data directory."""
        raw_dir = self._data_dir / "raw"

        if not raw_dir.exists():
            self._try_download(raw_dir)

        questions = self._process_raw_data(raw_dir)
        self._save_cache(questions)
        return questions

    def _try_download(self, raw_dir: Path) -> None:
        """Attempt to download Pew Internet & Technology survey data.

        Pew Research datasets require a free account, so auto-download is
        not available.  Raises with manual setup instructions.
        """
        raw_dir.mkdir(parents=True, exist_ok=True)

        raise DatasetDownloadError(
            "Pew Internet & Technology survey data requires manual setup.\n\n"
            "Steps:\n"
            f"  1. Visit: {_PEW_DATASETS_URL}\n"
            "  2. Create a free Pew Research account (if needed)\n"
            "  3. Download American Trends Panel datasets for tech waves\n"
            f"     Known tech waves: {', '.join(f'W{w}' for w in TECH_WAVES)}\n"
            "  4. Convert SPSS (.sav) files to the OpinionsQA directory format:\n"
            f"     {raw_dir}/human_resp/American_Trends_Panel_W{{N}}/\n"
            "       info.csv           - question metadata (key, question, references)\n"
            "       NONE_data.json     - overall response counts\n"
            "       {{ATTR}}_data.json - demographic response counts\n"
            "  5. Re-run synthbench\n"
        )

    def _process_raw_data(self, raw_dir: Path) -> list[Question]:
        """Process raw Pew ATP data into Question objects.

        Expected directory structure (same as OpinionsQA):
          raw_dir/human_resp/American_Trends_Panel_W{N}/
            info.csv          - question metadata (key, question, references, ...)
            NONE_data.json    - overall response counts (preferred)
            *_data.json       - demographic response counts (fallback)
        """
        human_resp_dir = _find_subdir(raw_dir, "human_resp")

        if human_resp_dir is None:
            raise DatasetDownloadError(
                f"Expected human_resp/ directory in {raw_dir}.\n"
                f"See {_PEW_DATASETS_URL} for data download instructions."
            )

        questions: list[Question] = []

        # Scan for all wave directories, not just TECH_WAVES.
        for wave_dir in sorted(human_resp_dir.glob("American_Trends_Panel_W*")):
            if not wave_dir.is_dir():
                continue

            wave_num = wave_dir.name.replace("American_Trends_Panel_W", "")

            info_path = wave_dir / "info.csv"
            if not info_path.exists():
                continue

            dist_by_key = _load_wave_distributions(wave_dir)

            for row in _read_csv(info_path):
                qkey = row.get("key", "")
                if not qkey:
                    continue

                refs_raw = row.get("references", "")
                try:
                    refs = literal_eval(refs_raw) if refs_raw else []
                except (ValueError, SyntaxError):
                    refs = [r.strip() for r in refs_raw.split(",")]

                if not refs:
                    continue

                question_text = row.get("question", qkey)
                human_dist = dist_by_key.get(qkey, {})

                if not human_dist:
                    continue

                questions.append(
                    Question(
                        key=qkey,
                        text=question_text,
                        options=refs,
                        human_distribution=human_dist,
                        survey=f"ATP W{wave_num}",
                    )
                )

        return questions

    def load_demographic_distributions(
        self,
        attribute: str,
    ) -> dict[str, dict[str, dict[str, float]]]:
        """Load per-group human distributions for a demographic attribute.

        Args:
            attribute: Demographic attribute name (e.g., "AGE", "POLIDEOLOGY").
                Must be one of the 8 standard Pew ATP attributes.

        Returns:
            {question_key: {group_name: {option: probability}}}
        """
        raw_dir = self._data_dir / "raw"
        human_resp_dir = _find_subdir(raw_dir, "human_resp")
        if human_resp_dir is None:
            return {}

        result: dict[str, dict[str, dict[str, float]]] = {}

        for wave_dir in sorted(human_resp_dir.glob("American_Trends_Panel_W*")):
            attr_path = wave_dir / f"{attribute}_data.json"
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


def _load_wave_distributions(wave_dir: Path) -> dict[str, dict[str, float]]:
    """Load aggregated human response distributions for one survey wave.

    Prefers NONE_data.json (overall population).  Falls back to summing
    sub-groups from the first available demographic *_data.json.
    Returns {question_key: {option: count}} (unnormalized).
    """
    none_path = wave_dir / "NONE_data.json"
    json_path = None
    if none_path.exists():
        json_path = none_path
    else:
        for p in sorted(wave_dir.glob("*_data.json")):
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
                totals[option] = totals.get(option, 0.0) + float(val)
        if totals:
            result[qkey] = totals
    return result


def _find_subdir(root: Path, name: str) -> Path | None:
    """Find a named subdirectory, searching recursively if needed."""
    if (root / name).is_dir():
        return root / name
    for p in root.rglob(name):
        if p.is_dir():
            return p
    return None


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)
