"""Leaderboard and comparison utilities for SynthBench result files."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASELINE_PROVIDERS = {"random-baseline", "majority-baseline"}

# Canonical taxonomy: provider string → (display_name, framework)
# framework is one of: "raw" (raw LLM APIs), "product" (orchestration layers),
# "baseline" (statistical baselines)
MODEL_MAP: dict[str, tuple[str, str]] = {
    # Raw LLMs via OpenRouter
    "openrouter/meta-llama/llama-3.3-70b-instruct": ("Llama 3.3 70B", "raw"),
    "openrouter/openai/gpt-4o-mini": ("GPT-4o-mini", "raw"),
    "openrouter/openai/gpt-4o": ("GPT-4o", "raw"),
    "openrouter/anthropic/claude-haiku-4-5": ("Claude Haiku 4.5", "raw"),
    "openrouter/anthropic/claude-sonnet-4": ("Claude Sonnet 4", "raw"),
    "openrouter/google/gemini-2.5-flash": ("Gemini 2.5 Flash", "raw"),
    "openrouter/google/gemini-2.5-flash-lite": ("Gemini Flash Lite", "raw"),
    # Raw LLMs via direct API
    "raw-anthropic/claude-haiku-4-5-20251001": ("Claude Haiku 4.5 (direct)", "raw"),
    "raw-gemini/gemini-2.5-flash-lite": ("Gemini Flash Lite (direct)", "raw"),
    # Products (orchestration / adapter layers)
    "synthpanel/claude-haiku-4-5-20251001": ("SynthPanel (Haiku 4.5)", "product"),
    "synthpanel/gemini-2.5-flash-lite": (
        "SynthPanel (Gemini Flash Lite)",
        "product",
    ),
    # Products — via OpenRouter
    "synthpanel/openrouter/anthropic/claude-haiku-4-5": (
        "SynthPanel (Haiku 4.5)",
        "product",
    ),
    "synthpanel/openrouter/google/gemini-2.5-flash-lite": (
        "SynthPanel (Gemini Flash Lite)",
        "product",
    ),
    "synthpanel/openrouter/openai/gpt-4o-mini": (
        "SynthPanel (GPT-4o-mini)",
        "product",
    ),
    "synthpanel/gpt-4o-mini": ("SynthPanel (GPT-4o-mini)", "product"),
    # Baselines
    "random-baseline": ("Random Baseline", "baseline"),
    "majority-baseline": ("Majority Baseline", "baseline"),
}


def _parse_provider_base(provider: str) -> str:
    """Strip temperature/template suffixes from provider name.

    'synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85 tpl=current'
    → 'synthpanel/openrouter/anthropic/claude-haiku-4-5'
    """
    return provider.split(" t=")[0].split(" tpl=")[0].split(" profile=")[0].strip()


def _extract_hyperparams(result: dict) -> dict[str, object]:
    """Extract temperature, template, and other hyperparams from a result."""
    cfg = result.get("config", {})
    hp: dict[str, object] = {}
    temp = cfg.get("temperature")
    if temp is not None:
        hp["temperature"] = temp
    tpl = cfg.get("prompt_template")
    if tpl:
        from pathlib import Path

        hp["template"] = Path(tpl).stem
    return hp


def _config_key(result: dict) -> tuple:
    """Build a grouping key: (display_name, framework, dataset, temperature, template).

    Results with the same key are replications to be aggregated.
    """
    cfg = result.get("config", {})
    provider = _parse_provider_base(cfg.get("provider", "unknown"))
    name = display_provider_name(provider)
    fw = provider_framework(provider)
    dataset = cfg.get("dataset", "unknown")
    temp = cfg.get("temperature")
    tpl = cfg.get("prompt_template")
    tpl_name = None
    if tpl:
        from pathlib import Path

        tpl_name = Path(tpl).stem
    return (name, fw, dataset, temp, tpl_name)


def display_provider_name(provider: str) -> str:
    """Map full provider paths to human-friendly display names via MODEL_MAP.

    Handles suffixed names like 'synthpanel/... t=0.85 tpl=current' by
    stripping suffixes before lookup.
    """
    entry = MODEL_MAP.get(provider)
    if entry:
        return entry[0]
    base = _parse_provider_base(provider)
    entry = MODEL_MAP.get(base)
    if entry:
        return entry[0]
    return provider


def provider_framework(provider: str) -> str:
    """Return the framework category for a provider: 'raw', 'product', or 'baseline'."""
    entry = MODEL_MAP.get(provider)
    if entry:
        return entry[1]
    base = _parse_provider_base(provider)
    entry = MODEL_MAP.get(base)
    if entry:
        return entry[1]
    if provider in BASELINE_PROVIDERS:
        return "baseline"
    return "raw"


def load_result(path: Path) -> dict:
    """Load a single result JSON file and return the dict as-is."""
    with open(path) as f:
        return json.load(f)


def _column_label(result: dict) -> str:
    """Build a short column label from a result dict: display_name (n=N)."""
    cfg = result.get("config", {})
    provider = cfg.get("provider", "unknown")
    name = display_provider_name(provider)
    n = cfg.get("n_evaluated", cfg.get("n_requested", "?"))
    return f"{name} (n={n})"


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
        _metric_row("SPS", aggregates, "composite_parity", bold=True),
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


def _result_entry(r: dict, rank: int) -> dict:
    """Build a leaderboard entry dict from a result dict."""
    cfg = r.get("config", {})
    agg = r.get("aggregate", {})
    ts = r.get("timestamp", "")
    date_str = ts[:10] if len(ts) >= 10 else "--"
    hp = _extract_hyperparams(r)
    entry = {
        "rank": rank,
        "provider": cfg.get("provider", "unknown"),
        "dataset": cfg.get("dataset", "unknown"),
        "n": cfg.get("n_evaluated", 0),
        "samples_per_question": cfg.get("samples_per_question", 0),
        "topic": cfg.get("topic"),
        "composite_parity": round(agg.get("composite_parity", 0), 4),
        "mean_jsd": round(agg.get("mean_jsd", 0), 4),
        "mean_kendall_tau": round(agg.get("mean_kendall_tau", 0), 4),
        "sps": round(agg.get("composite_parity", 0), 4),
        "date": date_str,
    }
    # Hyperparameters
    if "temperature" in hp:
        entry["temperature"] = hp["temperature"]
    if "template" in hp:
        entry["template"] = hp["template"]
    # Per-metric SPS components from CI data
    ci = agg.get("per_metric_ci", {})
    if ci:
        for metric in ("p_dist", "p_rank", "p_refuse"):
            bounds = ci.get(metric)
            if bounds and len(bounds) == 2:
                entry[metric] = round((bounds[0] + bounds[1]) / 2, 4)
    return entry


def _count_runs(results: list[dict]) -> dict[tuple, int]:
    """Count total runs per config key (includes temperature/template)."""
    counts: dict[tuple, int] = {}
    for r in results:
        key = _config_key(r)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _aggregate_replications(
    results: list[dict],
) -> dict[tuple, dict]:
    """Aggregate replications into mean ± std per config key.

    Returns {config_key: {"mean_sps": ..., "std_sps": ..., "n_runs": ...,
                          "mean_jsd": ..., "mean_tau": ..., "best_result": dict}}
    """
    import math

    groups: dict[tuple, list[dict]] = {}
    for r in results:
        key = _config_key(r)
        groups.setdefault(key, []).append(r)

    aggregated: dict[tuple, dict] = {}
    for key, runs in groups.items():
        sps_vals = [r.get("aggregate", {}).get("composite_parity", 0) for r in runs]
        jsd_vals = [r.get("aggregate", {}).get("mean_jsd", 0) for r in runs]
        tau_vals = [r.get("aggregate", {}).get("mean_kendall_tau", 0) for r in runs]

        n = len(sps_vals)
        mean_sps = sum(sps_vals) / n if n else 0
        std_sps = (
            math.sqrt(sum((v - mean_sps) ** 2 for v in sps_vals) / n) if n > 1 else 0
        )

        # Pick the result with most questions evaluated as representative
        best = max(
            runs,
            key=lambda r: r.get("config", {}).get("n_evaluated", 0),
        )

        aggregated[key] = {
            "mean_sps": round(mean_sps, 4),
            "std_sps": round(std_sps, 4),
            "mean_jsd": round(sum(jsd_vals) / n, 4) if n else 0,
            "mean_tau": round(sum(tau_vals) / n, 4) if n else 0,
            "n_runs": n,
            "best_result": best,
        }
    return aggregated


def _format_leaderboard_md(
    entries: list[dict],
    title: str = "# SynthBench Leaderboard",
    topics_present: list[str] | None = None,
    topic_scores: dict[str, dict[str, float]] | None = None,
    show_samples: bool = False,
    show_baselines: bool = False,
    show_hyperparams: bool = False,
    show_aggregation: bool = False,
) -> str:
    """Format leaderboard entries as markdown table."""
    topics_present = topics_present or []
    topic_scores = topic_scores or {}

    extra_cols = ""
    extra_seps = ""
    if show_samples:
        extra_cols = " Samples |"
        extra_seps = "---------|"

    baseline_cols = ""
    baseline_seps = ""
    if show_baselines:
        baseline_cols = " vs Random | vs Majority |"
        baseline_seps = "-----------|-------------|"

    # Build header with optional hyperparameter columns
    hp_cols = " Temp | Template |" if show_hyperparams else ""
    hp_seps = "------|----------|" if show_hyperparams else ""
    agg_cols = " ± Std | Runs |" if show_aggregation else ""
    agg_seps = "-------|------|" if show_aggregation else ""

    if topics_present:
        topic_headers = " | ".join(t.capitalize() for t in topics_present)
        topic_seps = " | ".join("---" for _ in topics_present)
        lines = [
            title,
            "",
            f"| Rank | Provider | Dataset | N |{extra_cols}{hp_cols} SPS |{agg_cols}{baseline_cols} {topic_headers} | JSD | tau | Date |",
            f"|------|----------|---------|---|{extra_seps}{hp_seps}--------|{agg_seps}{baseline_seps}{topic_seps}|-----|-----|------|",
        ]
    else:
        lines = [
            title,
            "",
            f"| Rank | Provider | Dataset | N |{extra_cols}{hp_cols} SPS |{agg_cols}{baseline_cols} JSD | tau | Date |",
            f"|------|----------|---------|---|{extra_seps}{hp_seps}--------|{agg_seps}{baseline_seps}-----|-----|------|",
        ]

    for e in entries:
        samples_col = (
            f" {e.get('samples_per_question', '--')} |" if show_samples else ""
        )
        hp_str = ""
        if show_hyperparams:
            temp = e.get("temperature")
            temp_str = f"{temp}" if temp is not None else "default"
            tpl = e.get("template", "—")
            hp_str = f" {temp_str} | {tpl} |"

        agg_str = ""
        if show_aggregation:
            std = e.get("std_sps")
            n_runs = e.get("n_runs", 1)
            std_str = f"±{std:.4f}" if std is not None and std > 0 else "—"
            agg_str = f" {std_str} | {n_runs} |"

        topic_str = ""
        if topics_present:
            topic_cells = []
            for t in topics_present:
                score = topic_scores.get(e["provider"], {}).get(t)
                topic_cells.append(f"{score:.4f}" if score is not None else "--")
            topic_str = " | " + " | ".join(topic_cells) + " "

        baseline_str = ""
        if show_baselines:
            vs_r = e.get("vs_random") or "--"
            vs_m = e.get("vs_majority") or "--"
            baseline_str = f" {vs_r} | {vs_m} |"

        runs_note = ""
        if not show_aggregation and "n_runs" in e and e["n_runs"] > 1:
            runs_note = f" ({e['n_runs']} runs)"

        provider_label = display_provider_name(e["provider"])
        lines.append(
            f"| {e['rank']} "
            f"| {provider_label}{runs_note} "
            f"| {e['dataset']} "
            f"| {e['n']} "
            f"|{samples_col}{hp_str} {e['composite_parity']:.4f} "
            f"|{agg_str}{baseline_str}"
            f"{topic_str}"
            f" {e['mean_jsd']:.4f} "
            f"| {e['mean_kendall_tau']:.4f} "
            f"| {e['date']} |"
        )

    lines.append("")
    return "\n".join(lines)


def _extract_baseline_scores(
    results: list[dict],
) -> dict[str, dict[str, float]]:
    """Extract best baseline scores per (baseline_provider, dataset).

    Returns {baseline_name: {dataset: composite_parity}}.
    """
    baselines: dict[str, dict[str, float]] = {}
    for r in results:
        cfg = r.get("config", {})
        provider = cfg.get("provider", "unknown")
        if provider not in BASELINE_PROVIDERS:
            continue
        dataset = cfg.get("dataset", "unknown")
        cp = r.get("aggregate", {}).get("composite_parity", 0)
        existing = baselines.setdefault(provider, {})
        if dataset not in existing or cp > existing[dataset]:
            existing[dataset] = cp
    return baselines


def _add_baseline_deltas(
    entries: list[dict], baseline_scores: dict[str, dict[str, float]]
) -> None:
    """Add vs_random and vs_majority delta fields to entries in-place."""
    for entry in entries:
        dataset = entry["dataset"]
        provider = entry["provider"]
        for baseline_name, label in [
            ("random-baseline", "vs_random"),
            ("majority-baseline", "vs_majority"),
        ]:
            base_cp = baseline_scores.get(baseline_name, {}).get(dataset)
            if base_cp is not None and provider not in BASELINE_PROVIDERS:
                delta = entry["composite_parity"] - base_cp
                entry[label] = f"{delta:+.4f}"
            else:
                entry[label] = None


def build_convergence_data(
    results: list[dict],
) -> dict[str, list[dict[str, object]]]:
    """Group runs by provider and extract sample-count sweeps.

    Returns {provider: [{samples: N, runs: [parity1, parity2, ...]}, ...]}
    Only includes providers with 2+ runs at different sample counts.
    """
    # Group by provider -> {samples_per_question: [composite_parity, ...]}
    provider_sweeps: dict[str, dict[int, list[float]]] = {}
    for r in results:
        cfg = r.get("config", {})
        provider = cfg.get("provider", "unknown")
        if provider in BASELINE_PROVIDERS:
            continue
        samples = cfg.get("samples_per_question", 0)
        cp = r.get("aggregate", {}).get("composite_parity", 0)
        provider_sweeps.setdefault(provider, {}).setdefault(samples, []).append(
            round(cp, 4)
        )

    # Filter to providers with 2+ distinct sample counts
    convergence: dict[str, list[dict[str, object]]] = {}
    for provider, sweep in provider_sweeps.items():
        if len(sweep) < 2:
            continue
        convergence[provider] = sorted(
            [{"samples": s, "runs": scores} for s, scores in sweep.items()],
            key=lambda x: x["samples"],
        )
    return convergence


def build_leaderboard(
    results: list[dict],
    *,
    show_all: bool = False,
    model_filter: str | None = None,
) -> tuple[str, dict]:
    """Build a ranked leaderboard from multiple result dicts.

    Args:
        results: List of SynthBench result dicts.
        show_all: If True, show all runs (detail tier) instead of summary.
        model_filter: If set, filter to results whose provider contains this string.

    Returns:
        (markdown_table, leaderboard_json) where leaderboard_json has the
        structure with "summary" and "detail" tiers plus "generated" timestamp.
    """
    if not results:
        return "No results for leaderboard.\n", {
            "summary": [],
            "detail": [],
            "generated": _now_iso(),
        }

    # Apply model filter
    if model_filter:
        results = [
            r
            for r in results
            if model_filter.lower() in r.get("config", {}).get("provider", "").lower()
        ]
        if not results:
            return f"No results matching model '{model_filter}'.\n", {
                "summary": [],
                "detail": [],
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

    # --- Detail tier: ALL runs, no dedup ---
    target = overall_results if overall_results else results
    detail_ranked = sorted(
        target,
        key=lambda r: r.get("aggregate", {}).get("composite_parity", 0),
        reverse=True,
    )
    detail_entries = [_result_entry(r, i + 1) for i, r in enumerate(detail_ranked)]

    # --- Summary tier: aggregate replications per config key ---
    aggregated = _aggregate_replications(target)

    # Sort by mean SPS descending
    sorted_keys = sorted(
        aggregated.keys(),
        key=lambda k: aggregated[k]["mean_sps"],
        reverse=True,
    )

    summary_entries = []
    for rank, key in enumerate(sorted_keys, 1):
        agg_data = aggregated[key]
        best_r = agg_data["best_result"]
        entry = _result_entry(best_r, rank)
        # Override SPS with aggregated mean
        entry["composite_parity"] = agg_data["mean_sps"]
        entry["sps"] = agg_data["mean_sps"]
        entry["mean_jsd"] = agg_data["mean_jsd"]
        entry["mean_kendall_tau"] = agg_data["mean_tau"]
        entry["std_sps"] = agg_data["std_sps"]
        entry["n_runs"] = agg_data["n_runs"]
        entry["framework"] = key[1]  # framework from config key
        if entry["provider"] in topic_scores:
            entry["topic_scores"] = topic_scores[entry["provider"]]
        summary_entries.append(entry)

    # --- Baseline deltas ---
    baseline_scores = _extract_baseline_scores(target)
    _add_baseline_deltas(summary_entries, baseline_scores)
    _add_baseline_deltas(detail_entries, baseline_scores)

    # Build markdown for the selected tier
    # Check if any results have hyperparameters worth showing
    has_hyperparams = any(
        e.get("temperature") is not None or e.get("template") is not None
        for e in summary_entries
    )
    has_multi_runs = any(e.get("n_runs", 1) > 1 for e in summary_entries)

    if show_all:
        md = _format_leaderboard_md(
            detail_entries,
            title="# SynthBench Leaderboard (All Runs)",
            topics_present=topics_present,
            topic_scores=topic_scores,
            show_samples=True,
            show_baselines=bool(baseline_scores),
            show_hyperparams=has_hyperparams,
        )
    else:
        md = _format_leaderboard_md(
            summary_entries,
            topics_present=topics_present,
            topic_scores=topic_scores,
            show_baselines=bool(baseline_scores),
            show_hyperparams=has_hyperparams,
            show_aggregation=has_multi_runs,
        )

    # --- Convergence data ---
    convergence = build_convergence_data(target)

    leaderboard_json = {
        "summary": summary_entries,
        "detail": detail_entries,
        "baselines": {
            name: {ds: round(cp, 4) for ds, cp in scores.items()}
            for name, scores in baseline_scores.items()
        },
        "convergence": convergence,
        "generated": _now_iso(),
    }

    return md, leaderboard_json


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()
