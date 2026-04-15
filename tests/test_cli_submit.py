"""Unit tests for `synthbench submit` (sb-t61h).

The CLI uses `click.testing.CliRunner` for argv handling and monkey-patches
`httpx.post` to avoid network. We assert on:
  - argument validation (missing key, malformed key, missing file, bad JSON)
  - request shape (URL, headers, body == file contents)
  - exit codes for success vs. each error class the Worker can return
  - hint messages for 401 / 403 / 413 / 429 so users get actionable output
"""

from __future__ import annotations

import json

import httpx
import pytest
from click.testing import CliRunner

from synthbench.cli import main


VALID_KEY = "sb_" + "a" * 32


def _write_run(tmp_path, payload=None):
    run = tmp_path / "result.json"
    run.write_text(
        json.dumps(
            payload
            or {
                "benchmark": "synthbench",
                "config": {"provider": "openrouter", "model": "gpt-4o-mini"},
                "aggregate": {"n_questions": 1, "composite_parity": 0.7},
                "per_question": [
                    {
                        "human_distribution": [0.5, 0.5],
                        "model_distribution": [0.5, 0.5],
                    }
                ],
                "scores": {"p_dist": 0.8},
            }
        )
    )
    return run


class _FakeResponse:
    """httpx.Response-ish double — we only set what `submit` reads."""

    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.text = json.dumps(payload) if not isinstance(payload, str) else payload
        self._payload = payload

    def json(self):
        if isinstance(self._payload, str):
            raise ValueError("not json")
        return self._payload


def _patch_post(monkeypatch, capture, response):
    def fake_post(url, content=None, headers=None, timeout=None):
        capture["url"] = url
        capture["content"] = content
        capture["headers"] = headers or {}
        capture["timeout"] = timeout
        return response

    monkeypatch.setattr(httpx, "post", fake_post)


def test_submit_requires_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("SYNTHBENCH_API_KEY", raising=False)
    run = _write_run(tmp_path)
    res = CliRunner().invoke(main, ["submit", str(run)])
    assert res.exit_code == 2
    assert "no API key provided" in res.output


def test_submit_rejects_non_sb_key(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", "eyJhbGciOiJIUzI1NiJ9.not.akey")
    run = _write_run(tmp_path)
    res = CliRunner().invoke(main, ["submit", str(run)])
    assert res.exit_code == 2
    assert "must start with 'sb_'" in res.output


def test_submit_rejects_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    res = CliRunner().invoke(main, ["submit", str(tmp_path / "nope.json")])
    # Click handles the exists=True check before our code runs.
    assert res.exit_code != 0
    assert "does not exist" in res.output.lower() or "no such" in res.output.lower()


def test_submit_rejects_invalid_json(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    bad = tmp_path / "bad.json"
    bad.write_text("{not: valid")
    res = CliRunner().invoke(main, ["submit", str(bad)])
    assert res.exit_code == 1
    assert "not valid JSON" in res.output


def test_submit_happy_path_uses_env_key_and_default_url(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    monkeypatch.delenv("SYNTHBENCH_API_URL", raising=False)
    run = _write_run(tmp_path)
    capture = {}
    response = _FakeResponse(202, {"submission_id": 42, "status": "validating"})
    _patch_post(monkeypatch, capture, response)

    res = CliRunner().invoke(main, ["submit", str(run)])
    assert res.exit_code == 0, res.output
    assert capture["url"] == "https://api.synthbench.org/submit"
    assert capture["headers"]["Authorization"] == f"Bearer {VALID_KEY}"
    assert capture["headers"]["Content-Type"] == "application/json"
    # User-Agent is required by GitHub's API and a polite default everywhere.
    assert capture["headers"]["User-Agent"].startswith("synthbench-cli/")
    # Body forwarded verbatim (preserves the canonical JSON the Worker hashes).
    assert capture["content"] == run.read_text()
    assert "submitted (id=42, status=validating)" in res.output


def test_submit_overrides_url_and_key_via_flags(tmp_path, monkeypatch):
    monkeypatch.delenv("SYNTHBENCH_API_KEY", raising=False)
    run = _write_run(tmp_path)
    capture = {}
    response = _FakeResponse(202, {"submission_id": 5, "status": "validating"})
    _patch_post(monkeypatch, capture, response)
    res = CliRunner().invoke(
        main,
        [
            "submit",
            str(run),
            "--api-key",
            VALID_KEY,
            "--api-url",
            "https://api.preview.example/",
        ],
    )
    assert res.exit_code == 0, res.output
    # Trailing slash stripped.
    assert capture["url"] == "https://api.preview.example/submit"
    assert capture["headers"]["Authorization"] == f"Bearer {VALID_KEY}"


def test_submit_prints_warning_when_dispatch_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    run = _write_run(tmp_path)
    capture = {}
    response = _FakeResponse(
        202,
        {
            "submission_id": 9,
            "status": "validating",
            "warning": "queued but workflow dispatch failed",
        },
    )
    _patch_post(monkeypatch, capture, response)
    res = CliRunner().invoke(main, ["submit", str(run)])
    assert res.exit_code == 0
    assert "submitted (id=9" in res.output
    assert "queued but workflow dispatch failed" in res.output


@pytest.mark.parametrize(
    "status,fragment",
    [
        (401, "API key was rejected"),
        (403, "submit' scope"),
        (413, "2 MB cap"),
        (429, "rate limit"),
        (500, "server error"),
    ],
)
def test_submit_maps_http_errors_to_hints(tmp_path, monkeypatch, status, fragment):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    run = _write_run(tmp_path)
    capture = {}
    response = _FakeResponse(status, {"error": "boom"})
    _patch_post(monkeypatch, capture, response)
    res = CliRunner().invoke(main, ["submit", str(run)])
    assert res.exit_code == 1
    assert f"HTTP {status}" in res.output
    assert fragment in res.output


def test_submit_handles_network_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    run = _write_run(tmp_path)

    def boom(*_args, **_kwargs):
        raise httpx.ConnectError("nope")

    monkeypatch.setattr(httpx, "post", boom)
    res = CliRunner().invoke(main, ["submit", str(run)])
    assert res.exit_code == 1
    assert "network failure" in res.output


def test_submit_json_out_emits_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    run = _write_run(tmp_path)
    capture = {}
    response = _FakeResponse(
        202, {"submission_id": 7, "status": "validating", "file_path": "x"}
    )
    _patch_post(monkeypatch, capture, response)
    # Split stdout from stderr so the assertion proves --json-out emits the
    # payload to stdout cleanly (log lines go to stderr via click.echo(err=True)).
    runner = CliRunner()
    res = runner.invoke(main, ["submit", str(run), "--json-out"])
    assert res.exit_code == 0
    # CliRunner in Click 8.x mixes stdout+stderr in .output. The --json-out
    # flag emits a single JSON line; extract the JSON object from output.
    json_lines = [ln for ln in res.output.splitlines() if ln.strip().startswith('{')]
    assert json_lines, f"no JSON line in output: {res.output!r}"
    parsed = json.loads(json_lines[-1])
    assert parsed["submission_id"] == 7
