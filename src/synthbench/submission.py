"""HTTP client helpers for `POST /submit` and `GET /submit/<id>` (sb-ymux).

Extracted from the `synthbench submit` CLI so the `synthbench run --submit`
flow and `synthbench submit` share a single, tested implementation of the
Worker round-trip. Neither command needs to know about httpx, auth headers,
or status-code → hint mapping directly.

The functions here return small dataclasses rather than raising, so the
caller can layer its own CLI-specific exit codes on top without catching
HTTP-specific exceptions everywhere.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

import httpx

from synthbench import __version__

DEFAULT_API_URL = "https://api.synthbench.org"

# Terminal states the Worker's GET /submit/<id> can return. Anything else
# (currently just "validating") keeps the --wait poller in its loop.
TERMINAL_STATUSES = frozenset({"published", "rejected"})


@dataclass
class SubmitSuccess:
    submission_id: int
    status: str
    payload: dict[str, Any]


@dataclass
class SubmitError:
    status_code: int
    message: str
    hint: str = ""
    payload: Optional[dict] = None


SubmitOutcome = Union[SubmitSuccess, SubmitError]


def resolve_api_key(cli_value: Optional[str]) -> Union[str, SubmitError]:
    """Return the API key to use, or a structured error for missing/malformed
    keys. Mirrors the validation the `synthbench submit` command already did;
    factored out so `run --submit` can't accidentally diverge."""
    key = cli_value or os.environ.get("SYNTHBENCH_API_KEY")
    if not key:
        return SubmitError(
            status_code=0,
            message="no API key provided. Pass --api-key or set SYNTHBENCH_API_KEY.",
            hint="Generate one at https://synthbench.org/account.",
        )
    if not key.startswith("sb_"):
        return SubmitError(
            status_code=0,
            message="API key must start with 'sb_'. Did you paste a JWT by mistake?",
        )
    return key


def resolve_api_base(cli_value: Optional[str]) -> str:
    """Pick the Worker base URL, normalizing trailing slashes."""
    base = cli_value or os.environ.get("SYNTHBENCH_API_URL") or DEFAULT_API_URL
    return base.rstrip("/")


def _hint_for(status: int) -> str:
    """Translate a Worker HTTP error into a user-visible next step. Matches
    the set of hints the `synthbench submit` CLI already surfaced — kept in
    one place so both callers print consistent error messages."""
    if status == 401:
        return "API key was rejected. Check it's not revoked at /account."
    if status == 403:
        return (
            "API key lacks the 'submit' scope. Generate a new key with submit access."
        )
    if status == 413:
        return "submission exceeded the 2 MB cap."
    if status == 429:
        return "per-key rate limit (60/hr) exceeded. Wait or use another key."
    if status >= 500:
        return "server error. Re-run; if it persists, check status.synthbench.org."
    return ""


def post_submission(
    *,
    body: str,
    api_key: str,
    api_base: str,
    timeout: int = 60,
    user_agent: Optional[str] = None,
) -> SubmitOutcome:
    """POST a canonical submission JSON body to `<api_base>/submit`.

    `body` MUST be the exact string that was saved to disk — we never
    re-serialize because the Worker's Tier-1 check and downstream config_id
    hash depend on the canonical bytes.
    """
    endpoint = f"{api_base}/submit"
    ua = user_agent or f"synthbench-cli/{__version__}"
    try:
        resp = httpx.post(
            endpoint,
            content=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": ua,
            },
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        return SubmitError(status_code=0, message=f"network failure: {exc}")

    try:
        payload = resp.json()
    except ValueError:
        payload = {"raw": resp.text}

    if resp.status_code in (200, 202):
        sub_id = payload.get("submission_id")
        status = payload.get("status", "unknown")
        if not isinstance(sub_id, int):
            return SubmitError(
                status_code=resp.status_code,
                message="server returned an unexpected response shape (no submission_id).",
                payload=payload if isinstance(payload, dict) else None,
            )
        return SubmitSuccess(submission_id=sub_id, status=status, payload=payload)

    error_msg = (
        payload.get("error", resp.text or "unknown error")
        if isinstance(payload, dict)
        else (resp.text or "unknown error")
    )
    return SubmitError(
        status_code=resp.status_code,
        message=str(error_msg),
        hint=_hint_for(resp.status_code),
        payload=payload if isinstance(payload, dict) else None,
    )


@dataclass
class StatusResult:
    status: str
    rejection_reason: Optional[str]
    leaderboard_entry_id: Optional[str]
    payload: dict


@dataclass
class PollTimeout:
    last_status: str


@dataclass
class PollError:
    status_code: int
    message: str


PollOutcome = Union[StatusResult, PollTimeout, PollError]


def poll_submission_status(
    *,
    submission_id: int,
    api_key: str,
    api_base: str,
    interval: float = 5.0,
    timeout: float = 600.0,
    http_timeout: int = 30,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
    on_poll: Optional[Callable[[str], None]] = None,
) -> PollOutcome:
    """Block on `GET /submit/<id>` until the row hits a terminal state or
    `timeout` elapses.

    Yields control back to `sleep()` between polls so tests can stub time
    without actually waiting. Returns a `StatusResult` on terminal, a
    `PollTimeout` when the budget is exhausted (the caller surfaces exit
    code 2), or a `PollError` for unrecoverable HTTP failures.
    """
    endpoint = f"{api_base}/submit/{submission_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": f"synthbench-cli/{__version__}",
    }
    deadline = now() + timeout
    last_status = "unknown"
    while True:
        try:
            resp = httpx.get(endpoint, headers=headers, timeout=http_timeout)
        except httpx.HTTPError as exc:
            return PollError(status_code=0, message=f"network failure: {exc}")

        if resp.status_code == 200:
            try:
                payload = resp.json()
            except ValueError:
                return PollError(
                    status_code=200,
                    message="server returned non-JSON status body",
                )
            status = str(payload.get("status", "unknown"))
            last_status = status
            if on_poll is not None:
                on_poll(status)
            if status in TERMINAL_STATUSES:
                return StatusResult(
                    status=status,
                    rejection_reason=payload.get("rejection_reason"),
                    leaderboard_entry_id=payload.get("leaderboard_entry_id"),
                    payload=payload if isinstance(payload, dict) else {},
                )
        else:
            # 4xx: no point retrying — api key rejected, row gone, etc. 5xx we
            # *could* retry, but a Worker 5xx is usually Supabase flaking and
            # the benchmark JSON is safe on disk, so a clean surface-and-exit
            # is kinder than silent spin.
            try:
                payload = resp.json()
            except ValueError:
                payload = {}
            msg = (
                payload.get("error", resp.text or "unknown error")
                if isinstance(payload, dict)
                else resp.text or "unknown error"
            )
            return PollError(status_code=resp.status_code, message=str(msg))

        if now() >= deadline:
            return PollTimeout(last_status=last_status)
        sleep(interval)


def read_run_body(path: str) -> Union[str, SubmitError]:
    """Load a saved benchmark JSON file. Separate from `post_submission` so
    a run that generated the file in-memory can skip the round-trip through
    disk."""
    from pathlib import Path

    p = Path(path)
    try:
        text = p.read_text()
    except OSError as exc:
        return SubmitError(status_code=0, message=f"cannot read {p}: {exc}")
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        return SubmitError(status_code=0, message=f"{p} is not valid JSON: {exc}")
    return text


def inject_submit_message(body: str, message: Optional[str]) -> str:
    """Stamp `--submit-message` onto an in-memory submission body.

    Stored at top level (`submit_message`) rather than under `config` so it
    can't affect the canonical config_id hash, which only reads a fixed set
    of config keys. Empty/whitespace-only messages are ignored so the field
    is never added as a no-op placeholder.
    """
    if not message or not message.strip():
        return body
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return body
    if not isinstance(data, dict):
        return body
    data["submit_message"] = message
    return json.dumps(data, sort_keys=False, separators=(",", ":"))
