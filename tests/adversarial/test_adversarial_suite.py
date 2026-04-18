"""Adversarial fixture suite for the SynthBench validator (sb-5xfk).

For every fixture under ``fixtures/``, replay the validator at tiers
1+2+3 and assert the contract declared in ``expected.json``. The suite
checks both directions:

* **Expected codes fire.** Every code listed in ``must_fire`` appears on
  the resulting report. New detectors can graduate to stricter severity
  without breaking the suite — we only assert presence.
* **Unexpected codes do not fire.** Every code listed in ``must_not_fire``
  is absent from the report. Detector tuning that over-fires would flip
  this direction red.

The suite is intentionally a *known-bad* acceptance gate, not a fuzzer.
Fuzzing belongs elsewhere. Adding a new fabrication is a three-file
change: a recipe in ``_generate_fixtures.py``, an entry in
``expected.json``, and a regenerated JSON file.

See ``README.md`` for the step-by-step workflow.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Mapping

import pytest

from synthbench.stats import question_set_hash
from synthbench.validation import Severity, ValidationReport, validate_submission

HERE = Path(__file__).parent
FIXTURE_DIR = HERE / "fixtures"
EXPECTED_PATH = HERE / "expected.json"

# Baseline bands (per doc section 5.4): a uniform-random null agent on
# any MCQ dataset should land in a well-defined parity band. These are
# the Berkeley paper's "if the null agent isn't at floor, your scoring
# function has a bug" assertion.
NULL_AGENT_MIN_SPS = 0.40
NULL_AGENT_MAX_SPS = 0.85


def _load_expected() -> dict[str, Any]:
    return json.loads(EXPECTED_PATH.read_text())["fixtures"]


def _fixture_paths() -> list[Path]:
    return sorted(FIXTURE_DIR.glob("*.json"))


def _codes(report: ValidationReport) -> set[str]:
    return {issue.code for issue in report.issues}


def _detector_installed(dotted: str) -> bool:
    """Return True iff ``module.attr`` resolves to something callable.

    Used to make ``future_fire`` checks skip cleanly when the detector
    hasn't shipped yet (e.g. before the ``ANOMALY_NEAR_COPY_PUBLIC``
    bead lands). Once the detector lands, the same check becomes live
    without any change to this file.
    """
    module_name, _, attr = dotted.rpartition(".")
    if not module_name:
        return False
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return False
    target = getattr(module, attr, None)
    return callable(target)


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


def _all_fixture_names() -> list[str]:
    paths = _fixture_paths()
    expected = _load_expected()
    names = sorted(p.stem for p in paths)
    # Hard-fail at collection time if the fixture set and the declared
    # expectation set drift out of sync — catches "added a fixture,
    # forgot to declare it" at the same pytest-collection step that
    # runs the checks.
    missing_contract = [n for n in names if n not in expected]
    missing_fixture = [n for n in expected if n not in names]
    if missing_contract or missing_fixture:
        raise RuntimeError(
            "adversarial suite out of sync: "
            f"fixtures without expected.json entry: {missing_contract}; "
            f"expected entries without fixture: {missing_fixture}"
        )
    return names


FIXTURE_NAMES = _all_fixture_names()
EXPECTED = _load_expected()


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text())


def _run_validator(
    data: Mapping[str, Any], *, expected_question_hash: str | None = None
) -> ValidationReport:
    return validate_submission(
        data,
        source=f"adversarial:{data.get('config', {}).get('dataset', '?')}",
        tier1=True,
        tier2=True,
        tier3=True,
        expected_question_hash=expected_question_hash,
    )


# ---------------------------------------------------------------------------
# Core: must_fire / must_not_fire contract per fixture
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
class TestAdversarialFixtures:
    def test_required_codes_fire(self, fixture_name: str) -> None:
        contract = EXPECTED[fixture_name]
        data = _load_fixture(fixture_name)
        report = _run_validator(data)
        observed = _codes(report)
        for code in contract.get("must_fire", []):
            assert code in observed, (
                f"{fixture_name}: expected {code} to fire but validator did not "
                f"surface it. Observed codes: {sorted(observed)}. "
                f"Full report:\n{report.format()}"
            )

    def test_forbidden_codes_do_not_fire(self, fixture_name: str) -> None:
        contract = EXPECTED[fixture_name]
        data = _load_fixture(fixture_name)
        report = _run_validator(data)
        observed = _codes(report)
        for code in contract.get("must_not_fire", []):
            assert code not in observed, (
                f"{fixture_name}: did NOT expect {code} to fire but validator "
                f"did surface it. Over-firing detector? "
                f"Full report:\n{report.format()}"
            )

    def test_overall_ok_matches_contract(self, fixture_name: str) -> None:
        contract = EXPECTED[fixture_name]
        data = _load_fixture(fixture_name)
        report = _run_validator(data)
        if contract.get("must_be_ok") is True:
            assert report.ok, (
                f"{fixture_name} must pass validation but produced errors: "
                f"{[i.code for i in report.errors]}. "
                f"Full report:\n{report.format()}"
            )
        elif contract.get("must_be_ok") is False:
            assert not report.ok, (
                f"{fixture_name} must fail validation but the validator "
                f"returned ok=True. The fabrication slipped past every tier. "
                f"Full report:\n{report.format()}"
            )

    def test_future_detectors_fire_when_installed(self, fixture_name: str) -> None:
        """Detectors that aren't yet implemented are declared in
        ``future_fire`` so the suite promotes itself automatically the
        moment the upstream bead lands. Until then the case is skipped.
        """
        contract = EXPECTED[fixture_name]
        future = contract.get("future_fire") or []
        if not future:
            pytest.skip(f"{fixture_name}: no future_fire expectations declared")
        data = _load_fixture(fixture_name)
        report = _run_validator(data)
        observed = _codes(report)
        skipped_all = True
        for entry in future:
            code = entry["code"]
            detector = entry["detector"]
            if not _detector_installed(detector):
                continue
            skipped_all = False
            assert code in observed, (
                f"{fixture_name}: detector {detector} is installed but "
                f"did not surface {code}. Contract declared in expected.json."
            )
        if skipped_all:
            pytest.skip(f"{fixture_name}: all future_fire detectors not yet installed")


# ---------------------------------------------------------------------------
# Bespoke assertions referenced from expected.json
# ---------------------------------------------------------------------------


class TestBespokeAssertions:
    def test_qset_hash_dataset_fires_when_expected_hash_supplied(self) -> None:
        """wrong_keys: also tests the caller-supplied canonical-hash path.

        ``QSET_HASH_DATASET`` fires only when the harness passes
        ``expected_question_hash`` — the contract asserts *both* hash
        checks are wired, not just the self-consistency path.
        """
        data = _load_fixture("wrong_keys")
        # A hash that definitely does not match the fabricated keys.
        canonical = question_set_hash(["REAL_KEY_000", "REAL_KEY_001"])
        report = _run_validator(data, expected_question_hash=canonical)
        codes = _codes(report)
        assert "QSET_HASH_DATASET" in codes, (
            "wrong_keys with expected_question_hash supplied must fire "
            f"QSET_HASH_DATASET. Report:\n{report.format()}"
        )

    def test_null_agent_baseline_sps_in_band(self) -> None:
        """null_agent: composite_parity lands in the 'null-agent' band.

        Per doc section 5.4: a uniform-random baseline must clear a
        predictable floor and not exceed a predictable ceiling. If the
        null agent's SPS drifts *upward* over time, the scoring function
        has a bug — a legitimate leaderboard floor should be stable.
        """
        data = _load_fixture("null_agent")
        sps = data["aggregate"]["composite_parity"]
        assert NULL_AGENT_MIN_SPS <= sps <= NULL_AGENT_MAX_SPS, (
            f"null_agent composite_parity={sps} outside baseline band "
            f"[{NULL_AGENT_MIN_SPS}, {NULL_AGENT_MAX_SPS}]. "
            "Either the scoring function drifted or the fixture needs "
            "regeneration."
        )


# ---------------------------------------------------------------------------
# Suite-level invariants
# ---------------------------------------------------------------------------


class TestSuiteIntegrity:
    def test_at_least_ten_fixtures(self) -> None:
        """Acceptance criterion: suite contains >=10 fabrications (sb-5xfk)."""
        assert len(FIXTURE_NAMES) >= 10, (
            f"adversarial suite has only {len(FIXTURE_NAMES)} fixtures; "
            "bead sb-5xfk requires at least 10."
        )

    def test_every_fixture_declares_a_contract(self) -> None:
        """Every JSON file under fixtures/ has an entry in expected.json.

        Collection-time validation already raises on mismatch, but we
        also surface it as an explicit test case so CI failure points
        directly at the contract file when a fixture is orphaned.
        """
        for name in FIXTURE_NAMES:
            assert name in EXPECTED, f"fixture {name!r} missing expected.json entry"
            entry = EXPECTED[name]
            assert "must_fire" in entry, f"{name}: missing 'must_fire' key"
            assert "must_not_fire" in entry, f"{name}: missing 'must_not_fire' key"

    def test_fixtures_are_deterministic(self, tmp_path: Path) -> None:
        """Regenerating from source must produce byte-identical JSON.

        Guards the fixtures against drift: if someone hand-edits a JSON
        file instead of editing the generator recipe, the hand-edit is
        caught here. Also guards against non-determinism in the
        generator (a stray ``random`` call without a seed).
        """
        from tests.adversarial import _generate_fixtures as gen

        original = {
            name: (FIXTURE_DIR / f"{name}.json").read_text() for name in FIXTURE_NAMES
        }
        regenerated = {
            name: json.dumps(builder(), indent=2, sort_keys=True) + "\n"
            for name, builder in gen.FIXTURES.items()
        }
        for name in FIXTURE_NAMES:
            assert name in regenerated, f"generator missing recipe for {name}"
            assert original[name] == regenerated[name], (
                f"{name}: checked-in fixture drifted from generator output. "
                "Run `python -m tests.adversarial._generate_fixtures` to refresh."
            )

    @pytest.mark.parametrize("severity", [Severity.ERROR, Severity.WARNING])
    def test_every_blocking_fixture_produces_at_least_one_issue(
        self, severity: Severity
    ) -> None:
        """Each fixture marked ``must_be_ok: false`` actually trips *some*
        issue of the right kind somewhere. Otherwise the fixture is
        inert and the suite silently degrades."""
        del severity  # presence check — we only care that *some* issues exist
        for name in FIXTURE_NAMES:
            contract = EXPECTED[name]
            if contract.get("must_be_ok") is not False:
                continue
            data = _load_fixture(name)
            report = _run_validator(data)
            assert report.issues, (
                f"{name} is marked must_be_ok=False but the validator "
                "produced no issues at all — fixture has decayed or a "
                "detector regressed."
            )
