"""Tests for the deterministic 80/20 private holdout split."""

from __future__ import annotations

import random
import string

import pytest

from synthbench import private_holdout as ph
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


class TestSaltRotation:
    """Salt-based rotation: bead sb-ssld.

    The hash must include the active salt so a quarterly rotation shuffles
    the partition, forces a cheater's cached answer key to go stale, and
    still leaves a one-cycle backward-compat path for historical scoring.
    """

    def test_module_exposes_salt_constants(self):
        # Both constants must exist so callers can pass them explicitly
        # for old-salt re-scoring. The default salt may be None
        # (pre-rotation) or a string (post-rotation).
        assert hasattr(ph, "HOLDOUT_SALT")
        assert hasattr(ph, "HOLDOUT_SALT_PREVIOUS")
        assert ph.HOLDOUT_SALT is None or isinstance(ph.HOLDOUT_SALT, str)
        assert ph.HOLDOUT_SALT_PREVIOUS is None or isinstance(
            ph.HOLDOUT_SALT_PREVIOUS, str
        )

    def test_explicit_none_salt_matches_legacy_partition(self):
        # The legacy unsalted scheme must remain reachable via salt=None
        # so one-cycle old-salt re-scoring of pre-rotation submissions
        # works after the first rotation lands.
        keys = _random_keys(500, seed=7)
        legacy = {k: is_private_holdout("opinionsqa", k, salt=None) for k in keys}
        # Stable across invocations — sanity check determinism of the
        # explicit-None path independent of the active salt.
        again = {k: is_private_holdout("opinionsqa", k, salt=None) for k in keys}
        assert legacy == again

    def test_different_salts_shuffle_the_partition(self):
        # The whole point of rotation: two different salts must assign a
        # meaningfully different set of keys to the private bucket.
        # Under independent 80/20 partitions two salts agree on a given
        # key with probability 0.68, so on 500 keys we expect ~160
        # disagreements. Threshold at 50 is well below the noise floor.
        keys = _random_keys(500, seed=11)
        q3 = [is_private_holdout("opinionsqa", k, salt="2026Q3") for k in keys]
        q4 = [is_private_holdout("opinionsqa", k, salt="2026Q4") for k in keys]
        disagreements = sum(1 for a, b in zip(q3, q4) if a != b)
        assert disagreements > 50
        # Also: salted != unsalted for many keys.
        legacy = [is_private_holdout("opinionsqa", k, salt=None) for k in keys]
        assert sum(1 for a, b in zip(q3, legacy) if a != b) > 50

    def test_same_salt_same_partition(self):
        # Determinism property under an explicit salt — a quarterly
        # rotation must keep the partition stable for the duration of
        # the quarter.
        keys = _random_keys(200, seed=13)
        first = [is_private_holdout("opinionsqa", k, salt="2026Q3") for k in keys]
        second = [is_private_holdout("opinionsqa", k, salt="2026Q3") for k in keys]
        assert first == second

    def test_salted_split_preserves_ratio(self):
        # Salting must not change the 80/20 ratio — if it did, we'd
        # silently move statistical power between public and private on
        # every rotation.
        keys = _random_keys(5000, seed=17)
        n_private = sum(
            is_private_holdout("opinionsqa", k, salt="2026Q3") for k in keys
        )
        ratio = n_private / len(keys)
        expected = HOLDOUT_FRACTION / HOLDOUT_MOD
        assert abs(ratio - expected) < 0.03

    def test_salt_is_prefixed_not_appended(self):
        # Regression guard: the salt goes in front, so a key that happens
        # to equal a would-be concatenation collision can't masquerade as
        # an unsalted input. Probe a handful of concrete keys.
        # Legacy hash is sha256("base:key"); salted hash is
        # sha256("salt:base:key"). If these collided the partition would
        # be identical — fail fast.
        legacy = [
            is_private_holdout("opinionsqa", f"K{i}", salt=None) for i in range(200)
        ]
        salted = [
            is_private_holdout("opinionsqa", f"K{i}", salt="2026Q3") for i in range(200)
        ]
        assert legacy != salted

    def test_holdout_keys_threads_salt(self):
        keys = _random_keys(200, seed=19)
        set_a = holdout_keys("opinionsqa", keys, salt="2026Q3")
        set_b = holdout_keys("opinionsqa", keys, salt="2026Q4")
        # Both subsets are 20%-ish; they should overlap ~56% (0.2*0.2 +
        # 0.8*0.8 for the "both private" intersection is 0.04 → expected
        # |A ∩ B| ≈ 0.04 * 200 = 8 with both at 20%). Strict assertion
        # is that at least one key moves in and at least one moves out.
        assert set_a != set_b
        assert set_a - set_b
        assert set_b - set_a

    def test_split_keys_threads_salt(self):
        keys = _random_keys(200, seed=23)
        pub_a, priv_a = split_keys("opinionsqa", keys, salt="2026Q3")
        pub_b, priv_b = split_keys("opinionsqa", keys, salt="2026Q4")
        # Partition remains exhaustive under every salt.
        assert set(pub_a) | set(priv_a) == set(keys)
        assert set(pub_b) | set(priv_b) == set(keys)
        # Different salts rearrange the buckets.
        assert set(priv_a) != set(priv_b)

    def test_compute_split_sps_threads_salt(self):
        # If salt weren't propagated, the SPS split would silently score
        # under the active salt regardless of what the caller asked for —
        # masking rotation bugs. Construct rows that are private under
        # one salt and public under another, and assert that the counts
        # flip when we change the salt argument.
        keys = _random_keys(400, seed=29)
        rows = [{"key": k, "jsd": 0.1, "kendall_tau": 0.6} for k in keys]
        out_a = compute_split_sps("opinionsqa", rows, salt="2026Q3")
        out_b = compute_split_sps("opinionsqa", rows, salt="2026Q4")
        assert (
            out_a["n_private"] != out_b["n_private"]
            or out_a["n_public"] != out_b["n_public"]
        )
        # Total coverage unchanged — every row lands in exactly one bucket.
        assert out_a["n_public"] + out_a["n_private"] == len(rows)
        assert out_b["n_public"] + out_b["n_private"] == len(rows)

    def test_env_var_override_resolves_to_salt_string(self, monkeypatch):
        # The acceptance criterion says the module accepts HOLDOUT_SALT
        # as env OR constant. Probe the env-reading helper directly so
        # we don't have to reload the module (reload replaces the
        # sentinel used to mean "use the active salt", which would
        # leak across test files).
        monkeypatch.setenv("SYNTHBENCH_HOLDOUT_SALT", "2026Q3")
        assert ph._resolve_env_salt() == "2026Q3"

    def test_empty_env_var_resolves_to_legacy(self, monkeypatch):
        # Rollback knob: SYNTHBENCH_HOLDOUT_SALT="" must yield the
        # pre-rotation unsalted hash, not salt="" which would be a
        # distinct partition.
        monkeypatch.setenv("SYNTHBENCH_HOLDOUT_SALT", "")
        assert ph._resolve_env_salt() is None

    def test_unset_env_var_resolves_to_legacy(self, monkeypatch):
        monkeypatch.delenv("SYNTHBENCH_HOLDOUT_SALT", raising=False)
        assert ph._resolve_env_salt() is None

    def test_active_salt_matches_module_constant(self):
        # When the caller omits ``salt=``, the helper uses
        # ``HOLDOUT_SALT`` — verify by computing both branches side by
        # side and asserting they match on a 200-key probe. (This is
        # the no-reload way to validate "env/constant drives the hash".)
        keys = _random_keys(200, seed=41)
        default = [is_private_holdout("opinionsqa", k) for k in keys]
        explicit = [
            is_private_holdout("opinionsqa", k, salt=ph.HOLDOUT_SALT) for k in keys
        ]
        assert default == explicit

    def test_disabled_dataset_ignores_salt(self):
        # Non-holdout datasets must never classify as private regardless
        # of salt — otherwise a rotation could silently start suppressing
        # data on a dataset whose license doesn't require it.
        for k in _random_keys(200, seed=37):
            assert is_private_holdout("pewtech", k, salt="2026Q3") is False
            assert is_private_holdout("pewtech", k, salt=None) is False
