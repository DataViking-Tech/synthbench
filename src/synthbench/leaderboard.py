"""Leaderboard and comparison utilities for SynthBench result files."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def load_result(path: Path) -> dict:
    """Load a single result JSON file and return the dict as-is."""
    with open(path) as f:
        return json.load(f)


def _column_label(result: dict) -> str:
    """Build a short column label from a result dict: provider (n=N)."""
    cfg = result.get("config", {})
    provider = cfg.get("provider", "unknown")
    n = cfg.get("n_evaluated", cfg.get("n_requested", "?"))
    return f"{provider} (n={n})"


def compare_results(results: list[dict]) -> str:
    """Produce a side-by-side markdown comparison table for multiple results.

    Each result dict must have the standard SynthBench JSON structure
    with 'config' and 'aggregate' top-level keys.
    """
    if not results:
        return "No results to compare.\n"

    labels = [_column_label(r) for r in results]
    aggregates = [r.get("aggregate", {}) for r in results]
    configs = [r.get("config", {}) for r in results]

    # Header row
    header = "| Metric | " + " | ".join(labels) + " |"
    sep = "|--------|" + "|".join("-" * (len(label) + 2) for label in labels) + "|"

    rows = [
        _metric_row("Composite Parity", aggregates, "composite_parity", bold=True),
        _metric_row("Mean JSD", aggregates, "mean_jsd"),
        _metric_row("Median JSD", aggregates, "median_jsd"),
        _metric_row("Mean Kendall's tau", aggregates, "mean_kendall_tau"),
        _count_row("Questions", aggregates, "n_questions"),
        _config_row("Samples/q", configs, "samples_per_question"),
        _elapsed_row(aggregates),
    ]

    lines = [
        "# SynthBench Comparison",
        "",
        header,
        sep,
        *rows,
        "",
    ]
    return "\n".join(lines)


def _metric_row(
    label: str, aggregates: list[dict], key: str, bold: bool = False
) -> str:
    """Format a metric row with 4-decimal formatting."""
    cells = []
    for agg in aggregates:
        val = agg.get(key)
        if val is not None:
            formatted = f"{val:.4f}"
            if bold:
                formatted = f"**{formatted}**"
            cells.append(formatted)
        else:
            cells.append("--")
    return f"| {label} | " + " | ".join(cells) + " |"


def _count_row(label: str, aggregates: list[dict], key: str) -> str:
    """Format an integer count row."""
    cells = []
    for agg in aggregates:
        val = agg.get(key)
        cells.append(str(val) if val is not None else "--")
    return f"| {label} | " + " | ".join(cells) + " |"


def _config_row(label: str, configs: list[dict], key: str) -> str:
    """Format a config value row."""
    cells = []
    for cfg in configs:
        val = cfg.get(key)
        cells.append(str(val) if val is not None else "--")
    return f"| {label} | " + " | ".join(cells) + " |"


def _elapsed_row(aggregates: list[dict]) -> str:
    """Format the elapsed time row."""
    cells = []
    for agg in aggregates:
        val = agg.get("elapsed_seconds")
        if val is not None:
            cells.append(f"{val:.1f}s")
        else:
            cells.append("--")
    return "| Elapsed | " + " | ".join(cells) + " |"


def _collect_topic_scores(
    results: list[dict],
) -> dict[str, dict[str, float]]:
    """Collect per-topic composite parity scores from results with topic tags.

    Returns {provider: {topic: composite_parity}} for results that have
    a config.topic field.
    """
    topic_scores: dict[str, dict[str, float]] = {}
    for r in results:
        cfg = r.get("config", {})
        topic = cfg.get("topic")
        if not topic:
            continue
        provider = cfg.get("provider", "unknown")
        cp = r.get("aggregate", {}).get("composite_parity", 0)
        topic_scores.setdefault(provider, {})[topic] = round(cp, 4)
    return topic_scores


def build_leaderboard(results: list[dict]) -> tuple[str, dict]:
    """Build a ranked leaderboard from multiple result dicts.

    When multiple runs exist for the same provider+dataset+topic combination,
    only the run with the largest n_evaluated is kept.

    If results with topic tags exist, per-topic columns are included.

    Returns:
        (markdown_table, leaderboard_json) where leaderboard_json has the
        structure {"leaderboard": [...], "generated": "ISO timestamp"}.
    """
    if not results:
        return "No results for leaderboard.\n", {
            "leaderboard": [],
            "generated": _now_iso(),
        }

    # Separate topic-tagged results from overall results
    overall_results = [r for r in results if not r.get("config", {}).get("topic")]
    topic_results = [r for r in results if r.get("config", {}).get("topic")]

    # Collect topic scores per provider
    topic_scores = _collect_topic_scores(topic_results)
    topics_present = sorted(
        {
            r.get("config", {}).get("topic")
            for r in topic_results
            if r.get("config", {}).get("topic")
        }
    )

    # De-duplicate overall: keep the run with the most questions per provider+dataset
    target = overall_results if overall_results else results
    best: dict[tuple[str, str], dict] = {}
    for r in target:
        cfg = r.get("config", {})
        provider = cfg.get("provider", "unknown")
        dataset = cfg.get("dataset", "unknown")
        n_eval = cfg.get("n_evaluated", 0)
        key = (provider, dataset)

        existing = best.get(key)
        if existing is None or n_eval > existing["config"].get("n_evaluated", 0):
            best[key] = r

    # Sort by composite_parity descending
    ranked = sorted(
        best.values(),
        key=lambda r: r.get("aggregate", {}).get("composite_parity", 0),
        reverse=True,
    )

    # Build entries
    entries = []
    for rank, r in enumerate(ranked, 1):
        cfg = r.get("config", {})
        agg = r.get("aggregate", {})
        ts = r.get("timestamp", "")
        date_str = ts[:10] if len(ts) >= 10 else "--"

        provider = cfg.get("provider", "unknown")
        entry = {
            "rank": rank,
            "provider": provider,
            "dataset": cfg.get("dataset", "unknown"),
            "n": cfg.get("n_evaluated", 0),
            "composite_parity": round(agg.get("composite_parity", 0), 4),
            "mean_jsd": round(agg.get("mean_jsd", 0), 4),
            "mean_kendall_tau": round(agg.get("mean_kendall_tau", 0), 4),
            "date": date_str,
        }

        # Add per-topic scores if available
        if provider in topic_scores:
            entry["topic_scores"] = topic_scores[provider]

        entries.append(entry)

    # Build markdown
    if topics_present:
        topic_headers = " | ".join(t.capitalize() for t in topics_present)
        topic_seps = " | ".join("---" for _ in topics_present)
        lines = [
            "# SynthBench Leaderboard",
            "",
            f"| Rank | Provider | Dataset | N | Parity | {topic_headers} | JSD | tau | Date |",
            f"|------|----------|---------|---|--------|{topic_seps}|-----|-----|------|",
        ]
        for e in entries:
            topic_cells = []
            for t in topics_present:
                score = e.get("topic_scores", {}).get(t)
                topic_cells.append(f"{score:.4f}" if score is not None else "--")
            topic_str = " | ".join(topic_cells)
            lines.append(
                f"| {e['rank']} "
                f"| {e['provider']} "
                f"| {e['dataset']} "
                f"| {e['n']} "
                f"| {e['composite_parity']:.4f} "
                f"| {topic_str} "
                f"| {e['mean_jsd']:.4f} "
                f"| {e['mean_kendall_tau']:.4f} "
                f"| {e['date']} |"
            )
    else:
        lines = [
            "# SynthBench Leaderboard",
            "",
            "| Rank | Provider | Dataset | N | Parity | JSD | tau | Date |",
            "|------|----------|---------|---|--------|-----|-----|------|",
        ]
        for e in entries:
            lines.append(
                f"| {e['rank']} "
                f"| {e['provider']} "
                f"| {e['dataset']} "
                f"| {e['n']} "
                f"| {e['composite_parity']:.4f} "
                f"| {e['mean_jsd']:.4f} "
                f"| {e['mean_kendall_tau']:.4f} "
                f"| {e['date']} |"
            )
    lines.append("")

    leaderboard_json = {
        "leaderboard": entries,
        "generated": _now_iso(),
    }

    return "\n".join(lines), leaderboard_json


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()
