"""Tests for topic-based question categorization."""

from __future__ import annotations

import json

import pytest

from synthbench.topics import (
    categorize_question,
    TAXONOMY,
    CATEGORIES,
    FALLBACK_CATEGORY,
)
from synthbench.suites import (
    load_topic_suite,
    AVAILABLE_TOPICS,
    SUITE_DIR,
)


class TestCategorizeQuestion:
    def test_political_question(self):
        assert (
            categorize_question("Do you support the Republican party?")
            == "Politics & Governance"
        )

    def test_technology_question(self):
        assert (
            categorize_question("How often do you use the internet?")
            == "Technology & Digital Life"
        )

    def test_religion_question(self):
        assert (
            categorize_question("How important is religion in your life?")
            == "Social Values & Religion"
        )

    def test_case_insensitive(self):
        assert (
            categorize_question("WHAT IS YOUR VIEW ON ABORTION?")
            == "Social Values & Religion"
        )
        assert (
            categorize_question("DO YOU USE TECHNOLOGY DAILY?")
            == "Technology & Digital Life"
        )

    def test_first_match_wins(self):
        # "vote" matches Politics & Governance first
        assert (
            categorize_question("Did you vote in the last election?")
            == "Politics & Governance"
        )

    def test_gun_is_social_values(self):
        assert categorize_question("Do you own a gun?") == "Social Values & Religion"

    def test_health_question(self):
        assert (
            categorize_question("How would you rate your health?") == "Health & Science"
        )

    def test_election_is_politics(self):
        assert (
            categorize_question("Did you vote in the last election?")
            == "Politics & Governance"
        )

    def test_no_keywords_is_general(self):
        assert (
            categorize_question("What do you think about the situation?")
            == "General Attitudes"
        )

    def test_empty_string_is_general(self):
        assert categorize_question("") == "General Attitudes"

    def test_international_relations(self):
        assert (
            categorize_question("What is your view on relations with China?")
            == "International Relations & Security"
        )

    def test_economy(self):
        assert (
            categorize_question("How do you feel about the economy?")
            == "Economy & Work"
        )

    def test_trust(self):
        assert (
            categorize_question("Do you approve of the way things are going?")
            == "Trust & Wellbeing"
        )

    def test_identity(self):
        assert (
            categorize_question("Is there racial bias in hiring?")
            == "Identity & Demographics"
        )


class TestTaxonomyStructure:
    def test_taxonomy_has_nine_categories(self):
        assert len(TAXONOMY) == 9

    def test_categories_has_ten_entries(self):
        assert len(CATEGORIES) == 10
        assert "General Attitudes" in CATEGORIES

    def test_fallback_is_general_attitudes(self):
        assert FALLBACK_CATEGORY == "General Attitudes"

    def test_all_keywords_are_strings(self):
        for category, keywords in TAXONOMY.items():
            for kw in keywords:
                assert isinstance(kw, str), f"Non-string keyword in {category}: {kw}"

    def test_all_keywords_are_lowercase(self):
        for category, keywords in TAXONOMY.items():
            for kw in keywords:
                assert kw == kw.lower(), f"Non-lowercase keyword in {category}: {kw}"


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
