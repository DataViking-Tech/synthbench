"""Export leaderboard data as JSON for the Astro frontend."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _dedup_results(results: list[dict]) -> list[dict]:
    """De-duplicate results: keep the run with the most n_evaluated per (display_name, framework, dataset)."""
    from synthbench.leaderboard import display_provider_name, provider_framework

    best: dict[tuple[str, str, str], dict] = {}
    for r in results:
        cfg = r.get("config", {})
        provider = cfg.get("provider", "unknown")
        dataset = cfg.get("dataset", "unknown")
        n_eval = cfg.get("n_evaluated", 0)
        name = display_provider_name(provider)
        fw = provider_framework(provider)
        key = (name, fw, dataset)
        existing = best.get(key)
        if existing is None or n_eval > existing["config"].get("n_evaluated", 0):
            best[key] = r
    return list(best.values())


def publish_leaderboard_data(
    results_dir: Path, output_path: Path, version: str = "0.1.0"
) -> Path:
    """Export leaderboard data as JSON for the Astro frontend.

    Reads all result JSON files from results_dir, deduplicates and ranks them,
    then writes a single JSON file conforming to the LeaderboardData TypeScript
    interface.

    Returns the path to the generated JSON file.
    """
    from synthbench.leaderboard import (
        display_provider_name,
        provider_framework,
    )

    json_files = sorted(results_dir.glob("*.json"))
    results = []
    for jf in json_files:
        try:
            with open(jf) as f:
                data = json.load(f)
            if data.get("benchmark") == "synthbench":
                results.append(data)
        except (json.JSONDecodeError, KeyError):
            continue

    if not results:
        raise ValueError(f"No valid SynthBench result files found in {results_dir}")

    deduped = _dedup_results(results)

    # Collect all datasets
    datasets_set: set[str] = set()
    for r in deduped:
        ds = r.get("config", {}).get("dataset", "unknown")
        datasets_set.add(ds)
    datasets = sorted(datasets_set)

    # Build ranked entries per dataset
    entries = []
    for ds in datasets:
        ds_results = [
            r for r in deduped if r.get("config", {}).get("dataset", "unknown") == ds
        ]
        # Sort by SPS descending
        ds_results.sort(key=lambda r: r.get("scores", {}).get("sps", 0), reverse=True)

        for rank, r in enumerate(ds_results, 1):
            cfg = r.get("config", {})
            provider_raw = cfg.get("provider", "unknown")
            provider_name = display_provider_name(provider_raw)
            framework = provider_framework(provider_raw)
            scores = r.get("scores", {})
            agg = r.get("aggregate", {})
            ci = agg.get("per_metric_ci", {}).get("sps", [0, 0])

            is_baseline = framework == "baseline"
            is_ensemble = "ensemble" in provider_raw.lower()

            # Derive model name from provider name
            model = provider_name

            entry = {
                "rank": rank,
                "provider": provider_name,
                "model": model,
                "dataset": ds,
                "sps": round(scores.get("sps", 0), 6),
                "jsd": round(agg.get("mean_jsd", 0), 6),
                "tau": round(agg.get("mean_kendall_tau", 0), 6),
                "n": cfg.get("n_evaluated", 0),
                "ci_lower": round(ci[0], 6) if len(ci) >= 2 else 0,
                "ci_upper": round(ci[1], 6) if len(ci) >= 2 else 0,
                "is_baseline": is_baseline,
                "is_ensemble": is_ensemble,
            }

            temp = cfg.get("temperature")
            if temp is not None:
                entry["temperature"] = temp

            tpl = cfg.get("prompt_template")
            if tpl:
                entry["template"] = Path(tpl).stem

            # Topic scores if available
            topic_scores = r.get("demographic_breakdown", {})
            if topic_scores:
                entry["topic_scores"] = {
                    k: round(v, 6) if isinstance(v, float) else v
                    for k, v in topic_scores.items()
                }

            entries.append(entry)

    leaderboard_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "synthbench_version": version,
        "datasets": datasets,
        "entries": entries,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(leaderboard_data, f, indent=2)
        f.write("\n")
    return output_path
