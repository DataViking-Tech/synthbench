"""Tests for the temporal holdout validation module."""

from __future__ import annotations

import pytest

from synthbench.holdout import (
    HoldoutPrompt,
    HoldoutResult,
    HoldoutSuiteResult,
    VALID_OUTCOMES,
    load_holdout_suite,
    parse_verdict,
    evaluate_prompt,
    format_holdout_report,
)
from synthbench.providers.base import Provider, Response


class TestHoldoutPrompt:
    def test_valid_outcomes(self):
        for outcome in VALID_OUTCOMES:
            p = HoldoutPrompt(
                id="test",
                sector="tech",
                launch_quarter="2026-Q1",
                concept="A product",
                ground_truth=outcome,
                reception_summary="",
            )
            assert p.ground_truth == outcome

    def test_invalid_outcome_raises(self):
        with pytest.raises(ValueError, match="Invalid ground_truth"):
            HoldoutPrompt(
                id="test",
                sector="tech",
                launch_quarter="2026-Q1",
                concept="A product",
                ground_truth="unknown",
                reception_summary="",
            )


class TestParseVerdict:
    def test_exact_match(self):
        assert parse_verdict("SUCCESS") == "success"
        assert parse_verdict("MIXED") == "mixed"
        assert parse_verdict("FAILURE") == "failure"

    def test_lowercase(self):
        assert parse_verdict("success") == "success"
        assert parse_verdict("mixed") == "mixed"
        assert parse_verdict("failure") == "failure"

    def test_with_whitespace(self):
        assert parse_verdict("  SUCCESS  ") == "success"
        assert parse_verdict("\nMIXED\n") == "mixed"

    def test_embedded_in_text(self):
        assert parse_verdict("I think this will be a SUCCESS.") == "success"
        assert parse_verdict("My verdict: MIXED") == "mixed"
        assert parse_verdict("This is likely a FAILURE due to...") == "failure"

    def test_unparseable(self):
        assert parse_verdict("I don't know") == "unparseable"
        assert parse_verdict("") == "unparseable"
        assert parse_verdict("maybe") == "unparseable"


class TestLoadHoldoutSuite:
    def test_loads_temporal_holdout(self):
        meta, prompts = load_holdout_suite("temporal_holdout")
        assert meta["version"] == "2026-Q1"
        assert meta["n_prompts"] == 30
        assert len(prompts) == 30

    def test_all_prompts_have_required_fields(self):
        _, prompts = load_holdout_suite("temporal_holdout")
        for p in prompts:
            assert p.id
            assert p.sector
            assert p.launch_quarter
            assert len(p.concept) > 20
            assert p.ground_truth in VALID_OUTCOMES
            assert p.reception_summary

    def test_unique_ids(self):
        _, prompts = load_holdout_suite("temporal_holdout")
        ids = [p.id for p in prompts]
        assert len(ids) == len(set(ids))

    def test_outcome_distribution(self):
        """Suite should have a mix of outcomes, not all one type."""
        _, prompts = load_holdout_suite("temporal_holdout")
        outcomes = {p.ground_truth for p in prompts}
        assert outcomes == {"success", "mixed", "failure"}

    def test_sector_diversity(self):
        """Suite should cover multiple sectors."""
        _, prompts = load_holdout_suite("temporal_holdout")
        sectors = {p.sector for p in prompts}
        assert len(sectors) >= 10

    def test_nonexistent_suite_raises(self):
        with pytest.raises(FileNotFoundError):
            load_holdout_suite("nonexistent_suite_xyz")


class TestHoldoutSuiteResult:
    def _make_result(self, ground_truth: str, verdict: str) -> HoldoutResult:
        return HoldoutResult(
            prompt_id="test",
            sector="tech",
            ground_truth=ground_truth,
            model_verdict=verdict,
            correct=ground_truth == verdict,
            raw_response=verdict.upper(),
        )

    def test_accuracy_all_correct(self):
        results = [
            self._make_result("success", "success"),
            self._make_result("mixed", "mixed"),
            self._make_result("failure", "failure"),
        ]
        suite = HoldoutSuiteResult(
            provider_name="test",
            suite_version="test",
            results=results,
        )
        assert suite.accuracy == 1.0
        assert suite.n_correct == 3

    def test_accuracy_none_correct(self):
        results = [
            self._make_result("success", "failure"),
            self._make_result("mixed", "success"),
        ]
        suite = HoldoutSuiteResult(
            provider_name="test",
            suite_version="test",
            results=results,
        )
        assert suite.accuracy == 0.0

    def test_accuracy_empty(self):
        suite = HoldoutSuiteResult(
            provider_name="test",
            suite_version="test",
            results=[],
        )
        assert suite.accuracy == 0.0

    def test_per_outcome_accuracy(self):
        results = [
            self._make_result("success", "success"),
            self._make_result("success", "mixed"),
            self._make_result("failure", "failure"),
        ]
        suite = HoldoutSuiteResult(
            provider_name="test",
            suite_version="test",
            results=results,
        )
        acc = suite.per_outcome_accuracy
        assert acc["success"] == 0.5
        assert acc["failure"] == 1.0

    def test_per_sector_accuracy(self):
        r1 = HoldoutResult("p1", "tech", "success", "success", True, "SUCCESS")
        r2 = HoldoutResult("p2", "tech", "mixed", "failure", False, "FAILURE")
        r3 = HoldoutResult("p3", "health", "success", "success", True, "SUCCESS")
        suite = HoldoutSuiteResult(
            provider_name="test",
            suite_version="test",
            results=[r1, r2, r3],
        )
        acc = suite.per_sector_accuracy
        assert acc["tech"] == 0.5
        assert acc["health"] == 1.0

    def test_confusion_matrix(self):
        results = [
            self._make_result("success", "success"),
            self._make_result("success", "mixed"),
            self._make_result("failure", "failure"),
            self._make_result("failure", "success"),
        ]
        suite = HoldoutSuiteResult(
            provider_name="test",
            suite_version="test",
            results=results,
        )
        cm = suite.confusion_matrix
        assert cm["success"]["success"] == 1
        assert cm["success"]["mixed"] == 1
        assert cm["failure"]["failure"] == 1
        assert cm["failure"]["success"] == 1

    def test_to_dict(self):
        results = [self._make_result("success", "success")]
        suite = HoldoutSuiteResult(
            provider_name="test-prov",
            suite_version="2026-Q1",
            results=results,
        )
        d = suite.to_dict()
        assert d["benchmark"] == "synthbench"
        assert d["type"] == "holdout"
        assert d["provider"] == "test-prov"
        assert d["aggregate"]["accuracy"] == 1.0
        assert len(d["per_prompt"]) == 1


class MockHoldoutProvider(Provider):
    """Provider that always returns SUCCESS."""

    @property
    def name(self) -> str:
        return "mock/holdout"

    async def respond(self, question, options, *, persona=None):
        return Response(selected_option="SUCCESS")


class TestEvaluatePrompt:
    @pytest.mark.asyncio
    async def test_evaluate_single_prompt(self):
        import asyncio

        prompt = HoldoutPrompt(
            id="test_001",
            sector="tech",
            launch_quarter="2026-Q1",
            concept="A new AI product that does X",
            ground_truth="success",
            reception_summary="It worked great",
        )
        provider = MockHoldoutProvider()
        sem = asyncio.Semaphore(1)

        result = await evaluate_prompt(prompt, provider, sem)
        assert result.prompt_id == "test_001"
        assert result.model_verdict == "success"
        assert result.correct is True

    @pytest.mark.asyncio
    async def test_evaluate_wrong_verdict(self):
        import asyncio

        prompt = HoldoutPrompt(
            id="test_002",
            sector="retail",
            launch_quarter="2026-Q1",
            concept="A product that fails",
            ground_truth="failure",
            reception_summary="It flopped",
        )
        provider = MockHoldoutProvider()  # always returns SUCCESS
        sem = asyncio.Semaphore(1)

        result = await evaluate_prompt(prompt, provider, sem)
        assert result.model_verdict == "success"
        assert result.correct is False


class TestFormatHoldoutReport:
    def test_report_contains_key_sections(self):
        results = [
            HoldoutResult("p1", "tech", "success", "success", True, "SUCCESS"),
            HoldoutResult("p2", "health", "failure", "mixed", False, "MIXED"),
        ]
        suite = HoldoutSuiteResult(
            provider_name="test-prov",
            suite_version="2026-Q1",
            results=results,
        )
        report = format_holdout_report(suite)
        assert "Temporal Holdout Validation Report" in report
        assert "test-prov" in report
        assert "2026-Q1" in report
        assert "50.0%" in report
        assert "Confusion Matrix" in report
        assert "Per-Prompt Results" in report

    def test_report_empty_results(self):
        suite = HoldoutSuiteResult(
            provider_name="test",
            suite_version="test",
            results=[],
        )
        report = format_holdout_report(suite)
        assert "0.0%" in report
