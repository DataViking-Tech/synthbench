"""Routing tests for the R2 publish path (sb-sjs, sb-sj6).

Verifies the three-way tier routing now that ``aggregates_only`` and
``gated`` have distinct semantics (sb-sj6):

* ``full``  → local ``site/public/data/`` (static Pages origin)
* ``gated`` → R2 (authenticated Worker origin)
* ``aggregates_only`` → no per-question/run/config artifact at all

Uses a fake S3 client wrapped by a real ``R2Uploader`` so the assertions
cover end-to-end serialization, not a mocked boundary inside the publish
module.
"""

from __future__ import annotations

import json
from pathlib import Path

from synthbench.publish import publish_questions, publish_runs
from synthbench.r2_upload import R2Config, R2Uploader


# -- Test helpers -----------------------------------------------------------


class _FakeS3Client:
    def __init__(self):
        self.calls: list[dict] = []

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str):
        self.calls.append({"Bucket": Bucket, "Key": Key, "Body": Body})
        return {"ETag": "fake"}


def _uploader() -> tuple[R2Uploader, _FakeS3Client]:
    client = _FakeS3Client()
    cfg = R2Config(
        account_id="acct",
        access_key_id="ak",
        secret_access_key="sk",
        bucket="synthbench-data-test",
    )
    return R2Uploader(cfg, client=client), client


def _make_question_result(provider: str, dataset: str, key: str) -> dict:
    return {
        "benchmark": "synthbench",
        "config": {"provider": provider, "dataset": dataset},
        "per_question": [
            {
                "key": key,
                "text": "q?",
                "options": ["A", "B"],
                "human_distribution": {"A": 0.6, "B": 0.4},
                "model_distribution": {"A": 0.5, "B": 0.5},
                "jsd": 0.05,
                "n_samples": 10,
                "model_refusal_rate": 0.0,
                "human_refusal_rate": 0.05,
            }
        ],
    }


def _make_run_result(provider: str, dataset: str) -> dict:
    return {
        "benchmark": "synthbench",
        "config": {
            "provider": provider,
            "dataset": dataset,
            "n_evaluated": 1,
        },
        "scores": {"sps": 0.5, "p_dist": 0.5, "p_rank": 0.5, "p_refuse": 1.0},
        "aggregate": {"mean_jsd": 0.1, "mean_kendall_tau": 0.5, "n_questions": 1},
        "per_question": [
            {
                "key": "Q1",
                "text": "q?",
                "options": ["A", "B"],
                "human_distribution": {"A": 0.6, "B": 0.4},
                "model_distribution": {"A": 0.5, "B": 0.5},
                "jsd": 0.1,
                "n_samples": 10,
                "model_refusal_rate": 0.0,
            }
        ],
    }


# -- publish_questions routing ---------------------------------------------


def test_publish_questions_routes_gated_dataset_to_r2(tmp_path: Path):
    """``gated`` datasets (e.g. subpop) send per-question + index to R2."""
    results_dir = tmp_path / "raw"
    results_dir.mkdir()
    (results_dir / "run_one.json").write_text(
        json.dumps(
            _make_question_result(
                "openrouter/anthropic/claude-haiku-4-5", "subpop", "Q1"
            )
        )
    )
    (results_dir / "run_two.json").write_text(
        json.dumps(
            _make_question_result("openrouter/openai/gpt-4o-mini", "subpop", "Q1")
        )
    )

    out_dir = tmp_path / "site_data"
    uploader, client = _uploader()
    counts = publish_questions(results_dir, out_dir, r2_uploader=uploader)

    assert counts == {"questions": 1, "datasets": 1}
    # No per-question file on disk for the gated dataset — it lives in R2.
    assert not (out_dir / "question" / "subpop" / "Q1.json").exists()
    assert not (out_dir / "question" / "subpop" / "index.json").exists()

    keys = {c["Key"] for c in client.calls}
    assert "question/subpop/Q1.json" in keys
    assert "question/subpop/index.json" in keys

    # Payload integrity: the body for Q1 still parses and carries the
    # cross-model rollup the site expects. Unlike under the pre-sb-sj6
    # aggregates_only treatment, ``human_distribution`` stays populated
    # because authenticated readers are the whole point of the gate.
    q1_body = next(
        c["Body"] for c in client.calls if c["Key"] == "question/subpop/Q1.json"
    )
    payload = json.loads(q1_body)
    assert payload["dataset"] == "subpop"
    assert payload["key"] == "Q1"
    assert payload["human_distribution"] == {"A": 0.6, "B": 0.4}

    # The gated-routes manifest is always written locally so the Astro SSG
    # can enumerate shell pages for this dataset/key.
    routes = json.loads((out_dir / "gated-routes.json").read_text())
    assert routes["datasets"].get("subpop") == ["Q1"]


def test_publish_questions_keeps_full_dataset_on_disk_with_uploader(tmp_path: Path):
    """NTIA is `full` → per-question lands locally even with uploader present."""
    results_dir = tmp_path / "raw"
    results_dir.mkdir()
    (results_dir / "ntia_run.json").write_text(
        json.dumps(
            _make_question_result(
                "openrouter/anthropic/claude-haiku-4-5", "ntia", "NQ1"
            )
        )
    )

    out_dir = tmp_path / "site_data"
    uploader, client = _uploader()
    counts = publish_questions(results_dir, out_dir, r2_uploader=uploader)

    assert counts == {"questions": 1, "datasets": 1}
    assert (out_dir / "question" / "ntia" / "NQ1.json").exists()
    assert (out_dir / "question" / "ntia" / "index.json").exists()
    assert client.calls == []


def test_publish_questions_aggregates_only_emits_nothing_per_question(tmp_path: Path):
    """``aggregates_only`` datasets emit no per-question artifact — not to
    disk, not to R2. The leaderboard still gets its aggregate row via
    ``runs-index.json`` + ``leaderboard.json``.

    Uses an unregistered dataset name so ``policy_for`` falls back to
    ``aggregates_only`` — post-sb-dek no shipped adapter remains at that
    tier (OpinionsQA was promoted to ``gated``)."""
    results_dir = tmp_path / "raw"
    results_dir.mkdir()
    (results_dir / "run.json").write_text(
        json.dumps(
            _make_question_result(
                "openrouter/anthropic/claude-haiku-4-5", "aggr_only_fixture", "Q1"
            )
        )
    )

    out_dir = tmp_path / "site_data"
    uploader, client = _uploader()
    counts = publish_questions(results_dir, out_dir, r2_uploader=uploader)

    assert counts == {"questions": 0, "datasets": 0}
    assert not (out_dir / "question" / "aggr_only_fixture" / "Q1.json").exists()
    assert client.calls == []


def test_publish_questions_without_uploader_writes_gated_locally(tmp_path: Path):
    """Debug mode: without an uploader, gated-tier artifacts fall back to
    local disk so operators can inspect publish output end-to-end."""
    results_dir = tmp_path / "raw"
    results_dir.mkdir()
    (results_dir / "gated_run.json").write_text(
        json.dumps(
            _make_question_result(
                "openrouter/anthropic/claude-haiku-4-5", "subpop", "Q1"
            )
        )
    )

    out_dir = tmp_path / "site_data"
    counts = publish_questions(results_dir, out_dir, r2_uploader=None)

    assert counts == {"questions": 1, "datasets": 1}
    assert (out_dir / "question" / "subpop" / "Q1.json").exists()


# -- publish_runs routing ---------------------------------------------------


def test_publish_runs_routes_gated_run_and_config_to_r2(tmp_path: Path):
    results_dir = tmp_path / "raw"
    results_dir.mkdir()
    # Use a deterministic run_id-shaped filename so _run_id_from_path keys work.
    (results_dir / "20260101-aaa.json").write_text(
        json.dumps(_make_run_result("openrouter/anthropic/claude-haiku-4-5", "subpop"))
    )

    out_dir = tmp_path / "site_data"
    uploader, client = _uploader()
    counts = publish_runs(results_dir, out_dir, r2_uploader=uploader)

    assert counts["runs"] == 1
    assert counts["configs"] == 1
    # runs-index always stays public/local.
    assert (out_dir / "runs-index.json").exists()
    # Per-run + per-config land in R2 for gated datasets.
    keys = {c["Key"] for c in client.calls}
    assert any(k.startswith("run/") and k.endswith(".json") for k in keys)
    assert any(k.startswith("config/") and k.endswith(".json") for k in keys)
    # Local run/ + config/ dirs exist (publish_runs creates them) but contain
    # no JSON for the gated run.
    assert list((out_dir / "run").glob("*.json")) == []
    assert list((out_dir / "config").glob("*.json")) == []


def test_publish_runs_keeps_full_run_local(tmp_path: Path):
    results_dir = tmp_path / "raw"
    results_dir.mkdir()
    (results_dir / "20260101-bbb.json").write_text(
        json.dumps(_make_run_result("openrouter/anthropic/claude-haiku-4-5", "ntia"))
    )

    out_dir = tmp_path / "site_data"
    uploader, client = _uploader()
    counts = publish_runs(results_dir, out_dir, r2_uploader=uploader)

    assert counts["runs"] == 1
    assert client.calls == []
    assert list((out_dir / "run").glob("*.json")) != []
    assert list((out_dir / "config").glob("*.json")) != []


def test_publish_runs_aggregates_only_suppresses_detail(tmp_path: Path):
    """sb-sj6: ``aggregates_only`` datasets contribute an index entry (so
    the leaderboard row still renders) but emit NO per-run or per-config
    JSON — neither to disk nor to R2. The front-end derives the aggregate
    row from ``runs-index.json`` + ``leaderboard.json`` and disables the
    drill-down link via ``dataset_policies``.

    Uses an unregistered dataset name so ``policy_for`` falls back to
    ``aggregates_only`` — post-sb-dek no shipped adapter remains at that
    tier (OpinionsQA was promoted to ``gated``)."""
    results_dir = tmp_path / "raw"
    results_dir.mkdir()
    (results_dir / "20260101-ddd.json").write_text(
        json.dumps(
            _make_run_result(
                "openrouter/anthropic/claude-haiku-4-5", "aggr_only_fixture"
            )
        )
    )

    out_dir = tmp_path / "site_data"
    uploader, client = _uploader()
    counts = publish_runs(results_dir, out_dir, r2_uploader=uploader)

    # Index entry still counted (the run exists; it just has no drill-down).
    assert counts["runs"] == 1
    # No uploads for aggregates_only.
    assert client.calls == []
    # No local per-run or per-config JSON.
    assert list((out_dir / "run").glob("*.json")) == []
    assert list((out_dir / "config").glob("*.json")) == []
    # But the runs-index carries the aggregate row.
    index = json.loads((out_dir / "runs-index.json").read_text())
    assert index["n_runs"] == 1
    assert index["runs"][0]["dataset"] == "aggr_only_fixture"


def test_publish_runs_runs_index_always_local_even_with_gated_runs(tmp_path: Path):
    """The cross-dataset catalog stays public so the site can route to it."""
    results_dir = tmp_path / "raw"
    results_dir.mkdir()
    (results_dir / "20260101-ccc.json").write_text(
        json.dumps(_make_run_result("openrouter/anthropic/claude-haiku-4-5", "subpop"))
    )

    out_dir = tmp_path / "site_data"
    uploader, _client = _uploader()
    publish_runs(results_dir, out_dir, r2_uploader=uploader)

    index = json.loads((out_dir / "runs-index.json").read_text())
    assert index["n_runs"] == 1
    assert index["runs"][0]["dataset"] == "subpop"
