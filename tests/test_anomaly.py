"""Tests for Tier-3 statistical anomaly detectors."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from synthbench.anomaly import (
    ANOMALY_PERFECTION_ERROR_MIN_N,
    check_missing_refusals,
    check_peer_distribution_outlier,
    check_suspicious_perfection,
    tier3_checks,
)
from synthbench.validation import Severity

LEADERBOARD_DIR = Path(__file__).resolve().parent.parent / "leaderboard-results"
ADVERSARIAL_FIXTURES_DIR = Path(__file__).resolve().parent / "adversarial" / "fixtures"


def _q(
    key: str,
    jsd: float,
    *,
    tau: float = 0.5,
    model_refusal_rate: float = 0.0,
    human_refusal_rate: float = 0.0,
) -> dict:
    return {
        "key": key,
        "jsd": jsd,
        "kendall_tau": tau,
        "model_refusal_rate": model_refusal_rate,
        "human_refusal_rate": human_refusal_rate,
    }


class TestSuspiciousPerfection:
    def test_answer_key_copy_flagged(self):
        """JSD ≈ 0 across every question is the signature of a copied
        answer key. The detector must catch it regardless of std."""
        pq = [_q(f"Q{i}", jsd=0.001) for i in range(20)]
        issue = check_suspicious_perfection(pq)
        assert issue is not None
        assert issue.severity is Severity.WARNING
        assert issue.code == "ANOMALY_PERFECTION"

    def test_constant_jsd_flagged(self):
        """Zero variance across questions is impossible for a real sampling
        pipeline — flag it even when the mean is nonzero."""
        pq = [_q(f"Q{i}", jsd=0.1) for i in range(20)]
        issue = check_suspicious_perfection(pq)
        assert issue is not None
        assert "std=" in issue.message

    def test_real_submission_not_flagged(self):
        """A plausible real submission (mean JSD ~0.4, nontrivial std)
        must not fire the detector."""
        pq = [_q(f"Q{i}", jsd=0.05 + (i % 10) * 0.07) for i in range(30)]
        issue = check_suspicious_perfection(pq)
        assert issue is None

    def test_small_sample_skipped(self):
        """<5 questions is too small to reason about — skip silently."""
        pq = [_q(f"Q{i}", jsd=0.0) for i in range(3)]
        assert check_suspicious_perfection(pq) is None

    def test_severity_warning_below_error_threshold(self):
        """Just under ``ANOMALY_PERFECTION_ERROR_MIN_N`` stays WARNING so
        small debug fixtures aren't hard-rejected."""
        n = ANOMALY_PERFECTION_ERROR_MIN_N - 1
        pq = [_q(f"Q{i}", jsd=0.0001) for i in range(n)]
        issue = check_suspicious_perfection(pq)
        assert issue is not None
        assert issue.severity is Severity.WARNING

    def test_severity_error_at_threshold(self):
        """At the minimum production sample size the thresholds are far
        enough below the real-run noise floor that the detector is
        promoted to ERROR — see docs/benchmark-hardening-analysis.md §2."""
        pq = [_q(f"Q{i}", jsd=0.0001) for i in range(ANOMALY_PERFECTION_ERROR_MIN_N)]
        issue = check_suspicious_perfection(pq)
        assert issue is not None
        assert issue.severity is Severity.ERROR
        assert issue.code == "ANOMALY_PERFECTION"

    def test_severity_error_on_large_constant_jsd(self):
        """Std-near-zero on a large-N submission also escalates to ERROR."""
        pq = [_q(f"Q{i}", jsd=0.1) for i in range(50)]
        issue = check_suspicious_perfection(pq)
        assert issue is not None
        assert issue.severity is Severity.ERROR


class TestMissingRefusals:
    def test_zero_refusals_flagged_when_humans_refuse(self):
        pq = [
            _q(f"Q{i}", jsd=0.3, human_refusal_rate=0.15, model_refusal_rate=0.0)
            for i in range(5)
        ]
        issue = check_missing_refusals(pq)
        assert issue is not None
        assert issue.code == "ANOMALY_NO_REFUSAL"
        assert "human_refusal_rate" in issue.message

    def test_some_refusals_not_flagged(self):
        pq = [_q(f"Q{i}", jsd=0.3, human_refusal_rate=0.15) for i in range(5)]
        pq[0]["model_refusal_rate"] = 0.1
        assert check_missing_refusals(pq) is None

    def test_no_human_refusals_not_flagged(self):
        """If humans never refuse, zero model refusals is fine."""
        pq = [_q(f"Q{i}", jsd=0.3, human_refusal_rate=0.0) for i in range(20)]
        assert check_missing_refusals(pq) is None

    def test_few_refusing_questions_not_flagged(self):
        """Below the minimum count, don't flag — too noisy a signal."""
        pq = [_q(f"Q{i}", jsd=0.3, human_refusal_rate=0.0) for i in range(20)]
        pq[0]["human_refusal_rate"] = 0.2
        assert check_missing_refusals(pq) is None


class TestPeerOutlier:
    def _submission(self, provider: str, jsd_values: list[float]) -> dict:
        return {
            "config": {"dataset": "globalopinionqa", "provider": provider},
            "per_question": [
                {"key": f"Q{i}", "jsd": v} for i, v in enumerate(jsd_values)
            ],
        }

    def test_no_peers_returns_none(self):
        sub = self._submission("openrouter/anthropic/claude-haiku-4-5", [0.4] * 10)
        assert check_peer_distribution_outlier(sub, []) is None

    def test_different_family_not_compared(self):
        sub = self._submission("openrouter/anthropic/claude-haiku-4-5", [0.4] * 10)
        peer = self._submission("openrouter/openai/gpt-4o-mini", [0.1] * 10)
        assert check_peer_distribution_outlier(sub, [peer]) is None

    def test_same_family_outlier_flagged(self):
        """Submission systematically below peer JSD by several sigma."""
        peer1 = self._submission(
            "anthropic/claude-haiku-4-5", [0.40 + i * 0.01 for i in range(20)]
        )
        peer2 = self._submission(
            "openrouter/anthropic/claude-haiku-4-5",
            [0.41 + i * 0.01 for i in range(20)],
        )
        sub = self._submission("openrouter/anthropic/claude-haiku-4-5", [0.02] * 20)
        issue = check_peer_distribution_outlier(sub, [peer1, peer2])
        assert issue is not None
        assert issue.code == "ANOMALY_PEER_OUTLIER"

    def test_similar_runs_not_flagged(self):
        """Two honest runs of the same model should not flag each other."""
        peer = self._submission(
            "anthropic/claude-haiku-4-5", [0.40 + i * 0.01 for i in range(20)]
        )
        sub = self._submission(
            "openrouter/anthropic/claude-haiku-4-5",
            [0.42 + i * 0.01 for i in range(20)],
        )
        assert check_peer_distribution_outlier(sub, [peer]) is None

    def test_baseline_not_compared(self):
        """Baselines are never same-family."""
        peer = self._submission("random-baseline", [0.5] * 20)
        sub = self._submission("majority-baseline", [0.02] * 20)
        assert check_peer_distribution_outlier(sub, [peer]) is None


class TestTier3Dispatch:
    def test_empty_submission_returns_empty(self):
        assert tier3_checks({}) == []

    def test_aggregates_multiple_issues(self):
        """A fabricated submission trips the perfection detector.

        ``check_missing_refusals`` is intentionally not wired into
        ``tier3_checks`` — current provider prompts give the model no
        way to refuse (see anomaly.py docstring). The perfection
        detector alone covers this fabrication fixture.
        """
        pq = [_q(f"Q{i}", jsd=0.001) for i in range(20)]
        data = {
            "config": {"dataset": "globalopinionqa", "provider": "fake/model"},
            "per_question": pq,
        }
        issues = tier3_checks(data)
        codes = {i.code for i in issues}
        assert "ANOMALY_PERFECTION" in codes
        # ANOMALY_NO_REFUSAL is retired from the default dispatch.
        assert "ANOMALY_NO_REFUSAL" not in codes


# ---------------------------------------------------------------------------
# Integration: real leaderboard-results fixtures must pass every detector.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not LEADERBOARD_DIR.is_dir(),
    reason="leaderboard-results/ not present in this worktree",
)
class TestRealSubmissionsPassCleanly:
    """Every real submission in ``leaderboard-results/`` must pass the
    anomaly detectors individually. If one trips the detectors, either
    the detector is miscalibrated or the file is legitimately anomalous
    — both cases are bugs worth failing the test over."""

    @pytest.fixture(scope="class")
    def real_submissions(self) -> list[dict]:
        results: list[dict] = []
        for path in sorted(LEADERBOARD_DIR.glob("*.json")):
            try:
                with open(path) as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("benchmark") != "synthbench":
                continue
            results.append(data)
        return results

    def test_no_perfection_false_positives(self, real_submissions):
        assert real_submissions, "leaderboard-results/ empty — fixtures gone?"
        for sub in real_submissions:
            pq = sub.get("per_question") or []
            if not pq:
                continue
            issue = check_suspicious_perfection(pq)
            provider = sub.get("config", {}).get("provider", "?")
            assert issue is None, (
                f"real submission from {provider} unexpectedly flagged: "
                f"{issue.message if issue else ''}"
            )

    def test_missing_refusal_detector_runs_without_error(self, real_submissions):
        """The detector is warning-level by design — some real LLM
        submissions may legitimately never refuse (depends on prompt
        template + model). We only assert the detector executes without
        error on every real file and produces either ``None`` or a
        WARNING-severity issue (never ERROR).
        """
        assert real_submissions
        for sub in real_submissions:
            pq = sub.get("per_question") or []
            if not pq:
                continue
            issue = check_missing_refusals(pq)
            if issue is not None:
                assert issue.severity is Severity.WARNING


# ---------------------------------------------------------------------------
# Fabrication fixture — synthetic submission crafted to copy the answer key.
# ---------------------------------------------------------------------------


def _answer_key_copy_submission() -> dict:
    """Fabricator 'runs' the benchmark by copying human distributions."""
    pq = []
    for i in range(20):
        human = {"A": 0.5, "B": 0.3, "C": 0.2}
        pq.append(
            {
                "key": f"Q_{i:03d}",
                "text": "",
                "options": ["A", "B", "C"],
                "human_distribution": human,
                "model_distribution": human,
                "jsd": 0.0001,
                "kendall_tau": 0.99,
                "parity": 0.99,
                "n_samples": 15,
                "n_parse_failures": 0,
                "model_refusal_rate": 0.0,
                "human_refusal_rate": 0.15 if i < 10 else 0.0,
                "temporal_year": 2024,
            }
        )
    return {
        "benchmark": "synthbench",
        "version": "0.1.0",
        "config": {
            "dataset": "globalopinionqa",
            "provider": "fabricator/copied-answer-key",
        },
        "per_question": pq,
    }


class TestFabricationRejection:
    def test_answer_key_copy_trips_detector(self):
        data = _answer_key_copy_submission()
        issues = tier3_checks(data)
        codes = {i.code for i in issues}
        # Perfection is the primary signature of an answer-key copy and
        # still fires on this fixture. ANOMALY_NO_REFUSAL is retired
        # from the default dispatch (see anomaly.tier3_checks docstring).
        assert "ANOMALY_PERFECTION" in codes, codes
        assert "ANOMALY_NO_REFUSAL" not in codes, codes
        assert all(i.severity is Severity.WARNING for i in issues)

    def test_near_perfect_but_varied_still_flagged(self):
        """Even if the fabricator varies the JSD slightly, mean < threshold
        still trips the detector."""
        sub = _answer_key_copy_submission()
        for i, q in enumerate(sub["per_question"]):
            q["jsd"] = 0.0001 * (1 + i * 0.1)  # tiny variation
        issues = tier3_checks(sub)
        assert any(i.code == "ANOMALY_PERFECTION" for i in issues)


class TestAdversarialFixtures:
    """Load on-disk adversarial fixtures and assert the required detectors
    fire at the required severity. These are the foundation of the
    adversarial-suite CI gate described in
    ``docs/benchmark-hardening-analysis.md §5``.
    """

    def test_pure_copy_trips_anomaly_perfection_as_error(self):
        fixture_path = ADVERSARIAL_FIXTURES_DIR / "pure_copy.json"
        assert fixture_path.is_file(), fixture_path
        with open(fixture_path) as f:
            data = json.load(f)

        assert len(data["per_question"]) >= ANOMALY_PERFECTION_ERROR_MIN_N

        issues = tier3_checks(data)
        perfection = [i for i in issues if i.code == "ANOMALY_PERFECTION"]
        assert perfection, (
            "pure_copy fixture did not trip ANOMALY_PERFECTION: "
            f"got codes {[i.code for i in issues]}"
        )
        assert all(i.severity is Severity.ERROR for i in perfection), [
            (i.code, i.severity) for i in perfection
        ]


class TestPeerOutlierWithFabricator:
    """Fabricator who claims claude-haiku while inflating JSD far from
    real claude-haiku peers."""

    def _legit_peer(self) -> dict:
        return {
            "config": {
                "dataset": "globalopinionqa",
                "provider": "openrouter/anthropic/claude-haiku-4-5",
            },
            "per_question": [
                {"key": f"Q_{i:03d}", "jsd": 0.35 + (i % 5) * 0.02} for i in range(50)
            ],
        }

    def test_fabricator_out_of_peer_envelope_flagged(self):
        fake = copy.deepcopy(self._legit_peer())
        fake["config"]["provider"] = "fabricator/anthropic/claude-haiku-4-5"
        # Fabricator claims haiku but per-q JSD is dramatically lower.
        for q in fake["per_question"]:
            q["jsd"] = 0.05
        peers = [self._legit_peer(), self._legit_peer()]
        issue = check_peer_distribution_outlier(fake, peers)
        assert issue is not None
        assert "lower" in issue.message
