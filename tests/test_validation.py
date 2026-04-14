"""Tests for the submission validation pipeline."""

from __future__ import annotations

import copy
import json

import pytest

from synthbench.stats import question_set_hash
from synthbench.validation import (
    Severity,
    validate_file,
    validate_submission,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _pq(
    key: str,
    human: dict[str, float],
    model: dict[str, float],
    jsd: float,
    tau: float,
    parity: float | None = None,
    *,
    n_samples: int = 10,
    n_parse_failures: int = 0,
    model_refusal_rate: float = 0.0,
    human_refusal_rate: float = 0.0,
) -> dict:
    return {
        "key": key,
        "text": "",
        "options": sorted(set(human) | set(model)),
        "human_distribution": human,
        "model_distribution": model,
        "jsd": jsd,
        "kendall_tau": tau,
        "parity": parity
        if parity is not None
        else (1.0 - jsd + (1.0 + tau) / 2.0) / 2.0,
        "n_samples": n_samples,
        "n_parse_failures": n_parse_failures,
        "model_refusal_rate": model_refusal_rate,
        "human_refusal_rate": human_refusal_rate,
        "temporal_year": 2024,
    }


@pytest.fixture
def clean_submission() -> dict:
    """A minimal, self-consistent submission that should validate cleanly.

    Constructed so that reported JSD / tau / mean / composite_parity
    match values recomputed from the distributions.
    """

    from synthbench.metrics.distributional import jensen_shannon_divergence
    from synthbench.metrics.ranking import kendall_tau_b

    human_a = {"A": 0.5, "B": 0.3, "C": 0.2}
    model_a = {"A": 0.4, "B": 0.4, "C": 0.2}
    human_b = {"A": 0.7, "B": 0.2, "C": 0.1}
    model_b = {"A": 0.6, "B": 0.3, "C": 0.1}

    jsd_a = jensen_shannon_divergence(human_a, model_a)
    tau_a = kendall_tau_b(human_a, model_a)
    jsd_b = jensen_shannon_divergence(human_b, model_b)
    tau_b = kendall_tau_b(human_b, model_b)

    mean_jsd = (jsd_a + jsd_b) / 2
    mean_tau = (tau_a + tau_b) / 2
    p_dist = 1.0 - mean_jsd
    p_rank = (1.0 + mean_tau) / 2.0
    composite = 0.5 * p_dist + 0.5 * p_rank

    q_keys = ["Q_A", "Q_B"]

    return {
        "benchmark": "synthbench",
        "version": "0.1.0",
        "timestamp": "2026-04-13T00:00:00+00:00",
        "config": {
            "dataset": "globalopinionqa",
            "provider": "test-provider",
            "question_set_hash": question_set_hash(q_keys),
            "parse_failure_rate": 0.0,
        },
        "scores": {
            "sps": composite,
            "p_dist": p_dist,
            "p_rank": p_rank,
            "p_refuse": 1.0,
        },
        "aggregate": {
            "mean_jsd": mean_jsd,
            "mean_kendall_tau": mean_tau,
            "composite_parity": composite,
            "n_questions": 2,
        },
        "per_question": [
            _pq("Q_A", human_a, model_a, jsd_a, tau_a),
            _pq("Q_B", human_b, model_b, jsd_b, tau_b),
        ],
    }


# ---------------------------------------------------------------------------
# Tier 1: schema + plausibility
# ---------------------------------------------------------------------------


class TestSchemaChecks:
    def test_clean_submission_passes(self, clean_submission):
        report = validate_submission(clean_submission)
        assert report.ok, report.format()

    def test_missing_top_level_keys(self, clean_submission):
        bad = copy.deepcopy(clean_submission)
        del bad["aggregate"]
        report = validate_submission(bad)
        assert not report.ok
        codes = {i.code for i in report.errors}
        assert "SCHEMA_MISSING" in codes

    def test_wrong_benchmark_identifier(self, clean_submission):
        bad = copy.deepcopy(clean_submission)
        bad["benchmark"] = "pretend-bench"
        report = validate_submission(bad)
        assert not report.ok
        assert any(i.code == "SCHEMA_BENCHMARK" for i in report.errors)

    def test_non_dict_root(self):
        report = validate_submission(["not", "an", "object"])
        assert not report.ok
        assert any(i.code == "SCHEMA_ROOT" for i in report.errors)

    def test_config_missing_required_fields(self, clean_submission):
        bad = copy.deepcopy(clean_submission)
        del bad["config"]["dataset"]
        report = validate_submission(bad)
        assert not report.ok
        assert any(i.path == "config.dataset" for i in report.errors)


class TestBoundsChecks:
    def test_sps_above_one_rejected(self, clean_submission):
        bad = copy.deepcopy(clean_submission)
        bad["aggregate"]["composite_parity"] = 1.05
        report = validate_submission(bad)
        assert not report.ok
        assert any(i.code == "BOUNDS_RANGE" for i in report.errors)

    def test_mean_jsd_negative_rejected(self, clean_submission):
        bad = copy.deepcopy(clean_submission)
        bad["aggregate"]["mean_jsd"] = -0.1
        report = validate_submission(bad)
        assert not report.ok

    def test_kendall_tau_within_minus_one_and_one(self, clean_submission):
        bad = copy.deepcopy(clean_submission)
        bad["aggregate"]["mean_kendall_tau"] = 1.5
        report = validate_submission(bad)
        assert not report.ok

    def test_parse_failure_rate_above_one(self, clean_submission):
        bad = copy.deepcopy(clean_submission)
        bad["config"]["parse_failure_rate"] = 2.0
        report = validate_submission(bad)
        assert not report.ok


class TestDistributionChecks:
    def test_distribution_sum_bad(self, clean_submission):
        bad = copy.deepcopy(clean_submission)
        bad["per_question"][0]["model_distribution"] = {"A": 0.2, "B": 0.2, "C": 0.1}
        report = validate_submission(bad, tier2=False)
        assert not report.ok
        assert any(i.code == "DIST_SUM" for i in report.errors)

    def test_negative_probability(self, clean_submission):
        bad = copy.deepcopy(clean_submission)
        bad["per_question"][0]["model_distribution"] = {
            "A": 1.2,
            "B": -0.3,
            "C": 0.1,
        }
        report = validate_submission(bad, tier2=False)
        assert any(i.code == "DIST_NEGATIVE" for i in report.errors)


class TestQuestionSetHash:
    def test_reported_hash_mismatch(self, clean_submission):
        bad = copy.deepcopy(clean_submission)
        bad["config"]["question_set_hash"] = "0" * 64
        report = validate_submission(bad, tier2=False)
        assert not report.ok
        assert any(i.code == "QSET_HASH" for i in report.errors)

    def test_expected_hash_enforced(self, clean_submission):
        report = validate_submission(clean_submission, expected_question_hash="1" * 64)
        assert not report.ok
        assert any(i.code == "QSET_HASH_DATASET" for i in report.errors)

    def test_expected_hash_matches(self, clean_submission):
        expected = question_set_hash(
            [q["key"] for q in clean_submission["per_question"]]
        )
        report = validate_submission(clean_submission, expected_question_hash=expected)
        assert report.ok


class TestCountMismatch:
    def test_aggregate_count_mismatch(self, clean_submission):
        bad = copy.deepcopy(clean_submission)
        bad["aggregate"]["n_questions"] = 5  # only 2 per_question entries
        report = validate_submission(bad, tier2=False)
        assert not report.ok
        assert any(i.code == "COUNT_MISMATCH" for i in report.errors)


class TestParseFailurePlausibility:
    def test_large_zero_failure_run_warns(self, clean_submission):
        submission = copy.deepcopy(clean_submission)
        # Extend to 50+ questions with 10 samples each and zero failures.
        base_q = submission["per_question"][0]
        extra = []
        for i in range(60):
            q = copy.deepcopy(base_q)
            q["key"] = f"Q_{i}"
            extra.append(q)
        submission["per_question"] = extra
        submission["aggregate"]["n_questions"] = len(extra)
        submission["config"]["question_set_hash"] = question_set_hash(
            [q["key"] for q in extra]
        )
        report = validate_submission(submission, tier2=False)
        assert any(
            i.code == "PARSE_SUSPICIOUS" and i.severity is Severity.WARNING
            for i in report.warnings
        )

    def test_baseline_exempt(self, clean_submission):
        submission = copy.deepcopy(clean_submission)
        submission["config"]["provider"] = "random-baseline"
        base_q = submission["per_question"][0]
        extra = []
        for i in range(60):
            q = copy.deepcopy(base_q)
            q["key"] = f"Q_{i}"
            extra.append(q)
        submission["per_question"] = extra
        submission["aggregate"]["n_questions"] = len(extra)
        submission["config"]["question_set_hash"] = question_set_hash(
            [q["key"] for q in extra]
        )
        report = validate_submission(submission, tier2=False)
        assert not any(i.code == "PARSE_SUSPICIOUS" for i in report.issues)


# ---------------------------------------------------------------------------
# Tier 2: recomputation
# ---------------------------------------------------------------------------


class TestRecomputationChecks:
    def test_fabricated_per_question_jsd_caught(self, clean_submission):
        """An attacker lies about the per-question JSD to lower it.

        The delta must exceed METRIC_RECOMPUTE_TOLERANCE (3e-2); small
        fabrications under that threshold are noise and not worth failing
        a submission over.
        """

        bad = copy.deepcopy(clean_submission)
        # Real JSD for Q_A is ~0.010; fabricate a large dishonest shift.
        bad["per_question"][0]["jsd"] = 0.5
        report = validate_submission(bad)
        assert not report.ok
        assert any(i.code == "PER_Q_JSD" for i in report.errors)

    def test_fabricated_per_question_tau_caught(self, clean_submission):
        bad = copy.deepcopy(clean_submission)
        # Real tau is close to 1; flip it wrong to force a fail.
        bad["per_question"][0]["kendall_tau"] = -0.5
        report = validate_submission(bad)
        assert not report.ok
        assert any(i.code == "PER_Q_TAU" for i in report.errors)

    def test_tau_rounding_tie_artifact_tolerated(self):
        """Serialization to 4 decimals can collapse distinct probabilities
        into ties, shifting Kendall's tau-b by ~0.012 on small-option
        distributions (e.g. 3/√75 = 0.3464 unrounded vs 3/√70 = 0.3586
        after a single rounding-induced tie). The validator must absorb
        this artifact — the value is arithmetically correct at full
        precision, just inconsistent with the rounded public form.
        """
        human = {
            "Greatly reduce": 0.2222,
            "Slightly reduce": 0.3382,
            "Not change": 0.3494,
            "Slightly increase": 0.0463,
            "Greatly increase": 0.022,
            "Refused": 0.022,
        }
        model = {
            "Greatly reduce": 0.0,
            "Slightly reduce": 1.0,
            "Not change": 0.0,
            "Slightly increase": 0.0,
            "Greatly increase": 0.0,
            "Refused": 0.0,
        }
        # Reported tau computed pre-rounding (no tie between 0.022 and 0.022).
        reported_tau = 0.34641
        q_keys = ["Q_ROUND"]
        submission = {
            "benchmark": "synthbench",
            "version": "0.1.0",
            "config": {
                "dataset": "subpop",
                "provider": "test-provider",
                "question_set_hash": question_set_hash(q_keys),
                "parse_failure_rate": 0.0,
            },
            "aggregate": {
                "mean_jsd": 0.45,
                "mean_kendall_tau": reported_tau,
                "composite_parity": 0.5,
                "n_questions": 1,
            },
            "per_question": [
                _pq("Q_ROUND", human, model, jsd=0.454308, tau=reported_tau),
            ],
        }
        report = validate_submission(submission)
        assert not any(i.code == "PER_Q_TAU" for i in report.errors), (
            "serialization-induced tie must not trigger PER_Q_TAU:\n" + report.format()
        )

    def test_fabricated_aggregate_parity_caught(self, clean_submission):
        """An attacker inflates composite_parity without changing per-question data."""

        bad = copy.deepcopy(clean_submission)
        # Inflate well beyond the 2-metric blend (~0.97) AND the SPS
        # mean variant (~0.98), pushing the claim into obviously-bad
        # territory no legitimate recomputation could produce.
        bad["aggregate"]["composite_parity"] = 0.5
        report = validate_submission(bad)
        assert not report.ok
        assert any(i.code == "AGG_COMPOSITE" for i in report.errors)

    def test_fabricated_mean_jsd_caught(self, clean_submission):
        bad = copy.deepcopy(clean_submission)
        # Real mean_jsd is ~0.01; fabricate an impossible 0.9.
        bad["aggregate"]["mean_jsd"] = 0.9
        report = validate_submission(bad)
        assert not report.ok
        assert any(i.code == "AGG_MEAN_JSD" for i in report.errors)

    def test_skip_recompute_respected(self, clean_submission):
        """With tier2=False, aggregate lies are not caught."""

        bad = copy.deepcopy(clean_submission)
        bad["aggregate"]["composite_parity"] = 0.5
        report = validate_submission(bad, tier2=False)
        # No recomputation codes fired:
        assert not any(
            i.code.startswith("AGG_") or i.code.startswith("PER_Q_")
            for i in report.errors
        )


# ---------------------------------------------------------------------------
# End-to-end fabrication detection (the acceptance criterion)
# ---------------------------------------------------------------------------


def _fabricated_submission() -> dict:
    """Build a submission with plausible-looking metadata but fabricated scores.

    Per-question distributions imply SPS ≈ 0.55; fabricator reports 0.97.
    """

    human = {"A": 0.5, "B": 0.3, "C": 0.2}
    # Terrible match — clearly not drawn from the same distribution.
    model = {"A": 0.0, "B": 0.0, "C": 1.0}

    per_question = []
    for i in range(20):
        per_question.append(
            {
                "key": f"Q_{i:03d}",
                "text": "",
                "options": ["A", "B", "C"],
                "human_distribution": human,
                "model_distribution": model,
                # Fabricated: claim great metrics despite bad distribution.
                "jsd": 0.02,
                "kendall_tau": 0.99,
                "parity": 0.97,
                "n_samples": 15,
                "n_parse_failures": 0,
                "model_refusal_rate": 0.0,
                "human_refusal_rate": 0.0,
                "temporal_year": 2024,
            }
        )
    q_keys = [q["key"] for q in per_question]

    return {
        "benchmark": "synthbench",
        "version": "0.1.0",
        "timestamp": "2026-04-13T00:00:00+00:00",
        "config": {
            "dataset": "globalopinionqa",
            "provider": "fabricator/fake-model",
            "question_set_hash": question_set_hash(q_keys),
            "parse_failure_rate": 0.0,
        },
        "scores": {
            "sps": 0.97,
            "p_dist": 0.98,
            "p_rank": 0.995,
            "p_refuse": 1.0,
        },
        "aggregate": {
            "mean_jsd": 0.02,
            "mean_kendall_tau": 0.99,
            "composite_parity": 0.97,
            "n_questions": 20,
        },
        "per_question": per_question,
    }


class TestFabricationRejection:
    """The acceptance criterion: intentionally fabricated data must be rejected."""

    def test_fabricator_rejected(self):
        fake = _fabricated_submission()
        report = validate_submission(fake)
        assert not report.ok, (
            "Fabricated submission unexpectedly validated clean:\n" + report.format()
        )
        # The fabrication touches both per-question and aggregate layers;
        # assert at least one of each class of check fires.
        codes = {i.code for i in report.errors}
        assert codes & {"PER_Q_JSD", "PER_Q_TAU"}, codes
        assert codes & {
            "AGG_MEAN_JSD",
            "AGG_MEAN_TAU",
            "AGG_COMPOSITE",
            "SCORES_SUB",
        }, codes

    def test_fabricator_rejected_via_file(self, tmp_path):
        fake = _fabricated_submission()
        path = tmp_path / "fabricated.json"
        path.write_text(json.dumps(fake))
        report = validate_file(path)
        assert not report.ok


class TestFileIO:
    def test_missing_file(self, tmp_path):
        report = validate_file(tmp_path / "nope.json")
        assert not report.ok
        assert any(i.code == "IO_MISSING" for i in report.errors)

    def test_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not valid json")
        report = validate_file(path)
        assert not report.ok
        assert any(i.code == "IO_DECODE" for i in report.errors)

    def test_clean_file_roundtrip(self, tmp_path, clean_submission):
        path = tmp_path / "good.json"
        path.write_text(json.dumps(clean_submission))
        report = validate_file(path)
        assert report.ok, report.format()
