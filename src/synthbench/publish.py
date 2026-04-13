"""Export leaderboard data as JSON for the Astro frontend."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _dedup_results(results: list[dict]) -> list[dict]:
    """De-duplicate results: keep the run with the most n_evaluated per (display_name, framework, dataset).

    Also merges demographic_breakdown data from all runs sharing the same key
    into the winning entry, since conditioned runs may have fewer n_evaluated
    but carry unique demographic data.
    """
    from synthbench.leaderboard import display_provider_name, provider_framework

    best: dict[tuple[str, str, str], dict] = {}
    all_demographics: dict[tuple[str, str, str], dict[str, list]] = {}
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
        # Collect demographic data from all runs
        demo = r.get("demographic_breakdown", {})
        if demo:
            merged = all_demographics.setdefault(key, {})
            for attr, groups in demo.items():
                if isinstance(groups, list) and attr not in merged:
                    merged[attr] = groups

    # Merge collected demographics into winning entries
    for key, r in best.items():
        if key in all_demographics:
            existing_demo = r.get("demographic_breakdown", {})
            if not existing_demo:
                r["demographic_breakdown"] = all_demographics[key]
            else:
                for attr, groups in all_demographics[key].items():
                    if attr not in existing_demo:
                        existing_demo[attr] = groups

    return list(best.values())


def _compute_topic_scores(per_question: list[dict]) -> dict[str, float]:
    """Compute per-topic aggregate SPS from per-question data using keyword categorization."""
    from synthbench.topics import categorize_question

    topic_parities: dict[str, list[float]] = {}
    for q in per_question:
        text = q.get("text", "")
        if not text:
            continue
        category = categorize_question(text)
        parity = q.get("parity")
        if parity is not None:
            topic_parities.setdefault(category, []).append(parity)

    topic_scores: dict[str, float] = {}
    for category, parities in sorted(topic_parities.items()):
        if parities:
            topic_scores[category] = round(sum(parities) / len(parities), 6)
    return topic_scores


def _build_entry(r: dict, rank: int) -> dict:
    """Build a leaderboard entry from a result dict."""
    from synthbench.leaderboard import display_provider_name, provider_framework

    cfg = r.get("config", {})
    provider_raw = cfg.get("provider", "unknown")
    provider_name = display_provider_name(provider_raw)
    framework = provider_framework(provider_raw)
    scores = r.get("scores", {})
    agg = r.get("aggregate", {})
    ci = agg.get("per_metric_ci", {}).get("sps", [0, 0])

    is_baseline = framework == "baseline"
    is_ensemble = "ensemble" in provider_raw.lower()

    entry: dict = {
        "rank": rank,
        "provider": provider_name,
        "model": provider_name,
        "dataset": cfg.get("dataset", "unknown"),
        "framework": framework,
        "sps": round(scores.get("sps", 0), 6),
        "p_dist": round(scores.get("p_dist", 0), 6),
        "p_rank": round(scores.get("p_rank", 0), 6),
        "p_refuse": round(scores.get("p_refuse", 0), 6),
        "jsd": round(agg.get("mean_jsd", 0), 6),
        "tau": round(agg.get("mean_kendall_tau", 0), 6),
        "n": cfg.get("n_evaluated", 0),
        "ci_lower": round(ci[0], 6) if len(ci) >= 2 else 0,
        "ci_upper": round(ci[1], 6) if len(ci) >= 2 else 0,
        "is_baseline": is_baseline,
        "is_ensemble": is_ensemble,
    }

    # Optional sub-metrics (conditioned runs only)
    p_cond = scores.get("p_cond")
    if p_cond is not None and p_cond > 0:
        entry["p_cond"] = round(p_cond, 6)
    p_sub = scores.get("p_sub")
    if p_sub is not None:
        entry["p_sub"] = round(p_sub, 6)

    # Run metadata
    spq = cfg.get("samples_per_question")
    if spq is not None:
        entry["samples_per_question"] = spq
    temp = cfg.get("temperature")
    if temp is not None:
        entry["temperature"] = temp
    tpl = cfg.get("prompt_template")
    if tpl:
        entry["template"] = Path(tpl).stem

    # Topic scores from per-question keyword categorization
    per_question = r.get("per_question", [])
    if per_question:
        topic_scores = _compute_topic_scores(per_question)
        if topic_scores:
            entry["topic_scores"] = topic_scores

    # Demographic scores (real SubPOP data)
    demo_breakdown = r.get("demographic_breakdown", {})
    if demo_breakdown:
        flat_demographics: list[dict] = []
        for _attr, groups in demo_breakdown.items():
            if isinstance(groups, list):
                for g in groups:
                    flat_demographics.append(
                        {
                            "attribute": g.get("attribute", ""),
                            "group": g.get("group", ""),
                            "p_dist": round(g.get("p_dist", 0), 6),
                            "p_cond": round(g.get("p_cond", 0), 6),
                            "n_questions": g.get("n_questions", 0),
                        }
                    )
        if flat_demographics:
            entry["demographic_scores"] = flat_demographics

    return entry


def _build_findings() -> dict:
    """Build pre-computed findings data from FINDINGS.md experiment results."""
    return {
        "temperature_sweep": [
            # Experiment A: Claude Haiku 4.5
            {
                "model": "Claude Haiku 4.5",
                "temperature": 0.3,
                "sps": 0.843,
                "std": 0.003,
            },
            {
                "model": "Claude Haiku 4.5",
                "temperature": 0.5,
                "sps": 0.845,
                "std": 0.002,
            },
            {
                "model": "Claude Haiku 4.5",
                "temperature": 0.7,
                "sps": 0.847,
                "std": 0.003,
            },
            {
                "model": "Claude Haiku 4.5",
                "temperature": 0.85,
                "sps": 0.849,
                "std": 0.002,
            },
            {
                "model": "Claude Haiku 4.5",
                "temperature": 1.0,
                "sps": 0.850,
                "std": 0.001,
            },
            # Experiment A: Gemini Flash Lite
            {
                "model": "Gemini Flash Lite",
                "temperature": 0.3,
                "sps": 0.819,
                "std": 0.004,
            },
            {
                "model": "Gemini Flash Lite",
                "temperature": 0.5,
                "sps": 0.831,
                "std": 0.003,
            },
            {
                "model": "Gemini Flash Lite",
                "temperature": 0.7,
                "sps": 0.842,
                "std": 0.003,
            },
            {
                "model": "Gemini Flash Lite",
                "temperature": 0.85,
                "sps": 0.850,
                "std": 0.002,
            },
            {
                "model": "Gemini Flash Lite",
                "temperature": 1.0,
                "sps": 0.856,
                "std": 0.003,
            },
            # Experiment D: Gemini extended temperature
            {
                "model": "Gemini Flash Lite",
                "temperature": 1.2,
                "sps": 0.856,
                "std": 0.002,
            },
            {
                "model": "Gemini Flash Lite",
                "temperature": 1.5,
                "sps": 0.858,
                "std": 0.003,
            },
            {
                "model": "Gemini Flash Lite",
                "temperature": 1.8,
                "sps": 0.857,
                "std": 0.002,
            },
            {
                "model": "Gemini Flash Lite",
                "temperature": 2.0,
                "sps": 0.864,
                "std": 0.002,
            },
            # Experiment A: GPT-4o-mini
            {"model": "GPT-4o-mini", "temperature": 0.3, "sps": 0.817, "std": 0.004},
            {"model": "GPT-4o-mini", "temperature": 0.5, "sps": 0.820, "std": 0.003},
            {"model": "GPT-4o-mini", "temperature": 0.7, "sps": 0.823, "std": 0.003},
            {"model": "GPT-4o-mini", "temperature": 0.85, "sps": 0.826, "std": 0.002},
            {"model": "GPT-4o-mini", "temperature": 1.0, "sps": 0.829, "std": 0.002},
        ],
        "ensemble_comparison": [
            {
                "dataset": "opinionsqa",
                "best_single_model": "Claude Haiku 4.5",
                "best_single_sps": 0.766,
                "ensemble_sps": 0.836,
                "improvement": 0.070,
            },
            {
                "dataset": "subpop",
                "best_single_model": "Gemini Flash Lite",
                "best_single_sps": 0.744,
                "ensemble_sps": 0.796,
                "improvement": 0.052,
            },
            {
                "dataset": "globalopinionqa",
                "best_single_model": "GPT-4o-mini",
                "best_single_sps": 0.692,
                "ensemble_sps": 0.747,
                "improvement": 0.056,
            },
        ],
        "conditioning_results": [
            {
                "attribute": "POLPARTY",
                "group": "Republican",
                "p_dist": 0.666,
                "p_cond": 0.073,
                "p_cond_std": 0.004,
                "n_replications": 4,
            },
            {
                "attribute": "POLPARTY",
                "group": "Democrat",
                "p_dist": 0.644,
                "p_cond": 0.033,
                "p_cond_std": 0.005,
                "n_replications": 4,
            },
            {
                "attribute": "INCOME",
                "group": "$100K+",
                "p_dist": 0.673,
                "p_cond": 0.031,
                "n_replications": 2,
            },
            {
                "attribute": "INCOME",
                "group": "<$30K",
                "p_dist": 0.603,
                "p_cond": 0.020,
                "n_replications": 2,
            },
            {
                "attribute": "EDUCATION",
                "group": "College graduate",
                "p_dist": 0.641,
                "p_cond": 0.036,
                "n_replications": 1,
            },
            {
                "attribute": "EDUCATION",
                "group": "Less than HS",
                "p_dist": 0.597,
                "p_cond": 0.038,
                "n_replications": 1,
            },
        ],
        "lever_hierarchy": [
            {
                "name": "Ensemble blending",
                "effect_min": 5.0,
                "effect_max": 7.0,
                "cost": "zero",
                "status": "done",
            },
            {
                "name": "Per-model optimal temperature",
                "effect_min": 0.0,
                "effect_max": 4.5,
                "cost": "low",
                "status": "actionable",
            },
            {
                "name": "Demographic conditioning",
                "effect_min": 2.0,
                "effect_max": 7.0,
                "cost": "moderate",
                "status": "scientific",
            },
            {
                "name": "Persona template",
                "effect_min": 0.0,
                "effect_max": 0.0,
                "cost": "zero",
                "status": "done",
            },
        ],
    }


def publish_leaderboard_data(
    results_dir: Path, output_path: Path, version: str = "0.1.0"
) -> Path:
    """Export leaderboard data as JSON for the Astro frontend.

    Reads all result JSON files from results_dir, deduplicates and ranks them,
    then writes a single JSON file conforming to the SynthBenchData TypeScript
    interface.

    Returns the path to the generated JSON file.
    """
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
        ds_results.sort(key=lambda r: r.get("scores", {}).get("sps", 0), reverse=True)
        for rank, r in enumerate(ds_results, 1):
            entries.append(_build_entry(r, rank))

    # Build convergence data
    from synthbench.leaderboard import build_convergence_data

    convergence_raw = build_convergence_data(results)
    convergence: list[dict] = []
    for provider, sweeps in convergence_raw.items():
        for sweep in sweeps:
            for sps_val in sweep.get("runs", []):
                convergence.append(
                    {
                        "model": provider,
                        "dataset": "opinionsqa",
                        "rep_count": sweep.get("samples", 0),
                        "sps": sps_val,
                    }
                )

    synthbench_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "synthbench_version": version,
        "datasets": datasets,
        "entries": entries,
        "convergence": convergence,
        "findings": _build_findings(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(synthbench_data, f, indent=2)
        f.write("\n")
    return output_path
