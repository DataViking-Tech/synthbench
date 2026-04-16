"""Tests for the submission validation pipeline."""

from __future__ import annotations

import copy
import json

import pytest

from synthbench.stats import question_set_hash
from synthbench.validation import (
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

    def test_all_zero_distribution_treated_as_sentinel(self, clean_submission):
        # Catastrophic parse-failure sentinel (sb-7gn): an all-zero
        # model_distribution is the legitimate encoding for "model produced
        # no parseable response on this question". It's paired with
        # jsd=1.0 / tau=0.0 in per_question, and should NOT trip DIST_SUM.
        bad = copy.deepcopy(clean_submission)
        q = bad["per_question"][0]
        q["model_distribution"] = dict.fromkeys(q["model_distribution"], 0.0)
        q["jsd"] = 1.0
        q["kendall_tau"] = 0.0
        report = validate_submission(bad, tier2=False)
        assert not any(i.code == "DIST_SUM" for i in report.errors)


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
    """PARSE_SUSPICIOUS was retired in sb-a613.

    Every provider prompt in ``src/synthbench/providers/`` ends with
    ``"Respond with ONLY the letter of your choice"``, which reliably
    yields zero parse failures from any modern MCQ-capable model. The
    detector false-positived on every real run at production scale and
    was never able to catch fabrication (fabricators just report
    non-zero failures). These tests assert the detector is dormant;
    they intentionally cover the regression behaviour rather than
    deleting the class, so a future reinstatement is visible in the
    test diff.
    """

    def test_large_zero_failure_run_no_longer_warns(self, clean_submission):
        submission = copy.deepcopy(clean_submission)
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

    def test_baseline_still_not_flagged(self, clean_submission):
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


# ---------------------------------------------------------------------------
# Tier 3: raw_responses, reproducibility metadata, anomaly dispatch
# ---------------------------------------------------------------------------


def _with_raw_and_repro(submission: dict) -> dict:
    """Attach a minimal raw_responses + reproducibility block to a clean fixture."""
    sub = copy.deepcopy(submission)
    sub["raw_responses"] = [
        {
            "key": q["key"],
            "raw_text": ("The most likely answer given the population described is A."),
            "selected_option": max(
                q["model_distribution"], key=q["model_distribution"].get
            ),
        }
        for q in sub["per_question"]
    ]
    sub["reproducibility"] = {
        "seed": 42,
        "model_revision_hash": "sha256:deadbeef",
        "prompt_template_hash": "sha256:cafef00d",
        "framework_version": "0.1.0",
        "submitted_at": "2026-04-15T00:00:00+00:00",
    }
    return sub


class TestTier3Orchestration:
    def test_tier3_skipped_when_disabled(self, clean_submission):
        """Tier 1+2 must ignore missing raw_responses/reproducibility."""
        report = validate_submission(clean_submission, tier3=False)
        assert report.ok
        codes = {i.code for i in report.issues}
        assert "RAW_RESPONSES_MISSING" not in codes
        assert "REPRO_MISSING" not in codes

    def test_tier3_flags_missing_fields_as_warnings(self, clean_submission):
        """Legacy submissions without the new fields must warn, not error."""
        report = validate_submission(clean_submission, tier3=True)
        # Legacy-style fixture: no errors, but warnings for new fields.
        assert report.ok
        warning_codes = {i.code for i in report.warnings}
        assert "RAW_RESPONSES_MISSING" in warning_codes
        assert "REPRO_MISSING" in warning_codes

    def test_tier3_with_valid_new_fields_clean(self, clean_submission):
        """A submission supplying all tier-3 fields validates cleanly."""
        submission = _with_raw_and_repro(clean_submission)
        report = validate_submission(submission, tier3=True)
        assert report.ok
        # No tier-3 warnings should fire on a fully-populated valid submission.
        tier3_codes = {
            i.code
            for i in report.issues
            if i.code.startswith(("RAW_", "REPRO_", "ANOMALY_"))
        }
        assert tier3_codes == set()

    def test_tier3_peers_parameter_passed_through(self, clean_submission):
        """peers iterable should reach the outlier detector without error."""
        submission = _with_raw_and_repro(clean_submission)
        peers = [copy.deepcopy(submission)]
        report = validate_submission(submission, tier3=True, peers=peers)
        # Self-vs-self is identical → no outlier warning.
        assert not any(i.code == "ANOMALY_PEER_OUTLIER" for i in report.issues)


class TestRawResponsesValidator:
    def test_non_list_is_warning(self, clean_submission):
        sub = _with_raw_and_repro(clean_submission)
        sub["raw_responses"] = "not a list"
        report = validate_submission(sub, tier3=True)
        assert any(i.code == "RAW_RESPONSES_TYPE" for i in report.warnings)

    def test_low_coverage_warns(self, clean_submission):
        """Must cover at least 10% of questions."""
        sub = copy.deepcopy(clean_submission)
        # Extend the fixture to 100 questions so 10% = 10 samples required.
        base_q = sub["per_question"][0]
        extra = []
        for i in range(100):
            q = copy.deepcopy(base_q)
            q["key"] = f"Q_{i:03d}"
            extra.append(q)
        sub["per_question"] = extra
        sub["aggregate"]["n_questions"] = 100
        sub["config"]["question_set_hash"] = question_set_hash(
            [q["key"] for q in extra]
        )
        sub = _with_raw_and_repro(sub)
        sub["raw_responses"] = sub["raw_responses"][:2]  # only 2 of 100 = 2%
        report = validate_submission(sub, tier3=True)
        assert any(i.code == "RAW_RESPONSES_COVERAGE" for i in report.warnings)

    def test_empty_raw_text_warns(self, clean_submission):
        sub = _with_raw_and_repro(clean_submission)
        sub["raw_responses"][0]["raw_text"] = ""
        report = validate_submission(sub, tier3=True)
        assert any(i.code == "RAW_RESPONSES_EMPTY" for i in report.warnings)

    def test_mode_mismatch_warns(self, clean_submission):
        """Selected option whose probability is well below the top and
        outside sample-count noise must be flagged. Q_B has
        ``model_distribution = {A:0.6, B:0.3, C:0.1}`` with n_samples=10
        so the sampling-noise tolerance is ~0.316; picking ``C`` (gap
        0.5) sits clearly outside that envelope."""
        sub = _with_raw_and_repro(clean_submission)
        sub["raw_responses"][1]["selected_option"] = "C"
        report = validate_submission(sub, tier3=True)
        assert any(i.code == "RAW_RESPONSES_MODE" for i in report.warnings)

    def test_mode_within_sampling_noise_not_flagged(self, clean_submission):
        """A raw sample that picked the second option on a distribution
        where the gap is within sampling noise must not trip
        RAW_RESPONSES_MODE (sb-a613). Q_B's 0.6/0.3/0.1 split at
        n_samples=10 puts ``B`` at a gap of 0.3, just inside the
        ~1/sqrt(10) ≈ 0.316 tolerance band."""
        sub = _with_raw_and_repro(clean_submission)
        sub["raw_responses"][1]["selected_option"] = "B"
        report = validate_submission(sub, tier3=True)
        assert not any(i.code == "RAW_RESPONSES_MODE" for i in report.warnings)

    def test_all_short_warns(self, clean_submission):
        """All 1-character samples should fire the short-length detector."""
        sub = _with_raw_and_repro(clean_submission)
        for sample in sub["raw_responses"]:
            sample["raw_text"] = "A"
        report = validate_submission(sub, tier3=True)
        assert any(i.code == "RAW_RESPONSES_LENGTH_SHORT" for i in report.warnings)


class TestReproducibilityValidator:
    def test_missing_block_warns(self, clean_submission):
        report = validate_submission(clean_submission, tier3=True)
        assert any(i.code == "REPRO_MISSING" for i in report.warnings)

    def test_non_dict_warns(self, clean_submission):
        sub = _with_raw_and_repro(clean_submission)
        sub["reproducibility"] = "not a dict"
        report = validate_submission(sub, tier3=True)
        assert any(i.code == "REPRO_TYPE" for i in report.warnings)

    def test_missing_field_warns(self, clean_submission):
        sub = _with_raw_and_repro(clean_submission)
        del sub["reproducibility"]["seed"]
        report = validate_submission(sub, tier3=True)
        codes = {i.code for i in report.warnings}
        assert "REPRO_FIELD_MISSING" in codes

    def test_empty_string_field_warns(self, clean_submission):
        sub = _with_raw_and_repro(clean_submission)
        sub["reproducibility"]["model_revision_hash"] = ""
        report = validate_submission(sub, tier3=True)
        codes = {i.code for i in report.warnings}
        assert "REPRO_FIELD_EMPTY" in codes

    def test_bad_seed_type_warns(self, clean_submission):
        sub = _with_raw_and_repro(clean_submission)
        sub["reproducibility"]["seed"] = "not-a-number"
        report = validate_submission(sub, tier3=True)
        codes = {i.code for i in report.warnings}
        assert "REPRO_FIELD_TYPE" in codes

    def test_none_seed_allowed(self, clean_submission):
        """Providers without stochastic sampling legitimately have seed=None."""
        sub = _with_raw_and_repro(clean_submission)
        sub["reproducibility"]["seed"] = None
        report = validate_submission(sub, tier3=True)
        assert not any(
            i.code in ("REPRO_FIELD_TYPE", "REPRO_FIELD_EMPTY")
            and i.path == "reproducibility.seed"
            for i in report.issues
        )


class TestTier3StrictMode:
    """CI-style strict mode: tier-3 warnings become failures at the caller."""

    def test_clean_in_strict_mode(self, clean_submission):
        sub = _with_raw_and_repro(clean_submission)
        report = validate_submission(sub, tier3=True)
        # report.ok stays True (warnings only); caller decides strict behavior.
        assert report.ok
        assert report.warnings == []


class TestTier3FabricationEndToEnd:
    """The full submission-integrity pipeline against a fabricated run."""

    def test_fabrication_rejected_at_tier2_even_without_tier3(self):
        """Tier 2 already catches a classic fabricator. Tier 3 piles on."""
        fabrication = _fabricated_submission()
        report = validate_submission(fabrication, tier3=True)
        assert not report.ok
        error_codes = {i.code for i in report.errors}
        warning_codes = {i.code for i in report.warnings}
        # Tier-2 arithmetic rejects inflated aggregate scores.
        assert error_codes & {
            "AGG_COMPOSITE",
            "AGG_MEAN_JSD",
            "PER_Q_JSD",
            "SCORES_SUB",
        }
        # Tier-3 adds raw_responses + repro warnings.
        assert "RAW_RESPONSES_MISSING" in warning_codes
        assert "REPRO_MISSING" in warning_codes


class TestSbA613Regression:
    """End-to-end regression guarding the sb-a613 false-positive cluster.

    The first real API-key submission (openrouter/anthropic/claude-haiku-4-5,
    n_questions=100, n_samples=15) was rejected under ``--strict`` because
    Tier-3 fired four warnings that were all artefacts of the current
    MCQ-only harness rather than fabrication: PARSE_SUSPICIOUS,
    ANOMALY_NO_REFUSAL, HOLDOUT_DIVERGENCE, and RAW_RESPONSES_MODE.
    This test rebuilds a shape-equivalent submission and asserts that the
    pipeline accepts it cleanly under the full tier-1+2+3 strict path.
    """

    def _haiku_like_submission(self) -> dict:
        """Minimal approximation of the sb-0qlc submission shape.

        Uses ``opinionsqa`` so the partitioning deterministically lands
        enough rows on each side of the 80/20 holdout split, even at
        n=100. Each question ships ``n_samples=15`` with zero parse
        failures and zero model refusals (architectural for the current
        provider prompt). One raw sample per ~10 questions is attached,
        and for the first ten questions the raw sample deliberately
        picks the second option on a close-distribution question —
        exactly the legitimate sampling pattern the original detector
        rejected.
        """

        from synthbench.metrics.distributional import jensen_shannon_divergence
        from synthbench.metrics.ranking import kendall_tau_b
        from synthbench.private_holdout import is_private_holdout

        dataset = "opinionsqa"
        q_keys: list[str] = []
        rows: list[dict] = []
        # Build 100 questions with realistic three-way distributions.
        # The human distribution varies slightly so mean_jsd is nonzero
        # but within plausible model output, not near-perfection.
        import random

        rng = random.Random(0x_A613)
        n_private = 0
        i = 0
        while len(q_keys) < 100:
            key = f"Q_{rng.getrandbits(48):012x}"
            if key in q_keys:
                continue
            q_keys.append(key)
            if is_private_holdout(dataset, key):
                n_private += 1
            # Human distribution: three options, slightly skewed.
            h_a = 0.45 + (i % 5) * 0.02
            h_b = 0.30 - (i % 3) * 0.02
            h_c = 1.0 - h_a - h_b
            human = {"A": round(h_a, 4), "B": round(h_b, 4), "C": round(h_c, 4)}
            # Model distribution:
            # - First 10 questions: close 6/5/4-style split at s=15 so the
            #   argmax is only weakly separated (6/15=0.40 vs 5/15=0.33).
            #   This is the shape that tripped RAW_RESPONSES_MODE on every
            #   minority-pick raw sample in sb-0qlc.
            # - Remaining 90: noisy reflection of the human distribution
            #   so mean_jsd and its std sit in the observed-honest range
            #   and ANOMALY_PERFECTION stays dormant.
            if i < 10:
                model = {
                    "A": round(6 / 15, 4),
                    "B": round(5 / 15, 4),
                    "C": round(4 / 15, 4),
                }
            else:
                m_a = round(max(0.01, min(0.98, h_a + rng.uniform(-0.2, 0.2))), 4)
                m_b = round(max(0.01, min(0.98, h_b + rng.uniform(-0.2, 0.2))), 4)
                m_c_raw = 1.0 - m_a - m_b
                if m_c_raw < 0.01:
                    # Renormalise if the first two drew too much mass.
                    scale = 0.99 / (m_a + m_b)
                    m_a = round(m_a * scale, 4)
                    m_b = round(m_b * scale, 4)
                    m_c_raw = 1.0 - m_a - m_b
                model = {"A": m_a, "B": m_b, "C": round(m_c_raw, 4)}
            jsd = jensen_shannon_divergence(human, model)
            tau = kendall_tau_b(human, model)
            human_refusal = 0.15 if i < 14 else 0.0
            rows.append(
                _pq(
                    key,
                    human,
                    model,
                    jsd,
                    tau,
                    n_samples=15,
                    n_parse_failures=0,
                    model_refusal_rate=0.0,  # harness has no refusal channel
                    human_refusal_rate=human_refusal,
                )
            )
            i += 1

        # Coverage requires ≥10% of questions with raw samples: attach 15.
        # For the first 10, pick the second option ("B") on a close
        # 6/5/4-style distribution. Pre-fix, this tripped RAW_RESPONSES_MODE
        # on every minority pick; post-fix, sampling noise tolerates it.
        raw_responses: list[dict] = []
        for idx in range(15):
            q = rows[idx]
            selected = "B" if idx < 10 else "A"
            raw_responses.append(
                {
                    "key": q["key"],
                    "raw_text": "A",
                    "selected_option": selected,
                }
            )

        mean_jsd = sum(q["jsd"] for q in rows) / len(rows)
        mean_tau = sum(q["kendall_tau"] for q in rows) / len(rows)
        p_dist = 1.0 - mean_jsd
        p_rank = (1.0 + mean_tau) / 2.0
        composite = 0.5 * p_dist + 0.5 * p_rank

        return {
            "benchmark": "synthbench",
            "version": "0.1.0",
            "timestamp": "2026-04-15T18:25:27+00:00",
            "config": {
                "dataset": dataset,
                "provider": "openrouter/anthropic/claude-haiku-4-5",
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
                "n_questions": len(rows),
            },
            "per_question": rows,
            "raw_responses": raw_responses,
            "reproducibility": {
                "seed": 42,
                "model_revision_hash": "sha256:deadbeef",
                "prompt_template_hash": "sha256:cafef00d",
                "framework_version": "0.1.0",
                "submitted_at": "2026-04-15T18:25:27+00:00",
            },
        }

    def test_strict_tier3_accepts_haiku_shaped_submission(self):
        submission = self._haiku_like_submission()
        report = validate_submission(submission, tier3=True)
        blocked = {
            "PARSE_SUSPICIOUS",
            "ANOMALY_NO_REFUSAL",
            "HOLDOUT_DIVERGENCE",
            "RAW_RESPONSES_MODE",
        }
        fired = {i.code for i in report.issues} & blocked
        assert fired == set(), (
            "sb-a613 regression: the following Tier-3 codes falsely fired on a "
            f"legitimate haiku-shaped submission: {sorted(fired)}\n"
            + "\n".join(i.format() for i in report.issues if i.code in blocked)
        )
        # Under --strict, any warning fails the run — make sure we're clean.
        # Permit only advisory codes that reflect fixture simplifications.
        allowed = {"RAW_RESPONSES_LENGTH_SHORT"}
        unexpected = [i for i in report.warnings if i.code not in allowed]
        assert unexpected == [], "\n".join(i.format() for i in unexpected)
        assert report.ok


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
