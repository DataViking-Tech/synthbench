"""Validation-pipeline tests for private-holdout enforcement."""

from __future__ import annotations

import random
import string

from synthbench.private_holdout import is_private_holdout
from synthbench.validation import (
    Severity,
    _validate_private_holdout,
    validate_submission,
)


def _find_keys_by_partition(
    dataset: str, n_public: int, n_private: int
) -> tuple[list[str], list[str]]:
    """Build lists of real hash-sorted keys for the given dataset."""
    rng = random.Random(0)
    public: list[str] = []
    private: list[str] = []
    while len(public) < n_public or len(private) < n_private:
        k = "".join(rng.choices(string.ascii_letters + string.digits, k=12))
        if is_private_holdout(dataset, k):
            if len(private) < n_private:
                private.append(k)
        else:
            if len(public) < n_public:
                public.append(k)
    return public, private


def _mk_row(key: str, *, jsd: float = 0.05, tau: float = 0.9) -> dict:
    return {
        "key": key,
        "human_distribution": {"A": 0.6, "B": 0.4},
        "model_distribution": {"A": 0.6, "B": 0.4},
        "jsd": jsd,
        "kendall_tau": tau,
    }


def _mk_submission(dataset: str, rows: list[dict]) -> dict:
    return {
        "benchmark": "synthbench",
        "version": "0.1.0",
        "config": {
            "dataset": dataset,
            "provider": "openrouter/anthropic/claude-haiku-4-5",
        },
        "aggregate": {
            "mean_jsd": 0.05,
            "mean_kendall_tau": 0.9,
            "composite_parity": 0.9,
            "n_questions": len(rows),
        },
        "per_question": rows,
    }


class TestPrivateHoldoutValidator:
    def test_public_only_submission_rejected(self):
        pub_keys, _ = _find_keys_by_partition("opinionsqa", 50, 0)
        rows = [_mk_row(k) for k in pub_keys]
        data = _mk_submission("opinionsqa", rows)
        issues = _validate_private_holdout(data)
        codes = [i.code for i in issues]
        assert "HOLDOUT_MISSING_PRIVATE" in codes
        err = next(i for i in issues if i.code == "HOLDOUT_MISSING_PRIVATE")
        assert err.severity is Severity.ERROR

    def test_full_submission_passes(self):
        pub_keys, priv_keys = _find_keys_by_partition("opinionsqa", 80, 20)
        rows = [_mk_row(k) for k in pub_keys + priv_keys]
        data = _mk_submission("opinionsqa", rows)
        issues = _validate_private_holdout(data)
        assert issues == []

    def test_near_empty_private_subset_rejected(self):
        # Only 1 private row out of 100 — below the 5% expected threshold.
        pub_keys, priv_keys = _find_keys_by_partition("opinionsqa", 99, 1)
        rows = [_mk_row(k) for k in pub_keys + priv_keys]
        data = _mk_submission("opinionsqa", rows)
        issues = _validate_private_holdout(data)
        assert any(i.code == "HOLDOUT_COVERAGE" for i in issues)

    def test_divergent_scores_warn(self):
        pub_keys, priv_keys = _find_keys_by_partition("opinionsqa", 80, 20)
        # High-SPS public rows (jsd=0.02, tau=0.9) + low-SPS private rows (jsd=0.5, tau=-0.2).
        rows = [_mk_row(k, jsd=0.02, tau=0.9) for k in pub_keys] + [
            _mk_row(k, jsd=0.5, tau=-0.2) for k in priv_keys
        ]
        data = _mk_submission("opinionsqa", rows)
        issues = _validate_private_holdout(data)
        assert any(i.code == "HOLDOUT_DIVERGENCE" for i in issues)
        warn = next(i for i in issues if i.code == "HOLDOUT_DIVERGENCE")
        assert warn.severity is Severity.WARNING

    def test_non_holdout_dataset_skipped(self):
        # pewtech isn't in HOLDOUT_ENABLED_DATASETS — validator is a no-op.
        rows = [_mk_row(f"pt_{i}") for i in range(10)]
        data = _mk_submission("pewtech", rows)
        assert _validate_private_holdout(data) == []


class TestValidateSubmissionIntegration:
    """Verify the new validator is wired into validate_submission()."""

    def test_missing_private_surfaces_as_error_in_tier1(self):
        pub_keys, _ = _find_keys_by_partition("opinionsqa", 50, 0)
        rows = [_mk_row(k) for k in pub_keys]
        data = _mk_submission("opinionsqa", rows)
        report = validate_submission(data, tier2=False)
        error_codes = [i.code for i in report.errors]
        assert "HOLDOUT_MISSING_PRIVATE" in error_codes

    def test_balanced_submission_has_no_holdout_errors(self):
        pub_keys, priv_keys = _find_keys_by_partition("opinionsqa", 80, 20)
        rows = [_mk_row(k) for k in pub_keys + priv_keys]
        data = _mk_submission("opinionsqa", rows)
        report = validate_submission(data, tier2=False)
        holdout_codes = [i.code for i in report.issues if i.code.startswith("HOLDOUT_")]
        assert holdout_codes == []
