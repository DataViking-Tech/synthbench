"""Tests for the benchmark runner."""

from __future__ import annotations

import pytest

from synthbench.datasets.base import Dataset, Question
from synthbench.providers.base import (
    PersonaSpec,
    Provider,
    Response,
    build_persona_system_prompt,
)
from synthbench.runner import BenchmarkRunner, DemographicGroupResult


@pytest.mark.asyncio
async def test_runner_with_mock_provider(mock_dataset, mock_provider):
    """End-to-end: runner produces results with deterministic mock."""
    runner = BenchmarkRunner(
        dataset=mock_dataset,
        provider=mock_provider,
        samples_per_question=10,
        concurrency=5,
    )
    result = await runner.run(n=3)

    assert result.dataset_name == "mock"
    assert result.provider_name == "mock/deterministic"
    assert len(result.questions) == 3
    assert result.elapsed_seconds > 0

    for qr in result.questions:
        assert 0.0 <= qr.jsd <= 1.0
        assert -1.0 <= qr.kendall_tau <= 1.0
        assert 0.0 <= qr.parity <= 1.0
        assert qr.n_samples == 10
        # Deterministic provider always picks first option
        assert qr.model_distribution[qr.options[0]] == 1.0

    assert 0.0 <= result.composite_parity <= 1.0


@pytest.mark.asyncio
async def test_runner_with_random_provider(mock_dataset, random_provider):
    """Random provider produces varied distributions."""
    runner = BenchmarkRunner(
        dataset=mock_dataset,
        provider=random_provider,
        samples_per_question=100,
        concurrency=5,
    )
    result = await runner.run(n=2)

    assert len(result.questions) == 2
    for qr in result.questions:
        # Random should spread across options (not all on one)
        nonzero = sum(1 for v in qr.model_distribution.values() if v > 0)
        assert nonzero >= 2


@pytest.mark.asyncio
async def test_runner_n_limits_questions(mock_dataset, mock_provider):
    """--n flag limits the number of questions evaluated."""
    runner = BenchmarkRunner(
        dataset=mock_dataset,
        provider=mock_provider,
        samples_per_question=5,
    )
    result = await runner.run(n=1)
    assert len(result.questions) == 1


@pytest.mark.asyncio
async def test_runner_progress_callback(mock_dataset, mock_provider):
    """Progress callback is called for each question."""
    calls = []

    def cb(done, total, qr):
        calls.append((done, total))

    runner = BenchmarkRunner(
        dataset=mock_dataset,
        provider=mock_provider,
        samples_per_question=5,
    )
    await runner.run(n=3, progress_callback=cb)

    assert len(calls) == 3
    assert calls[-1] == (3, 3)


# --- Demographic evaluation tests ---

# Sample demographic distributions for testing
_DEMO_DISTS = {
    "ABORTION_W82": {
        "young": {
            "Legal in all cases": 0.35,
            "Legal in most cases": 0.35,
            "Illegal in most cases": 0.20,
            "Illegal in all cases": 0.10,
        },
        "old": {
            "Legal in all cases": 0.20,
            "Legal in most cases": 0.30,
            "Illegal in most cases": 0.28,
            "Illegal in all cases": 0.22,
        },
    },
    "CLIMATE_W29": {
        "young": {
            "A great deal": 0.60,
            "Some": 0.25,
            "Not too much": 0.10,
            "Not at all": 0.05,
        },
        "old": {
            "A great deal": 0.35,
            "Some": 0.35,
            "Not too much": 0.18,
            "Not at all": 0.12,
        },
    },
}


class DemoAwareDataset(Dataset):
    """Dataset that provides demographic distributions for testing."""

    def __init__(self, questions: list[Question]):
        self._questions = questions

    @property
    def name(self) -> str:
        return "demo-mock"

    def load(self, n: int | None = None) -> list[Question]:
        qs = list(self._questions)
        if n is not None:
            qs = qs[:n]
        return qs

    def info(self) -> dict:
        return {"name": "demo-mock", "n_questions": len(self._questions)}

    def load_demographic_distributions(
        self, attribute: str
    ) -> dict[str, dict[str, dict[str, float]]]:
        if attribute == "AGE":
            return _DEMO_DISTS
        return {}


class PersonaAwareProvider(Provider):
    """Provider that shifts response based on persona."""

    def __init__(self):
        import random

        self._rng = random.Random(99)

    @property
    def name(self) -> str:
        return "mock/persona-aware"

    async def respond(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        if persona and persona.group == "young":
            # Young persona biases toward first option
            return Response(selected_option=options[0])
        elif persona and persona.group == "old":
            # Old persona biases toward last option
            return Response(selected_option=options[-1])
        # Unconditioned: pick uniformly
        return Response(selected_option=self._rng.choice(options))


@pytest.fixture
def demo_dataset(sample_questions):
    return DemoAwareDataset(sample_questions)


@pytest.fixture
def persona_provider():
    return PersonaAwareProvider()


@pytest.mark.asyncio
async def test_run_with_demographics(demo_dataset, persona_provider):
    """Demographic runner produces group scores and P_sub/P_cond."""
    runner = BenchmarkRunner(
        dataset=demo_dataset,
        provider=persona_provider,
        samples_per_question=20,
        concurrency=5,
    )
    result = await runner.run_with_demographics(demographics=["AGE"], n=2)

    # Should have group scores
    assert len(result.group_scores) > 0

    # Should have demographic breakdown for AGE
    assert "AGE" in result.demographic_breakdown
    age_results = result.demographic_breakdown["AGE"]
    assert len(age_results) == 2  # young, old

    for gr in age_results:
        assert isinstance(gr, DemographicGroupResult)
        assert gr.attribute == "AGE"
        assert gr.group in ("young", "old")
        assert 0.0 <= gr.p_dist <= 1.0
        assert 0.0 <= gr.p_cond <= 1.0
        assert gr.n_questions == 2

    # P_sub should be computable now
    assert result.p_sub is not None
    assert 0.0 <= result.p_sub <= 1.0

    # P_cond should be computable now
    assert result.p_cond is not None
    assert result.p_cond >= 0.0

    # SPS should now include all 5 metrics
    components = result.sps_components
    assert "p_sub" in components
    assert "p_cond" in components
    assert len(components) == 5


@pytest.mark.asyncio
async def test_run_with_demographics_unknown_attr(demo_dataset, persona_provider):
    """Unknown demographic attribute produces no breakdown."""
    runner = BenchmarkRunner(
        dataset=demo_dataset,
        provider=persona_provider,
        samples_per_question=10,
        concurrency=5,
    )
    result = await runner.run_with_demographics(demographics=["UNKNOWN"], n=2)

    assert result.demographic_breakdown == {}
    assert result.p_sub is None
    assert result.p_cond is None


@pytest.mark.asyncio
async def test_run_with_demographics_baseline_still_works(
    demo_dataset, persona_provider
):
    """Demographic run still produces valid baseline metrics."""
    runner = BenchmarkRunner(
        dataset=demo_dataset,
        provider=persona_provider,
        samples_per_question=20,
        concurrency=5,
    )
    result = await runner.run_with_demographics(demographics=["AGE"], n=2)

    assert len(result.questions) == 2
    assert result.p_dist > 0
    assert result.p_rank > 0
    assert result.sps > 0


def test_build_persona_system_prompt_none():
    """No persona returns base system prompt unchanged."""
    base = "You are answering a survey."
    assert build_persona_system_prompt(base, None) == base


def test_build_persona_system_prompt_with_persona():
    """Persona produces demographics-aware system prompt."""
    base = "You are answering a survey."
    persona = PersonaSpec(demographics={"AGE": "18-29"}, attribute="AGE", group="18-29")
    result = build_persona_system_prompt(base, persona)
    assert "AGE: 18-29" in result
    assert "survey respondent" in result.lower()


def test_build_persona_system_prompt_multi_demographics():
    """Multiple demographics appear in the prompt."""
    base = "You are answering a survey."
    persona = PersonaSpec(
        demographics={"AGE": "18-29", "SEX": "Female"},
        attribute="AGE",
        group="18-29",
    )
    result = build_persona_system_prompt(base, persona)
    assert "AGE: 18-29" in result
    assert "SEX: Female" in result
