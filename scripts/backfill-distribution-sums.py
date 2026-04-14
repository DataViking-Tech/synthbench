#!/usr/bin/env python3
"""Backfill historical leaderboard-results with normalized distributions.

Historical runs published model_distributions that sum to values like 0.47,
0.53, or 0.91 because parse failures and refusals dropped option mass without
renormalization (sb-7bg). The runtime fix lives in src/synthbench/report.py;
this script rewrites existing JSONs in place so the on-disk leaderboard also
satisfies the sum=1.0 validator contract.

Safe to re-run: files already within tolerance are skipped and left byte-for-byte
unchanged. Scores (jsd, kendall_tau, parity) are NOT recomputed because JSD
internally renormalizes — the score values are already correct; only the
serialized distributions were broken.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from synthbench.report import normalize_distribution  # noqa: E402
from synthbench.validation import DISTRIBUTION_SUM_TOLERANCE  # noqa: E402


def needs_fix(dist: dict) -> bool:
    if not isinstance(dist, dict) or not dist:
        return False
    total = sum(float(v) for v in dist.values() if isinstance(v, (int, float)))
    return abs(total - 1.0) > DISTRIBUTION_SUM_TOLERANCE


def fix_file(path: Path, dry_run: bool) -> tuple[bool, int]:
    try:
        with path.open() as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return False, 0

    per_q = data.get("per_question") or []
    if not isinstance(per_q, list):
        return False, 0

    fixed_count = 0
    for q in per_q:
        if not isinstance(q, dict):
            continue
        md = q.get("model_distribution")
        if needs_fix(md):
            q["model_distribution"] = normalize_distribution(md)
            fixed_count += 1

    if fixed_count == 0:
        return False, 0

    if not dry_run:
        with path.open("w") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")

    return True, fixed_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory",
        type=Path,
        nargs="?",
        default=REPO_ROOT / "leaderboard-results",
        help="Directory of result JSONs (default: leaderboard-results/)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.directory.is_dir():
        print(f"error: not a directory: {args.directory}", file=sys.stderr)
        return 2

    files_touched = 0
    total_fixed = 0
    for path in sorted(args.directory.glob("*.json")):
        changed, n = fix_file(path, args.dry_run)
        if changed:
            files_touched += 1
            total_fixed += n
            marker = "[dry-run] " if args.dry_run else ""
            print(f"{marker}{path.name}: fixed {n} per_question distributions")

    verb = "would fix" if args.dry_run else "fixed"
    print(f"\n{verb} {total_fixed} distributions across {files_touched} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
