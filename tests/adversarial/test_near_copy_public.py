"""Adversarial fixtures for :code:`ANOMALY_NEAR_COPY_PUBLIC` (sb-hbgz).

Each fixture is a complete, tier-1/2-consistent submission that would
have slipped past the validator before the near-copy detector shipped.
These tests assert that the detector catches the fabrication (ERROR),
and as a regression guard against threshold regressions, that real
leaderboard submissions still pass.

Regenerate the fixtures with::

    PYTHONPATH=src python3 tests/adversarial/build_fixtures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from synthbench.anomaly import check_near_copy_public
from synthbench.validation import Severity, validate_file

FIXTURES = Path(__file__).resolve().parent / "fixtures"
LEADERBOARD = Path(__file__).resolve().parents[2] / "leaderboard-results"


@pytest.mark.parametrize(
    "fixture_name",
    ["near_pure_copy.json", "public_copy_fake_private.json"],
)
def test_fixture_fails_with_near_copy_error(fixture_name: str) -> None:
    """Each adversarial fixture must fail validation with an ERROR-severity
    ``ANOMALY_NEAR_COPY_PUBLIC`` issue. The detector is the whole point of
    these fixtures — other errors would mean tier-1/2 got there first and
    the new detector never ran."""
    path = FIXTURES / fixture_name
    assert path.is_file(), f"fixture missing: {path} (run build_fixtures.py)"

    report = validate_file(path, tier1=True, tier2=True, tier3=True)

    near_copy = [i for i in report.issues if i.code == "ANOMALY_NEAR_COPY_PUBLIC"]
    assert len(near_copy) == 1, (
        f"expected exactly one ANOMALY_NEAR_COPY_PUBLIC issue, got "
        f"{[(i.code, i.severity.value) for i in report.issues]}"
    )
    assert near_copy[0].severity is Severity.ERROR
    assert not report.ok, "fixture must fail validation overall"


@pytest.mark.parametrize(
    "provider_match",
    [
        "claude-haiku-4-5",
        "claude-sonnet-4",
        "gpt-4o-mini",  # closest stand-in for gpt-5 in checked-in leaderboard
    ],
)
def test_real_submissions_not_flagged(provider_match: str) -> None:
    """Real submissions for representative providers must not trip the
    detector. If this ever fires, either the thresholds drifted too
    conservative or the detector's holdout-subset logic regressed."""
    if not LEADERBOARD.is_dir():
        pytest.skip("leaderboard-results/ not present in this worktree")

    matches = sorted(LEADERBOARD.glob(f"*{provider_match}*.json"))
    if not matches:
        pytest.skip(f"no leaderboard fixture matching {provider_match}")

    flagged: list[tuple[str, str]] = []
    for path in matches:
        data = json.loads(path.read_text())
        if data.get("benchmark") != "synthbench":
            continue
        issue = check_near_copy_public(data)
        if issue is not None:
            flagged.append((path.name, issue.message))

    assert not flagged, (
        f"real submissions for {provider_match} tripped ANOMALY_NEAR_COPY_PUBLIC: "
        f"{flagged}"
    )
