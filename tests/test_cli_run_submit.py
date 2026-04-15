"""Tests for `synthbench run --submit [--wait]` (sb-ymux).

The tests here deliberately split into two layers:

  1. Click-layer validation (e.g. `--wait` requires `--submit`) — asserted
     via `CliRunner.invoke(main, ["run", ...])` so we catch flag contracts
     without spinning up the benchmark runner.
  2. `_submit_and_maybe_wait` helper called directly on a pre-written JSON
     file, with httpx double-patched — this is where the post+poll+exit-code
     contract is pinned.

We stop short of running the full `run` command end-to-end (which would
require real datasets and providers); those paths are covered by the
existing `test_runner.py` + `test_cli_submit.py` suites.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from click.testing import CliRunner

from synthbench import submission as sub
from synthbench.cli import _submit_and_maybe_wait, main


VALID_KEY = "sb_" + "a" * 32


def _write_result(tmp_path) -> "Any":
    # Shape matches the Tier-1 schema the Worker enforces so the test stays
    # valid if we ever swap the double for a tiny real Worker.
    p = tmp_path / "openrouter_haiku_opinionsqa.json"
    p.write_text(
        json.dumps(
            {
                "benchmark": "synthbench",
                "config": {"provider": "openrouter", "model": "haiku"},
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
    return p


class _FakeResponse:
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self.text = json.dumps(payload) if not isinstance(payload, str) else payload
        self._payload = payload

    def json(self):
        if isinstance(self._payload, str):
            raise ValueError("not json")
        return self._payload


# --- Click-layer flag validation ------------------------------------------


def test_run_refuses_wait_without_submit():
    res = CliRunner().invoke(main, ["run", "-p", "random", "--wait"])
    assert res.exit_code == 2
    assert "--wait requires --submit" in res.output


def test_run_refuses_submit_message_without_submit():
    res = CliRunner().invoke(main, ["run", "-p", "random", "--submit-message", "x"])
    assert res.exit_code == 2
    assert "--submit-message requires --submit" in res.output


def test_run_refuses_submit_with_json_only():
    res = CliRunner().invoke(main, ["run", "-p", "random", "--submit", "--json-only"])
    assert res.exit_code == 2
    assert "incompatible with --json-only" in res.output


# --- _submit_and_maybe_wait end-to-end -------------------------------------


def _patch(monkeypatch, *, post_factory, get_factory=None):
    """Install httpx doubles. Returns call-capture dict for assertions."""
    calls: dict[str, list[dict[str, Any]]] = {"post": [], "get": []}

    def fake_post(url, content=None, headers=None, timeout=None):
        calls["post"].append(
            {"url": url, "content": content, "headers": headers, "timeout": timeout}
        )
        return post_factory(url)

    def fake_get(url, headers=None, timeout=None):
        calls["get"].append({"url": url, "headers": headers, "timeout": timeout})
        if get_factory is None:
            raise AssertionError("--wait path unexpectedly polled")
        return get_factory(url)

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)
    return calls


def test_submit_and_wait_exits_0_on_published(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    monkeypatch.delenv("SYNTHBENCH_API_URL", raising=False)
    result_file = _write_result(tmp_path)
    calls = _patch(
        monkeypatch,
        post_factory=lambda _u: _FakeResponse(
            202, {"submission_id": 42, "status": "validating"}
        ),
        get_factory=lambda _u: _FakeResponse(
            200,
            {
                "status": "published",
                "rejection_reason": None,
                "leaderboard_entry_id": "haiku__opinionsqa",
            },
        ),
    )

    # `published` is the success path — the helper returns normally so the
    # CLI wrapper's implicit exit code is 0.
    _submit_and_maybe_wait(
        json_path=result_file,
        submit_api_key=None,
        submit_api_url=None,
        submit_message=None,
        submit_timeout=30,
        wait=True,
        poll_interval=0.0,
        poll_timeout=60.0,
    )

    assert calls["post"][0]["url"] == "https://api.synthbench.org/submit"
    assert calls["get"][0]["url"] == "https://api.synthbench.org/submit/42"


def test_submit_and_wait_exits_0_when_already_published_on_first_poll(
    tmp_path, monkeypatch, capsys
):
    # Tighter variant of the happy-path test: no explicit SystemExit expected
    # because `_submit_and_maybe_wait` returns cleanly on `published`.
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    monkeypatch.delenv("SYNTHBENCH_API_URL", raising=False)
    result_file = _write_result(tmp_path)
    _patch(
        monkeypatch,
        post_factory=lambda _u: _FakeResponse(
            202, {"submission_id": 1, "status": "validating"}
        ),
        get_factory=lambda _u: _FakeResponse(
            200, {"status": "published", "leaderboard_entry_id": "e"}
        ),
    )
    # No SystemExit on published — just a successful return.
    _submit_and_maybe_wait(
        json_path=result_file,
        submit_api_key=None,
        submit_api_url=None,
        submit_message=None,
        submit_timeout=30,
        wait=True,
        poll_interval=0.0,
        poll_timeout=60.0,
    )
    out = capsys.readouterr().err
    assert "published" in out


def test_submit_and_wait_exits_1_on_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    monkeypatch.delenv("SYNTHBENCH_API_URL", raising=False)
    result_file = _write_result(tmp_path)
    _patch(
        monkeypatch,
        post_factory=lambda _u: _FakeResponse(
            202, {"submission_id": 1, "status": "validating"}
        ),
        get_factory=lambda _u: _FakeResponse(
            200,
            {
                "status": "rejected",
                "rejection_reason": "per_question length mismatch",
            },
        ),
    )
    with pytest.raises(SystemExit) as exc:
        _submit_and_maybe_wait(
            json_path=result_file,
            submit_api_key=None,
            submit_api_url=None,
            submit_message=None,
            submit_timeout=30,
            wait=True,
            poll_interval=0.0,
            poll_timeout=60.0,
        )
    assert exc.value.code == 1


def test_submit_and_wait_exits_2_on_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    monkeypatch.delenv("SYNTHBENCH_API_URL", raising=False)
    result_file = _write_result(tmp_path)
    _patch(
        monkeypatch,
        post_factory=lambda _u: _FakeResponse(
            202, {"submission_id": 1, "status": "validating"}
        ),
        get_factory=lambda _u: _FakeResponse(200, {"status": "validating"}),
    )
    # Tiny budget so the poller gives up on its first iteration deterministically.
    with pytest.raises(SystemExit) as exc:
        _submit_and_maybe_wait(
            json_path=result_file,
            submit_api_key=None,
            submit_api_url=None,
            submit_message=None,
            submit_timeout=30,
            wait=True,
            poll_interval=0.0,
            poll_timeout=0.0,
        )
    assert exc.value.code == 2


def test_submit_without_wait_returns_after_post(tmp_path, monkeypatch, capsys):
    # No GET calls allowed — --wait is off, so the helper must return as soon
    # as it gets a submission_id back.
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    monkeypatch.delenv("SYNTHBENCH_API_URL", raising=False)
    result_file = _write_result(tmp_path)
    calls = _patch(
        monkeypatch,
        post_factory=lambda _u: _FakeResponse(
            202, {"submission_id": 7, "status": "validating"}
        ),
        # get_factory=None causes an assertion if polling happens.
        get_factory=None,
    )
    _submit_and_maybe_wait(
        json_path=result_file,
        submit_api_key=None,
        submit_api_url=None,
        submit_message=None,
        submit_timeout=30,
        wait=False,
        poll_interval=0.0,
        poll_timeout=0.0,
    )
    assert len(calls["get"]) == 0
    assert "submitted (id=7" in capsys.readouterr().err


def test_submit_message_is_injected_into_uploaded_body(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    monkeypatch.delenv("SYNTHBENCH_API_URL", raising=False)
    result_file = _write_result(tmp_path)
    calls = _patch(
        monkeypatch,
        post_factory=lambda _u: _FakeResponse(
            202, {"submission_id": 1, "status": "validating"}
        ),
    )
    _submit_and_maybe_wait(
        json_path=result_file,
        submit_api_key=None,
        submit_api_url=None,
        submit_message="first pass with new prompt template",
        submit_timeout=30,
        wait=False,
        poll_interval=0.0,
        poll_timeout=0.0,
    )
    sent = calls["post"][0]["content"]
    parsed = json.loads(sent)
    assert parsed["submit_message"] == "first pass with new prompt template"
    # Original fields still present — we don't clobber the canonical schema.
    assert parsed["benchmark"] == "synthbench"
    # And the file on disk is untouched — the injection happens in-memory.
    on_disk = json.loads(result_file.read_text())
    assert "submit_message" not in on_disk


def test_post_failure_exits_1_with_hint(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    monkeypatch.delenv("SYNTHBENCH_API_URL", raising=False)
    result_file = _write_result(tmp_path)
    _patch(
        monkeypatch,
        post_factory=lambda _u: _FakeResponse(401, {"error": "unknown api key"}),
    )
    with pytest.raises(SystemExit) as exc:
        _submit_and_maybe_wait(
            json_path=result_file,
            submit_api_key=None,
            submit_api_url=None,
            submit_message=None,
            submit_timeout=30,
            wait=True,  # wait set, but we should never reach polling
            poll_interval=0.0,
            poll_timeout=60.0,
        )
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "HTTP 401" in err
    assert "rejected" in err  # 401 hint


def test_missing_api_key_exits_2(tmp_path, monkeypatch):
    # Matches `synthbench submit`'s exit code for the same class of error —
    # surfacing it the same way keeps CI scripts that branch on exit codes
    # portable between the two commands.
    monkeypatch.delenv("SYNTHBENCH_API_KEY", raising=False)
    monkeypatch.delenv("SYNTHBENCH_API_URL", raising=False)
    result_file = _write_result(tmp_path)
    with pytest.raises(SystemExit) as exc:
        _submit_and_maybe_wait(
            json_path=result_file,
            submit_api_key=None,
            submit_api_url=None,
            submit_message=None,
            submit_timeout=30,
            wait=False,
            poll_interval=0.0,
            poll_timeout=0.0,
        )
    assert exc.value.code == 2


def test_bad_result_file_exits_1(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    monkeypatch.delenv("SYNTHBENCH_API_URL", raising=False)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(SystemExit) as exc:
        _submit_and_maybe_wait(
            json_path=bad,
            submit_api_key=None,
            submit_api_url=None,
            submit_message=None,
            submit_timeout=30,
            wait=False,
            poll_interval=0.0,
            poll_timeout=0.0,
        )
    assert exc.value.code == 1


def test_forwarded_headers_include_user_agent(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    monkeypatch.delenv("SYNTHBENCH_API_URL", raising=False)
    result_file = _write_result(tmp_path)
    calls = _patch(
        monkeypatch,
        post_factory=lambda _u: _FakeResponse(
            202, {"submission_id": 1, "status": "validating"}
        ),
    )
    _submit_and_maybe_wait(
        json_path=result_file,
        submit_api_key=None,
        submit_api_url=None,
        submit_message=None,
        submit_timeout=30,
        wait=False,
        poll_interval=0.0,
        poll_timeout=0.0,
    )
    headers = calls["post"][0]["headers"]
    assert headers["User-Agent"].startswith("synthbench-cli/")
    assert headers["Content-Type"] == "application/json"


def test_flag_override_for_api_url(tmp_path, monkeypatch):
    # Trailing slash normalization + flag-over-env precedence.
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    monkeypatch.setenv("SYNTHBENCH_API_URL", "https://should-not-be-used.example")
    result_file = _write_result(tmp_path)
    calls = _patch(
        monkeypatch,
        post_factory=lambda _u: _FakeResponse(
            202, {"submission_id": 1, "status": "validating"}
        ),
    )
    _submit_and_maybe_wait(
        json_path=result_file,
        submit_api_key=None,
        submit_api_url="https://api.preview.example/",
        submit_message=None,
        submit_timeout=30,
        wait=False,
        poll_interval=0.0,
        poll_timeout=0.0,
    )
    assert calls["post"][0]["url"] == "https://api.preview.example/submit"


def test_terminal_statuses_frozen():
    # Pinning the contract: the Worker's status field → poller's terminal
    # mapping should never accept "validating" as terminal. If the backend
    # ever adds a new state, this test forces the CLI to explicitly decide
    # what exit code maps to it.
    assert sub.TERMINAL_STATUSES == frozenset({"published", "rejected"})
