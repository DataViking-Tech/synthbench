#!/usr/bin/env python3
"""Print the null-agent baseline floor summary and full drift history.

Reads every ``*-baseline_*.json`` under ``leaderboard-results/`` and
emits two sections to stdout: the canonical per-dataset floor (what
the CI gate enforces) and the full time-ordered history (what the
gate's companion log shows over time).

Exits 1 if any canonical floor >= its threshold, mirroring the
pytest CI gate (tests/test_baseline_floors.py). Useful for a quick
local read without running pytest.

Usage:
    python3 scripts/baseline-floors-report.py
    python3 scripts/baseline-floors-report.py --results-dir ./leaderboard-results
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from synthbench.baseline_floors import (  # noqa: E402
    canonical_baselines,
    check_floors,
    discover_baseline_runs,
    history_report,
    summary_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir",
        default=str(REPO_ROOT / "leaderboard-results"),
        help="directory of benchmark result JSONs (default: leaderboard-results/)",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="also print every baseline run in time order",
    )
    args = parser.parse_args()

    runs = discover_baseline_runs(args.results_dir)
    if not runs:
        print(
            f"No baseline submissions found under {args.results_dir}",
            file=sys.stderr,
        )
        return 2

    canon = canonical_baselines(runs)
    print(summary_report(canon))

    if args.history:
        print()
        print(history_report(runs))

    violations = check_floors(canon)
    if violations:
        print()
        print("FAILURES:")
        for v in violations:
            print(f"  {v.format()}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
