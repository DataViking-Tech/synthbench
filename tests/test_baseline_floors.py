"""CI gate: null-agent baseline SPS floors (sb-lhoh).

Per Berkeley paper recommendation (via docs/benchmark-hardening-analysis.md
§5.4), null-agent baseline composite_parity must stay bounded. Upward
drift on a stable dataset is itself a scoring-function bug.

This test scans ``leaderboard-results/`` for every
``random-baseline`` and ``majority-baseline`` submission, computes the
canonical per-dataset SPS (max across runs — the value the leaderboard
displays and that new submissions must beat), and asserts it stays
below configured thresholds.

If this test fires on a known good scoring-function change that
legitimately moves the null-agent band, raise the threshold in
``synthbench.baseline_floors`` *deliberately*, commit the new ceiling,
and publish the new floor on the methodology page. Don't silence it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from synthbench.baseline_floors import (
    ASPIRATIONAL_MAJORITY_MAX_SPS,
    ASPIRATIONAL_RANDOM_MAX_SPS,
    BaselineRun,
    MAJORITY_MAX_SPS,
    RANDOM_MAX_SPS,
    canonical_baselines,
    check_floors,
    discover_baseline_runs,
    history_report,
    summary_report,
    threshold_for,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "leaderboard-results"


# ---------------------------------------------------------------------------
# CI gate: live check against leaderboard-results/
# ---------------------------------------------------------------------------


class TestBaselineFloorsCI:
    """The drift-detection gate itself. Fails if any canonical baseline
    has crept above its threshold."""

    def test_leaderboard_results_dir_exists(self) -> None:
        assert RESULTS_DIR.is_dir(), (
            f"expected leaderboard-results/ at {RESULTS_DIR}; this test "
            "must run from a full repo checkout"
        )

    def test_baselines_discovered(self) -> None:
        """At least one baseline of each provider must exist — otherwise
        the gate would silently pass with nothing to check."""
        runs = discover_baseline_runs(RESULTS_DIR)
        providers = {r.provider for r in runs}
        assert "random-baseline" in providers, (
            "no random-baseline submissions in leaderboard-results/; gate "
            "would silently pass. Restore at least one canonical random "
            "baseline or this test loses its teeth."
        )
        assert "majority-baseline" in providers, (
            "no majority-baseline submissions in leaderboard-results/; "
            "gate would silently pass."
        )

    def test_canonical_sps_below_thresholds(self) -> None:
        """The acceptance gate for sb-lhoh.

        Fails with a full summary if any canonical baseline (max SPS
        per dataset/provider) meets or exceeds its configured ceiling.
        """
        runs = discover_baseline_runs(RESULTS_DIR)
        canon = canonical_baselines(runs)
        violations = check_floors(canon)
        if violations:
            report = summary_report(canon)
            detail = "\n".join(v.format() for v in violations)
            pytest.fail(
                "Null-agent baseline SPS drift detected "
                "(sb-lhoh / docs/benchmark-hardening-analysis.md §5.4):\n"
                f"{detail}\n\n{report}"
            )


# ---------------------------------------------------------------------------
# Unit tests: logic in isolation
# ---------------------------------------------------------------------------


def _write_result(
    root: Path,
    *,
    provider: str,
    dataset: str,
    sps: float,
    n: int = 100,
    timestamp: str = "2026-04-18T00:00:00+00:00",
    stem: str | None = None,
) -> Path:
    stem = stem or f"{dataset}_{provider}_fixture"
    path = root / f"{stem}.json"
    payload = {
        "benchmark": "synthbench",
        "version": "0.1.0",
        "timestamp": timestamp,
        "config": {
            "dataset": dataset,
            "provider": provider,
            "n_evaluated": n,
        },
        "scores": {"sps": sps},
        "aggregate": {"composite_parity": sps, "n_questions": n},
    }
    path.write_text(json.dumps(payload))
    return path


class TestDiscovery:
    def test_skips_non_baseline_providers(self, tmp_path: Path) -> None:
        _write_result(
            tmp_path,
            provider="openrouter_anthropic_claude-haiku-4-5",
            dataset="opinionsqa",
            sps=0.80,
            stem="opinionsqa_claude_fixture",
        )
        _write_result(
            tmp_path,
            provider="random-baseline",
            dataset="opinionsqa",
            sps=0.70,
        )
        runs = discover_baseline_runs(tmp_path)
        assert len(runs) == 1
        assert runs[0].provider == "random-baseline"

    def test_skips_malformed_files(self, tmp_path: Path) -> None:
        (tmp_path / "garbage.json").write_text("not json")
        (tmp_path / "array.json").write_text("[1, 2, 3]")
        _write_result(
            tmp_path,
            provider="random-baseline",
            dataset="opinionsqa",
            sps=0.70,
        )
        runs = discover_baseline_runs(tmp_path)
        assert len(runs) == 1

    def test_skips_baseline_without_sps(self, tmp_path: Path) -> None:
        path = tmp_path / "opinionsqa_random-baseline_empty.json"
        path.write_text(
            json.dumps(
                {
                    "timestamp": "2026-04-18T00:00:00+00:00",
                    "config": {
                        "provider": "random-baseline",
                        "dataset": "opinionsqa",
                    },
                    "scores": {},
                    "aggregate": {"n_questions": 10},
                }
            )
        )
        assert discover_baseline_runs(tmp_path) == []

    def test_falls_back_to_composite_parity_when_sps_missing(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "opinionsqa_random-baseline_oldformat.json"
        path.write_text(
            json.dumps(
                {
                    "timestamp": "2026-04-18T00:00:00+00:00",
                    "config": {
                        "provider": "random-baseline",
                        "dataset": "opinionsqa",
                        "n_evaluated": 50,
                    },
                    "aggregate": {
                        "composite_parity": 0.62,
                        "n_questions": 50,
                    },
                }
            )
        )
        runs = discover_baseline_runs(tmp_path)
        assert len(runs) == 1
        assert runs[0].sps == pytest.approx(0.62)


class TestCanonicalSelection:
    def test_picks_max_sps_per_provider_dataset(self) -> None:
        runs = [
            BaselineRun("random-baseline", "opinionsqa", 0.65, 100, "t1", "a.json"),
            BaselineRun("random-baseline", "opinionsqa", 0.72, 100, "t2", "b.json"),
            BaselineRun("random-baseline", "opinionsqa", 0.68, 100, "t3", "c.json"),
            BaselineRun("random-baseline", "subpop", 0.60, 100, "t4", "d.json"),
            BaselineRun("majority-baseline", "opinionsqa", 0.71, 100, "t5", "e.json"),
        ]
        canon = canonical_baselines(runs)
        assert canon[("random-baseline", "opinionsqa")].sps == pytest.approx(0.72)
        assert canon[("random-baseline", "opinionsqa")].source_file == "b.json"
        assert canon[("random-baseline", "subpop")].sps == pytest.approx(0.60)
        assert canon[("majority-baseline", "opinionsqa")].sps == pytest.approx(0.71)
        assert len(canon) == 3


class TestCheckFloors:
    def test_passes_when_below_threshold(self) -> None:
        runs = [
            BaselineRun(
                "random-baseline",
                "opinionsqa",
                RANDOM_MAX_SPS - 0.01,
                100,
                "t1",
                "a.json",
            ),
            BaselineRun(
                "majority-baseline",
                "opinionsqa",
                MAJORITY_MAX_SPS - 0.01,
                100,
                "t2",
                "b.json",
            ),
        ]
        assert check_floors(canonical_baselines(runs)) == []

    def test_fails_when_random_at_or_above_threshold(self) -> None:
        runs = [
            BaselineRun(
                "random-baseline",
                "opinionsqa",
                RANDOM_MAX_SPS,
                100,
                "t1",
                "a.json",
            ),
        ]
        violations = check_floors(canonical_baselines(runs))
        assert len(violations) == 1
        assert violations[0].provider == "random-baseline"
        assert violations[0].threshold == RANDOM_MAX_SPS

    def test_fails_when_majority_above_threshold(self) -> None:
        runs = [
            BaselineRun(
                "majority-baseline",
                "opinionsqa",
                MAJORITY_MAX_SPS + 0.001,
                100,
                "t1",
                "a.json",
            ),
        ]
        violations = check_floors(canonical_baselines(runs))
        assert len(violations) == 1
        assert violations[0].provider == "majority-baseline"

    def test_multiple_violations_reported(self) -> None:
        runs = [
            BaselineRun(
                "random-baseline",
                "opinionsqa",
                0.95,
                100,
                "t1",
                "a.json",
            ),
            BaselineRun(
                "random-baseline",
                "subpop",
                0.91,
                100,
                "t2",
                "b.json",
            ),
            BaselineRun(
                "majority-baseline",
                "opinionsqa",
                MAJORITY_MAX_SPS + 0.01,
                100,
                "t3",
                "c.json",
            ),
            BaselineRun(
                "majority-baseline",
                "subpop",
                0.10,
                100,
                "t4",
                "d.json",
            ),
        ]
        violations = check_floors(canonical_baselines(runs))
        assert len(violations) == 3
        provs = sorted((v.provider, v.dataset) for v in violations)
        assert provs == [
            ("majority-baseline", "opinionsqa"),
            ("random-baseline", "opinionsqa"),
            ("random-baseline", "subpop"),
        ]


class TestThresholdConfig:
    def test_known_providers(self) -> None:
        assert threshold_for("random-baseline") == RANDOM_MAX_SPS
        assert threshold_for("majority-baseline") == MAJORITY_MAX_SPS

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ValueError):
            threshold_for("openrouter_anthropic_claude-haiku-4-5")

    def test_aspirational_thresholds_bounded(self) -> None:
        """Berkeley-paper floors are <= hard thresholds. Aspirational is
        the stricter target; the hard gate may not be tighter than the
        aspiration, or the labels are backwards."""
        assert ASPIRATIONAL_RANDOM_MAX_SPS <= RANDOM_MAX_SPS
        assert ASPIRATIONAL_MAJORITY_MAX_SPS <= MAJORITY_MAX_SPS


# ---------------------------------------------------------------------------
# Reporting: smoke tests so summary/history helpers don't silently break
# ---------------------------------------------------------------------------


class TestReporting:
    def test_summary_includes_every_canonical(self) -> None:
        runs = [
            BaselineRun("random-baseline", "opinionsqa", 0.65, 684, "t1", "a.json"),
            BaselineRun("majority-baseline", "subpop", 0.67, 200, "t2", "b.json"),
        ]
        text = summary_report(canonical_baselines(runs))
        assert "random-baseline" in text
        assert "majority-baseline" in text
        assert "opinionsqa" in text
        assert "subpop" in text
        assert "0.6500" in text

    def test_history_lists_every_run(self) -> None:
        runs = [
            BaselineRun("random-baseline", "opinionsqa", 0.72, 100, "t1", "a.json"),
            BaselineRun("random-baseline", "opinionsqa", 0.76, 684, "t2", "b.json"),
        ]
        text = history_report(runs)
        assert "0.7200" in text
        assert "0.7600" in text
