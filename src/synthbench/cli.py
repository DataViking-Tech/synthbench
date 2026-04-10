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
}


@click.group()
@click.version_option(__version__)
def main():
    """SynthBench — benchmark harness for synthetic survey respondents."""
    pass


@main.command()
@click.option(
    "--provider", "-p",
    required=True,
    help="Provider name (raw-anthropic, raw-openai, http).",
)
@click.option(
    "--model", "-m",
    default="haiku",
    help="Model name or alias (haiku, sonnet, gpt-4o-mini, etc.).",
)
@click.option(
    "--dataset", "-d",
    default="opinionsqa",
    help="Dataset to benchmark against.",
)
@click.option(
    "--n", "-n",
    type=int,
    default=None,
    help="Number of questions to evaluate (default: all).",
)
@click.option(
    "--samples", "-s",
    type=int,
    default=30,
    help="Samples per question for distribution estimation.",
)
@click.option(
    "--concurrency", "-c",
    type=int,
    default=10,
    help="Max concurrent API requests.",
)
@click.option(
    "--output", "-o",
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
@click.option("--json-only", is_flag=True, help="Output JSON to stdout instead of files.")
def run(provider, model, dataset, n, samples, concurrency, output, data_dir, url, json_only):
    """Run a benchmark evaluation.

    Example:
        synthbench run --provider raw-anthropic --model haiku --n 100
    """
    asyncio.run(_run_async(
        provider, model, dataset, n, samples, concurrency, output, data_dir, url, json_only,
    ))


async def _run_async(
    provider_name, model, dataset_name, n, samples, concurrency, output, data_dir, url, json_only,
):
    from synthbench.datasets import DATASETS
    from synthbench.providers import load_provider
    from synthbench.runner import BenchmarkRunner
    from synthbench import report

    # Resolve model alias
    resolved_model = MODEL_ALIASES.get(model, model)

    # Load dataset
    if dataset_name not in DATASETS:
        click.echo(f"Unknown dataset '{dataset_name}'. Available: {list(DATASETS)}", err=True)
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

    # Run benchmark
    runner = BenchmarkRunner(
        dataset=ds,
        provider=prov,
        samples_per_question=samples,
        concurrency=concurrency,
    )

    click.echo(f"SynthBench v{__version__}")
    click.echo(f"  Provider: {prov.name}")
    click.echo(f"  Dataset:  {ds.name}")
    click.echo(f"  Questions: {n or 'all'}")
    click.echo(f"  Samples/q: {samples}")
    click.echo()

    def progress(done, total, qr):
        pct = done / total * 100
        click.echo(
            f"\r  [{done}/{total}] {pct:5.1f}% | "
            f"JSD={qr.jsd:.4f} tau={qr.kendall_tau:.4f}",
            nl=False,
        )

    try:
        result = await runner.run(n=n, progress_callback=progress)
    finally:
        await prov.close()

    click.echo()  # Newline after progress
    click.echo()

    if json_only:
        click.echo(json.dumps(report.to_json(result), indent=2))
    else:
        # Print markdown summary to terminal
        click.echo(report.to_markdown(result))

        # Save files
        json_path, md_path = report.save(result, output)
        click.echo(f"\nResults saved:")
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
        click.echo(f"Unknown dataset '{dataset}'. Available: {list(DATASETS)}", err=True)
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


if __name__ == "__main__":
    main()
