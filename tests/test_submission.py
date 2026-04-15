"""Unit tests for synthbench.submission (sb-ymux).

The module is the single point of truth for the /submit POST + /submit/<id>
poll HTTP contract shared by `synthbench submit` and
`synthbench run --submit --wait`. These tests exercise the helpers in
isolation so CLI-layer tests can assume the transport works.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from synthbench import submission as sub


VALID_KEY = "sb_" + "a" * 32


# --- resolve_api_key / resolve_api_base ------------------------------------


def test_resolve_api_key_prefers_explicit(monkeypatch):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", "sb_" + "b" * 32)
    assert sub.resolve_api_key(VALID_KEY) == VALID_KEY


def test_resolve_api_key_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("SYNTHBENCH_API_KEY", VALID_KEY)
    assert sub.resolve_api_key(None) == VALID_KEY


def test_resolve_api_key_errors_when_missing(monkeypatch):
    monkeypatch.delenv("SYNTHBENCH_API_KEY", raising=False)
    err = sub.resolve_api_key(None)
    assert isinstance(err, sub.SubmitError)
    assert "no API key" in err.message


def test_resolve_api_key_rejects_non_sb_prefix(monkeypatch):
    monkeypatch.delenv("SYNTHBENCH_API_KEY", raising=False)
    err = sub.resolve_api_key("not-a-key")
    assert isinstance(err, sub.SubmitError)
    assert "sb_" in err.message


def test_resolve_api_base_strips_trailing_slash(monkeypatch):
    monkeypatch.delenv("SYNTHBENCH_API_URL", raising=False)
    assert (
        sub.resolve_api_base("https://api.preview.example/")
        == "https://api.preview.example"
    )


def test_resolve_api_base_defaults_to_production(monkeypatch):
    monkeypatch.delenv("SYNTHBENCH_API_URL", raising=False)
    assert sub.resolve_api_base(None) == sub.DEFAULT_API_URL


# --- post_submission --------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self.text = json.dumps(payload) if not isinstance(payload, str) else payload
        self._payload = payload

    def json(self):
        if isinstance(self._payload, str):
            raise ValueError("not json")
        return self._payload


def _patch_httpx(monkeypatch, post_factory=None, get_factory=None):
    calls: dict[str, list] = {"post": [], "get": []}

    def fake_post(url, content=None, headers=None, timeout=None):
        calls["post"].append(
            {"url": url, "content": content, "headers": headers, "timeout": timeout}
        )
        return (
            post_factory(url)
            if post_factory
            else _FakeResponse(202, {"submission_id": 1, "status": "validating"})
        )

    def fake_get(url, headers=None, timeout=None):
        calls["get"].append({"url": url, "headers": headers, "timeout": timeout})
        return (
            get_factory(url)
            if get_factory
            else _FakeResponse(200, {"status": "validating"})
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)
    return calls


def test_post_submission_happy_path(monkeypatch):
    calls = _patch_httpx(
        monkeypatch,
        post_factory=lambda _u: _FakeResponse(
            202, {"submission_id": 42, "status": "validating", "file_path": "x"}
        ),
    )
    res = sub.post_submission(
        body='{"benchmark":"synthbench"}',
        api_key=VALID_KEY,
        api_base="https://api.example",
    )
    assert isinstance(res, sub.SubmitSuccess)
    assert res.submission_id == 42
    assert res.status == "validating"
    post = calls["post"][0]
    assert post["url"] == "https://api.example/submit"
    assert post["headers"]["Authorization"] == f"Bearer {VALID_KEY}"
    assert post["headers"]["User-Agent"].startswith("synthbench-cli/")
    # Canonical bytes preserved so Worker's Tier-1 validator sees exactly what
    # the caller gave us (no silent re-serialization).
    assert post["content"] == '{"benchmark":"synthbench"}'


def test_post_submission_maps_http_error(monkeypatch):
    _patch_httpx(
        monkeypatch,
        post_factory=lambda _u: _FakeResponse(401, {"error": "unknown api key"}),
    )
    res = sub.post_submission(
        body="{}", api_key=VALID_KEY, api_base="https://api.example"
    )
    assert isinstance(res, sub.SubmitError)
    assert res.status_code == 401
    assert "unknown api key" in res.message
    assert "rejected" in res.hint  # 401 hint text


def test_post_submission_handles_network_error(monkeypatch):
    def boom(*_a, **_kw):
        raise httpx.ConnectError("nope")

    monkeypatch.setattr(httpx, "post", boom)
    res = sub.post_submission(
        body="{}", api_key=VALID_KEY, api_base="https://api.example"
    )
    assert isinstance(res, sub.SubmitError)
    assert res.status_code == 0
    assert "network failure" in res.message


def test_post_submission_unexpected_shape(monkeypatch):
    _patch_httpx(
        monkeypatch,
        post_factory=lambda _u: _FakeResponse(200, {"no_id_here": True}),
    )
    res = sub.post_submission(
        body="{}", api_key=VALID_KEY, api_base="https://api.example"
    )
    assert isinstance(res, sub.SubmitError)
    assert "submission_id" in res.message


# --- poll_submission_status -------------------------------------------------


def test_poll_returns_immediately_on_terminal_published(monkeypatch):
    calls = _patch_httpx(
        monkeypatch,
        get_factory=lambda _u: _FakeResponse(
            200,
            {
                "status": "published",
                "rejection_reason": None,
                "leaderboard_entry_id": "model__dataset",
            },
        ),
    )
    # now() and sleep() are injected so the test never waits. A tight sleep
    # stub also lets us assert we didn't loop more than necessary.
    slept: list[float] = []
    res = sub.poll_submission_status(
        submission_id=1,
        api_key=VALID_KEY,
        api_base="https://api.example",
        interval=5.0,
        timeout=60.0,
        sleep=slept.append,
        now=lambda: 0.0,
    )
    assert isinstance(res, sub.StatusResult)
    assert res.status == "published"
    assert res.leaderboard_entry_id == "model__dataset"
    assert calls["get"][0]["url"] == "https://api.example/submit/1"
    assert calls["get"][0]["headers"]["Authorization"] == f"Bearer {VALID_KEY}"
    assert slept == []  # terminal on first poll → no sleep


def test_poll_returns_rejected_with_reason(monkeypatch):
    _patch_httpx(
        monkeypatch,
        get_factory=lambda _u: _FakeResponse(
            200,
            {"status": "rejected", "rejection_reason": "missing per_question"},
        ),
    )
    res = sub.poll_submission_status(
        submission_id=7,
        api_key=VALID_KEY,
        api_base="https://api.example",
        sleep=lambda _s: None,
        now=lambda: 0.0,
    )
    assert isinstance(res, sub.StatusResult)
    assert res.status == "rejected"
    assert res.rejection_reason == "missing per_question"


def test_poll_times_out_when_never_terminal(monkeypatch):
    _patch_httpx(
        monkeypatch,
        get_factory=lambda _u: _FakeResponse(200, {"status": "validating"}),
    )
    # Inject a monotonic clock that jumps past the deadline on the second tick
    # so we exit deterministically after exactly one poll.
    ticks = iter([0.0, 0.0, 100.0])
    res = sub.poll_submission_status(
        submission_id=1,
        api_key=VALID_KEY,
        api_base="https://api.example",
        interval=1.0,
        timeout=10.0,
        sleep=lambda _s: None,
        now=lambda: next(ticks),
    )
    assert isinstance(res, sub.PollTimeout)
    assert res.last_status == "validating"


def test_poll_surfaces_4xx_error(monkeypatch):
    _patch_httpx(
        monkeypatch,
        get_factory=lambda _u: _FakeResponse(404, {"error": "not found"}),
    )
    res = sub.poll_submission_status(
        submission_id=1,
        api_key=VALID_KEY,
        api_base="https://api.example",
        sleep=lambda _s: None,
        now=lambda: 0.0,
    )
    assert isinstance(res, sub.PollError)
    assert res.status_code == 404
    assert "not found" in res.message


def test_poll_surfaces_network_error(monkeypatch):
    def boom(*_a, **_kw):
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr(httpx, "get", boom)
    res = sub.poll_submission_status(
        submission_id=1,
        api_key=VALID_KEY,
        api_base="https://api.example",
        sleep=lambda _s: None,
        now=lambda: 0.0,
    )
    assert isinstance(res, sub.PollError)
    assert res.status_code == 0


def test_poll_loops_until_terminal_via_callback(monkeypatch):
    # Sequence: validating → validating → published.
    responses = iter(
        [
            _FakeResponse(200, {"status": "validating"}),
            _FakeResponse(200, {"status": "validating"}),
            _FakeResponse(200, {"status": "published", "leaderboard_entry_id": "e"}),
        ]
    )

    def fake_get(_url, headers=None, timeout=None):
        return next(responses)

    monkeypatch.setattr(httpx, "get", fake_get)
    observed: list[str] = []
    res = sub.poll_submission_status(
        submission_id=1,
        api_key=VALID_KEY,
        api_base="https://api.example",
        interval=0.01,
        timeout=60.0,
        sleep=lambda _s: None,
        now=lambda: 0.0,
        on_poll=observed.append,
    )
    assert isinstance(res, sub.StatusResult)
    assert res.status == "published"
    # Callback invoked exactly once per poll including the terminal one.
    assert observed == ["validating", "validating", "published"]


# --- read_run_body + inject_submit_message ---------------------------------


def test_read_run_body_happy_path(tmp_path):
    p = tmp_path / "r.json"
    p.write_text('{"a":1}')
    assert sub.read_run_body(str(p)) == '{"a":1}'


def test_read_run_body_missing_file(tmp_path):
    err = sub.read_run_body(str(tmp_path / "nope.json"))
    assert isinstance(err, sub.SubmitError)
    assert "cannot read" in err.message


def test_read_run_body_bad_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    err = sub.read_run_body(str(p))
    assert isinstance(err, sub.SubmitError)
    assert "not valid JSON" in err.message


def test_inject_submit_message_no_op_when_empty():
    assert sub.inject_submit_message('{"a":1}', None) == '{"a":1}'
    assert sub.inject_submit_message('{"a":1}', "") == '{"a":1}'
    assert sub.inject_submit_message('{"a":1}', "   ") == '{"a":1}'


def test_inject_submit_message_adds_top_level_key():
    out = sub.inject_submit_message('{"a":1}', "first run with new prompt")
    parsed = json.loads(out)
    assert parsed["a"] == 1
    assert parsed["submit_message"] == "first run with new prompt"


def test_inject_submit_message_refuses_non_dict_bodies():
    # Arrays and scalars pass through unchanged rather than silently wrapping
    # them in a dict — caller is responsible for sending a dict body.
    arr = "[1,2,3]"
    assert sub.inject_submit_message(arr, "msg") == arr


@pytest.mark.parametrize(
    "status,fragment",
    [
        (401, "rejected"),
        (403, "submit"),
        (413, "2 MB cap"),
        (429, "rate limit"),
        (500, "server error"),
    ],
)
def test_hint_for_covers_documented_errors(status, fragment):
    # Private helper; stable hint text is load-bearing for the CLI's
    # "Hint: ..." line, so we pin it here.
    hint = sub._hint_for(status)
    assert fragment in hint
