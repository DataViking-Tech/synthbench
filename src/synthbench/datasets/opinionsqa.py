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
                "  - model_input/ (survey questions)\n"
                "  - human_resp/ (response distributions)"
            ) from e

    def _process_raw_data(self, raw_dir: Path) -> list[Question]:
        """Process raw OpinionsQA CSVs into Question objects.

        Expected directory structure under raw_dir:
          model_input/  or  data/model_input/
          human_resp/   or  data/human_resp/
        """
        # Find the data directories (may be nested)
        model_input_dir = self._find_subdir(raw_dir, "model_input")
        human_resp_dir = self._find_subdir(raw_dir, "human_resp")

        if model_input_dir is None or human_resp_dir is None:
            raise DatasetDownloadError(
                f"Expected model_input/ and human_resp/ directories in {raw_dir}.\n"
                "Download the OpinionsQA dataset from CodaLab and extract it there."
            )

        # Load question metadata
        questions_by_key: dict[str, Question] = {}

        # Process each survey wave
        for wave in PEW_WAVES:
            info_path = model_input_dir / f"American_Trends_Panel_W{wave}" / "info.csv"
            if not info_path.exists():
                # Try alternate naming
                for p in model_input_dir.rglob(f"*W{wave}*info*csv"):
                    info_path = p
                    break
                else:
                    continue

            survey_dir = info_path.parent
            meta_path = survey_dir / "metadata.csv"

            # Load info.csv: key, option_ordinal, references, survey
            info_rows = self._read_csv(info_path)

            # Load metadata for answer text if available
            meta_lookup: dict[str, list[str]] = {}
            if meta_path.exists():
                for row in self._read_csv(meta_path):
                    key = row.get("key", row.get("qkey", ""))
                    options_raw = row.get("options", "")
                    try:
                        opts = literal_eval(options_raw) if options_raw else []
                    except (ValueError, SyntaxError):
                        opts = [o.strip() for o in options_raw.split(",")]
                    meta_lookup[key] = opts

            for row in info_rows:
                qkey = row.get("key", row.get("qkey", ""))
                if not qkey:
                    continue

                # Parse references (answer options)
                refs_raw = row.get("references", "")
                try:
                    refs = literal_eval(refs_raw) if refs_raw else []
                except (ValueError, SyntaxError):
                    refs = [r.strip() for r in refs_raw.split(",")]

                if not refs:
                    refs = meta_lookup.get(qkey, [])

                if not refs:
                    continue

                # Question text: from metadata or reconstruct from key
                question_text = row.get("question", row.get("text", qkey))

                questions_by_key[qkey] = Question(
                    key=qkey,
                    text=question_text,
                    options=refs,
                    human_distribution={r: 0.0 for r in refs},
                    survey=f"ATP W{wave}",
                )

        # Load human response distributions
        self._load_human_distributions(human_resp_dir, questions_by_key)

        questions = list(questions_by_key.values())
        # Filter out questions without valid distributions
        questions = [q for q in questions if any(v > 0 for v in q.human_distribution.values())]

        return questions

    def _load_human_distributions(
        self,
        human_resp_dir: Path,
        questions: dict[str, Question],
    ) -> None:
        """Load human response distributions from raw data.

        Looks for CSV files with per-question response counts/proportions
        and computes the 'Overall' population distribution.
        """
        # Try to find processed distribution files
        for csv_path in human_resp_dir.rglob("*.csv"):
            for row in self._read_csv(csv_path):
                qkey = row.get("key", row.get("qkey", ""))
                if qkey not in questions:
                    continue

                # Check if this is an 'Overall' demographic row
                attr = row.get("attribute", row.get("demographic", "Overall"))
                if attr != "Overall":
                    continue

                # Try to get distribution from D_H column
                dist_raw = row.get("D_H", "")
                if dist_raw:
                    try:
                        dist_vals = literal_eval(dist_raw)
                        q = questions[qkey]
                        if len(dist_vals) == len(q.options):
                            q.human_distribution = {
                                opt: float(val)
                                for opt, val in zip(q.options, dist_vals)
                            }
                            continue
                    except (ValueError, SyntaxError):
                        pass

                # Try column-per-option format
                q = questions[qkey]
                dist = {}
                for opt in q.options:
                    val = row.get(opt, "")
                    if val:
                        try:
                            dist[opt] = float(val)
                        except ValueError:
                            pass
                if dist:
                    q.human_distribution = dist

        # Try numpy files as fallback
        for npy_path in human_resp_dir.rglob("*.npy"):
            try:
                import numpy as np
                data = np.load(npy_path, allow_pickle=True).item()
                if isinstance(data, dict):
                    for qkey, dist_data in data.items():
                        if qkey in questions and isinstance(dist_data, dict):
                            q = questions[qkey]
                            if "Overall" in dist_data:
                                overall = dist_data["Overall"]
                                if isinstance(overall, (list, tuple)) and len(overall) == len(q.options):
                                    q.human_distribution = {
                                        opt: float(val)
                                        for opt, val in zip(q.options, overall)
                                    }
            except Exception:
                continue

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


class DatasetDownloadError(Exception):
    """Raised when dataset download or setup fails."""
