"""Integration tests: publish pipeline filters invalid (uniform-garbage) runs.

Covers ``publish_leaderboard_data``, ``publish_runs``, and ``publish_questions``
to ensure uniform-distribution garbage (sb-knd reproducer signature) never
reaches the published artifacts, while valid runs alongside are unaffected.
"""

from __future__ import annotations

import json

from synthbench.publish import (
    publish_leaderboard_data,
    publish_questions,
    publish_runs,
)


def _uniform_pq(key: str, n: int = 4) -> dict:
    prob = 1.0 / n
    return {
        "key": key,
        "text": f"question {key}",
        "options": [f"opt{i}" for i in range(n)],
        "human_distribution": {f"opt{i}": prob for i in range(n)},
        "human_refusal_rate": 0.0,
        "model_distribution": {f"opt{i}": prob for i in range(n)},
        "jsd": 0.0,
        "kendall_tau": 0.0,
        "parity": 0.5,
        "n_samples": 30,
        "model_refusal_rate": 0.0,
    }


def _healthy_pq(key: str) -> dict:
    return {
        "key": key,
        "text": f"question {key}",
        "options": ["A", "B", "C", "D"],
        "human_distribution": {"A": 0.55, "B": 0.2, "C": 0.15, "D": 0.1},
        "human_refusal_rate": 0.02,
        "model_distribution": {"A": 0.5, "B": 0.3, "C": 0.15, "D": 0.05},
        "jsd": 0.08,
        "kendall_tau": 0.6,
        "parity": 0.82,
        "n_samples": 30,
        "model_refusal_rate": 0.01,
    }


def _mk_result(
    provider: str,
    dataset: str,
    per_question: list[dict],
    sps: float = 0.75,
) -> dict:
    return {
        "benchmark": "synthbench",
        "timestamp": "2026-04-15T00:00:00Z",
        "config": {
            "provider": provider,
            "dataset": dataset,
            "samples_per_question": 30,
            "n_requested": len(per_question),
            "n_evaluated": len(per_question),
            "question_set_hash": f"hash_{dataset}",
        },
        "scores": {"sps": sps, "p_dist": 0.8, "p_rank": 0.55, "p_refuse": 0.96},
        "aggregate": {
            "mean_jsd": 0.2,
            "mean_kendall_tau": 0.1,
            "composite_parity": sps,
            "n_questions": len(per_question),
            "per_metric_ci": {
                "sps": [sps - 0.01, sps + 0.01],
                "p_dist": [0.79, 0.82],
                "p_rank": [0.53, 0.57],
                "p_refuse": [0.95, 0.97],
            },
            "n_parse_failures": 0,
        },
        "per_question": per_question,
    }


# ---------------------------------------------------------------------------
# publish_leaderboard_data
# ---------------------------------------------------------------------------


def test_publish_leaderboard_data_excludes_invalid_runs(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    good = _mk_result(
        "openrouter/anthropic/claude-haiku-4-5",
        "opinionsqa",
        [_healthy_pq(f"Q{i}") for i in range(20)],
        sps=0.77,
    )
    bad = _mk_result(
        "synthpanel/claude-haiku-4-5-20251001",
        "subpop",
        [_uniform_pq(f"Q{i}") for i in range(20)],
        sps=0.677,
    )
    (results_dir / "good.json").write_text(json.dumps(good))
    (results_dir / "bad_uniform_garbage.json").write_text(json.dumps(bad))

    out = tmp_path / "leaderboard.json"
    publish_leaderboard_data(results_dir, out)

    payload = json.loads(out.read_text())

    # Excluded runs block exposes the filtered run for audit transparency.
    assert "excluded_runs" in payload
    assert len(payload["excluded_runs"]) == 1
    excluded = payload["excluded_runs"][0]
    assert excluded["run_id"] == "bad_uniform_garbage"
    assert excluded["provider"] == "synthpanel/claude-haiku-4-5-20251001"
    assert excluded["metrics"]["n_uniform_questions"] == 20
    assert "uniform-garbage" in excluded["reason"]

    # The invalid run does NOT appear in ranked entries.
    entry_providers = [e["provider"] for e in payload["entries"]]
    assert not any("synthpanel" in p.lower() for p in entry_providers)
    assert len(payload["entries"]) == 1


def test_publish_leaderboard_data_empty_excluded_runs_when_all_valid(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    good = _mk_result(
        "openrouter/anthropic/claude-haiku-4-5",
        "opinionsqa",
        [_healthy_pq(f"Q{i}") for i in range(20)],
    )
    (results_dir / "good.json").write_text(json.dumps(good))

    out = tmp_path / "leaderboard.json"
    publish_leaderboard_data(results_dir, out)
    payload = json.loads(out.read_text())
    assert payload["excluded_runs"] == []


def test_publish_leaderboard_data_all_invalid_raises(tmp_path):
    """If every run is invalid, we refuse to emit an empty leaderboard."""
    import pytest

    results_dir = tmp_path / "results"
    results_dir.mkdir()
    bad = _mk_result(
        "synthpanel/broken",
        "subpop",
        [_uniform_pq(f"Q{i}") for i in range(20)],
    )
    (results_dir / "bad.json").write_text(json.dumps(bad))

    out = tmp_path / "leaderboard.json"
    with pytest.raises(ValueError, match="filtered as invalid runs"):
        publish_leaderboard_data(results_dir, out)


# ---------------------------------------------------------------------------
# publish_runs
# ---------------------------------------------------------------------------


def test_publish_runs_skips_invalid_runs(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    # Use a `full`-tier dataset (ntia) for the good run so the per-run
    # artifact actually lands on disk under the new tier semantics
    # (sb-sj6: aggregates_only no longer emits per-run JSON).
    good = _mk_result(
        "openrouter/anthropic/claude-haiku-4-5",
        "ntia",
        [_healthy_pq(f"Q{i}") for i in range(20)],
    )
    bad = _mk_result(
        "synthpanel/claude-haiku-4-5-20251001",
        "subpop",
        [_uniform_pq(f"Q{i}") for i in range(20)],
    )
    (results_dir / "good.json").write_text(json.dumps(good))
    (results_dir / "bad.json").write_text(json.dumps(bad))

    out_dir = tmp_path / "site"
    counts = publish_runs(results_dir, out_dir)

    # Only the valid run is counted, and only its per-run JSON exists on disk.
    assert counts["runs"] == 1
    assert (out_dir / "run" / "good.json").exists()
    assert not (out_dir / "run" / "bad.json").exists()


# ---------------------------------------------------------------------------
# publish_questions
# ---------------------------------------------------------------------------


def test_publish_questions_skips_invalid_runs(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    # Use ``ntia`` (``full`` tier) so the per-question JSON actually lands
    # locally under the post-sb-sj6 tier semantics — gated-tier datasets
    # (incl. OpinionsQA post-sb-dek) only land locally as a debug fallback
    # when no R2 uploader is wired in.
    good = _mk_result(
        "openrouter/anthropic/claude-haiku-4-5",
        "ntia",
        [_healthy_pq("Q1"), _healthy_pq("Q2")],
    )
    bad = _mk_result(
        "synthpanel/claude-haiku-4-5-20251001",
        "ntia",
        [_uniform_pq(f"Q{i}") for i in range(20)],
    )
    (results_dir / "good.json").write_text(json.dumps(good))
    (results_dir / "bad.json").write_text(json.dumps(bad))

    out_dir = tmp_path / "site"
    publish_questions(results_dir, out_dir)

    # Q1 rollup must reference only the good run's model response.
    q1 = json.loads((out_dir / "question" / "ntia" / "Q1.json").read_text())
    response_run_ids = [r.get("run_id") for r in q1["model_responses"]]
    assert "bad" not in response_run_ids
    assert "good" in response_run_ids
