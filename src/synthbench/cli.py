"""SynthBench CLI — synthbench run, synthbench report."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click

from synthbench import __version__

# Model aliases for convenience
MODEL_ALIASES = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-5-20241022",
    "opus": "claude-opus-4-0-20250514",
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "gemini-flash": "gemini-2.5-flash-preview-05-20",
    "gemini-flash-lite": "gemini-2.5-flash-lite",
    "gemini-pro": "gemini-2.5-pro-preview-05-06",
}


@click.group()
@click.version_option(__version__)
def main():
    """SynthBench — benchmark harness for synthetic survey respondents."""
    pass


@main.command()
@click.option(
    "--provider",
    "-p",
    required=True,
    help="Provider name (raw-anthropic, raw-openai, raw-gemini, openrouter, ollama, synthpanel, http).",
)
@click.option(
    "--model",
    "-m",
    default="haiku",
    help="Model name or alias (haiku, sonnet, gpt-4o-mini, etc.).",
)
@click.option(
    "--dataset",
    "-d",
    default="opinionsqa",
    help="Dataset to benchmark against.",
)
@click.option(
    "--n",
    "-n",
    type=int,
    default=None,
    help="Number of questions to evaluate (default: all).",
)
@click.option(
    "--samples",
    "-s",
    type=int,
    default=30,
    help="Samples per question for distribution estimation.",
)
@click.option(
    "--concurrency",
    "-c",
    type=int,
    default=10,
    help="Max concurrent API requests.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="results",
    help="Output directory for score cards.",
)
@click.option(
    "--data-dir",
    type=click.Path(),
    default=None,
    help="Custom data directory for datasets.",
)
@click.option(
    "--url",
    default=None,
    help="Endpoint URL (required for --provider http).",
)
@click.option(
    "--json-only", is_flag=True, help="Output JSON to stdout instead of files."
)
@click.option(
    "--suite",
    type=click.Choice(["smoke", "core", "full"]),
    default=None,
    help="Use a pinned question set (smoke=28, core=200, full=all).",
)
@click.option(
    "--topic",
    type=click.Choice(["political", "consumer", "neutral"]),
    default=None,
    help="Filter to a topic subset (political, consumer, neutral).",
)
@click.option(
    "--baselines-dir",
    type=click.Path(exists=True),
    default=None,
    help="Directory with baseline results for 'vs Baselines' section.",
)
@click.option(
    "--demographics",
    default=None,
    help="Comma-separated demographic attributes to evaluate (e.g., AGE,POLIDEOLOGY).",
)
@click.option(
    "--full-evaluation",
    is_flag=True,
    help="Run all 8 demographic attributes (AGE,CREGION,EDUCATION,INCOME,POLIDEOLOGY,POLPARTY,RACE,SEX).",
)
def run(
    provider,
    model,
    dataset,
    n,
    samples,
    concurrency,
    output,
    data_dir,
    url,
    json_only,
    suite,
    topic,
    baselines_dir,
    demographics,
    full_evaluation,
):
    """Run a benchmark evaluation.

    Example:
        synthbench run --provider raw-anthropic --model haiku --n 100
        synthbench run --provider raw-anthropic --model haiku --suite core
        synthbench run --provider raw-anthropic --topic consumer
        synthbench run --provider raw-anthropic --demographics AGE,POLIDEOLOGY
        synthbench run --provider raw-anthropic --full-evaluation
    """
    # Resolve demographics
    demo_list = None
    if full_evaluation:
        demo_list = [
            "AGE",
            "CREGION",
            "EDUCATION",
            "INCOME",
            "POLIDEOLOGY",
            "POLPARTY",
            "RACE",
            "SEX",
        ]
    elif demographics:
        demo_list = [d.strip().upper() for d in demographics.split(",")]

    asyncio.run(
        _run_async(
            provider,
            model,
            dataset,
            n,
            samples,
            concurrency,
            output,
            data_dir,
            url,
            json_only,
            suite,
            topic,
            baselines_dir,
            demo_list,
        )
    )


async def _run_async(
    provider_name,
    model,
    dataset_name,
    n,
    samples,
    concurrency,
    output,
    data_dir,
    url,
    json_only,
    suite,
    topic,
    baselines_dir,
    demographics=None,
):
    from synthbench.datasets import DATASETS
    from synthbench.providers import load_provider
    from synthbench.runner import BenchmarkRunner
    from synthbench import report

    # Resolve model alias
    resolved_model = MODEL_ALIASES.get(model, model)

    # Load dataset
    if dataset_name not in DATASETS:
        click.echo(
            f"Unknown dataset '{dataset_name}'. Available: {list(DATASETS)}", err=True
        )
        sys.exit(1)

    ds_kwargs = {}
    if data_dir:
        ds_kwargs["data_dir"] = data_dir
    ds = DATASETS[dataset_name](**ds_kwargs)

    # Load provider
    provider_kwargs = {"model": resolved_model}
    if url:
        provider_kwargs["url"] = url
    try:
        prov = load_provider(provider_name, **provider_kwargs)
    except KeyError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    except ImportError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    # Load suite if specified
    question_keys = None
    if suite:
        from synthbench.suites import load_suite

        question_keys = load_suite(suite)

    # Load topic suite if specified (intersect with suite if both given)
    if topic:
        from synthbench.suites import load_topic_suite

        topic_keys = load_topic_suite(topic)
        if question_keys is not None:
            # Intersect: keep only keys in both suite and topic
            topic_set = set(topic_keys)
            question_keys = [k for k in question_keys if k in topic_set]
        else:
            question_keys = topic_keys

    # Run benchmark
    runner = BenchmarkRunner(
        dataset=ds,
        provider=prov,
        samples_per_question=samples,
        concurrency=concurrency,
    )

    suite_label = f"suite={suite}" if suite else (str(n) if n else "all")
    if topic:
        suite_label += f" topic={topic}"
    click.echo(f"SynthBench v{__version__}")
    click.echo(f"  Provider: {prov.name}")
    click.echo(f"  Dataset:  {ds.name}")
    click.echo(f"  Questions: {suite_label}")
    click.echo(f"  Samples/q: {samples}")
    if demographics:
        click.echo(f"  Demographics: {', '.join(demographics)}")
    click.echo()

    def progress(done, total, qr):
        pct = done / total * 100
        click.echo(
            f"\r  [{done}/{total}] {pct:5.1f}% | "
            f"JSD={qr.jsd:.4f} tau={qr.kendall_tau:.4f}",
            nl=False,
        )

    try:
        if demographics:
            result = await runner.run_with_demographics(
                demographics=demographics,
                n=n,
                progress_callback=progress,
                question_keys=question_keys,
            )
        else:
            result = await runner.run(
                n=n, progress_callback=progress, question_keys=question_keys
            )
    finally:
        await prov.close()

    # Tag result with topic if specified
    if topic:
        result.config["topic"] = topic

    click.echo()  # Newline after progress
    click.echo()

    # Per-metric SPS summary with CIs
    components = result.sps_components
    cis = result.per_metric_ci
    sps_ci = cis.get("sps")
    if sps_ci:
        click.echo(
            f"  SPS: {result.sps:.4f} [{sps_ci[0]:.4f}, {sps_ci[1]:.4f}]  ({len(components)} metrics)"
        )
    else:
        click.echo(f"  SPS: {result.sps:.4f}  ({len(components)} metrics)")
    for key, score in components.items():
        ci = cis.get(key)
        if ci:
            click.echo(f"    {key}: {score:.4f} [{ci[0]:.4f}, {ci[1]:.4f}]")
        else:
            click.echo(f"    {key}: {score:.4f}")
    if result.total_parse_failures > 0:
        click.echo(f"  Parse failures: {result.total_parse_failures}")

    # Demographic breakdown summary
    if result.demographic_breakdown:
        click.echo("  Demographic breakdown:")
        for attr, group_results in result.demographic_breakdown.items():
            best = max(group_results, key=lambda g: g.p_dist)
            worst = min(group_results, key=lambda g: g.p_dist)
            click.echo(
                f"    {attr}: Best={best.group} (P_dist={best.p_dist:.4f}) "
                f"/ Worst={worst.group} (P_dist={worst.p_dist:.4f})"
            )
    click.echo()

    if json_only:
        click.echo(json.dumps(report.to_json(result), indent=2))
    else:
        # Print markdown summary to terminal
        bl_dir = Path(baselines_dir) if baselines_dir else None
        click.echo(report.to_markdown(result, baselines_dir=bl_dir))

        # Save files
        json_path, md_path = report.save(result, output)
        click.echo("\nResults saved:")
        click.echo(f"  JSON: {json_path}")
        click.echo(f"  Report: {md_path}")


@main.command()
@click.argument("json_file", type=click.Path(exists=True))
def report(json_file):
    """Regenerate a markdown report from a JSON score card."""
    from synthbench.runner import BenchmarkResult, QuestionResult
    from synthbench import report as report_mod

    with open(json_file) as f:
        data = json.load(f)

    # Reconstruct BenchmarkResult from JSON
    questions = [
        QuestionResult(
            key=q["key"],
            text=q["text"],
            options=q["options"],
            human_distribution=q["human_distribution"],
            model_distribution=q["model_distribution"],
            jsd=q["jsd"],
            kendall_tau=q["kendall_tau"],
            parity=q["parity"],
            n_samples=q["n_samples"],
        )
        for q in data["per_question"]
    ]

    result = BenchmarkResult(
        provider_name=data["config"]["provider"],
        dataset_name=data["config"]["dataset"],
        questions=questions,
        config=data["config"],
        elapsed_seconds=data["aggregate"].get("elapsed_seconds", 0),
    )

    click.echo(report_mod.to_markdown(result))


@main.command()
@click.option("--dataset", "-d", default="opinionsqa", help="Dataset to download.")
@click.option("--data-dir", type=click.Path(), default=None, help="Target directory.")
def download(dataset, data_dir):
    """Download a benchmark dataset."""
    from synthbench.datasets import DATASETS

    if dataset not in DATASETS:
        click.echo(
            f"Unknown dataset '{dataset}'. Available: {list(DATASETS)}", err=True
        )
        sys.exit(1)

    ds_kwargs = {}
    if data_dir:
        ds_kwargs["data_dir"] = data_dir
    ds = DATASETS[dataset](**ds_kwargs)

    click.echo(f"Loading {dataset} dataset...")
    try:
        questions = ds.load()
        click.echo(f"Loaded {len(questions)} questions.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("files", nargs=-1, required=True, type=click.Path(exists=True))
@click.option(
    "--output", "-o", type=click.Path(), default=None, help="Save comparison to file."
)
def compare(files, output):
    """Compare 2+ result JSON files side-by-side with significance testing.

    When exactly 2 files are given, also runs a paired bootstrap test on
    per-question parity scores and reports delta, p-value, and verdict.

    Example:
        synthbench compare result1.json result2.json
    """
    if len(files) < 2:
        click.echo("Error: need at least 2 result files to compare.", err=True)
        sys.exit(1)

    from synthbench.leaderboard import load_result, compare_results
    from synthbench.stats import paired_bootstrap_test

    results = [load_result(Path(f)) for f in files]
    md = compare_results(results)

    click.echo(md)

    # Pairwise significance test for exactly 2 results
    if len(files) == 2:
        r1, r2 = results
        cfg1 = r1.get("config", {}).get("provider", "A")
        cfg2 = r2.get("config", {}).get("provider", "B")
        pq1 = {q["key"]: q["parity"] for q in r1.get("per_question", [])}
        pq2 = {q["key"]: q["parity"] for q in r2.get("per_question", [])}
        common_keys = sorted(set(pq1) & set(pq2))

        if common_keys:
            scores_a = [pq1[k] for k in common_keys]
            scores_b = [pq2[k] for k in common_keys]
            delta, p_val, verdict = paired_bootstrap_test(scores_a, scores_b, seed=42)

            alpha = 0.05
            sig_str = (
                f"SIGNIFICANT at alpha={alpha}"
                if verdict == "significant"
                else f"NOT significant at alpha={alpha}"
            )

            click.echo()
            click.echo("## Statistical Significance")
            click.echo()
            click.echo(f"  {cfg1} vs {cfg2}")
            click.echo(f"  Paired questions: {len(common_keys)}")
            click.echo(f"  Delta SPS = {delta:+.4f}, p = {p_val:.4f}, {sig_str}")
            click.echo()

            md += "\n## Statistical Significance\n\n"
            md += f"- {cfg1} vs {cfg2}\n"
            md += f"- Paired questions: {len(common_keys)}\n"
            md += f"- Delta SPS = {delta:+.4f}, p = {p_val:.4f}, **{sig_str}**\n"
        else:
            click.echo("\nNo common questions for significance test.", err=True)

    if output:
        Path(output).write_text(md)
        click.echo(f"\nSaved to {output}", err=True)


@main.command()
@click.option("--provider", "-p", required=True, help="Provider name.")
@click.option("--model", "-m", default="haiku", help="Model name or alias.")
@click.option("--dataset", "-d", default="opinionsqa", help="Dataset.")
@click.option("--n", "-n", type=int, default=None, help="Questions per run.")
@click.option("--samples", "-s", type=int, default=30, help="Samples per question.")
@click.option("--n-runs", type=int, default=5, help="Number of independent runs.")
@click.option(
    "--concurrency", "-c", type=int, default=10, help="Max concurrent requests."
)
@click.option(
    "--data-dir", type=click.Path(), default=None, help="Custom data directory."
)
@click.option("--url", default=None, help="Endpoint URL for http provider.")
@click.option(
    "--suite",
    type=click.Choice(["smoke", "core", "full"]),
    default=None,
    help="Use a pinned question set.",
)
@click.option(
    "--output", "-o", type=click.Path(), default="results", help="Output directory."
)
def replicate(
    provider,
    model,
    dataset,
    n,
    samples,
    n_runs,
    concurrency,
    data_dir,
    url,
    suite,
    output,
):
    """Run a benchmark N times and report stability metrics.

    Answers: "how stable is this provider's score?"

    Example:
        synthbench replicate --provider raw-anthropic --n-runs 5 --suite core
    """
    asyncio.run(
        _replicate_async(
            provider,
            model,
            dataset,
            n,
            samples,
            n_runs,
            concurrency,
            data_dir,
            url,
            suite,
            output,
        )
    )


async def _replicate_async(
    provider_name,
    model,
    dataset_name,
    n,
    samples,
    n_runs,
    concurrency,
    data_dir,
    url,
    suite,
    output,
):
    from synthbench.datasets import DATASETS
    from synthbench.providers import load_provider
    from synthbench.runner import BenchmarkRunner
    import statistics

    resolved_model = MODEL_ALIASES.get(model, model)

    if dataset_name not in DATASETS:
        click.echo(f"Unknown dataset '{dataset_name}'.", err=True)
        sys.exit(1)

    ds_kwargs = {}
    if data_dir:
        ds_kwargs["data_dir"] = data_dir
    ds = DATASETS[dataset_name](**ds_kwargs)

    provider_kwargs = {"model": resolved_model}
    if url:
        provider_kwargs["url"] = url
    try:
        prov = load_provider(provider_name, **provider_kwargs)
    except (KeyError, ImportError) as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    # Load suite
    question_keys = None
    if suite:
        from synthbench.suites import load_suite

        question_keys = load_suite(suite)

    runner = BenchmarkRunner(
        dataset=ds,
        provider=prov,
        samples_per_question=samples,
        concurrency=concurrency,
    )

    suite_label = f"suite={suite}" if suite else (str(n) if n else "all")
    click.echo(f"SynthBench Replicate v{__version__}")
    click.echo(f"  Provider: {prov.name}")
    click.echo(f"  Dataset:  {ds.name}")
    click.echo(f"  Questions: {suite_label}")
    click.echo(f"  Samples/q: {samples}")
    click.echo(f"  Runs: {n_runs}")
    click.echo()

    run_metrics: list[dict[str, float]] = []

    try:
        for run_i in range(n_runs):
            click.echo(f"  Run {run_i + 1}/{n_runs}...", nl=False)
            result = await runner.run(n=n, question_keys=question_keys)
            metrics = {"sps": result.sps, **result.sps_components}
            run_metrics.append(metrics)
            click.echo(f" SPS={result.sps:.4f}")
    finally:
        await prov.close()

    click.echo()

    # Aggregate
    all_metric_names = sorted(set().union(*run_metrics))
    lines = [
        "# SynthBench Replication Report",
        "",
        f"**Provider:** {prov.name}",
        f"**Runs:** {n_runs}",
        f"**Questions:** {suite_label}",
        f"**Samples/q:** {samples}",
        "",
        "| Metric | Mean | Std | Min | Max | CV |",
        "|--------|------|-----|-----|-----|-----|",
    ]

    summary = {}
    for metric in all_metric_names:
        vals = [rm[metric] for rm in run_metrics if metric in rm]
        if not vals:
            continue
        mean_val = statistics.mean(vals)
        std_val = statistics.stdev(vals) if len(vals) > 1 else 0.0
        min_val = min(vals)
        max_val = max(vals)
        cv = std_val / mean_val if mean_val > 0 else 0.0

        lines.append(
            f"| {metric} | {mean_val:.4f} | {std_val:.4f} "
            f"| {min_val:.4f} | {max_val:.4f} | {cv:.4f} |"
        )
        summary[metric] = {
            "mean": round(mean_val, 6),
            "std": round(std_val, 6),
            "min": round(min_val, 6),
            "max": round(max_val, 6),
            "cv": round(cv, 6),
            "values": [round(v, 6) for v in vals],
        }

    lines.append("")
    md = "\n".join(lines)
    click.echo(md)

    # Save
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    provider_slug = prov.name.replace("/", "_")

    json_data = {
        "benchmark": "synthbench",
        "type": "replication",
        "version": __version__,
        "config": {
            "provider": prov.name,
            "dataset": ds.name,
            "n_runs": n_runs,
            "n_questions": suite_label,
            "samples_per_question": samples,
        },
        "per_run": run_metrics,
        "summary": summary,
    }
    json_path = out_dir / f"replicate_{dataset_name}_{provider_slug}_{ts}.json"
    json_path.write_text(json.dumps(json_data, indent=2))
    click.echo(f"\nSaved: {json_path}")


@main.command()
@click.option(
    "--results-dir",
    "-d",
    type=click.Path(exists=True),
    default="results",
    help="Directory containing result JSON files.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Save markdown + JSON output.",
)
@click.option("--json", "json_only", is_flag=True, help="Output JSON only.")
@click.option(
    "--topic",
    type=click.Choice(["political", "consumer", "neutral"]),
    default=None,
    help="Filter to results for a specific topic.",
)
def leaderboard(results_dir, output, json_only, topic):
    """Build a ranked leaderboard from all result files in a directory.

    Example:
        synthbench leaderboard --results-dir ./results
        synthbench leaderboard --results-dir ./results --topic consumer
    """
    from synthbench.leaderboard import load_result, build_leaderboard

    results_path = Path(results_dir)
    json_files = sorted(results_path.glob("*.json"))

    if not json_files:
        click.echo(f"No JSON files found in {results_dir}", err=True)
        sys.exit(1)

    # Load and filter to valid synthbench results
    results = []
    for jf in json_files:
        try:
            data = load_result(jf)
            if data.get("benchmark") == "synthbench":
                results.append(data)
        except (json.JSONDecodeError, KeyError):
            continue

    if not results:
        click.echo("No valid SynthBench result files found.", err=True)
        sys.exit(1)

    # Filter by topic if specified
    if topic:
        results = [r for r in results if r.get("config", {}).get("topic") == topic]
        if not results:
            click.echo(f"No results found for topic '{topic}'.", err=True)
            sys.exit(1)

    md, lb_json = build_leaderboard(results)

    if json_only:
        click.echo(json.dumps(lb_json, indent=2))
    else:
        click.echo(md)

    if output:
        out = Path(output)
        if json_only:
            out.write_text(json.dumps(lb_json, indent=2))
        else:
            out.write_text(md)
            # Also write JSON sidecar
            json_out = out.with_suffix(".json")
            json_out.write_text(json.dumps(lb_json, indent=2))
            click.echo(f"\nSaved: {out} + {json_out}", err=True)


@main.command()
@click.option(
    "--results-dir",
    "-d",
    type=click.Path(exists=True),
    default="leaderboard-results",
    help="Directory containing result JSON files.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="docs",
    help="Output directory for the static site.",
)
def publish(results_dir, output):
    """Regenerate the static GitHub Pages leaderboard from result JSON files.

    Example:
        synthbench publish --results-dir ./leaderboard-results --output docs/
    """
    from synthbench.publish import publish_leaderboard

    try:
        out_path = publish_leaderboard(
            results_dir=Path(results_dir),
            output_dir=Path(output),
            version=__version__,
        )
        click.echo(f"Leaderboard published: {out_path}")
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
