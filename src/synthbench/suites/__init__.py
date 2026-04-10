"""Pinned question sets for reproducible benchmarking.

Suites define fixed sets of question keys that don't change between runs,
ensuring reproducibility regardless of dataset load order or --n parameter.

Available suites:
  - smoke: 28 questions for quick validation
  - core: 200 questions stratified by topic and entropy
  - full: all questions in the dataset

Topic suites (loaded via load_topic_suite):
  - political: ~80 questions on elections, party politics, guns, abortion
  - consumer: ~175 questions on technology, economy, health, work
  - neutral: ~429 questions that don't match political or consumer keywords
"""

from __future__ import annotations

import json
from pathlib import Path

SUITE_DIR = Path(__file__).parent

AVAILABLE_SUITES = ("smoke", "core", "full")

AVAILABLE_TOPICS = ("political", "consumer", "neutral")


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


def load_topic_suite(topic: str) -> list[str]:
    """Load a topic-based question set by name.

    Args:
        topic: Topic name ("political", "consumer", "neutral").

    Returns:
        List of question keys for the topic.

    Raises:
        ValueError: If topic name is unknown.
    """
    if topic not in AVAILABLE_TOPICS:
        raise ValueError(
            f"Unknown topic '{topic}'. Available: {list(AVAILABLE_TOPICS)}"
        )

    path = SUITE_DIR / f"{topic}.json"
    if not path.exists():
        raise FileNotFoundError(f"Topic suite file not found: {path}.")

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
