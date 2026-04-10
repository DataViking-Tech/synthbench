"""Tests for bootstrap CI computation, paired significance tests, and question set hashing."""

from __future__ import annotations

import pytest

from synthbench.stats import bootstrap_ci, paired_bootstrap_test, question_set_hash


def _mean(data: list[float]) -> float:
    return sum(data) / len(data)


def _median(data: list[float]) -> float:
    s = sorted(data)
    n = len(s)
    mid = n // 2
    return (s[mid - 1] + s[mid]) / 2.0 if n % 2 == 0 else s[mid]


class TestBootstrapCI:
    def test_constant_data_has_zero_width_ci(self):
        data = [0.5] * 50
        r = bootstrap_ci(data, _mean, seed=42)
        assert r.estimate == pytest.approx(0.5)
        assert r.ci_lower == pytest.approx(0.5)
        assert r.ci_upper == pytest.approx(0.5)

    def test_point_estimate_is_mean(self):
        data = [0.1, 0.2, 0.3, 0.4, 0.5]
        r = bootstrap_ci(data, _mean, seed=42)
        assert r.estimate == pytest.approx(0.3, abs=1e-10)

    def test_ci_contains_point_estimate(self):
        data = [0.2, 0.4, 0.6, 0.8, 0.3, 0.5, 0.7]
        r = bootstrap_ci(data, _mean, seed=42)
        assert r.ci_lower <= r.estimate <= r.ci_upper

    def test_ci_widens_with_more_variance(self):
        tight_data = [0.50, 0.51, 0.49, 0.50, 0.51, 0.49, 0.50, 0.50] * 5
        wide_data = [0.1, 0.9, 0.2, 0.8, 0.3, 0.7, 0.4, 0.6] * 5
        t = bootstrap_ci(tight_data, _mean, seed=42)
        w = bootstrap_ci(wide_data, _mean, seed=42)
        tight_width = t.ci_upper - t.ci_lower
        wide_width = w.ci_upper - w.ci_lower
        assert wide_width > tight_width

    def test_reproducible_with_seed(self):
        data = [0.1, 0.3, 0.5, 0.7, 0.9] * 10
        r1 = bootstrap_ci(data, _mean, seed=123)
        r2 = bootstrap_ci(data, _mean, seed=123)
        assert r1.ci_lower == r2.ci_lower
        assert r1.ci_upper == r2.ci_upper

    def test_too_few_data_raises(self):
        with pytest.raises(ValueError, match="at least 5"):
            bootstrap_ci([0.5, 0.6, 0.7, 0.8], _mean, seed=42)

    def test_median_statistic(self):
        data = [0.1, 0.2, 0.3, 0.4, 0.5]
        r = bootstrap_ci(data, _median, seed=42)
        assert r.estimate == pytest.approx(0.3)
        assert r.ci_lower <= r.estimate <= r.ci_upper

    def test_ci_bounds_reasonable_for_known_distribution(self):
        """For a large sample from [0, 1], the 95% CI for the mean should be tight around 0.5."""
        import random

        rng = random.Random(42)
        data = [rng.random() for _ in range(200)]
        r = bootstrap_ci(data, _mean, seed=42)
        assert 0.45 < r.estimate < 0.55
        assert 0.40 < r.ci_lower
        assert r.ci_upper < 0.60

    def test_result_has_metadata(self):
        data = [0.1, 0.2, 0.3, 0.4, 0.5]
        r = bootstrap_ci(data, _mean, seed=42)
        assert r.confidence == 0.95
        assert r.n_resamples == 2000
        assert r.method == "BCa"


class TestPairedBootstrapTest:
    def test_identical_scores_not_significant(self):
        scores = [0.5, 0.6, 0.7, 0.8, 0.9] * 10
        delta, p_val, verdict = paired_bootstrap_test(scores, scores, seed=42)
        assert delta == pytest.approx(0.0)
        assert p_val > 0.05
        assert verdict == "not significant"

    def test_clearly_different_scores_significant(self):
        a = [0.9, 0.85, 0.88, 0.92, 0.87] * 10
        b = [0.3, 0.35, 0.32, 0.28, 0.33] * 10
        delta, p_val, verdict = paired_bootstrap_test(a, b, seed=42)
        assert delta > 0.4
        assert p_val < 0.05
        assert verdict == "significant"

    def test_unequal_length_raises(self):
        with pytest.raises(ValueError, match="equal length"):
            paired_bootstrap_test([0.5, 0.6], [0.5], seed=42)

    def test_empty_scores(self):
        delta, p_val, verdict = paired_bootstrap_test([], [])
        assert delta == 0.0
        assert p_val == 1.0
        assert verdict == "not significant"

    def test_reproducible_with_seed(self):
        a = [0.5, 0.6, 0.7, 0.8] * 10
        b = [0.4, 0.5, 0.6, 0.7] * 10
        r1 = paired_bootstrap_test(a, b, seed=99)
        r2 = paired_bootstrap_test(a, b, seed=99)
        assert r1 == r2

    def test_delta_sign(self):
        a = [0.9, 0.8, 0.85] * 10
        b = [0.5, 0.4, 0.45] * 10
        delta, _, _ = paired_bootstrap_test(a, b, seed=42)
        assert delta > 0  # a is better than b

        delta2, _, _ = paired_bootstrap_test(b, a, seed=42)
        assert delta2 < 0  # b is worse than a


class TestQuestionSetHash:
    def test_deterministic(self):
        keys = ["Q1", "Q2", "Q3"]
        assert question_set_hash(keys) == question_set_hash(keys)

    def test_order_independent(self):
        """Hash should be the same regardless of input order (we sort internally)."""
        h1 = question_set_hash(["Q3", "Q1", "Q2"])
        h2 = question_set_hash(["Q1", "Q2", "Q3"])
        assert h1 == h2

    def test_different_keys_different_hash(self):
        h1 = question_set_hash(["Q1", "Q2"])
        h2 = question_set_hash(["Q1", "Q3"])
        assert h1 != h2

    def test_returns_hex_string(self):
        h = question_set_hash(["Q1"])
        assert len(h) == 64  # SHA256 hex digest
        assert all(c in "0123456789abcdef" for c in h)

    def test_empty_keys(self):
        h = question_set_hash([])
        assert len(h) == 64
