"""Tests for Tier-3 statistical anomaly detectors."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from synthbench.anomaly import (
    check_missing_refusals,
    check_peer_distribution_outlier,
    check_suspicious_perfection,
    tier3_checks,
)
from synthbench.validation import Severity

LEADERBOARD_DIR = Path(__file__).resolve().parent.parent / "leaderboard-results"


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
        """A clearly-fabricated submission trips multiple detectors."""
        pq = [
            _q(f"Q{i}", jsd=0.001, human_refusal_rate=0.2, model_refusal_rate=0.0)
            for i in range(20)
        ]
        data = {
            "config": {"dataset": "globalopinionqa", "provider": "fake/model"},
            "per_question": pq,
        }
        issues = tier3_checks(data)
        codes = {i.code for i in issues}
        assert "ANOMALY_PERFECTION" in codes
        assert "ANOMALY_NO_REFUSAL" in codes


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
        # Expect BOTH perfection AND no-refusal to fire on this fixture.
        assert "ANOMALY_PERFECTION" in codes, codes
        assert "ANOMALY_NO_REFUSAL" in codes, codes
        assert all(i.severity is Severity.WARNING for i in issues)

    def test_near_perfect_but_varied_still_flagged(self):
        """Even if the fabricator varies the JSD slightly, mean < threshold
        still trips the detector."""
        sub = _answer_key_copy_submission()
        for i, q in enumerate(sub["per_question"]):
            q["jsd"] = 0.0001 * (1 + i * 0.1)  # tiny variation
        issues = tier3_checks(sub)
        assert any(i.code == "ANOMALY_PERFECTION" for i in issues)


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
