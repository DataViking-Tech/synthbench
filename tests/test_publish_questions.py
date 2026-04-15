"""Tests for per-question publish step (sb-eiv).

Covers the pure-python rollup helpers. End-to-end directory emission is
exercised via ``publish_questions`` in a tmp_path run to assert the
expected on-disk layout and per-dataset index structure.
"""

from __future__ import annotations

import json

from synthbench.publish import (
    _build_question_index_entry,
    _collect_question_rollups,
    _finalize_question_payload,
    _safe_question_key,
    publish_questions,
)


def _make_result(
    provider: str,
    dataset: str,
    per_question: list[dict],
) -> dict:
    """Minimal raw result file shape, enough for the question rollup."""
    return {
        "benchmark": "synthbench",
        "config": {"provider": provider, "dataset": dataset},
        "per_question": per_question,
    }


def _pq(
    key: str,
    text: str,
    options: list[str],
    human_dist: dict[str, float],
    model_dist: dict[str, float],
    *,
    jsd: float = 0.0,
    n_samples: int = 10,
    refusal_rate: float = 0.0,
    human_refusal_rate: float | None = None,
) -> dict:
    return {
        "key": key,
        "text": text,
        "options": options,
        "human_distribution": human_dist,
        "model_distribution": model_dist,
        "jsd": jsd,
        "n_samples": n_samples,
        "model_refusal_rate": refusal_rate,
        "human_refusal_rate": human_refusal_rate,
    }


# -- Safe-key sanitization --------------------------------------------------


def test_safe_question_key_preserves_alnum_underscore_hyphen():
    assert _safe_question_key("GOQA_0_adeba4f8") == "GOQA_0_adeba4f8"
    assert _safe_question_key("PREDICTA_W27") == "PREDICTA_W27"
    assert _safe_question_key("AA-PERS") == "AA-PERS"


def test_safe_question_key_sanitizes_reserved_chars():
    assert _safe_question_key("with space") == "with_space"
    assert _safe_question_key("slash/path") == "slash_path"
    assert _safe_question_key("q?x=1") == "q_x_1"


# -- Rollup correctness -----------------------------------------------------


def test_collect_rollups_skips_baselines_and_ensembles():
    opts = ["A", "B"]
    results = [
        (
            "raw_run",
            _make_result(
                "openrouter/anthropic/claude-haiku-4-5",
                "opinionsqa",
                [_pq("Q1", "q1", opts, {"A": 0.6, "B": 0.4}, {"A": 0.5, "B": 0.5})],
            ),
        ),
        (
            "baseline_run",
            _make_result(
                "majority-baseline",
                "opinionsqa",
                [_pq("Q1", "q1", opts, {"A": 0.6, "B": 0.4}, {"A": 1.0, "B": 0.0})],
            ),
        ),
        (
            "ensemble_run",
            _make_result(
                "ensemble_3blend",
                "opinionsqa",
                [_pq("Q1", "q1", opts, {"A": 0.6, "B": 0.4}, {"A": 0.7, "B": 0.3})],
            ),
        ),
    ]
    rollups = _collect_question_rollups(results)
    assert list(rollups.keys()) == [("opinionsqa", "Q1")]
    responses = rollups[("opinionsqa", "Q1")]["model_responses"]
    # Only the raw run survives.
    assert len(responses) == 1
    assert responses[0]["model"] == "Claude Haiku 4.5"
    assert responses[0]["framework"] == "raw"


def test_collect_rollups_dedupes_by_sample_count():
    # Same model, two replicates on the same question — keep larger n_samples.
    opts = ["A", "B"]
    results = [
        (
            "small_run",
            _make_result(
                "openrouter/openai/gpt-4o-mini",
                "opinionsqa",
                [
                    _pq(
                        "Q1",
                        "q1",
                        opts,
                        {"A": 0.5, "B": 0.5},
                        {"A": 0.3, "B": 0.7},
                        n_samples=10,
                        jsd=0.1,
                    )
                ],
            ),
        ),
        (
            "big_run",
            _make_result(
                "openrouter/openai/gpt-4o-mini",
                "opinionsqa",
                [
                    _pq(
                        "Q1",
                        "q1",
                        opts,
                        {"A": 0.5, "B": 0.5},
                        {"A": 0.4, "B": 0.6},
                        n_samples=30,
                        jsd=0.05,
                    )
                ],
            ),
        ),
    ]
    rollups = _collect_question_rollups(results)
    responses = rollups[("opinionsqa", "Q1")]["model_responses"]
    assert len(responses) == 1
    assert responses[0]["run_id"] == "big_run"
    assert responses[0]["n_samples"] == 30
    assert responses[0]["jsd_to_human"] == 0.05


def test_collect_rollups_groups_by_dataset():
    # The same key across different datasets must not collide.
    opts = ["A", "B"]
    results = [
        (
            "run_oqa",
            _make_result(
                "openrouter/anthropic/claude-haiku-4-5",
                "opinionsqa",
                [_pq("SHARED", "q", opts, {"A": 0.5, "B": 0.5}, {"A": 0.6, "B": 0.4})],
            ),
        ),
        (
            "run_goqa",
            _make_result(
                "openrouter/anthropic/claude-haiku-4-5",
                "globalopinionqa",
                [_pq("SHARED", "q", opts, {"A": 0.5, "B": 0.5}, {"A": 0.7, "B": 0.3})],
            ),
        ),
    ]
    rollups = _collect_question_rollups(results)
    assert ("opinionsqa", "SHARED") in rollups
    assert ("globalopinionqa", "SHARED") in rollups


# -- Finalize payload -------------------------------------------------------


def test_finalize_sorts_by_jsd_to_human_ascending():
    opts = ["A", "B"]
    # Build rollup with three models; different jsd_to_human values.
    rollup = {
        "dataset": "opinionsqa",
        "key": "Q1",
        "question": "Example question text.",
        "options": opts,
        "human_distribution": {"A": 0.6, "B": 0.4},
        "human_refusal_rate": 0.01,
        "temporal_year": None,
        "topic": None,
        "model_responses": [
            {
                "config_id": "cfg-high",
                "model": "Model-High",
                "framework": "raw",
                "base_provider": "x",
                "distribution": {"A": 0.2, "B": 0.8},
                "n_samples": 30,
                "jsd_to_human": 0.30,
                "refusal_rate": 0.0,
                "run_id": "run-high",
                "temperature": None,
                "template": None,
            },
            {
                "config_id": "cfg-low",
                "model": "Model-Low",
                "framework": "raw",
                "base_provider": "x",
                "distribution": {"A": 0.58, "B": 0.42},
                "n_samples": 30,
                "jsd_to_human": 0.01,
                "refusal_rate": 0.0,
                "run_id": "run-low",
                "temperature": None,
                "template": None,
            },
            {
                "config_id": "cfg-mid",
                "model": "Model-Mid",
                "framework": "raw",
                "base_provider": "x",
                "distribution": {"A": 0.4, "B": 0.6},
                "n_samples": 30,
                "jsd_to_human": 0.1,
                "refusal_rate": 0.0,
                "run_id": "run-mid",
                "temperature": None,
                "template": None,
            },
        ],
    }
    payload = _finalize_question_payload(rollup)
    models = [r["model"] for r in payload["model_responses"]]
    assert models == ["Model-Low", "Model-Mid", "Model-High"]
    assert payload["summary"]["n_models"] == 3


def test_finalize_computes_cross_model_and_consensus():
    # Two models: identical distributions → cross-model JSD = 0, consensus matches.
    rollup = {
        "dataset": "opinionsqa",
        "key": "Q1",
        "question": "Example",
        "options": ["A", "B"],
        "human_distribution": {"A": 0.6, "B": 0.4},
        "human_refusal_rate": None,
        "temporal_year": None,
        "topic": None,
        "model_responses": [
            {
                "config_id": "cfg-1",
                "model": "M1",
                "framework": "raw",
                "base_provider": "p",
                "distribution": {"A": 1.0, "B": 0.0},
                "n_samples": 10,
                "jsd_to_human": 0.1,
                "refusal_rate": 0.0,
                "run_id": "r1",
                "temperature": None,
                "template": None,
            },
            {
                "config_id": "cfg-2",
                "model": "M2",
                "framework": "raw",
                "base_provider": "p",
                "distribution": {"A": 1.0, "B": 0.0},
                "n_samples": 10,
                "jsd_to_human": 0.1,
                "refusal_rate": 0.2,
                "run_id": "r2",
                "temperature": None,
                "template": None,
            },
        ],
    }
    payload = _finalize_question_payload(rollup)
    assert payload["summary"]["cross_model_jsd_mean"] == 0.0
    assert payload["summary"]["cross_model_jsd_max"] == 0.0
    # Both models pick A → consensus = A (matches human top).
    assert payload["summary"]["consensus_option"] == "A"
    assert payload["summary"]["human_top_option"] == "A"
    # Refusal spread = |0.0 - 0.2| = 0.2.
    assert payload["summary"]["refusal_rate_spread"] == 0.2


def test_finalize_single_model_has_none_cross_model():
    rollup = {
        "dataset": "opinionsqa",
        "key": "Q1",
        "question": "Example",
        "options": ["A", "B"],
        "human_distribution": {"A": 0.5, "B": 0.5},
        "human_refusal_rate": None,
        "temporal_year": None,
        "topic": None,
        "model_responses": [
            {
                "config_id": "cfg-1",
                "model": "M1",
                "framework": "raw",
                "base_provider": "p",
                "distribution": {"A": 0.3, "B": 0.7},
                "n_samples": 10,
                "jsd_to_human": 0.05,
                "refusal_rate": 0.0,
                "run_id": "r1",
                "temperature": None,
                "template": None,
            },
        ],
    }
    payload = _finalize_question_payload(rollup)
    assert payload["summary"]["n_models"] == 1
    assert payload["summary"]["cross_model_jsd_mean"] is None
    assert payload["summary"]["cross_model_jsd_max"] is None
    assert payload["summary"]["refusal_rate_spread"] is None


# -- Index entry ------------------------------------------------------------


def test_index_entry_truncates_long_questions():
    payload = {
        "key": "Q1",
        "question": "x" * 200,
        "summary": {
            "n_models": 4,
            "cross_model_jsd_mean": 0.2,
            "cross_model_jsd_max": 0.4,
            "jsd_to_human_mean": 0.1,
            "consensus_option": "A",
            "human_top_option": "A",
            "refusal_rate_spread": 0.0,
        },
    }
    entry = _build_question_index_entry(payload)
    assert entry["question_excerpt"].endswith("…")
    assert len(entry["question_excerpt"]) == 158  # 157 + ellipsis


def test_index_entry_preserves_short_questions():
    payload = {
        "key": "Q1",
        "question": "short question",
        "summary": {
            "n_models": 2,
            "cross_model_jsd_mean": 0.0,
            "cross_model_jsd_max": 0.0,
            "jsd_to_human_mean": 0.0,
            "consensus_option": None,
            "human_top_option": None,
            "refusal_rate_spread": None,
        },
    }
    entry = _build_question_index_entry(payload)
    assert entry["question_excerpt"] == "short question"


# -- End-to-end directory emission ------------------------------------------


def test_publish_questions_writes_expected_layout(tmp_path):
    """``publish_questions`` emits per-dataset dirs with keys + index.json."""
    results_dir = tmp_path / "raw"
    results_dir.mkdir()

    opts = ["A", "B"]
    run_one = _make_result(
        "openrouter/anthropic/claude-haiku-4-5",
        "opinionsqa",
        [
            _pq("Q1", "q1", opts, {"A": 0.6, "B": 0.4}, {"A": 0.5, "B": 0.5}, jsd=0.05),
            _pq("Q2", "q2", opts, {"A": 0.3, "B": 0.7}, {"A": 0.4, "B": 0.6}, jsd=0.03),
        ],
    )
    run_two = _make_result(
        "openrouter/openai/gpt-4o-mini",
        "opinionsqa",
        [
            _pq("Q1", "q1", opts, {"A": 0.6, "B": 0.4}, {"A": 0.7, "B": 0.3}, jsd=0.08),
        ],
    )

    (results_dir / "run_one.json").write_text(json.dumps(run_one))
    (results_dir / "run_two.json").write_text(json.dumps(run_two))

    out_dir = tmp_path / "site_data"
    counts = publish_questions(results_dir, out_dir)

    assert counts == {"questions": 2, "datasets": 1}

    # Per-question file exists and parses.
    q1_path = out_dir / "question" / "opinionsqa" / "Q1.json"
    assert q1_path.exists()
    q1 = json.loads(q1_path.read_text())
    assert q1["dataset"] == "opinionsqa"
    assert q1["key"] == "Q1"
    assert q1["summary"]["n_models"] == 2
    # Models sorted by jsd_to_human ascending.
    assert [r["model"] for r in q1["model_responses"]] == [
        "Claude Haiku 4.5",
        "GPT-4o-mini",
    ]

    # Q2 only has one model.
    q2 = json.loads((out_dir / "question" / "opinionsqa" / "Q2.json").read_text())
    assert q2["summary"]["n_models"] == 1
    assert q2["summary"]["cross_model_jsd_mean"] is None

    # Per-dataset index emitted and sorted by descending cross-model divergence.
    index_path = out_dir / "question" / "opinionsqa" / "index.json"
    assert index_path.exists()
    idx = json.loads(index_path.read_text())
    assert idx["dataset"] == "opinionsqa"
    assert idx["n_questions"] == 2
    keys_in_order = [e["key"] for e in idx["questions"]]
    # Q1 has non-null cross-model JSD; Q2 is null → Q1 first.
    assert keys_in_order == ["Q1", "Q2"]


def test_publish_questions_rejects_empty_dir(tmp_path):
    import pytest

    results_dir = tmp_path / "empty"
    results_dir.mkdir()
    with pytest.raises(ValueError):
        publish_questions(results_dir, tmp_path / "out")
