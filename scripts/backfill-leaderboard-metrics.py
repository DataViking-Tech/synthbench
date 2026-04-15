#!/usr/bin/env python3
"""Backfill stale metrics on historical leaderboard-results/*.json files.

Two classes of historical drift this resolves (sb-7gn):

1. DIST_SUM — synthpanel runs published before sb-7bg (PR #138) divided
   per-question option counts by total samples (incl. refusals/parse-failures),
   so model_distribution sums to <1.0 (typically 0.83 or 0.91). The new
   runner renormalizes over valid options before publishing. We bring
   historical files into the same convention by normalizing
   model_distribution where the sum is non-zero but outside the validator's
   DISTRIBUTION_SUM_TOLERANCE. All-zero distributions are left alone — they
   carry the legitimate sentinel jsd=1.0/tau=0.0 from catastrophic parse
   failure and the validator already accepts that.

2. PER_Q_TAU — a single record (subpop_random-baseline Q34) has
   double-tie rounding drift across human and model distributions large
   enough to trip the per-question recompute tolerance. Recomputing tau
   from the stored bytes resolves it.

Aggregate fields (mean_jsd, mean_kendall_tau, composite_parity, scores.*)
are recomputed from per-question values whenever they fall outside
AGGREGATE_RECOMPUTE_TOLERANCE. per_metric_ci is intentionally left
untouched — the validator does not check it and recomputation requires
a full bootstrap, which would balloon the diff for no integrity gain.

Idempotent: running on already-clean files produces no diff.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from synthbench.metrics.composite import (  # noqa: E402
    parity_score,
    synthbench_parity_score,
)
from synthbench.metrics.distributional import jensen_shannon_divergence  # noqa: E402
from synthbench.metrics.ranking import kendall_tau_b  # noqa: E402
from synthbench.validation import (  # noqa: E402
    AGGREGATE_RECOMPUTE_TOLERANCE,
    DISTRIBUTION_SUM_TOLERANCE,
    METRIC_RECOMPUTE_TOLERANCE,
)

DIST_PRECISION = 4  # report.py rounds distribution probabilities to 4 dp
METRIC_PRECISION = 6  # ...and metrics to 6 dp
# Per-question parity is derived from jsd + tau. Original runs computed it
# from full-precision values then rounded, while we recompute from already-
# rounded jsd/tau, so honest history can disagree by ~1e-6 in the last digit
# without representing real drift. Allow a small slack so we don't churn
# every file on cosmetic last-digit noise; real staleness (e.g., the
# subpop_random-baseline Q34 cascade after a tau correction) shifts parity
# by orders of magnitude more (~0.02) and still gets caught.
PARITY_RECOMPUTE_TOLERANCE = 1e-4


def _normalize_distribution(dist: dict) -> bool:
    """Renormalize a distribution to sum=1.0 if it currently doesn't.

    Returns True if the distribution was modified. Leaves all-zero
    distributions alone (sentinel for catastrophic parse failure).
    """
    total = sum(v for v in dist.values() if isinstance(v, (int, float)))
    if total <= 0:
        return False
    if abs(total - 1.0) <= DISTRIBUTION_SUM_TOLERANCE:
        return False
    for k in list(dist.keys()):
        v = dist[k]
        if isinstance(v, (int, float)):
            dist[k] = round(v / total, DIST_PRECISION)
    return True


def _maybe_replace(d: dict, key: str, new_value: float, tolerance: float) -> bool:
    """Replace d[key] with new_value if they disagree beyond tolerance.

    Returns True if a write happened. Preserves byte-stability when the
    stored value is already within tolerance of the recompute.
    """
    stored = d.get(key)
    if stored is None or not isinstance(stored, (int, float)):
        return False
    rounded = round(new_value, METRIC_PRECISION)
    if abs(float(stored) - rounded) <= tolerance:
        return False
    d[key] = rounded
    return True


def _median(vals: list[float]) -> float:
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2.0
    return s[mid]


def backfill_record(data: dict) -> dict:
    """Apply all backfill steps to a parsed submission. Returns stats."""
    stats = {
        "dist_normalized": 0,
        "per_q_jsd_updated": 0,
        "per_q_tau_updated": 0,
        "per_q_parity_updated": 0,
        "agg_updated": 0,
    }

    per_q = data.get("per_question") or []
    if not isinstance(per_q, list):
        return stats

    for q in per_q:
        if not isinstance(q, dict):
            continue

        # 1. Normalize distributions where they violate DIST_SUM.
        for fld in ("human_distribution", "model_distribution"):
            dist = q.get(fld)
            if isinstance(dist, dict) and _normalize_distribution(dist):
                stats["dist_normalized"] += 1

        # 2. Recompute per-question metrics from the (post-normalization)
        # distributions. Only write back when they actually disagree.
        hd = q.get("human_distribution") or {}
        md = q.get("model_distribution") or {}
        if not isinstance(hd, dict) or not isinstance(md, dict):
            continue

        try:
            new_jsd = jensen_shannon_divergence(hd, md)
            new_tau = kendall_tau_b(hd, md)
        except Exception:
            continue

        jsd_changed = _maybe_replace(q, "jsd", new_jsd, METRIC_RECOMPUTE_TOLERANCE)
        tau_changed = _maybe_replace(
            q, "kendall_tau", new_tau, METRIC_RECOMPUTE_TOLERANCE
        )
        if jsd_changed:
            stats["per_q_jsd_updated"] += 1
        if tau_changed:
            stats["per_q_tau_updated"] += 1

        # 3. Per-question parity is purely derived from jsd + tau (no
        # rounding noise to absorb), so we hold it to a tighter tolerance
        # than the recompute-vs-stored checks above. This catches the
        # cascade case where a prior backfill touched jsd/tau but left
        # the now-stale per-question parity behind.
        cur_jsd = q.get("jsd")
        cur_tau = q.get("kendall_tau")
        if isinstance(cur_jsd, (int, float)) and isinstance(cur_tau, (int, float)):
            new_parity = parity_score(float(cur_jsd), float(cur_tau))
            if _maybe_replace(q, "parity", new_parity, PARITY_RECOMPUTE_TOLERANCE):
                stats["per_q_parity_updated"] += 1

    # 4. Recompute aggregate / scores from current per-question values.
    jsd_vals = [
        float(q["jsd"])
        for q in per_q
        if isinstance(q, dict) and isinstance(q.get("jsd"), (int, float))
    ]
    tau_vals = [
        float(q["kendall_tau"])
        for q in per_q
        if isinstance(q, dict) and isinstance(q.get("kendall_tau"), (int, float))
    ]
    if jsd_vals and tau_vals and len(jsd_vals) == len(tau_vals):
        new_mean_jsd = sum(jsd_vals) / len(jsd_vals)
        new_mean_tau = sum(tau_vals) / len(tau_vals)
        new_median_jsd = _median(jsd_vals)
        new_p_dist = 1.0 - new_mean_jsd
        new_p_rank = (1.0 + new_mean_tau) / 2.0
        new_composite = parity_score(new_mean_jsd, new_mean_tau)

        agg = data.get("aggregate")
        if isinstance(agg, dict):
            for k, v in (
                ("mean_jsd", new_mean_jsd),
                ("median_jsd", new_median_jsd),
                ("mean_kendall_tau", new_mean_tau),
                ("composite_parity", new_composite),
            ):
                if _maybe_replace(agg, k, v, AGGREGATE_RECOMPUTE_TOLERANCE):
                    stats["agg_updated"] += 1

        scores = data.get("scores")
        if isinstance(scores, dict) and scores:
            if _maybe_replace(
                scores, "p_dist", new_p_dist, AGGREGATE_RECOMPUTE_TOLERANCE
            ):
                stats["agg_updated"] += 1
            if _maybe_replace(
                scores, "p_rank", new_p_rank, AGGREGATE_RECOMPUTE_TOLERANCE
            ):
                stats["agg_updated"] += 1
            # SPS = equal-weighted mean of available components. Use the
            # *current* stored components (post-update) so the recompute
            # is consistent with what the file now claims.
            components = {}
            for key in ("p_dist", "p_rank", "p_refuse", "p_sub", "p_cond"):
                v = scores.get(key)
                if isinstance(v, (int, float)):
                    components[key] = float(v)
            if components:
                new_sps = synthbench_parity_score(components)
                if _maybe_replace(
                    scores, "sps", new_sps, AGGREGATE_RECOMPUTE_TOLERANCE
                ):
                    stats["agg_updated"] += 1

    return stats


def backfill_file(path: Path, *, dry_run: bool = False) -> tuple[bool, dict]:
    """Backfill one file in-place. Returns (changed, stats)."""
    raw = path.read_bytes()
    data = json.loads(raw)
    stats = backfill_record(data)

    # Re-serialize with the same convention the runner uses
    # (json.dumps(..., indent=2), ASCII escapes, no trailing newline).
    new_text = json.dumps(data, indent=2)
    new_bytes = new_text.encode()
    changed = new_bytes != raw

    if changed and not dry_run:
        path.write_bytes(new_bytes)

    return changed, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[REPO_ROOT / "leaderboard-results"],
        help="Files or directories to backfill (default: leaderboard-results/)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Don't write changes.")
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress per-file output."
    )
    args = parser.parse_args()

    targets: list[Path] = []
    for p in args.paths:
        if p.is_dir():
            targets.extend(sorted(p.glob("*.json")))
        else:
            targets.append(p)

    totals = {
        "files_changed": 0,
        "files_total": len(targets),
        "dist_normalized": 0,
        "per_q_jsd_updated": 0,
        "per_q_tau_updated": 0,
        "per_q_parity_updated": 0,
        "agg_updated": 0,
    }

    for path in targets:
        try:
            changed, stats = backfill_file(path, dry_run=args.dry_run)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"!! {path}: {exc}", file=sys.stderr)
            continue
        if changed:
            totals["files_changed"] += 1
        for k in (
            "dist_normalized",
            "per_q_jsd_updated",
            "per_q_tau_updated",
            "per_q_parity_updated",
            "agg_updated",
        ):
            totals[k] += stats[k]
        if changed and not args.quiet:
            summary = ", ".join(f"{k}={v}" for k, v in stats.items() if v)
            print(f"  {path.name}: {summary}")

    print()
    mode = "[dry-run] would change" if args.dry_run else "Changed"
    print(f"{mode} {totals['files_changed']}/{totals['files_total']} files")
    print(f"  dist_normalized       : {totals['dist_normalized']}")
    print(f"  per_q_jsd_updated     : {totals['per_q_jsd_updated']}")
    print(f"  per_q_tau_updated     : {totals['per_q_tau_updated']}")
    print(f"  per_q_parity_updated  : {totals['per_q_parity_updated']}")
    print(f"  agg_updated           : {totals['agg_updated']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
