"""Topic-based question categorization for domain-specific benchmarking.

Categorizes OpinionsQA questions into:
  - political: elections, party politics, guns, abortion, immigration
  - consumer: technology, economy, health, work, internet, science
  - neutral: everything else (religion, institutions, demographics, society)
"""

from __future__ import annotations

POLITICAL_KEYS: frozenset[str] = frozenset(
    {
        "biden",
        "trump",
        "republican",
        "democrat",
        "party",
        "liberal",
        "conservative",
        "congress",
        "election",
        "vote",
        "political",
        "government",
        "abortion",
        "gun",
        "immigration",
    }
)

CONSUMER_KEYS: frozenset[str] = frozenset(
    {
        "technology",
        "internet",
        "social media",
        "online",
        "device",
        "app",
        "phone",
        "computer",
        "science",
        "work",
        "job",
        "financial",
        "economy",
        "health",
        "food",
        "environment",
    }
)

# Multi-word keys that need phrase matching
_POLITICAL_PHRASES: frozenset[str] = frozenset()
_CONSUMER_PHRASES: frozenset[str] = frozenset({"social media"})


def categorize_question(text: str) -> str:
    """Categorize a question as 'political', 'consumer', or 'neutral'.

    Uses case-insensitive keyword matching on the question text.
    If a question matches both categories, it is classified as 'neutral'.
    If it matches neither, it is also 'neutral'.
    """
    text_lower = text.lower()

    political_match = any(kw in text_lower for kw in POLITICAL_KEYS)
    consumer_match = any(kw in text_lower for kw in CONSUMER_KEYS)

    if political_match and consumer_match:
        return "neutral"
    if political_match:
        return "political"
    if consumer_match:
        return "consumer"
    return "neutral"
