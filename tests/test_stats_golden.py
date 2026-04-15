"""Golden tests for vendored stats.py — values must match synthpanel exactly."""

from __future__ import annotations

import pytest

from synthbench.stats import (
    bootstrap_ci,
    chi_squared_test,
    krippendorff_alpha,
)


class TestKrippendorffGolden:
    """4-rater 12-item nominal example with missing data.

    Verified against krippendorff 0.8.1 reference package: alpha = 0.871.
    Data matches synthpanel's test_stats.py exactly.
    """

    RELIABILITY_DATA = [
        [None, None, None, None, None, 3, 4, 1, 2, 1, 1, 3],
        [1, None, 2, 1, 3, 3, 4, 3, None, None, None, None],
        [None, None, 2, 1, 3, 3, 4, 2, 2, 1, 1, 3],
        [1, None, 2, 1, 3, 3, 4, 2, 2, 1, 1, 3],
    ]

    def test_alpha_value(self):
        result = krippendorff_alpha(
            self.RELIABILITY_DATA, level_of_measurement="nominal"
        )
        assert result.alpha == pytest.approx(0.871, abs=0.01)

    def test_metadata(self):
        result = krippendorff_alpha(
            self.RELIABILITY_DATA, level_of_measurement="nominal"
        )
        assert result.n_raters == 4
        assert result.n_items == 12
        assert result.level == "nominal"

    def test_interpretation_strong(self):
        result = krippendorff_alpha(
            self.RELIABILITY_DATA, level_of_measurement="nominal"
        )
        assert (
            "Strong" in result.interpretation
            or "reliable" in result.interpretation.lower()
        )


class TestBootstrapCIGolden:
    """Known data [2, 4, 6, 8, 10] with mean statistic.

    True mean = 6.0. The 95% CI must contain 6.0.
    """

    DATA = [2, 4, 6, 8, 10]

    @staticmethod
    def mean_fn(data: list) -> float:
        return sum(data) / len(data)

    def test_ci_contains_true_mean(self):
        result = bootstrap_ci(
            self.DATA,
            self.mean_fn,
            confidence=0.95,
            n_resamples=5000,
            seed=42,
        )
        assert result.ci_lower <= 6.0 <= result.ci_upper

    def test_point_estimate(self):
        result = bootstrap_ci(
            self.DATA,
            self.mean_fn,
            confidence=0.95,
            n_resamples=5000,
            seed=42,
        )
        assert result.estimate == pytest.approx(6.0)

    def test_confidence_level(self):
        result = bootstrap_ci(
            self.DATA,
            self.mean_fn,
            confidence=0.95,
            n_resamples=5000,
            seed=42,
        )
        assert result.confidence == 0.95
        assert result.n_resamples == 5000
        assert result.method == "BCa"


class TestChiSquaredGolden:
    """Hand-computed chi-squared example.

    Observed: A=30, B=20, C=50 (total=100)
    Expected (uniform): A=33.33, B=33.33, C=33.33
    chi2 = (30-33.33)^2/33.33 + (20-33.33)^2/33.33 + (50-33.33)^2/33.33
         = 0.333 + 5.333 + 8.333
         = ~14.0 (with uniform expected from total=100, each 33.33)
    df = 2

    With explicit expected={A:33.3, B:33.3, C:33.3}:
    chi2 = (30-33.3)^2/33.3 + (20-33.3)^2/33.3 + (50-33.3)^2/33.3
         = 0.327 + 5.315 + 8.378
         = ~14.02
    """

    def test_chi2_uniform_expected(self):
        observed = {"A": 30, "B": 20, "C": 50}
        result = chi_squared_test(observed)
        # Uniform expected = 100/3 = 33.333...
        # chi2 = (30-33.33)^2/33.33 + (20-33.33)^2/33.33 + (50-33.33)^2/33.33
        assert result.statistic == pytest.approx(14.0, abs=0.1)
        assert result.df == 2

    def test_chi2_explicit_expected(self):
        observed = {"A": 30, "B": 20, "C": 50}
        expected = {"A": 33.3, "B": 33.3, "C": 33.3}
        result = chi_squared_test(observed, expected)
        # chi2 = (30-33.3)^2/33.3 + (20-33.3)^2/33.3 + (50-33.3)^2/33.3
        #      = 0.327 + 5.315 + 8.378 = ~14.02
        assert result.statistic == pytest.approx(14.0, abs=0.5)
        assert result.df == 2

    def test_p_value_significant(self):
        observed = {"A": 30, "B": 20, "C": 50}
        result = chi_squared_test(observed)
        # chi2 ~14 with df=2 is highly significant
        assert result.p_value < 0.01

    def test_cramers_v_positive(self):
        observed = {"A": 30, "B": 20, "C": 50}
        result = chi_squared_test(observed)
        assert result.cramers_v > 0
