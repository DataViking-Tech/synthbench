"""Suite runner — execute a full structured benchmark matrix for a provider."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import yaml

from synthbench.suites import SUITE_DIR

SUITES_DIR = SUITE_DIR  # YAML configs live alongside pinned question sets

HIGH_CV_THRESHOLD = 0.02  # 2% — flag runs with CV above this


def load_suite_config(name: str = "standard") -> list[dict]:
    """Load a suite YAML config and return the list of run definitions."""
    path = SUITES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Suite config not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    return data["runs"]


def _gap_key(provider: str, dataset: str, topic: str | None, samples: int) -> str:
    """Build a canonical key for matching runs to existing results."""
    return f"{provider}|{dataset}|{topic or 'all'}|{samples}"


def find_existing_results(output_dir: Path, provider: str) -> dict[str, list[dict]]:
    """Scan output_dir for existing result JSONs matching this provider.

    Returns a dict mapping gap_key -> list[result_data] for results that match
    the given provider. Multiple results per key represent repeats.
    """
    results: dict[str, list[dict]] = {}
    if not output_dir.is_dir():
        return results

    for jf in output_dir.glob("*.json"):
        try:
            with open(jf) as f:
                data = json.load(f)
        except (json.JSONDecodeError, KeyError):
            continue
        if data.get("benchmark") != "synthbench":
            continue
        cfg = data.get("config", {})
        result_provider = cfg.get("provider", "")
        if result_provider != provider:
            continue

        dataset = cfg.get("dataset", "")
        topic = cfg.get("topic_filter") or cfg.get("topic")
        samples = cfg.get("samples_per_question", 0)

        key = _gap_key(provider, dataset, topic, samples)
        results.setdefault(key, []).append(data)

    return results


def check_suite(
    provider: str,
    output_dir: Path,
    suite_name: str = "standard",
    repeats_override: int | None = None,
) -> list[dict]:
    """Check which suite runs exist for a provider. Returns annotated run list."""
    runs = load_suite_config(suite_name)
    existing = find_existing_results(output_dir, provider)

    annotated = []
    for run in runs:
        repeats_needed = (
            repeats_override if repeats_override is not None else run.get("repeats", 3)
        )
        key = _gap_key(
            provider, run["dataset"], run.get("topic"), run.get("samples", 30)
        )
        matches = existing.get(key, [])
        n_existing = len(matches)

        if n_existing >= repeats_needed:
            status = "done"
        elif n_existing > 0:
            status = "partial"
        else:
            status = "missing"

        entry = {
            **run,
            "status": status,
            "n_existing": n_existing,
            "repeats_needed": repeats_needed,
        }
        if matches:
            sps_vals = [m.get("scores", {}).get("sps", 0.0) for m in matches]
            entry["sps_values"] = sps_vals
            entry["sps_mean"] = statistics.mean(sps_vals)
            if len(sps_vals) > 1:
                entry["sps_std"] = statistics.stdev(sps_vals)
            else:
                entry["sps_std"] = 0.0
        annotated.append(entry)

    return annotated


def _compute_variance_stats(sps_values: list[float]) -> dict:
    """Compute mean, std, CV from a list of SPS values."""
    if not sps_values:
        return {"mean": 0.0, "std": 0.0, "cv": 0.0, "high_variance": False}
    mean = statistics.mean(sps_values)
    std = statistics.stdev(sps_values) if len(sps_values) > 1 else 0.0
    cv = std / mean if mean > 0 else 0.0
    return {
        "mean": mean,
        "std": std,
        "cv": cv,
        "high_variance": cv > HIGH_CV_THRESHOLD,
    }


async def run_suite(
    provider_name: str,
    model: str,
    output_dir: Path,
    concurrency: int = 10,
    suite_name: str = "standard",
    url: str | None = None,
    data_dir: str | None = None,
    force: bool = False,
    default_repeats: int = 3,
    repeats_override: int | None = None,
) -> list[dict]:
    """Run the full suite of benchmarks for a provider/model combination.

    By default operates in gap-fill mode: only runs missing/partial repeats.
    Use force=True to re-run everything.

    Args:
        repeats_override: If set, overrides the per-run YAML repeats value.
        default_repeats: Fallback when a run has no repeats in the YAML.

    Returns a list of result summaries (one per run definition).
    """
    import click

    from synthbench import report
    from synthbench.cli import MODEL_ALIASES
    from synthbench.datasets import DATASETS
    from synthbench.providers import load_provider
    from synthbench.runner import BenchmarkRunner

    runs = load_suite_config(suite_name)
    resolved_model = MODEL_ALIASES.get(model, model)

    # Build provider once
    provider_kwargs = {"model": resolved_model}
    if url:
        provider_kwargs["url"] = url
    prov = load_provider(provider_name, **provider_kwargs)

    # Check existing results for gap detection
    existing = find_existing_results(output_dir, prov.name) if not force else {}

    summaries = []
    total_runs = len(runs)

    try:
        for i, run_cfg in enumerate(runs, 1):
            label = run_cfg["label"]
            dataset_name = run_cfg["dataset"]
            topic = run_cfg.get("topic")
            n = run_cfg.get("n")
            samples = run_cfg.get("samples", 30)
            repeats_needed = (
                repeats_override
                if repeats_override is not None
                else run_cfg.get("repeats", default_repeats)
            )

            key = _gap_key(prov.name, dataset_name, topic, samples)
            existing_matches = existing.get(key, [])
            n_existing = len(existing_matches)
            n_to_run = (
                max(0, repeats_needed - n_existing) if not force else repeats_needed
            )

            existing_sps = [
                m.get("scores", {}).get("sps", 0.0) for m in existing_matches
            ]

            if n_to_run == 0:
                vstats = _compute_variance_stats(existing_sps)
                cv_warn = " ⚠ high variance" if vstats["high_variance"] else ""
                click.echo(
                    f"Run {i}/{total_runs}: {label}... "
                    f"[SKIP {n_existing}/{repeats_needed}] "
                    f"mean SPS={vstats['mean']:.3f} CV={vstats['cv']:.3f}{cv_warn}"
                )
                summaries.append(
                    {
                        "label": label,
                        "status": "skipped",
                        "repeats_needed": repeats_needed,
                        "n_existing": n_existing,
                        "n_completed": 0,
                        "sps_values": existing_sps,
                        **vstats,
                    }
                )
                continue

            # Load dataset
            if dataset_name not in DATASETS:
                click.echo(
                    f"Run {i}/{total_runs}: {label}... [ERROR] unknown dataset '{dataset_name}'"
                )
                summaries.append(
                    {
                        "label": label,
                        "status": "error",
                        "error": f"unknown dataset '{dataset_name}'",
                    }
                )
                continue

            ds_kwargs = {}
            if data_dir:
                ds_kwargs["data_dir"] = data_dir
            ds = DATASETS[dataset_name](**ds_kwargs)

            # Load topic question keys
            question_keys = None
            if topic:
                from synthbench.suites import load_topic_suite

                question_keys = load_topic_suite(topic)

            runner = BenchmarkRunner(
                dataset=ds,
                provider=prov,
                samples_per_question=samples,
                concurrency=concurrency,
            )

            run_sps_values = list(existing_sps)  # start with existing

            click.echo(
                f"Run {i}/{total_runs}: {label} "
                f"({n_to_run} of {repeats_needed} repeats)..."
            )

            for rep in range(n_to_run):
                click.echo(
                    f"  repeat {n_existing + rep + 1}/{repeats_needed}...", nl=False
                )

                result = await runner.run(n=n, question_keys=question_keys)

                # Tag result config
                result.config["provider"] = prov.name
                result.config["dataset"] = dataset_name
                if topic:
                    result.config["topic"] = topic
                result.config["suite_label"] = label

                sps = result.sps
                run_sps_values.append(sps)
                click.echo(f" SPS={sps:.3f}")

                # Save
                report.save(result, output_dir)

            vstats = _compute_variance_stats(run_sps_values)
            cv_warn = (
                " ⚠ high variance — may need more samples"
                if vstats["high_variance"]
                else ""
            )
            click.echo(
                f"  → mean={vstats['mean']:.3f} std={vstats['std']:.4f} "
                f"CV={vstats['cv']:.3f}{cv_warn}"
            )

            summaries.append(
                {
                    "label": label,
                    "status": "completed",
                    "repeats_needed": repeats_needed,
                    "n_existing": n_existing,
                    "n_completed": n_to_run,
                    "sps_values": run_sps_values,
                    **vstats,
                }
            )
    finally:
        await prov.close()

    return summaries


def format_summary(summaries: list[dict], provider: str) -> str:
    """Format a summary table of all suite runs with variance stats."""
    lines = [
        f"Suite Summary: {provider}",
        "",
        f"{'#':<3} {'Run':<25} {'Status':<12} {'Mean SPS':>9} "
        f"{'Std':>7} {'CV':>6} {'Repeats':>8}",
        f"{'─' * 3} {'─' * 25} {'─' * 12} {'─' * 9} {'─' * 7} {'─' * 6} {'─' * 8}",
    ]

    completed = 0
    skipped = 0
    errors = 0

    for i, s in enumerate(summaries, 1):
        status = s.get("status", "unknown")
        label = s["label"]
        mean_sps = s.get("mean", 0.0)
        std = s.get("std", 0.0)
        cv = s.get("cv", 0.0)
        n_existing = s.get("n_existing", 0)
        n_completed = s.get("n_completed", 0)
        repeats_needed = s.get("repeats_needed", 0)
        high_var = s.get("high_variance", False)

        total_done = n_existing + n_completed

        if status == "completed":
            completed += 1
            status_str = "DONE"
        elif status == "skipped":
            skipped += 1
            status_str = "SKIP"
        else:
            errors += 1
            status_str = "ERROR"

        cv_flag = " ⚠" if high_var else ""
        repeats_str = f"{total_done}/{repeats_needed}"

        if status == "error":
            lines.append(
                f"{i:<3} {label:<25} {status_str:<12} {'—':>9} "
                f"{'—':>7} {'—':>6} {'—':>8}"
            )
        else:
            lines.append(
                f"{i:<3} {label:<25} {status_str:<12} {mean_sps:>9.3f} "
                f"{std:>7.4f} {cv:>5.3f}{cv_flag} {repeats_str:>8}"
            )

    lines.append("")
    lines.append(
        f"Total: {len(summaries)} runs | "
        f"{completed} completed | {skipped} skipped | {errors} errors"
    )

    # Flag high-variance runs
    high_var_runs = [s["label"] for s in summaries if s.get("high_variance")]
    if high_var_runs:
        lines.append("")
        lines.append(
            f"⚠ High variance (CV > {HIGH_CV_THRESHOLD:.0%}): "
            + ", ".join(high_var_runs)
        )

    return "\n".join(lines)


def format_check(annotated: list[dict], provider: str) -> str:
    """Format the --check dry-run output."""
    lines = [
        f"Suite Check: {provider}",
        "",
        f"{'#':<3} {'Run':<25} {'Status':<20} {'Mean SPS':>9} {'Std':>7}",
        f"{'─' * 3} {'─' * 25} {'─' * 20} {'─' * 9} {'─' * 7}",
    ]

    done = 0
    partial = 0
    missing = 0

    for i, entry in enumerate(annotated, 1):
        label = entry["label"]
        status = entry["status"]
        n_existing = entry["n_existing"]
        repeats_needed = entry["repeats_needed"]

        if status == "done":
            done += 1
            status_str = f"[DONE] {n_existing}/{repeats_needed}"
            mean_sps = entry.get("sps_mean", 0.0)
            std = entry.get("sps_std", 0.0)
            lines.append(
                f"{i:<3} {label:<25} {status_str:<20} {mean_sps:>9.3f} {std:>7.4f}"
            )
        elif status == "partial":
            partial += 1
            status_str = f"[PARTIAL {n_existing}/{repeats_needed}]"
            mean_sps = entry.get("sps_mean", 0.0)
            std = entry.get("sps_std", 0.0)
            lines.append(
                f"{i:<3} {label:<25} {status_str:<20} {mean_sps:>9.3f} {std:>7.4f}"
            )
        else:
            missing += 1
            status_str = "[MISSING]"
            lines.append(f"{i:<3} {label:<25} {status_str:<20} {'—':>9} {'—':>7}")

    lines.append("")
    lines.append(
        f"Total: {len(annotated)} runs | "
        f"{done} done | {partial} partial | {missing} missing"
    )

    return "\n".join(lines)
