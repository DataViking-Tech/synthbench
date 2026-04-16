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
from synthbench.runner import (
    BenchmarkRunner,
    DemographicGroupResult,
    _aggregate_token_usage,
    _normalize_model_dist,
)


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

# SEX-specific distributions (distinct from AGE) for isolation testing
_SEX_DISTS = {
    "ABORTION_W82": {
        "Male": {
            "Legal in all cases": 0.28,
            "Legal in most cases": 0.32,
            "Illegal in most cases": 0.24,
            "Illegal in all cases": 0.16,
        },
        "Female": {
            "Legal in all cases": 0.38,
            "Legal in most cases": 0.34,
            "Illegal in most cases": 0.18,
            "Illegal in all cases": 0.10,
        },
    },
    "CLIMATE_W29": {
        "Male": {
            "A great deal": 0.42,
            "Some": 0.30,
            "Not too much": 0.16,
            "Not at all": 0.12,
        },
        "Female": {
            "A great deal": 0.55,
            "Some": 0.28,
            "Not too much": 0.11,
            "Not at all": 0.06,
        },
    },
}


class DemoAwareDataset(Dataset):
    """Dataset that provides demographic distributions for testing."""

    DEMOGRAPHIC_ATTRIBUTES = ["AGE", "SEX"]

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
        if attribute == "SEX":
            return _SEX_DISTS
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


@pytest.mark.asyncio
async def test_run_with_demographics_attribute_isolation(
    demo_dataset, persona_provider
):
    """Each demographic attribute produces its own groups — no cross-contamination."""
    runner = BenchmarkRunner(
        dataset=demo_dataset,
        provider=persona_provider,
        samples_per_question=10,
        concurrency=5,
    )
    result = await runner.run_with_demographics(demographics=["SEX"], n=2)

    # Should have SEX breakdown, NOT AGE
    assert "SEX" in result.demographic_breakdown
    assert "AGE" not in result.demographic_breakdown

    sex_groups = {gr.group for gr in result.demographic_breakdown["SEX"]}
    assert sex_groups == {"Male", "Female"}

    # Group score labels should use SEX prefix
    for key in result.group_scores:
        assert key.startswith("SEX:"), f"Expected SEX: prefix, got {key}"


@pytest.mark.asyncio
async def test_run_with_demographics_multi_attribute(demo_dataset, persona_provider):
    """Multiple attributes produce independent breakdowns."""
    runner = BenchmarkRunner(
        dataset=demo_dataset,
        provider=persona_provider,
        samples_per_question=10,
        concurrency=5,
    )
    result = await runner.run_with_demographics(demographics=["AGE", "SEX"], n=2)

    assert "AGE" in result.demographic_breakdown
    assert "SEX" in result.demographic_breakdown

    age_groups = {gr.group for gr in result.demographic_breakdown["AGE"]}
    sex_groups = {gr.group for gr in result.demographic_breakdown["SEX"]}
    assert age_groups == {"young", "old"}
    assert sex_groups == {"Male", "Female"}


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


class RefusingProvider(Provider):
    """Provider that refuses every ``refusal_every``-th sample (and picks the
    first option otherwise) — exercises the partial-refusal branch so the
    runner has to renormalize to hit sum=1 distributions."""

    def __init__(self, refusal_every: int = 3):
        self._counter = 0
        self._refusal_every = refusal_every

    @property
    def name(self) -> str:
        return "mock/refusing"

    async def respond(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        self._counter += 1
        if self._counter % self._refusal_every == 0:
            return Response(selected_option="", refusal=True)
        return Response(selected_option=options[0])


class AlwaysRefuseProvider(Provider):
    """Every sample refuses — exercises the uniform-fallback branch."""

    @property
    def name(self) -> str:
        return "mock/always-refuse"

    async def respond(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        return Response(selected_option="", refusal=True)


def test_normalize_model_dist_renormalizes_partial_mass():
    """A distribution whose mass sums to <1 is rescaled to sum to 1."""
    options = ["a", "b", "c"]
    # Simulate "1 valid pick out of 3 samples (1 refusal), others missed":
    # mass is 1/3 on 'a', 0 elsewhere, total mass 1/3.
    normalized = _normalize_model_dist({"a": 1 / 3, "b": 0.0, "c": 0.0}, options)
    assert abs(sum(normalized.values()) - 1.0) < 1e-9
    assert normalized["a"] == pytest.approx(1.0)
    assert normalized["b"] == 0.0 and normalized["c"] == 0.0


def test_normalize_model_dist_preserves_ratios():
    """Rescaling should preserve option-to-option proportions."""
    options = ["a", "b", "c"]
    normalized = _normalize_model_dist({"a": 0.2, "b": 0.4, "c": 0.2}, options)
    assert abs(sum(normalized.values()) - 1.0) < 1e-9
    # Ratios before: 1:2:1. After renormalization they must be preserved.
    assert normalized["a"] == pytest.approx(0.25)
    assert normalized["b"] == pytest.approx(0.5)
    assert normalized["c"] == pytest.approx(0.25)


def test_normalize_model_dist_uniform_fallback_on_zero_mass():
    """All-refusal / all-parse-failure case falls back to a uniform vector."""
    options = ["a", "b", "c", "d"]
    normalized = _normalize_model_dist(
        {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0}, options
    )
    assert abs(sum(normalized.values()) - 1.0) < 1e-9
    for v in normalized.values():
        assert v == pytest.approx(0.25)


def test_normalize_model_dist_empty_options():
    """Empty option list produces an empty distribution without crashing."""
    assert _normalize_model_dist({}, []) == {}


@pytest.mark.asyncio
async def test_runner_normalizes_distribution_on_partial_refusal(mock_dataset):
    """Runner output distributions sum to 1 even when some samples refused."""
    runner = BenchmarkRunner(
        dataset=mock_dataset,
        provider=RefusingProvider(refusal_every=3),
        samples_per_question=9,
        concurrency=5,
    )
    result = await runner.run(n=2)

    # Every per-question distribution must be a valid probability vector
    # — this is what the tier-1 DIST_SUM validator checks on serialized
    # leaderboard entries.
    for qr in result.questions:
        total = sum(qr.model_distribution.values())
        assert abs(total - 1.0) < 1e-6, (
            f"model_distribution does not sum to 1: {qr.model_distribution} "
            f"(sum={total})"
        )
        # refusal rate is still tracked separately
        assert qr.model_refusal_rate > 0


@pytest.mark.asyncio
async def test_runner_normalizes_distribution_on_all_refusal(mock_dataset):
    """Degenerate all-refusal runs produce a valid (uniform) probability vector."""
    runner = BenchmarkRunner(
        dataset=mock_dataset,
        provider=AlwaysRefuseProvider(),
        samples_per_question=5,
        concurrency=5,
    )
    result = await runner.run(n=2)

    for qr in result.questions:
        total = sum(qr.model_distribution.values())
        assert abs(total - 1.0) < 1e-6
        # Uniform fallback: all options equally weighted
        expected = 1.0 / len(qr.options)
        for v in qr.model_distribution.values():
            assert v == pytest.approx(expected)
        assert qr.model_refusal_rate == pytest.approx(1.0)


def test_subpop_attributes_match_raw_data():
    """SUBPOP_ATTRIBUTES must match what's actually in the raw dataset."""
    from synthbench.datasets.subpop import SUBPOP_ATTRIBUTES

    # These are the 8 attributes in the SubPOP raw data (verified against HuggingFace)
    expected = {
        "CREGION",
        "EDUCATION",
        "INCOME",
        "POLIDEOLOGY",
        "POLPARTY",
        "RACE",
        "RELIG",
        "SEX",
    }
    assert set(SUBPOP_ATTRIBUTES) == expected, (
        f"SUBPOP_ATTRIBUTES mismatch. Got {sorted(SUBPOP_ATTRIBUTES)}, "
        f"expected {sorted(expected)}"
    )


# --- Token usage aggregation ---


def _resp_with_usage(input_tokens: int | None, output_tokens: int | None) -> Response:
    if input_tokens is None and output_tokens is None:
        return Response(selected_option="A", metadata={"model": "x", "usage": None})
    return Response(
        selected_option="A",
        metadata={
            "model": "x",
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        },
    )


class TestAggregateTokenUsage:
    def test_all_have_usage_sums_correctly(self):
        responses = [
            _resp_with_usage(10, 2),
            _resp_with_usage(15, 3),
            _resp_with_usage(7, 1),
        ]
        agg = _aggregate_token_usage(responses)
        assert agg == {"input_tokens": 32, "output_tokens": 6, "call_count": 3}

    def test_some_have_usage_sums_only_those(self):
        responses = [
            _resp_with_usage(10, 2),
            _resp_with_usage(None, None),  # ollama-style: usage=None
            Response(selected_option="A"),  # no metadata at all
            _resp_with_usage(5, 1),
        ]
        agg = _aggregate_token_usage(responses)
        assert agg == {"input_tokens": 15, "output_tokens": 3, "call_count": 2}

    def test_none_have_usage_returns_none(self):
        responses = [
            _resp_with_usage(None, None),
            Response(selected_option="A"),
            Response(selected_option="B", metadata={"model": "x"}),
        ]
        assert _aggregate_token_usage(responses) is None

    def test_zero_usage_returns_zeros_not_none(self):
        """Provider explicitly reporting zero tokens should still register."""
        responses = [
            _resp_with_usage(0, 0),
            _resp_with_usage(0, 0),
        ]
        agg = _aggregate_token_usage(responses)
        assert agg == {"input_tokens": 0, "output_tokens": 0, "call_count": 2}

    def test_empty_responses_returns_none(self):
        assert _aggregate_token_usage([]) is None


# --- Reproducibility hashes (sb-okdx) ---


class _CustomTemplateProvider(Provider):
    """Provider whose prompt_template_source is distinct from MockProvider's."""

    @property
    def name(self) -> str:
        return "custom/v2"

    @property
    def prompt_template_source(self) -> str:
        return "SYSTEM: be terse\nUSER: {question}"

    async def respond(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        return Response(selected_option=options[0])


@pytest.mark.asyncio
async def test_runner_populates_reproducibility_hashes(mock_dataset, mock_provider):
    """BenchmarkResult.config must carry sha256-prefixed repro hashes."""
    runner = BenchmarkRunner(
        dataset=mock_dataset, provider=mock_provider, samples_per_question=2
    )
    result = await runner.run(n=1)

    mrh = result.config["model_revision_hash"]
    pth = result.config["prompt_template_hash"]
    assert mrh.startswith("sha256:") and len(mrh) == len("sha256:") + 64
    assert pth.startswith("sha256:") and len(pth) == len("sha256:") + 64


@pytest.mark.asyncio
async def test_reproducibility_hashes_change_with_provider(mock_dataset, mock_provider):
    """Different providers must produce different revision + template hashes."""
    runner_a = BenchmarkRunner(
        dataset=mock_dataset, provider=mock_provider, samples_per_question=2
    )
    runner_b = BenchmarkRunner(
        dataset=mock_dataset,
        provider=_CustomTemplateProvider(),
        samples_per_question=2,
    )
    a = (await runner_a.run(n=1)).config
    b = (await runner_b.run(n=1)).config

    assert a["model_revision_hash"] != b["model_revision_hash"]
    assert a["prompt_template_hash"] != b["prompt_template_hash"]


@pytest.mark.asyncio
async def test_reproducibility_hashes_pass_tier3_strict(mock_dataset, mock_provider):
    """Runner output must clear the Tier-3 REPRO_FIELD_EMPTY gate under --strict."""
    from synthbench import report
    from synthbench.validation import _validate_reproducibility_metadata

    runner = BenchmarkRunner(
        dataset=mock_dataset, provider=mock_provider, samples_per_question=2
    )
    result = await runner.run(n=1)
    payload = report.to_json(result)

    issues = _validate_reproducibility_metadata(payload)
    repro_codes = {i.code for i in issues}
    assert "REPRO_FIELD_EMPTY" not in repro_codes
    assert "REPRO_FIELD_MISSING" not in repro_codes
