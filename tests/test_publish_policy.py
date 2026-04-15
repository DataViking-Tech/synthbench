"""Tests for publish-step enforcement of dataset redistribution policy (sb-r8n).

Verifies that publish.py suppresses per-question ``human_distribution`` and
``human_refusal_rate`` fields when the dataset's policy tier forbids raw
redistribution, while preserving aggregate metrics (JSD, Kendall τ, SPS).
"""

from __future__ import annotations

import json

from synthbench.datasets.policy import DatasetPolicy, policy_for
from synthbench.publish import (
    _augment_per_question,
    _finalize_question_payload,
    _policy_to_dict,
    publish_questions,
)


def _pq(key: str = "Q1") -> dict:
    return {
        "key": key,
        "text": "example",
        "options": ["A", "B"],
        "human_distribution": {"A": 0.6, "B": 0.4},
        "human_refusal_rate": 0.05,
        "model_distribution": {"A": 0.5, "B": 0.5},
        "jsd": 0.01,
        "kendall_tau": 0.9,
        "parity": 0.95,
        "n_samples": 10,
        "model_refusal_rate": 0.0,
    }


# -- _augment_per_question suppression --------------------------------------


def test_augment_full_policy_preserves_human_fields():
    full = DatasetPolicy(
        name="ntia", redistribution_policy="full", license_url=None, citation=None
    )
    out = _augment_per_question([_pq()], policy=full)
    assert out[0]["human_distribution"] == {"A": 0.6, "B": 0.4}
    assert out[0]["human_refusal_rate"] == 0.05


def test_augment_aggregates_only_suppresses_human_fields():
    aggr = DatasetPolicy(
        name="opinionsqa",
        redistribution_policy="aggregates_only",
        license_url=None,
        citation=None,
    )
    out = _augment_per_question([_pq()], policy=aggr)
    assert "human_distribution" not in out[0]
    assert "human_refusal_rate" not in out[0]
    # Aggregate metrics survive.
    assert out[0]["jsd"] == 0.01
    assert out[0]["kendall_tau"] == 0.9
    assert out[0]["parity"] == 0.95
    assert out[0]["model_distribution"] == {"A": 0.5, "B": 0.5}


def test_augment_none_policy_preserves_human_fields():
    """Backward-compat: unchanged behavior when caller passes no policy."""
    out = _augment_per_question([_pq()])
    assert out[0]["human_distribution"] == {"A": 0.6, "B": 0.4}


# -- _finalize_question_payload suppression ---------------------------------


def _rollup(dataset: str) -> dict:
    return {
        "dataset": dataset,
        "key": "Q1",
        "question": "example?",
        "options": ["A", "B"],
        "human_distribution": {"A": 0.7, "B": 0.3},
        "human_refusal_rate": 0.02,
        "temporal_year": None,
        "topic": None,
        "model_responses": [
            {
                "config_id": "cfg-1",
                "model": "M1",
                "framework": "raw",
                "base_provider": "p",
                "distribution": {"A": 0.5, "B": 0.5},
                "n_samples": 20,
                "jsd_to_human": 0.05,
                "refusal_rate": 0.0,
                "run_id": "r1",
                "temperature": None,
                "template": None,
            },
        ],
    }


def test_finalize_aggregates_only_clears_human_distribution():
    """Per-question payload for an aggregates_only dataset emits an empty
    dict for human_distribution — aggregate fields (modal, JSD-to-human
    mean) still work because they are pre-computed."""
    payload = _finalize_question_payload(_rollup("opinionsqa"))
    assert payload["human_distribution"] == {}
    assert payload["human_refusal_rate"] is None
    # But the human modal is derived — keep it.
    assert payload["summary"]["human_top_option"] == "A"
    # Aggregate model metrics intact.
    assert payload["summary"]["jsd_to_human_mean"] == 0.05
    assert payload["summary"]["n_models"] == 1
    # Policy metadata embedded.
    assert payload["dataset_policy"]["redistribution_policy"] == "aggregates_only"
    assert payload["dataset_policy"]["citation"]
    assert payload["dataset_policy"]["license_url"]


def test_finalize_full_tier_keeps_human_distribution():
    payload = _finalize_question_payload(_rollup("ntia"))
    assert payload["human_distribution"] == {"A": 0.7, "B": 0.3}
    assert payload["human_refusal_rate"] == 0.02
    assert payload["dataset_policy"]["redistribution_policy"] == "full"


# -- _policy_to_dict --------------------------------------------------------


def test_policy_to_dict_shape():
    p = policy_for("ntia")
    d = _policy_to_dict(p)
    assert set(d) == {"redistribution_policy", "license_url", "citation"}
    assert d["redistribution_policy"] == "full"


# -- End-to-end publish_questions spot-check --------------------------------


def _make_result(
    provider: str,
    dataset: str,
    per_question: list[dict],
) -> dict:
    return {
        "benchmark": "synthbench",
        "config": {"provider": provider, "dataset": dataset},
        "per_question": per_question,
    }


def test_publish_questions_suppresses_human_for_aggregates_only(tmp_path):
    """Integration: generated per-question JSON for an aggregates_only
    dataset must not expose the raw human distribution."""
    results_dir = tmp_path / "results"
    out_dir = tmp_path / "site"
    results_dir.mkdir()

    result = _make_result(
        "openrouter/anthropic/claude-haiku-4-5",
        "opinionsqa",  # aggregates_only
        [_pq("Q1")],
    )
    (results_dir / "run1.json").write_text(json.dumps(result))

    publish_questions(results_dir, out_dir)

    payload_path = out_dir / "question" / "opinionsqa" / "Q1.json"
    assert payload_path.exists()
    payload = json.loads(payload_path.read_text())
    assert payload["human_distribution"] == {}
    assert payload["human_refusal_rate"] is None
    assert payload["dataset_policy"]["redistribution_policy"] == "aggregates_only"


def test_publish_questions_full_tier_publishes_human(tmp_path):
    """Integration: the one `full`-tier dataset (NTIA) keeps raw human data."""
    results_dir = tmp_path / "results"
    out_dir = tmp_path / "site"
    results_dir.mkdir()

    result = _make_result(
        "openrouter/anthropic/claude-haiku-4-5",
        "ntia",
        [_pq("Q1")],
    )
    (results_dir / "run1.json").write_text(json.dumps(result))

    publish_questions(results_dir, out_dir)

    payload_path = out_dir / "question" / "ntia" / "Q1.json"
    payload = json.loads(payload_path.read_text())
    assert payload["human_distribution"] == {"A": 0.6, "B": 0.4}
    assert payload["human_refusal_rate"] == 0.05
    assert payload["dataset_policy"]["redistribution_policy"] == "full"
