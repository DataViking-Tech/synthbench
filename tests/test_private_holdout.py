"""Tests for the deterministic 80/20 private holdout split."""

from __future__ import annotations

import random
import string

import pytest

from synthbench.private_holdout import (
    HOLDOUT_ENABLED_DATASETS,
    HOLDOUT_FRACTION,
    HOLDOUT_MOD,
    SPS_DIVERGENCE_THRESHOLD,
    compute_split_sps,
    holdout_keys,
    is_holdout_enabled,
    is_private_holdout,
    split_keys,
)


def _random_keys(n: int, seed: int = 0) -> list[str]:
    rng = random.Random(seed)
    return [
        "".join(rng.choices(string.ascii_letters + string.digits, k=12))
        for _ in range(n)
    ]


class TestDeterminism:
    def test_same_input_same_output(self):
        assert is_private_holdout("opinionsqa", "Q_001") == is_private_holdout(
            "opinionsqa", "Q_001"
        )

    def test_different_dataset_independent_partition(self):
        # The same key must classify independently across datasets —
        # otherwise a leak on one dataset would propagate across all of
        # them. Sample many keys and confirm that disagreement happens
        # (under independent 80/20 partitions, two datasets agree on a
        # given key with probability 0.68, so across 500 keys we expect
        # ~160 disagreements — well above any reasonable lower bound).
        keys = _random_keys(500)
        disagreements = sum(
            1
            for k in keys
            if is_private_holdout("opinionsqa", k)
            != is_private_holdout("globalopinionqa", k)
        )
        assert disagreements > 50

    def test_name_filter_suffix_stripped(self):
        # "gss (2018)" and "gss" should partition identically.
        assert is_private_holdout("gss", "Q1") == is_private_holdout("gss (2018)", "Q1")


class TestEnabledDatasets:
    def test_bead_specifies_eight_datasets(self):
        assert len(HOLDOUT_ENABLED_DATASETS) == 8

    def test_unknown_dataset_returns_false(self):
        # Non-holdout datasets must never be marked holdout — otherwise
        # we'd silently start suppressing data on a dataset whose license
        # doesn't require it.
        for key in _random_keys(200):
            assert is_private_holdout("pewtech", key) is False
            assert is_private_holdout("unregistered_dataset", key) is False

    def test_is_holdout_enabled_matches_membership(self):
        for ds in HOLDOUT_ENABLED_DATASETS:
            assert is_holdout_enabled(ds)
        assert not is_holdout_enabled("pewtech")
        assert not is_holdout_enabled("novel_dataset")


class TestSplitRatio:
    @pytest.mark.parametrize("dataset", sorted(HOLDOUT_ENABLED_DATASETS))
    def test_split_is_close_to_twenty_percent(self, dataset):
        # Sample 5,000 synthetic keys per dataset; the observed ratio should
        # land within ~3% of the nominal 20% target.
        keys = _random_keys(5000, seed=hash(dataset) & 0xFFFFFFFF)
        n_private = sum(is_private_holdout(dataset, k) for k in keys)
        ratio = n_private / len(keys)
        expected = HOLDOUT_FRACTION / HOLDOUT_MOD
        assert abs(ratio - expected) < 0.03, (
            f"{dataset}: {n_private}/5000 = {ratio:.3%}, expected {expected:.1%}"
        )


class TestHelpers:
    def test_holdout_keys_empty_for_disabled_dataset(self):
        assert holdout_keys("pewtech", ["a", "b", "c"]) == set()

    def test_split_keys_returns_all_public_for_disabled_dataset(self):
        pub, priv = split_keys("pewtech", ["a", "b", "c"])
        assert pub == ["a", "b", "c"]
        assert priv == []

    def test_split_keys_partition_exhaustive(self):
        keys = _random_keys(100)
        pub, priv = split_keys("opinionsqa", keys)
        assert set(pub) | set(priv) == set(keys)
        assert set(pub) & set(priv) == set()


class TestComputeSplitSps:
    def _mk_rows(self, n_public: int, n_private: int, *, dataset: str):
        """Build per_question rows from real keys sorted into subsets.

        Uses real hash-derived partition so split logic receives plausible
        inputs; each row carries a jsd/tau consistent with a high-SPS run.
        """
        rows: list[dict] = []
        collected_public = 0
        collected_private = 0
        seed = 1
        while collected_public < n_public or collected_private < n_private:
            for key in _random_keys(1000, seed=seed):
                is_priv = is_private_holdout(dataset, key)
                if is_priv and collected_private < n_private:
                    rows.append({"key": key, "jsd": 0.10, "kendall_tau": 0.60})
                    collected_private += 1
                elif (not is_priv) and collected_public < n_public:
                    rows.append({"key": key, "jsd": 0.10, "kendall_tau": 0.60})
                    collected_public += 1
                if collected_public >= n_public and collected_private >= n_private:
                    break
            seed += 1
        return rows

    def test_returns_none_for_empty_subsets(self):
        out = compute_split_sps("opinionsqa", [])
        assert out["sps_public"] is None
        assert out["sps_private"] is None
        assert out["delta"] is None
        assert out["n_public"] == 0
        assert out["n_private"] == 0
        assert out["flagged"] is False

    def test_uniform_score_gives_matching_sps(self):
        rows = self._mk_rows(80, 20, dataset="opinionsqa")
        out = compute_split_sps("opinionsqa", rows)
        assert out["n_public"] == 80
        assert out["n_private"] == 20
        # jsd=0.10, tau=0.60 → p_dist=0.90, p_rank=0.80 → sps=0.85
        assert abs(out["sps_public"] - 0.85) < 1e-9
        assert abs(out["sps_private"] - 0.85) < 1e-9
        assert out["delta"] == pytest.approx(0.0, abs=1e-9)
        assert out["flagged"] is False

    def test_divergent_submission_is_flagged(self):
        public_rows = self._mk_rows(80, 0, dataset="opinionsqa")
        # High score on public (the cheater "memorized" public distributions)
        for row in public_rows:
            row["jsd"] = 0.02
            row["kendall_tau"] = 0.90
        private_rows = self._mk_rows(0, 20, dataset="opinionsqa")
        # Low score on private (no signal → noise)
        for row in private_rows:
            row["jsd"] = 0.40
            row["kendall_tau"] = 0.10
        out = compute_split_sps("opinionsqa", public_rows + private_rows)
        assert out["delta"] is not None
        assert out["delta"] > SPS_DIVERGENCE_THRESHOLD
        assert out["flagged"] is True

    def test_disabled_dataset_places_everything_public(self):
        rows = [{"key": f"k{i}", "jsd": 0.1, "kendall_tau": 0.6} for i in range(10)]
        out = compute_split_sps("pewtech", rows)
        assert out["n_public"] == 10
        assert out["n_private"] == 0
        assert out["sps_private"] is None
        assert out["flagged"] is False
