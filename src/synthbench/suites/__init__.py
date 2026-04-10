"""Pinned question sets for reproducible benchmarking.

Suites define fixed sets of question keys that don't change between runs,
ensuring reproducibility regardless of dataset load order or --n parameter.

Available suites:
  - smoke: 28 questions for quick validation
  - core: 200 questions stratified by topic and entropy
  - full: all questions in the dataset
"""

from __future__ import annotations

import json
from pathlib import Path

SUITE_DIR = Path(__file__).parent

AVAILABLE_SUITES = ("smoke", "core", "full")


def load_suite(name: str) -> list[str] | None:
    """Load a pinned question set by name.

    Args:
        name: Suite name ("smoke", "core", "full").

    Returns:
        List of question keys, or None for "full" (meaning use all questions).

    Raises:
        ValueError: If suite name is unknown.
    """
    if name not in AVAILABLE_SUITES:
        raise ValueError(f"Unknown suite '{name}'. Available: {list(AVAILABLE_SUITES)}")

    if name == "full":
        return None  # Signal to use all questions

    path = SUITE_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Suite file not found: {path}. "
            f"Run 'synthbench generate-suites' to create pinned question sets."
        )

    with open(path) as f:
        data = json.load(f)

    return data["keys"]


def filter_questions_by_suite(questions: list, suite_keys: list[str]) -> list:
    """Filter and order questions according to a suite's key list.

    Questions are returned in suite key order. Keys not found in the dataset
    are silently skipped (version mismatch tolerance).
    """
    key_to_q = {q.key: q for q in questions}
    return [key_to_q[k] for k in suite_keys if k in key_to_q]
