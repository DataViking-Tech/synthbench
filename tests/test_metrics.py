"""Tests for SynthBench metrics."""

from __future__ import annotations

import pytest

from synthbench.metrics.distributional import jensen_shannon_divergence
from synthbench.metrics.ranking import kendall_tau_b
from synthbench.metrics.composite import parity_score


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
