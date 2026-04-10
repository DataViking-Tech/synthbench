"""Score card generation — JSON and markdown output."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from synthbench import __version__
from synthbench.runner import BenchmarkResult


def to_json(result: BenchmarkResult) -> dict:
    """Convert a benchmark result to a JSON-serializable dict."""
    return {
        "benchmark": "synthbench",
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "dataset": result.dataset_name,
            "provider": result.provider_name,
            **result.config,
        },
        "aggregate": {
            "mean_jsd": round(result.mean_jsd, 6),
            "median_jsd": round(result.median_jsd, 6),
            "mean_kendall_tau": round(result.mean_kendall_tau, 6),
            "composite_parity": round(result.composite_parity, 6),
            "n_questions": len(result.questions),
            "elapsed_seconds": round(result.elapsed_seconds, 1),
        },
        "per_question": [
            {
                "key": q.key,
                "text": q.text[:120],
                "options": q.options,
                "human_distribution": {
                    k: round(v, 4) for k, v in q.human_distribution.items()
                },
                "model_distribution": {
                    k: round(v, 4) for k, v in q.model_distribution.items()
                },
                "jsd": round(q.jsd, 6),
                "kendall_tau": round(q.kendall_tau, 6),
                "parity": round(q.parity, 6),
                "n_samples": q.n_samples,
            }
            for q in result.questions
        ],
    }


def to_markdown(result: BenchmarkResult) -> str:
    """Generate a markdown score card."""
    lines = [
        "# SynthBench Score Card",
        "",
        f"**Provider:** {result.provider_name}",
        f"**Dataset:** {result.dataset_name} ({len(result.questions)} questions)",
        f"**Samples per question:** {result.config.get('samples_per_question', '?')}",
        f"**Elapsed:** {result.elapsed_seconds:.1f}s",
        "",
        "## Aggregate Scores",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Mean JSD | {result.mean_jsd:.4f} |",
        f"| Median JSD | {result.median_jsd:.4f} |",
        f"| Mean Kendall's tau | {result.mean_kendall_tau:.4f} |",
        f"| **Composite Parity** | **{result.composite_parity:.4f}** |",
        "",
        "## Interpretation",
        "",
        "- **JSD** (Jensen-Shannon Divergence): 0 = identical distributions, "
        "1 = maximally different. Lower is better.",
        "- **Kendall's tau**: -1 = reversed ranking, 0 = no correlation, "
        "+1 = identical ranking. Higher is better.",
        "- **Composite Parity**: 0 = no parity, 1 = perfect parity. Higher is better.",
        "",
    ]

    # Top 5 best and worst questions
    sorted_by_jsd = sorted(result.questions, key=lambda q: q.jsd)

    if len(sorted_by_jsd) >= 5:
        lines.extend([
            "## Best Matches (lowest JSD)",
            "",
            "| Question | JSD | tau |",
            "|----------|-----|-----|",
        ])
        for q in sorted_by_jsd[:5]:
            lines.append(f"| {q.text[:60]}... | {q.jsd:.4f} | {q.kendall_tau:.4f} |")

        lines.extend([
            "",
            "## Worst Matches (highest JSD)",
            "",
            "| Question | JSD | tau |",
            "|----------|-----|-----|",
        ])
        for q in sorted_by_jsd[-5:]:
            lines.append(f"| {q.text[:60]}... | {q.jsd:.4f} | {q.kendall_tau:.4f} |")

        lines.append("")

    return "\n".join(lines)


def save(result: BenchmarkResult, output_dir: Path | str) -> tuple[Path, Path]:
    """Save JSON and markdown score cards to output_dir.

    Returns (json_path, markdown_path).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    provider_slug = result.provider_name.replace("/", "_")
    base = f"{result.dataset_name}_{provider_slug}_{ts}"

    json_path = output_dir / f"{base}.json"
    md_path = output_dir / f"{base}.md"

    with open(json_path, "w") as f:
        json.dump(to_json(result), f, indent=2)

    with open(md_path, "w") as f:
        f.write(to_markdown(result))

    return json_path, md_path
