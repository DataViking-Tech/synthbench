"""Shared test fixtures for SynthBench."""

from __future__ import annotations

import pytest

from synthbench.datasets.base import Question, Dataset
from synthbench.providers.base import PersonaSpec, Provider, Response


# --- Sample questions with realistic distributions ---

SAMPLE_QUESTIONS = [
    Question(
        key="ABORTION_W82",
        text="Do you think abortion should be legal in all or most cases, or illegal in all or most cases?",
        options=[
            "Legal in all cases",
            "Legal in most cases",
            "Illegal in most cases",
            "Illegal in all cases",
        ],
        human_distribution={
            "Legal in all cases": 0.27,
            "Legal in most cases": 0.33,
            "Illegal in most cases": 0.23,
            "Illegal in all cases": 0.17,
        },
        survey="ATP W82",
    ),
    Question(
        key="CLIMATE_W29",
        text="How much do you think human activity contributes to global climate change?",
        options=["A great deal", "Some", "Not too much", "Not at all"],
        human_distribution={
            "A great deal": 0.49,
            "Some": 0.30,
            "Not too much": 0.12,
            "Not at all": 0.09,
        },
        survey="ATP W29",
    ),
    Question(
        key="ECON_W36",
        text="How would you rate economic conditions in this country today?",
        options=["Excellent", "Good", "Only fair", "Poor"],
        human_distribution={
            "Excellent": 0.07,
            "Good": 0.34,
            "Only fair": 0.40,
            "Poor": 0.19,
        },
        survey="ATP W36",
    ),
    Question(
        key="TRUST_GOV_W27",
        text="How much of the time do you think you can trust the government in Washington to do what is right?",
        options=[
            "Just about always",
            "Most of the time",
            "Only some of the time",
            "Never",
        ],
        human_distribution={
            "Just about always": 0.03,
            "Most of the time": 0.14,
            "Only some of the time": 0.60,
            "Never": 0.23,
        },
        survey="ATP W27",
    ),
    Question(
        key="GUNS_W26",
        text="What do you think is more important: protecting the right of Americans to own guns, or controlling gun ownership?",
        options=["Protecting gun rights", "Controlling gun ownership"],
        human_distribution={
            "Protecting gun rights": 0.47,
            "Controlling gun ownership": 0.53,
        },
        survey="ATP W26",
    ),
]


class MockDataset(Dataset):
    """In-memory dataset for testing."""

    @property
    def name(self) -> str:
        return "mock"

    def load(self, n: int | None = None) -> list[Question]:
        qs = list(SAMPLE_QUESTIONS)
        if n is not None:
            qs = qs[:n]
        return qs

    def info(self) -> dict:
        return {"name": "mock", "n_questions": len(SAMPLE_QUESTIONS)}


class MockProvider(Provider):
    """Deterministic provider that always picks the most popular option."""

    @property
    def name(self) -> str:
        return "mock/deterministic"

    async def respond(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        # Always return the first option (simulates a biased model)
        return Response(selected_option=options[0])


class RandomProvider(Provider):
    """Provider that picks options uniformly at random."""

    def __init__(self):
        import random

        self._rng = random.Random(42)

    @property
    def name(self) -> str:
        return "mock/random"

    async def respond(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        return Response(selected_option=self._rng.choice(options))


@pytest.fixture
def sample_questions():
    return list(SAMPLE_QUESTIONS)


@pytest.fixture
def mock_dataset():
    return MockDataset()


@pytest.fixture
def mock_provider():
    return MockProvider()


@pytest.fixture
def random_provider():
    return RandomProvider()
