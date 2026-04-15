"""SubPOP dataset loader.

Loads 3,362 survey questions with pre-computed response distributions
across 22 US subpopulations from the SubPOP dataset (ACL 2025).

Data source: https://huggingface.co/datasets/jjssuh/subpop
Paper: SubPOP: Subpopulation-Level Opinion Prediction

Requires: pip install datasets (HuggingFace datasets library)
The dataset is gated — you may need to accept terms at the HuggingFace page
and authenticate via `huggingface-cli login`.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from synthbench.datasets.base import Dataset, Question

# The 8 demographic attributes in SubPOP
SUBPOP_ATTRIBUTES = [
    "CREGION",
    "EDUCATION",
    "INCOME",
    "POLIDEOLOGY",
    "POLPARTY",
    "RACE",
    "RELIG",
    "SEX",
]


def _default_cache_dir() -> Path:
    return Path.home() / ".synthbench" / "data" / "subpop"


class SubPOPDataset(Dataset):
    """SubPOP: 3,362 questions across 22 US subpopulations."""

    # Dataset is gated on HuggingFace and published under CC-BY-NC-SA-4.0.
    # Non-commercial + share-alike restrictions tier this down to
    # aggregates_only per the conservative rubric.
    redistribution_policy = "aggregates_only"
    license_url = "https://huggingface.co/datasets/jjssuh/subpop"
    citation = "Suh et al., ACL 2025 — SubPOP: Subpopulation-Level Opinion Prediction"

    def __init__(self, data_dir: Path | str | None = None):
        self._data_dir = Path(data_dir) if data_dir else _default_cache_dir()

    @property
    def name(self) -> str:
        return "subpop"

    def info(self) -> dict:
        return {
            "name": "SubPOP",
            "source": "Suh et al., ACL 2025",
            "paper": "https://huggingface.co/datasets/jjssuh/subpop",
            "n_questions": 3362,
            "n_train": 3229,
            "n_eval": 133,
            "subpopulations": 22,
            "attributes": len(SUBPOP_ATTRIBUTES),
            "license": "CC-BY-NC-SA-4.0",
        }

    def load(self, n: int | None = None) -> list[Question]:
        """Load questions with overall (population-level) distributions.

        Aggregates per-subgroup distributions into a single population
        distribution per question by averaging across all groups.
        """
        cache_path = self._data_dir / "questions.json"

        if cache_path.exists():
            questions = self._load_cached(cache_path)
        else:
            questions = self._download_and_process()

        if n is not None:
            questions = questions[:n]
        return questions

    # ------------------------------------------------------------------ #
    # Demographic distributions (per-subgroup)
    # ------------------------------------------------------------------ #

    DEMOGRAPHIC_ATTRIBUTES = SUBPOP_ATTRIBUTES

    def load_demographic_distributions(
        self,
        attribute: str,
    ) -> dict[str, dict[str, dict[str, float]]]:
        """Load per-group distributions for a demographic attribute.

        Args:
            attribute: One of the 8 SubPOP attributes (e.g. "INCOME", "POLPARTY").

        Returns:
            {question_key: {group_name: {option: probability}}}
        """
        demo_cache = self._data_dir / f"demo_{attribute}.json"
        if demo_cache.exists():
            with open(demo_cache) as f:
                return json.load(f)

        # Build from raw data
        rows = self._load_raw_rows()
        result: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)

        for row in rows:
            if row["attribute"].upper() != attribute.upper():
                continue
            qkey = row["qkey"]
            group = row["group"]
            options = row["options"]
            responses = row["responses"]
            if len(options) != len(responses):
                continue
            dist = dict(zip(options, responses))
            result[qkey][group] = dist

        result = dict(result)
        self._save_demo_cache(attribute, result)
        return result

    # ------------------------------------------------------------------ #
    # Internal: download, process, cache
    # ------------------------------------------------------------------ #

    def _load_raw_rows(self) -> list[dict]:
        """Load raw SubPOP rows from cache or download."""
        raw_cache = self._data_dir / "raw_rows.json"
        if raw_cache.exists():
            with open(raw_cache) as f:
                return json.load(f)
        return self._download_raw()

    def _download_raw(self) -> list[dict]:
        """Download SubPOP from HuggingFace using the datasets library."""
        try:
            from datasets import load_dataset
        except ImportError:
            raise ImportError(
                "SubPOP requires the HuggingFace datasets library.\n"
                "Install it with: pip install datasets\n\n"
                "The dataset is gated — you may also need to:\n"
                "  1. Accept terms at https://huggingface.co/datasets/jjssuh/subpop\n"
                "  2. Authenticate: huggingface-cli login"
            )

        self._data_dir.mkdir(parents=True, exist_ok=True)

        all_rows: list[dict] = []
        ds = load_dataset("jjssuh/subpop")

        for split_name in ds:
            split = ds[split_name]
            for row in split:
                opts = list(row["options"])
                resp = list(row["responses"])
                refusal = row.get("refusal_rate", 0.0)

                # SubPOP stores refusal_rate separately; options includes
                # "Refused" but responses does not.  Append refusal to
                # align lengths, or trim "Refused" from options.
                if len(opts) == len(resp) + 1 and opts[-1].lower() in (
                    "refused",
                    "dk/refused",
                ):
                    resp.append(refusal)

                all_rows.append(
                    {
                        "qkey": row["qkey"],
                        "attribute": row["attribute"],
                        "group": row["group"],
                        "question": row["question"],
                        "options": opts,
                        "responses": resp,
                        "refusal_rate": refusal,
                        "split": split_name,
                    }
                )

        # Cache raw rows
        with open(self._data_dir / "raw_rows.json", "w") as f:
            json.dump(all_rows, f, indent=2)

        return all_rows

    def _download_and_process(self) -> list[Question]:
        """Download SubPOP and produce aggregated Question objects."""
        rows = self._load_raw_rows()
        questions = self._aggregate_questions(rows)
        self._save_cache(questions)
        return questions

    @staticmethod
    def _aggregate_questions(rows: list[dict]) -> list[Question]:
        """Aggregate per-subgroup rows into population-level Questions.

        Each question appears once per (attribute, group) pair. We average
        the response distributions across all groups to get a population-level
        distribution, then deduplicate by qkey.
        """
        # Collect all distributions per question
        q_dists: dict[str, list[list[float]]] = defaultdict(list)
        q_meta: dict[str, dict] = {}

        for row in rows:
            qkey = row["qkey"]
            if qkey not in q_meta:
                q_meta[qkey] = {
                    "question": row["question"],
                    "options": row["options"],
                    "attribute": row["attribute"],
                }
            q_dists[qkey].append(row["responses"])

        questions: list[Question] = []
        for qkey in sorted(q_meta):
            meta = q_meta[qkey]
            options = meta["options"]
            dists = q_dists[qkey]

            # Average across all subgroup distributions
            n_opts = len(options)
            if not dists or n_opts == 0:
                continue

            avg = [0.0] * n_opts
            for d in dists:
                if len(d) != n_opts:
                    continue
                for i in range(n_opts):
                    avg[i] += d[i]
            total = sum(avg)
            if total <= 0:
                continue
            avg = [v / total for v in avg]

            human_dist = dict(zip(options, avg))

            questions.append(
                Question(
                    key=qkey,
                    text=meta["question"],
                    options=options,
                    human_distribution=human_dist,
                    survey="SubPOP",
                )
            )

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
                survey=q.get("survey", "SubPOP"),
                topic=q.get("topic", ""),
            )
            for q in data["questions"]
        ]

    def _save_cache(self, questions: list[Question]) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "dataset": "subpop",
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
