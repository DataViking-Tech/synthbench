"""Tests for SynthBench metrics."""

from __future__ import annotations

import pytest

from synthbench.metrics.distributional import jensen_shannon_divergence
from synthbench.metrics.ranking import kendall_tau_b
from synthbench.metrics.composite import parity_score, synthbench_parity_score, SPS_METRICS
from synthbench.metrics.subgroup import subgroup_consistency
from synthbench.metrics.refusal import (
    refusal_calibration,
    detect_refusal,
    extract_human_refusal_rate,
)
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
    def test_perfect_improvement(self):
        cond = {"A": 0.9, "B": 0.8}
        default = {"A": 0.5, "B": 0.4}
        result = conditioning_fidelity(cond, default)
        # mean(0.4, 0.4) = 0.4
        assert result == pytest.approx(0.4)

    def test_no_improvement(self):
        cond = {"A": 0.5, "B": 0.5}
        default = {"A": 0.5, "B": 0.5}
        assert conditioning_fidelity(cond, default) == pytest.approx(0.0)

    def test_conditioning_makes_worse(self):
        cond = {"A": 0.3, "B": 0.4}
        default = {"A": 0.5, "B": 0.6}
        # Floored at 0 per group
        assert conditioning_fidelity(cond, default) == pytest.approx(0.0)

    def test_mixed_improvement(self):
        cond = {"A": 0.9, "B": 0.3}
        default = {"A": 0.5, "B": 0.5}
        # A improves by 0.4, B worsens (floored to 0)
        # mean(0.4, 0.0) = 0.2
        assert conditioning_fidelity(cond, default) == pytest.approx(0.2)

    def test_no_common_groups(self):
        cond = {"A": 0.9}
        default = {"B": 0.5}
        assert conditioning_fidelity(cond, default) == 0.0

    def test_empty_returns_zero(self):
        assert conditioning_fidelity({}, {}) == 0.0


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
