"""Publish-time holdout enforcement: suppression + split-SPS emission."""

from __future__ import annotations

import json
import random
import string

from synthbench.datasets.policy import policy_for
from synthbench.private_holdout import is_private_holdout
from synthbench.publish import (
    _augment_per_question,
    _build_run_detail,
    publish_questions,
)


def _find_keys_by_partition(
    dataset: str, n_public: int, n_private: int
) -> tuple[list[str], list[str]]:
    """Generate synthetic keys real-sorted into public vs. private subsets."""
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


class TestAugmentPerQuestion:
    def _mk_row(self, key: str) -> dict:
        return {
            "key": key,
            "text": "Test question",
            "human_distribution": {"A": 0.5, "B": 0.5},
            "human_refusal_rate": 0.03,
            "model_distribution": {"A": 0.6, "B": 0.4},
            "jsd": 0.05,
            "kendall_tau": 0.9,
            "parity": 0.9,
        }

    def test_public_row_keeps_human_distribution(self):
        pub_keys, _ = _find_keys_by_partition("opinionsqa", 1, 0)
        rows = [self._mk_row(pub_keys[0])]
        out = _augment_per_question(
            rows, policy=policy_for("opinionsqa"), dataset="opinionsqa"
        )
        # OpinionsQA is now ``gated`` (sb-dek), so human_distribution is
        # preserved on public rows for delivery to authenticated R2 clients.
        # The key assertion here is that the public row does NOT get an
        # is_holdout flag — that's the holdout suppression contract this
        # test guards.
        assert out[0].get("is_holdout") is not True

    def test_private_row_gets_is_holdout_flag(self):
        _, priv_keys = _find_keys_by_partition("opinionsqa", 0, 1)
        rows = [self._mk_row(priv_keys[0])]
        out = _augment_per_question(rows, policy=None, dataset="opinionsqa")
        assert out[0]["is_holdout"] is True
        assert "human_distribution" not in out[0]
        assert "human_refusal_rate" not in out[0]

    def test_private_row_suppressed_even_with_full_policy(self):
        """A full-policy dataset still suppresses human_distribution on
        the private subset. That's the whole point of the holdout split."""

        class FullPolicy:
            suppress_human_distribution = False
            suppress_per_question = False

        _, priv_keys = _find_keys_by_partition("opinionsqa", 0, 1)
        rows = [self._mk_row(priv_keys[0])]
        out = _augment_per_question(rows, policy=FullPolicy(), dataset="opinionsqa")
        assert out[0]["is_holdout"] is True
        assert "human_distribution" not in out[0]

    def test_disabled_dataset_never_flags_holdout(self):
        rows = [self._mk_row("pewtech_key_001")]
        out = _augment_per_question(rows, policy=None, dataset="pewtech")
        assert out[0].get("is_holdout") is not True


class TestRunDetailHoldoutSplit:
    def _mk_result(self, dataset: str, rows: list[dict]) -> dict:
        return {
            "benchmark": "synthbench",
            "version": "0.1.0",
            "timestamp": "2026-04-14T00:00:00Z",
            "config": {
                "dataset": dataset,
                "provider": "openrouter/anthropic/claude-haiku-4-5",
                "n_evaluated": len(rows),
            },
            "scores": {"sps": 0.85, "p_dist": 0.9, "p_rank": 0.8, "p_refuse": 0.9},
            "aggregate": {
                "mean_jsd": 0.1,
                "mean_kendall_tau": 0.6,
                "composite_parity": 0.85,
                "n_questions": len(rows),
            },
            "per_question": rows,
        }

    def test_holdout_dataset_emits_split_block(self):
        pub_keys, priv_keys = _find_keys_by_partition("opinionsqa", 40, 10)
        rows = [
            {
                "key": k,
                "jsd": 0.1,
                "kendall_tau": 0.6,
                "text": "",
                "options": [],
                "model_distribution": {"A": 0.5, "B": 0.5},
            }
            for k in pub_keys
        ] + [
            {
                "key": k,
                "jsd": 0.1,
                "kendall_tau": 0.6,
                "text": "",
                "options": [],
                "model_distribution": {"A": 0.5, "B": 0.5},
            }
            for k in priv_keys
        ]
        result = self._mk_result("opinionsqa", rows)
        from synthbench.leaderboard import provider_framework

        class Parsed:
            framework = provider_framework("openrouter/anthropic/claude-haiku-4-5")
            base_provider = "anthropic"
            model = "claude-haiku-4-5"

        detail = _build_run_detail(
            run_id="r1",
            config_id="c1",
            parsed=Parsed(),
            result=result,
            display_name="Claude Haiku 4.5",
            is_baseline=False,
            is_ensemble=False,
            timestamp="2026-04-14T00:00:00Z",
        )
        assert "holdout_split" in detail
        assert detail["holdout_split"]["n_public"] == 40
        assert detail["holdout_split"]["n_private"] == 10
        assert detail["holdout_split"]["flagged"] is False

    def test_non_holdout_dataset_omits_split_block(self):
        rows = [
            {
                "key": f"k{i}",
                "jsd": 0.1,
                "kendall_tau": 0.6,
                "text": "",
                "options": [],
                "model_distribution": {"A": 0.5, "B": 0.5},
            }
            for i in range(10)
        ]
        result = self._mk_result("pewtech", rows)

        class Parsed:
            framework = "openrouter"
            base_provider = "anthropic"
            model = "claude-haiku-4-5"

        detail = _build_run_detail(
            run_id="r1",
            config_id="c1",
            parsed=Parsed(),
            result=result,
            display_name="Claude Haiku 4.5",
            is_baseline=False,
            is_ensemble=False,
            timestamp="2026-04-14T00:00:00Z",
        )
        assert "holdout_split" not in detail


class TestQuestionPageSuppression:
    def test_private_keys_get_no_question_page(self, tmp_path):
        """Per-question artifacts (site/public/data/question/<dataset>/<key>.json)
        are not emitted for private holdout keys.

        Uses a ``gated`` dataset (subpop) — the post-sb-sj6 ``aggregates_only``
        tier suppresses per-question emission entirely, which would mask the
        holdout-specific suppression this test is meant to verify.
        """
        pub_keys, priv_keys = _find_keys_by_partition("subpop", 3, 2)
        all_keys = pub_keys + priv_keys

        results_dir = tmp_path / "results"
        results_dir.mkdir()
        per_question = [
            {
                "key": k,
                "text": f"Question {k}",
                "options": ["A", "B"],
                "human_distribution": {"A": 0.6, "B": 0.4},
                "model_distribution": {"A": 0.6, "B": 0.4},
                "jsd": 0.05,
                "kendall_tau": 0.9,
                "parity": 0.9,
                "n_samples": 10,
                "model_refusal_rate": 0.01,
                "human_refusal_rate": 0.01,
            }
            for k in all_keys
        ]
        run = {
            "benchmark": "synthbench",
            "version": "0.1.0",
            "timestamp": "2026-04-14T00:00:00Z",
            "config": {
                "dataset": "subpop",
                "provider": "openrouter/anthropic/claude-haiku-4-5",
                "n_evaluated": len(per_question),
            },
            "scores": {"sps": 0.85},
            "aggregate": {
                "mean_jsd": 0.05,
                "mean_kendall_tau": 0.9,
                "composite_parity": 0.9,
                "n_questions": len(per_question),
            },
            "per_question": per_question,
        }
        (results_dir / "run_one.json").write_text(json.dumps(run))

        output_dir = tmp_path / "out"
        publish_questions(results_dir, output_dir)

        question_dir = output_dir / "question" / "subpop"
        assert question_dir.is_dir()
        files = {p.stem for p in question_dir.glob("*.json") if p.stem != "index"}
        # Public keys produce pages; private keys do not.
        for k in pub_keys:
            from synthbench.publish import _safe_question_key

            assert _safe_question_key(k) in files
        for k in priv_keys:
            from synthbench.publish import _safe_question_key

            assert _safe_question_key(k) not in files

        index = json.loads((question_dir / "index.json").read_text())
        index_keys = {entry["key"] for entry in index["questions"]}
        for k in priv_keys:
            assert k not in index_keys
