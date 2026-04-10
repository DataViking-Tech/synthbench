"""Tests for SynthBench metrics."""

from __future__ import annotations

import pytest

from synthbench.metrics.distributional import jensen_shannon_divergence
from synthbench.metrics.ranking import kendall_tau_b
from synthbench.metrics.composite import (
    parity_score,
    synthbench_parity_score,
    SPS_METRICS,
)
from synthbench.metrics.subgroup import subgroup_consistency
from synthbench.metrics.refusal import (
    refusal_calibration,
    detect_refusal,
    extract_human_refusal_rate,
    refusal_rate,
    p_refuse,
)
from synthbench.metrics.subgroup import p_sub
from synthbench.metrics.conditioning import conditioning_fidelity


class TestJensenShannonDivergence:
    def test_identical_distributions(self):
        p = {"A": 0.5, "B": 0.3, "C": 0.2}
        assert jensen_shannon_divergence(p, p) == pytest.approx(0.0, abs=1e-10)

    def test_completely_different(self):
        p = {"A": 1.0, "B": 0.0}
        q = {"A": 0.0, "B": 1.0}
        jsd = jensen_shannon_divergence(p, q)
        assert jsd == pytest.approx(1.0, abs=1e-6)

    def test_symmetric(self):
        p = {"A": 0.7, "B": 0.2, "C": 0.1}
        q = {"A": 0.3, "B": 0.4, "C": 0.3}
        assert jensen_shannon_divergence(p, q) == pytest.approx(
            jensen_shannon_divergence(q, p), abs=1e-10
        )

    def test_range_zero_to_one(self):
        p = {"A": 0.6, "B": 0.4}
        q = {"A": 0.4, "B": 0.6}
        jsd = jensen_shannon_divergence(p, q)
        assert 0.0 <= jsd <= 1.0

    def test_missing_keys_handled(self):
        p = {"A": 0.5, "B": 0.5}
        q = {"A": 0.5, "C": 0.5}
        jsd = jensen_shannon_divergence(p, q)
        assert 0.0 < jsd <= 1.0

    def test_empty_distribution_returns_one(self):
        p = {"A": 0.5, "B": 0.5}
        q = {"A": 0.0, "B": 0.0}
        assert jensen_shannon_divergence(p, q) == 1.0

    def test_close_distributions_low_jsd(self):
        p = {"A": 0.50, "B": 0.30, "C": 0.20}
        q = {"A": 0.48, "B": 0.32, "C": 0.20}
        jsd = jensen_shannon_divergence(p, q)
        assert jsd < 0.01  # Very similar distributions


class TestKendallTauB:
    def test_identical_ranking(self):
        p = {"A": 0.5, "B": 0.3, "C": 0.2}
        assert kendall_tau_b(p, p) == pytest.approx(1.0, abs=1e-10)

    def test_reversed_ranking(self):
        p = {"A": 0.5, "B": 0.3, "C": 0.2}
        q = {"A": 0.2, "B": 0.3, "C": 0.5}
        tau = kendall_tau_b(p, q)
        assert tau == pytest.approx(-1.0, abs=1e-10)

    def test_range(self):
        p = {"A": 0.4, "B": 0.3, "C": 0.2, "D": 0.1}
        q = {"A": 0.3, "B": 0.4, "C": 0.1, "D": 0.2}
        tau = kendall_tau_b(p, q)
        assert -1.0 <= tau <= 1.0

    def test_single_option_returns_zero(self):
        p = {"A": 1.0}
        q = {"A": 1.0}
        assert kendall_tau_b(p, q) == 0.0

    def test_two_options_same_order(self):
        p = {"A": 0.6, "B": 0.4}
        q = {"A": 0.7, "B": 0.3}
        assert kendall_tau_b(p, q) == pytest.approx(1.0, abs=1e-10)

    def test_two_options_reversed(self):
        p = {"A": 0.6, "B": 0.4}
        q = {"A": 0.4, "B": 0.6}
        assert kendall_tau_b(p, q) == pytest.approx(-1.0, abs=1e-10)


class TestParityScore:
    def test_perfect_parity(self):
        assert parity_score(jsd=0.0, tau=1.0) == pytest.approx(1.0)

    def test_worst_parity(self):
        assert parity_score(jsd=1.0, tau=-1.0) == pytest.approx(0.0)

    def test_middle_ground(self):
        score = parity_score(jsd=0.5, tau=0.0)
        assert score == pytest.approx(0.5)

    def test_custom_weights(self):
        score = parity_score(jsd=0.0, tau=-1.0, jsd_weight=1.0, tau_weight=0.0)
        assert score == pytest.approx(1.0)  # JSD perfect, tau ignored

    def test_range(self):
        import random

        rng = random.Random(42)
        for _ in range(100):
            jsd = rng.random()
            tau = rng.uniform(-1, 1)
            score = parity_score(jsd, tau)
            assert 0.0 <= score <= 1.0


class TestSubgroupConsistency:
    def test_perfect_consistency(self):
        scores = {"A": 0.8, "B": 0.8, "C": 0.8}
        assert subgroup_consistency(scores) == pytest.approx(1.0)

    def test_high_variance_low_score(self):
        scores = {"A": 0.9, "B": 0.1}
        result = subgroup_consistency(scores)
        assert result < 0.5

    def test_moderate_variance(self):
        scores = {"A": 0.80, "B": 0.82, "C": 0.78, "D": 0.81}
        result = subgroup_consistency(scores)
        assert result > 0.95  # Very consistent

    def test_single_group_returns_one(self):
        assert subgroup_consistency({"A": 0.5}) == 1.0

    def test_empty_returns_one(self):
        assert subgroup_consistency({}) == 1.0

    def test_all_zero_returns_zero(self):
        scores = {"A": 0.0, "B": 0.0, "C": 0.0}
        assert subgroup_consistency(scores) == 0.0

    def test_range_zero_to_one(self):
        import random

        rng = random.Random(42)
        for _ in range(100):
            n = rng.randint(2, 10)
            scores = {str(i): rng.random() for i in range(n)}
            result = subgroup_consistency(scores)
            assert 0.0 <= result <= 1.0


class TestRefusalCalibration:
    def test_perfect_calibration(self):
        prov = [0.1, 0.2, 0.0]
        hum = [0.1, 0.2, 0.0]
        assert refusal_calibration(prov, hum) == pytest.approx(1.0)

    def test_worst_calibration(self):
        prov = [1.0, 1.0]
        hum = [0.0, 0.0]
        assert refusal_calibration(prov, hum) == pytest.approx(0.0)

    def test_partial_mismatch(self):
        prov = [0.1, 0.3]
        hum = [0.0, 0.1]
        result = refusal_calibration(prov, hum)
        # mean(|0.1-0.0|, |0.3-0.1|) = mean(0.1, 0.2) = 0.15
        assert result == pytest.approx(0.85)

    def test_empty_returns_one(self):
        assert refusal_calibration([], []) == 1.0

    def test_range_zero_to_one(self):
        import random

        rng = random.Random(42)
        for _ in range(100):
            n = rng.randint(1, 20)
            prov = [rng.random() for _ in range(n)]
            hum = [rng.random() for _ in range(n)]
            result = refusal_calibration(prov, hum)
            assert 0.0 <= result <= 1.0


class TestDetectRefusal:
    def test_detects_i_cannot(self):
        assert detect_refusal("I cannot answer this question.")

    def test_detects_as_an_ai(self):
        assert detect_refusal("As an AI language model, I don't have opinions.")

    def test_normal_response_not_refusal(self):
        assert not detect_refusal("I think option A is correct.")

    def test_empty_string_not_refusal(self):
        assert not detect_refusal("")


class TestExtractHumanRefusalRate:
    def test_no_refusal_option(self):
        dist = {"Yes": 0.6, "No": 0.4}
        assert extract_human_refusal_rate(dist) == 0.0

    def test_explicit_refused(self):
        dist = {"Yes": 0.5, "No": 0.4, "Refused": 0.1}
        assert extract_human_refusal_rate(dist) == pytest.approx(0.1)

    def test_dont_know_refused(self):
        dist = {"A": 0.6, "B": 0.3, "Don't know/Refused": 0.1}
        assert extract_human_refusal_rate(dist) == pytest.approx(0.1)


class TestConditioningFidelity:
    """Test JSD-based conditioning_fidelity(conditioned, unconditioned, human)."""

    def test_identical_distributions_zero(self):
        # Conditioned == unconditioned: no improvement
        dist = {"A": 0.5, "B": 0.3, "C": 0.2}
        human = {"A": 0.4, "B": 0.4, "C": 0.2}
        assert conditioning_fidelity(dist, dist, human) == pytest.approx(0.0)

    def test_conditioned_closer_to_human(self):
        human = {"A": 0.5, "B": 0.3, "C": 0.2}
        conditioned = {"A": 0.48, "B": 0.32, "C": 0.20}  # Very close to human
        unconditioned = {"A": 0.33, "B": 0.33, "C": 0.34}  # Uniform-ish
        result = conditioning_fidelity(conditioned, unconditioned, human)
        assert result > 0.0  # Should show positive improvement

    def test_conditioned_farther_returns_zero(self):
        human = {"A": 0.5, "B": 0.3, "C": 0.2}
        conditioned = {"A": 0.33, "B": 0.33, "C": 0.34}  # Farther from human
        unconditioned = {"A": 0.48, "B": 0.32, "C": 0.20}  # Closer to human
        result = conditioning_fidelity(conditioned, unconditioned, human)
        assert result == pytest.approx(0.0)

    def test_perfect_conditioned_match(self):
        human = {"A": 0.5, "B": 0.5}
        conditioned = {"A": 0.5, "B": 0.5}  # Perfect match
        unconditioned = {"A": 1.0, "B": 0.0}  # Maximally different
        result = conditioning_fidelity(conditioned, unconditioned, human)
        # JSD(unconditioned, human) should be high, JSD(conditioned, human) = 0
        assert result > 0.0
        assert result == pytest.approx(
            jensen_shannon_divergence(unconditioned, human), abs=1e-10
        )

    def test_range_zero_to_one(self):
        import random

        rng = random.Random(42)
        for _ in range(50):
            keys = ["A", "B", "C"]

            def _rand_dist():
                vals = [rng.random() for _ in keys]
                total = sum(vals)
                return {k: v / total for k, v in zip(keys, vals)}

            result = conditioning_fidelity(_rand_dist(), _rand_dist(), _rand_dist())
            assert 0.0 <= result <= 1.0


class TestSynthBenchParityScore:
    def test_all_five_metrics(self):
        metrics = {
            "p_dist": 0.8,
            "p_rank": 0.7,
            "p_cond": 0.6,
            "p_sub": 0.75,
            "p_refuse": 0.9,
        }
        expected = (0.8 + 0.7 + 0.6 + 0.75 + 0.9) / 5
        assert synthbench_parity_score(metrics) == pytest.approx(expected)

    def test_three_metrics_reweighted(self):
        metrics = {"p_dist": 0.8, "p_rank": 0.7, "p_refuse": 0.9}
        expected = (0.8 + 0.7 + 0.9) / 3
        assert synthbench_parity_score(metrics) == pytest.approx(expected)

    def test_empty_returns_zero(self):
        assert synthbench_parity_score({}) == 0.0

    def test_unknown_keys_ignored(self):
        metrics = {"p_dist": 0.8, "unknown": 0.5}
        assert synthbench_parity_score(metrics) == pytest.approx(0.8)

    def test_custom_weights(self):
        metrics = {"p_dist": 0.8, "p_rank": 0.6}
        weights = {"p_dist": 0.7, "p_rank": 0.3}
        expected = (0.7 * 0.8 + 0.3 * 0.6) / (0.7 + 0.3)
        assert synthbench_parity_score(metrics, weights) == pytest.approx(expected)

    def test_sps_metrics_constant(self):
        assert len(SPS_METRICS) == 5
        assert "p_dist" in SPS_METRICS
        assert "p_rank" in SPS_METRICS
        assert "p_cond" in SPS_METRICS
        assert "p_sub" in SPS_METRICS
        assert "p_refuse" in SPS_METRICS


class TestRefusalRate:
    def test_explicit_refused_option(self):
        dist = {"Yes": 0.5, "No": 0.4, "Refused": 0.1}
        assert refusal_rate(dist) == pytest.approx(0.1)

    def test_no_refused_option(self):
        dist = {"Yes": 0.6, "No": 0.4}
        assert refusal_rate(dist) == 0.0

    def test_high_refusal(self):
        dist = {"Yes": 0.05, "No": 0.05, "Refused": 0.9}
        assert refusal_rate(dist) == pytest.approx(0.9)


class TestPRefuse:
    def test_perfect_match(self):
        model = {"Yes": 0.5, "No": 0.4, "Refused": 0.1}
        human = {"Yes": 0.5, "No": 0.4, "Refused": 0.1}
        assert p_refuse(model, human) == pytest.approx(1.0)

    def test_no_refused_option_returns_none(self):
        model = {"Yes": 0.6, "No": 0.4}
        human = {"Yes": 0.5, "No": 0.5}
        assert p_refuse(model, human) is None

    def test_model_over_refuses(self):
        # Model refuses 90%, humans refuse 0.37% — Haiku LOCALELECT_W29 scenario
        model = {"Yes": 0.05, "No": 0.05, "Refused": 0.90}
        human = {"Yes": 0.50, "No": 0.4963, "Refused": 0.0037}
        result = p_refuse(model, human)
        # 1.0 - |0.90 - 0.0037| = 1.0 - 0.8963 = 0.1037
        assert result == pytest.approx(0.1037, abs=1e-4)
        assert result < 0.15  # Captures the over-refusal problem

    def test_haiku_localelect_w29_over_refusal(self):
        """Haiku selected 'Refused' on LOCALELECT_W29 90% vs 0.37% human rate.

        Raw LLMs over-refuse on politically adjacent questions. P_refuse
        captures this signal: the score should be very low (poor calibration).
        """
        model_dist = {
            "A great deal": 0.02,
            "Some": 0.03,
            "Not too much": 0.03,
            "Not at all": 0.02,
            "Refused": 0.90,
        }
        human_dist = {
            "A great deal": 0.30,
            "Some": 0.35,
            "Not too much": 0.20,
            "Not at all": 0.1163,
            "Refused": 0.0037,
        }
        score = p_refuse(model_dist, human_dist)
        assert score is not None
        # Score should be very low — massive refusal miscalibration
        assert score < 0.15
        # Exact: 1 - |0.90 - 0.0037| = 0.1037
        assert score == pytest.approx(1.0 - abs(0.90 - 0.0037), abs=1e-4)

    def test_human_has_refused_model_does_not(self):
        model = {"Yes": 0.6, "No": 0.4}
        human = {"Yes": 0.5, "No": 0.45, "Refused": 0.05}
        result = p_refuse(model, human)
        assert result is not None
        # 1.0 - |0.0 - 0.05| = 0.95
        assert result == pytest.approx(0.95)


class TestPSub:
    def test_perfect_consistency(self):
        assert p_sub([0.8, 0.8, 0.8]) == pytest.approx(1.0)

    def test_high_variance(self):
        result = p_sub([0.9, 0.1])
        assert result < 0.5

    def test_single_score_returns_one(self):
        assert p_sub([0.5]) == 1.0

    def test_empty_returns_one(self):
        assert p_sub([]) == 1.0

    def test_matches_subgroup_consistency(self):
        scores = [0.8, 0.82, 0.78, 0.81]
        named = {str(i): v for i, v in enumerate(scores)}
        assert p_sub(scores) == pytest.approx(subgroup_consistency(named))
