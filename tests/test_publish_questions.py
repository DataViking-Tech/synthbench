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


def test_collect_rollups_partitions_ensembles_and_skips_baselines():
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
                "ensemble/3-model-blend",
                "opinionsqa",
                [_pq("Q1", "q1", opts, {"A": 0.6, "B": 0.4}, {"A": 0.7, "B": 0.3})],
            ),
        ),
    ]
    rollups = _collect_question_rollups(results)
    assert list(rollups.keys()) == [("opinionsqa", "Q1")]
    rollup = rollups[("opinionsqa", "Q1")]

    # Cross-model bucket: only the raw run (baseline dropped, ensemble
    # partitioned out).
    responses = rollup["model_responses"]
    assert len(responses) == 1
    assert responses[0]["model"] == "Claude Haiku 4.5"
    assert responses[0]["framework"] == "raw"

    # Aggregated bucket: ensemble lands here, not in model_responses.
    aggregated = rollup["aggregated_responses"]
    assert len(aggregated) == 1
    assert aggregated[0]["model"] == "SynthPanel Ensemble (3-model)"
    assert aggregated[0]["run_id"] == "ensemble_run"
    # Ensembles are product-framework in MODEL_MAP; confirm they're not
    # leaking into the raw/product single-model bucket.
    assert all(r["run_id"] != "ensemble_run" for r in responses)


def test_collect_rollups_dedupes_ensemble_replicates_by_sample_count():
    # Two replicates of the same ensemble — keep the one with larger n_samples.
    opts = ["A", "B"]
    results = [
        (
            "ensemble_small",
            _make_result(
                "ensemble/3-model-blend",
                "opinionsqa",
                [
                    _pq(
                        "Q1",
                        "q1",
                        opts,
                        {"A": 0.5, "B": 0.5},
                        {"A": 0.5, "B": 0.5},
                        n_samples=10,
                        jsd=0.2,
                    )
                ],
            ),
        ),
        (
            "ensemble_big",
            _make_result(
                "ensemble/3-model-blend",
                "opinionsqa",
                [
                    _pq(
                        "Q1",
                        "q1",
                        opts,
                        {"A": 0.5, "B": 0.5},
                        {"A": 0.55, "B": 0.45},
                        n_samples=30,
                        jsd=0.05,
                    )
                ],
            ),
        ),
    ]
    rollups = _collect_question_rollups(results)
    aggregated = rollups[("opinionsqa", "Q1")].get("aggregated_responses", [])
    assert len(aggregated) == 1
    assert aggregated[0]["run_id"] == "ensemble_big"
    assert aggregated[0]["n_samples"] == 30


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


def test_finalize_emits_aggregated_responses_excluded_from_summary():
    """Ensembles ride in aggregated_responses; summary stats ignore them.

    Guards the core invariant from sb-3l3: the cross-model JSD summary is
    computed from single-model responses only so adding an ensemble row
    to the per-question view does NOT shift trendslop numbers.
    """
    base_rollup = {
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
                "distribution": {"A": 0.0, "B": 1.0},
                "n_samples": 10,
                "jsd_to_human": 0.5,
                "refusal_rate": 0.0,
                "run_id": "r2",
                "temperature": None,
                "template": None,
            },
        ],
    }
    no_ensemble = _finalize_question_payload(
        {**base_rollup, "aggregated_responses": []}
    )

    # Sanity: {A:1,B:0} vs {A:0,B:1} has a sharply non-zero pairwise JSD.
    base_mean = no_ensemble["summary"]["cross_model_jsd_mean"]
    assert base_mean is not None and base_mean > 0.0

    # Now add an ensemble that blends them — summary must be identical.
    with_ensemble = _finalize_question_payload(
        {
            **base_rollup,
            "model_responses": [{**r} for r in base_rollup["model_responses"]],
            "aggregated_responses": [
                {
                    "config_id": "cfg-ens",
                    "model": "SynthPanel Ensemble (3-model)",
                    "framework": "product",
                    "base_provider": "3-model-blend",
                    "distribution": {"A": 0.5, "B": 0.5},
                    "n_samples": 20,
                    "jsd_to_human": 0.01,
                    "refusal_rate": 0.0,
                    "run_id": "ens-1",
                    "temperature": None,
                    "template": None,
                }
            ],
        }
    )

    assert with_ensemble["summary"] == no_ensemble["summary"]
    assert with_ensemble["summary"]["n_models"] == 2
    # Ensemble was not silently merged into model_responses.
    assert all(r["run_id"] != "ens-1" for r in with_ensemble["model_responses"])
    # Ensemble surfaces in its own bucket.
    assert len(with_ensemble["aggregated_responses"]) == 1
    assert with_ensemble["aggregated_responses"][0]["run_id"] == "ens-1"


def test_finalize_emits_empty_aggregated_when_no_ensembles():
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
                "distribution": {"A": 0.5, "B": 0.5},
                "n_samples": 10,
                "jsd_to_human": 0.0,
                "refusal_rate": 0.0,
                "run_id": "r1",
                "temperature": None,
                "template": None,
            },
        ],
    }
    payload = _finalize_question_payload(rollup)
    # Field is always present (even empty) so the frontend can rely on it.
    assert payload["aggregated_responses"] == []


def test_finalize_sorts_aggregated_by_jsd_to_human_ascending():
    rollup = {
        "dataset": "opinionsqa",
        "key": "Q1",
        "question": "Example",
        "options": ["A", "B"],
        "human_distribution": {"A": 0.5, "B": 0.5},
        "human_refusal_rate": None,
        "temporal_year": None,
        "topic": None,
        "model_responses": [],
        "aggregated_responses": [
            {
                "config_id": "cfg-ens-hi",
                "model": "Ensemble-Hi",
                "framework": "product",
                "base_provider": "blend",
                "distribution": {"A": 0.2, "B": 0.8},
                "n_samples": 20,
                "jsd_to_human": 0.3,
                "refusal_rate": 0.0,
                "run_id": "ens-hi",
                "temperature": None,
                "template": None,
            },
            {
                "config_id": "cfg-ens-lo",
                "model": "Ensemble-Lo",
                "framework": "product",
                "base_provider": "blend",
                "distribution": {"A": 0.5, "B": 0.5},
                "n_samples": 20,
                "jsd_to_human": 0.02,
                "refusal_rate": 0.0,
                "run_id": "ens-lo",
                "temperature": None,
                "template": None,
            },
        ],
    }
    payload = _finalize_question_payload(rollup)
    ordered = [r["model"] for r in payload["aggregated_responses"]]
    assert ordered == ["Ensemble-Lo", "Ensemble-Hi"]


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
    run_ensemble = _make_result(
        "ensemble/3-model-blend",
        "opinionsqa",
        [
            _pq("Q1", "q1", opts, {"A": 0.6, "B": 0.4}, {"A": 0.6, "B": 0.4}, jsd=0.01),
        ],
    )

    (results_dir / "run_one.json").write_text(json.dumps(run_one))
    (results_dir / "run_two.json").write_text(json.dumps(run_two))
    (results_dir / "run_ensemble.json").write_text(json.dumps(run_ensemble))

    out_dir = tmp_path / "site_data"
    counts = publish_questions(results_dir, out_dir)

    assert counts == {"questions": 2, "datasets": 1}

    # Per-question file exists and parses.
    q1_path = out_dir / "question" / "opinionsqa" / "Q1.json"
    assert q1_path.exists()
    q1 = json.loads(q1_path.read_text())
    assert q1["dataset"] == "opinionsqa"
    assert q1["key"] == "Q1"
    # Summary counts single-model responses only; ensemble doesn't bump n_models.
    assert q1["summary"]["n_models"] == 2
    # Models sorted by jsd_to_human ascending.
    assert [r["model"] for r in q1["model_responses"]] == [
        "Claude Haiku 4.5",
        "GPT-4o-mini",
    ]
    # Ensemble lives in the aggregated bucket, not model_responses.
    assert [r["model"] for r in q1["aggregated_responses"]] == [
        "SynthPanel Ensemble (3-model)",
    ]
    assert all(
        "ensemble" not in r["base_provider"].lower() for r in q1["model_responses"]
    )

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
