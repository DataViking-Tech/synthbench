"""Null-agent baseline floor discovery and drift detection (sb-lhoh).

Per Berkeley paper recommendation ("run a null agent; if it's not zero,
something is wrong"), SynthBench's equivalent null agents are the
``random-baseline`` and ``majority-baseline`` providers. Their composite
parity ("SPS") must stay bounded; upward drift on a stable dataset
signals a scoring-function bug, not a success.

This module discovers the canonical per-dataset baseline SPS from
``leaderboard-results/`` (mirroring leaderboard.build_baseline_scores:
max composite_parity per (provider, dataset)) and checks it against
configured ceilings.

Thresholds:
    * ``MAJORITY_MAX_SPS = 0.85`` — Berkeley target. Current observed
      max across datasets is ~0.71, leaving >0.13 headroom.
    * ``RANDOM_MAX_SPS = 0.80`` — calibrated. Berkeley's aspirational
      target is 0.70, but SynthBench's composite_parity weights
      ``p_refuse`` (where uniform-random naturally matches human DK/
      Refused rates), pushing observed random SPS to ~0.71-0.76.
      We set the hard CI gate at 0.80 (drift detection over current
      max) and surface 0.70 as the published aspirational floor.

See ``docs/benchmark-hardening-analysis.md`` §5.4 for full context.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

BASELINE_PROVIDERS = ("random-baseline", "majority-baseline")

# Hard CI thresholds. A baseline run whose SPS meets-or-exceeds the
# threshold signals upward scoring-function drift and fails CI.
MAJORITY_MAX_SPS = 0.85
RANDOM_MAX_SPS = 0.80

# Aspirational floors from Wang et al. (UC Berkeley, 2026). Published on
# the methodology page as "the floor any benchmark-serious model must
# clear." The hard CI gate above is looser because SynthBench's
# composite_parity rewards random agents for matching human DK/Refused
# rates (high p_refuse) — a known property of the scoring protocol, not
# a bug. If p_refuse is rebalanced in future scoring revisions, the
# hard gate should drop toward these Berkeley targets.
ASPIRATIONAL_RANDOM_MAX_SPS = 0.70
ASPIRATIONAL_MAJORITY_MAX_SPS = 0.85


@dataclass(frozen=True)
class BaselineRun:
    """One null-agent submission discovered under leaderboard-results/."""

    provider: str
    dataset: str
    sps: float
    n_evaluated: int
    timestamp: str
    source_file: str


@dataclass(frozen=True)
class FloorViolation:
    """One canonical-baseline SPS that met-or-exceeded its ceiling."""

    provider: str
    dataset: str
    sps: float
    threshold: float
    source_file: str

    def format(self) -> str:
        return (
            f"{self.provider} on {self.dataset}: SPS={self.sps:.4f} "
            f">= threshold {self.threshold:.2f}  (source: {self.source_file})"
        )


def _load_result(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    cfg = data.get("config") or {}
    if cfg.get("provider") not in BASELINE_PROVIDERS:
        return None
    agg = data.get("aggregate") or {}
    scores = data.get("scores") or {}
    sps = scores.get("sps")
    if sps is None:
        sps = agg.get("composite_parity")
    if not isinstance(sps, (int, float)):
        return None
    return {
        "provider": cfg["provider"],
        "dataset": cfg.get("dataset", "unknown"),
        "sps": float(sps),
        "n_evaluated": int(cfg.get("n_evaluated") or agg.get("n_questions") or 0),
        "timestamp": str(data.get("timestamp", "")),
    }


def discover_baseline_runs(results_dir: Path | str) -> list[BaselineRun]:
    """Enumerate every baseline submission under ``results_dir``.

    Non-baseline submissions, malformed files, and files without an
    SPS are silently skipped. Sorted by timestamp ascending to make
    the output stable and usable as a drift log.
    """
    root = Path(results_dir)
    runs: list[BaselineRun] = []
    for path in sorted(root.glob("*.json")):
        rec = _load_result(path)
        if rec is None:
            continue
        runs.append(
            BaselineRun(
                provider=rec["provider"],
                dataset=rec["dataset"],
                sps=rec["sps"],
                n_evaluated=rec["n_evaluated"],
                timestamp=rec["timestamp"],
                source_file=path.name,
            )
        )
    runs.sort(key=lambda r: (r.provider, r.dataset, r.timestamp))
    return runs


def canonical_baselines(
    runs: list[BaselineRun],
) -> dict[tuple[str, str], BaselineRun]:
    """Pick the canonical (max-SPS) run per (provider, dataset).

    Mirrors ``leaderboard.build_baseline_scores``: the value shown to
    users as "the random baseline" on the leaderboard is the max
    composite_parity across all runs for that provider/dataset. That
    is the number a new submission must beat, so that is what we gate
    on.
    """
    best: dict[tuple[str, str], BaselineRun] = {}
    for run in runs:
        key = (run.provider, run.dataset)
        if key not in best or run.sps > best[key].sps:
            best[key] = run
    return best


def threshold_for(provider: str) -> float:
    if provider == "random-baseline":
        return RANDOM_MAX_SPS
    if provider == "majority-baseline":
        return MAJORITY_MAX_SPS
    raise ValueError(f"unknown baseline provider: {provider!r}")


def check_floors(
    canonicals: dict[tuple[str, str], BaselineRun],
) -> list[FloorViolation]:
    """Return any canonical-baseline entry whose SPS >= its threshold."""
    violations: list[FloorViolation] = []
    for (provider, dataset), run in sorted(canonicals.items()):
        t = threshold_for(provider)
        if run.sps >= t:
            violations.append(
                FloorViolation(
                    provider=provider,
                    dataset=dataset,
                    sps=run.sps,
                    threshold=t,
                    source_file=run.source_file,
                )
            )
    return violations


def summary_report(
    canonicals: dict[tuple[str, str], BaselineRun],
) -> str:
    """Render a human-readable floor summary. Used by tests and scripts."""
    lines = ["Null-agent baseline floors (max SPS per provider/dataset):"]
    by_provider: dict[str, list[BaselineRun]] = {}
    for run in canonicals.values():
        by_provider.setdefault(run.provider, []).append(run)
    for provider in sorted(by_provider):
        t = threshold_for(provider)
        lines.append(f"  {provider}  (CI threshold: SPS < {t:.2f})")
        for run in sorted(by_provider[provider], key=lambda r: r.dataset):
            status = "OK " if run.sps < t else "FAIL"
            lines.append(
                f"    [{status}] {run.dataset:20s} SPS={run.sps:.4f}  "
                f"n={run.n_evaluated:4d}  ({run.source_file})"
            )
    return "\n".join(lines)


def history_report(runs: list[BaselineRun]) -> str:
    """Render every observed baseline run in time order.

    This is the persisted drift log: every baseline submission ever
    checked into leaderboard-results/ is listed with its SPS. Grep
    this output to watch a specific (provider, dataset) over time.
    """
    lines = ["Null-agent baseline SPS history (ascending by time):"]
    for run in sorted(runs, key=lambda r: (r.provider, r.dataset, r.timestamp)):
        lines.append(
            f"  {run.timestamp:30s}  {run.provider:20s}  "
            f"{run.dataset:20s}  SPS={run.sps:.4f}  n={run.n_evaluated:4d}"
        )
    return "\n".join(lines)
