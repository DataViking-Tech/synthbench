"""GlobalOpinionQA dataset loader.

Loads 2,556 survey questions (2,203 Pew Global Attitudes + 353 World Values
Survey) across 138 countries from the Anthropic/llm_global_opinions HuggingFace
dataset.

Source: https://huggingface.co/datasets/Anthropic/llm_global_opinions
License: CC-BY-NC-SA-4.0
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from synthbench.datasets.base import Dataset, Question


def _default_cache_dir() -> Path:
    return Path.home() / ".synthbench" / "data" / "globalopinionqa"


def _question_key(text: str, index: int) -> str:
    """Generate a stable key from question text."""
    h = hashlib.sha256(text.encode()).hexdigest()[:8]
    return f"GOQA_{index}_{h}"


def _normalize_options(options: list) -> list[str]:
    """Coerce option values to strings.

    Upstream Likert-scale questions store options as floats (e.g. ``[0.0, 1.0,
    ..., 10.0]``). Downstream consumers (report/publish serializers, the Astro
    run-detail page) assume option labels are strings, so normalize at the
    dataset boundary.
    """
    return [str(o) for o in options]


def _aggregate_distributions(
    selections: dict[str, list[float]],
    options: list[str],
    country: str | None = None,
) -> dict[str, float]:
    """Build a probability distribution from the selections dict.

    If *country* is given, use that country's distribution as ground truth.
    Otherwise, average across all countries.
    """
    if country is not None:
        probs = selections.get(country)
        if probs is None:
            raise ValueError(
                f"Country '{country}' not found in selections. "
                f"Available: {sorted(selections)[:10]}... ({len(selections)} total)"
            )
        dist = {opt: float(p) for opt, p in zip(options, probs)}
    else:
        # Average across all countries
        n_countries = len(selections)
        if n_countries == 0:
            return {}
        sums = [0.0] * len(options)
        for probs in selections.values():
            for i, p in enumerate(probs):
                sums[i] += float(p)
        dist = {opt: s / n_countries for opt, s in zip(options, sums)}

    return dist


class GlobalOpinionQADataset(Dataset):
    """GlobalOpinionQA: 2,556 questions across 138 countries."""

    # Upstream license CC-BY-NC-SA-4.0 carries non-commercial + share-alike
    # restrictions. Per the conservative rubric we withhold per-question
    # distributions; aggregate metrics remain public.
    redistribution_policy = "aggregates_only"
    license_url = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
    citation = "Durmus et al. 2023, Anthropic — llm_global_opinions"

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
            return f"globalopinionqa ({self._country})"
        return "globalopinionqa"

    def info(self) -> dict:
        return {
            "name": "GlobalOpinionQA",
            "source": "Anthropic/llm_global_opinions (HuggingFace)",
            "license": "CC-BY-NC-SA-4.0",
            "n_questions": 2556,
            "n_countries": 138,
            "country_filter": self._country,
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

        questions = []
        for q in data["questions"]:
            options = _normalize_options(q["options"])
            dist = _aggregate_distributions(
                q["selections"],
                options,
                country=self._country,
            )
            if not dist:
                continue
            questions.append(
                Question(
                    key=q["key"],
                    text=q["text"],
                    options=options,
                    human_distribution=dist,
                    survey=q.get("survey", ""),
                )
            )
        return questions

    def _save_cache(self, raw_rows: list[dict]) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "dataset": "globalopinionqa",
            "version": "1.0",
            "n_questions": len(raw_rows),
            "questions": raw_rows,
        }
        cache_path = self._data_dir / "questions.json"
        with open(cache_path, "w") as f:
            json.dump(data, f, indent=2)

    def _download_and_process(self) -> list[Question]:
        try:
            from datasets import load_dataset
        except ImportError:
            raise ImportError(
                "The 'datasets' package is required for GlobalOpinionQA.\n"
                "Install it with: pip install 'synthbench[hf]'\n"
                "  or: pip install datasets"
            )

        ds = load_dataset(
            "Anthropic/llm_global_opinions",
            cache_dir=str(self._data_dir / "hf_cache"),
        )

        # The dataset has a single split (typically "train")
        split = ds["train"] if "train" in ds else ds[list(ds.keys())[0]]

        raw_rows: list[dict] = []
        questions: list[Question] = []

        for i, row in enumerate(split):
            text = row["question"]
            if not text:
                continue
            options = row["options"]
            selections = row["selections"]

            # HuggingFace returns these as strings — parse them
            if isinstance(options, str):
                import ast

                try:
                    options = ast.literal_eval(options)
                except (ValueError, SyntaxError):
                    continue
            options = _normalize_options(options)
            if isinstance(selections, str):
                import ast
                import re

                # selections is repr() of defaultdict — extract the dict portion
                m = re.search(r"\{.*\}", selections, re.DOTALL)
                if m:
                    try:
                        selections = ast.literal_eval(m.group(0))
                    except (ValueError, SyntaxError):
                        continue
                else:
                    continue

            key = _question_key(text, i)
            survey = ""
            if "source" in row:
                survey = row["source"]

            raw_rows.append(
                {
                    "key": key,
                    "text": text,
                    "options": options,
                    "selections": selections,
                    "survey": survey,
                }
            )

            dist = _aggregate_distributions(selections, options, country=self._country)
            if not dist:
                continue

            questions.append(
                Question(
                    key=key,
                    text=text,
                    options=options,
                    human_distribution=dist,
                    survey=survey,
                )
            )

        self._save_cache(raw_rows)
        return questions

    def available_countries(self) -> list[str]:
        """Return sorted list of available country names from the cached data."""
        cache_path = self._data_dir / "questions.json"
        if not cache_path.exists():
            return []

        with open(cache_path) as f:
            data = json.load(f)

        countries: set[str] = set()
        for q in data["questions"]:
            countries.update(q.get("selections", {}).keys())
        return sorted(countries)
