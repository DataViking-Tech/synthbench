"""OpinionsQA dataset loader.

Loads 1,498 survey questions from the OpinionsQA dataset
(Santurkar et al., ICML 2023) based on Pew American Trends Panel data.

Data source: https://worksheets.codalab.org/worksheets/0x6fb693719477478aac73fc07db333f69
Paper: https://arxiv.org/abs/2303.17548
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from ast import literal_eval
from pathlib import Path

import httpx

from synthbench.datasets.base import Dataset, Question

_CODALAB_WORKSHEET = "0x6fb693719477478aac73fc07db333f69"
_CODALAB_API = "https://worksheets.codalab.org/rest"

# Surveys included in OpinionsQA
PEW_WAVES = [26, 27, 29, 32, 34, 36, 41, 42, 43, 45, 49, 50, 54, 82, 92]


def _default_cache_dir() -> Path:
    return Path.home() / ".synthbench" / "data" / "opinionsqa"


class OpinionsQADataset(Dataset):
    """OpinionsQA: 1,498 questions from Pew American Trends Panel."""

    def __init__(self, data_dir: Path | str | None = None):
        self._data_dir = Path(data_dir) if data_dir else _default_cache_dir()

    @property
    def name(self) -> str:
        return "opinionsqa"

    def info(self) -> dict:
        return {
            "name": "OpinionsQA",
            "source": "Santurkar et al., ICML 2023",
            "paper": "https://arxiv.org/abs/2303.17548",
            "n_questions": 1498,
            "n_waves": len(PEW_WAVES),
            "demographics": 13,
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
            "dataset": "opinionsqa",
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
        """Try to download from CodaLab, then process raw data."""
        raw_dir = self._data_dir / "raw"

        if not raw_dir.exists():
            self._download_from_codalab(raw_dir)

        questions = self._process_raw_data(raw_dir)
        self._save_cache(questions)
        return questions

    def _download_from_codalab(self, raw_dir: Path) -> None:
        """Attempt to download the OpinionsQA bundle from CodaLab."""
        raw_dir.mkdir(parents=True, exist_ok=True)

        try:
            # List bundles on the worksheet
            resp = httpx.get(
                f"{_CODALAB_API}/interpret/worksheet/{_CODALAB_WORKSHEET}",
                timeout=30,
            )
            resp.raise_for_status()
            worksheet = resp.json()

            # Find data bundles
            bundle_uuids = []
            for item in worksheet.get("blocks", []):
                if item.get("mode") == "table_block":
                    for row in item.get("rows", []):
                        bundle_uuids.append(row.get("uuid"))
                elif "bundles_spec" in item:
                    for bundle in item.get("bundles_spec", {}).get("bundle_infos", []):
                        bundle_uuids.append(bundle.get("uuid"))

            if not bundle_uuids:
                # Try alternate structure
                for item in worksheet.get("items", []):
                    if "bundle_info" in item:
                        bundle_uuids.append(item["bundle_info"].get("uuid"))

            bundle_uuids = [u for u in bundle_uuids if u]

            if not bundle_uuids:
                raise RuntimeError("No bundles found on CodaLab worksheet")

            # Download each bundle
            for uuid in bundle_uuids:
                blob_url = f"{_CODALAB_API}/bundles/{uuid}/contents/blob/"
                blob_resp = httpx.get(blob_url, timeout=120, follow_redirects=True)
                blob_resp.raise_for_status()

                content_type = blob_resp.headers.get("content-type", "")
                if "zip" in content_type or blob_resp.content[:4] == b"PK\x03\x04":
                    with zipfile.ZipFile(io.BytesIO(blob_resp.content)) as zf:
                        zf.extractall(raw_dir)
                else:
                    # Try to determine filename
                    fname = f"bundle_{uuid[:8]}.dat"
                    (raw_dir / fname).write_bytes(blob_resp.content)

        except Exception as e:
            raise DatasetDownloadError(
                f"Could not auto-download OpinionsQA data: {e}\n\n"
                "Manual setup:\n"
                "  1. Go to: https://worksheets.codalab.org/worksheets/"
                f"{_CODALAB_WORKSHEET}\n"
                "  2. Download the dataset bundle\n"
                "  3. Extract to: {raw_dir}\n"
                "  4. Re-run synthbench\n\n"
                "The raw/ directory should contain:\n"
                "  - human_resp/ (survey waves with info.csv + *_data.json)"
            ) from e

    def _process_raw_data(self, raw_dir: Path) -> list[Question]:
        """Process raw OpinionsQA data into Question objects.

        Expected directory structure under raw_dir:
          human_resp/American_Trends_Panel_W{N}/
            info.csv          — question metadata (key, question, references, ...)
            NONE_data.json    — overall response counts (preferred)
            *_data.json       — demographic response counts (fallback)
        """
        human_resp_dir = self._find_subdir(raw_dir, "human_resp")

        if human_resp_dir is None:
            raise DatasetDownloadError(
                f"Expected human_resp/ directory in {raw_dir}.\n"
                "Download the OpinionsQA dataset and extract it there."
            )

        questions: list[Question] = []

        for wave in PEW_WAVES:
            wave_dir = human_resp_dir / f"American_Trends_Panel_W{wave}"
            if not wave_dir.is_dir():
                continue

            info_path = wave_dir / "info.csv"
            if not info_path.exists():
                continue

            # Load response distributions from JSON
            dist_by_key = self._load_wave_distributions(wave_dir)

            for row in self._read_csv(info_path):
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
                        survey=f"ATP W{wave}",
                    )
                )

        return questions

    @staticmethod
    def _load_wave_distributions(wave_dir: Path) -> dict[str, dict[str, float]]:
        """Load aggregated human response distributions for one survey wave.

        Prefers NONE_data.json (overall population). Falls back to summing
        sub-groups from the first available demographic *_data.json.
        Returns {question_key: {option: count}} (unnormalized — Question
        __post_init__ handles normalization).
        """
        # Prefer NONE_data.json; fall back to any *_data.json
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

    @staticmethod
    def _find_subdir(root: Path, name: str) -> Path | None:
        if (root / name).is_dir():
            return root / name
        for p in root.rglob(name):
            if p.is_dir():
                return p
        return None

    @staticmethod
    def _read_csv(path: Path) -> list[dict[str, str]]:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return list(reader)

    # The 8 universal demographic attributes in OpinionsQA
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

    def load_demographic_distributions(
        self,
        attribute: str,
    ) -> dict[str, dict[str, dict[str, float]]]:
        """Load per-group human distributions for a demographic attribute.

        Reads {attribute}_data.json from each survey wave directory and
        aggregates them into a single mapping.

        Args:
            attribute: Demographic attribute name (e.g., "AGE", "POLIDEOLOGY").
                Must be one of the 8 universal OpinionsQA attributes.

        Returns:
            {question_key: {group_name: {option: probability}}}
            Counts are normalized to probabilities per group.
        """
        raw_dir = self._data_dir / "raw"
        human_resp_dir = self._find_subdir(raw_dir, "human_resp")
        if human_resp_dir is None:
            return {}

        result: dict[str, dict[str, dict[str, float]]] = {}

        for wave in PEW_WAVES:
            wave_dir = human_resp_dir / f"American_Trends_Panel_W{wave}"
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
                    if sub_key in ("MC_options", "question_text"):
                        continue
                    if sub_key == "nan":
                        continue
                    if not isinstance(counts, dict):
                        continue

                    # Normalize counts to probabilities
                    total = sum(float(v) for v in counts.values())
                    if total <= 0:
                        continue
                    groups[sub_key] = {
                        opt: float(val) / total for opt, val in counts.items()
                    }

                if groups:
                    result[qkey] = groups

        return result


class DatasetDownloadError(Exception):
    """Raised when dataset download or setup fails."""
