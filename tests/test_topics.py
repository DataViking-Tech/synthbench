"""Tests for topic-based question categorization."""

from __future__ import annotations

import json

import pytest

from synthbench.topics import (
    categorize_question,
    POLITICAL_KEYS,
    CONSUMER_KEYS,
)
from synthbench.suites import (
    load_topic_suite,
    AVAILABLE_TOPICS,
    SUITE_DIR,
)


class TestCategorizeQuestion:
    def test_political_question(self):
        assert (
            categorize_question("Do you support the Republican party?") == "political"
        )

    def test_consumer_question(self):
        assert categorize_question("How often do you use the internet?") == "consumer"

    def test_neutral_question(self):
        assert (
            categorize_question("How important is religion in your life?") == "neutral"
        )

    def test_case_insensitive(self):
        assert categorize_question("WHAT IS YOUR VIEW ON ABORTION?") == "political"
        assert categorize_question("DO YOU USE TECHNOLOGY DAILY?") == "consumer"

    def test_both_matches_returns_neutral(self):
        # A question matching both political and consumer keywords -> neutral
        assert (
            categorize_question(
                "How does government technology policy affect the economy?"
            )
            == "neutral"
        )

    def test_gun_is_political(self):
        assert categorize_question("Do you own a gun?") == "political"

    def test_health_is_consumer(self):
        assert categorize_question("How would you rate your health?") == "consumer"

    def test_election_is_political(self):
        assert categorize_question("Did you vote in the last election?") == "political"

    def test_no_keywords_is_neutral(self):
        assert (
            categorize_question("What do you think about life in general?") == "neutral"
        )

    def test_empty_string_is_neutral(self):
        assert categorize_question("") == "neutral"


class TestKeywordSets:
    def test_political_keys_are_frozen(self):
        assert isinstance(POLITICAL_KEYS, frozenset)

    def test_consumer_keys_are_frozen(self):
        assert isinstance(CONSUMER_KEYS, frozenset)

    def test_no_overlap_between_single_word_keys(self):
        # Single-word keys shouldn't overlap
        single_political = {k for k in POLITICAL_KEYS if " " not in k}
        single_consumer = {k for k in CONSUMER_KEYS if " " not in k}
        assert not single_political & single_consumer


class TestTopicSuites:
    def test_available_topics_constant(self):
        assert "political" in AVAILABLE_TOPICS
        assert "consumer" in AVAILABLE_TOPICS
        assert "neutral" in AVAILABLE_TOPICS

    def test_political_loads(self):
        keys = load_topic_suite("political")
        assert len(keys) > 0
        assert all(isinstance(k, str) for k in keys)

    def test_consumer_loads(self):
        keys = load_topic_suite("consumer")
        assert len(keys) > 0
        assert all(isinstance(k, str) for k in keys)

    def test_neutral_loads(self):
        keys = load_topic_suite("neutral")
        assert len(keys) > 0
        assert all(isinstance(k, str) for k in keys)

    def test_unknown_topic_raises(self):
        with pytest.raises(ValueError, match="Unknown topic"):
            load_topic_suite("nonexistent")

    def test_topic_json_files_valid(self):
        for topic in AVAILABLE_TOPICS:
            path = SUITE_DIR / f"{topic}.json"
            assert path.exists(), f"Missing topic suite file: {path}"
            with open(path) as f:
                data = json.load(f)
            assert "keys" in data
            assert "suite" in data
            assert data["suite"] == topic
            assert len(data["keys"]) == data["n_keys"]

    def test_no_duplicate_keys_in_topics(self):
        for topic in AVAILABLE_TOPICS:
            keys = load_topic_suite(topic)
            assert len(keys) == len(set(keys)), f"Duplicate keys in {topic}"

    def test_topics_are_disjoint(self):
        political = set(load_topic_suite("political"))
        consumer = set(load_topic_suite("consumer"))
        neutral = set(load_topic_suite("neutral"))
        assert not political & consumer, "political and consumer overlap"
        assert not political & neutral, "political and neutral overlap"
        assert not consumer & neutral, "consumer and neutral overlap"

    def test_topics_cover_all_questions(self):
        """All questions should be in exactly one topic."""
        political = set(load_topic_suite("political"))
        consumer = set(load_topic_suite("consumer"))
        neutral = set(load_topic_suite("neutral"))
        total = len(political) + len(consumer) + len(neutral)
        union = political | consumer | neutral
        assert len(union) == total  # No overlaps
