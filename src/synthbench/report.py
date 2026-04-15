"""Score card generation — JSON and markdown output."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from synthbench import __version__
from synthbench.runner import BenchmarkResult, QuestionResult


def _sum_per_question_usage(per_q: list[QuestionResult]) -> dict | None:
    """Sum token_usage across per-question results.

    Returns None when no question carries usage. ``source`` is ``"measured"``
    if every question reported usage, ``"partial"`` if only some did.
    """
    input_tot = 0
    output_tot = 0
    calls = 0
    with_usage = 0
    for q in per_q:
        if not q.token_usage:
            continue
        with_usage += 1
        input_tot += q.token_usage.get("input_tokens", 0) or 0
        output_tot += q.token_usage.get("output_tokens", 0) or 0
        calls += q.token_usage.get("call_count", 0) or 0
    if with_usage == 0:
        return None
    return {
        "input_tokens": input_tot,
        "output_tokens": output_tot,
        "call_count": calls,
        "source": "measured" if with_usage == len(per_q) else "partial",
    }


def _build_reproducibility_block(result: BenchmarkResult) -> dict:
    """Build the Tier-3 reproducibility metadata block.

    Fields sourced directly from ``result.config`` when the runner /
    caller populated them; otherwise populated with safe defaults
    (framework_version and submitted_at always auto-populated).
    The remaining hashes (``model_revision_hash``, ``prompt_template_hash``)
    default to ``""`` — the validator warns when they're blank, so
    submitters know to fill them in before opening a PR.
    """
    cfg = result.config
    return {
        "seed": cfg.get("seed"),
        "model_revision_hash": cfg.get("model_revision_hash", ""),
        "prompt_template_hash": cfg.get("prompt_template_hash", ""),
        "framework_version": cfg.get("framework_version", __version__),
        "submitted_at": cfg.get("submitted_at", datetime.now(timezone.utc).isoformat()),
    }


def _build_raw_responses(per_q: list[QuestionResult]) -> list[dict]:
    """Collect preserved raw response samples for Tier-3 audits."""
    samples: list[dict] = []
    for q in per_q:
        if not q.raw_sample:
            continue
        raw_text = q.raw_sample.get("raw_text")
        if not isinstance(raw_text, str) or not raw_text.strip():
            continue
        samples.append(
            {
                "key": q.key,
                "raw_text": raw_text,
                "selected_option": q.raw_sample.get("selected_option", ""),
            }
        )
    return samples


def to_json(result: BenchmarkResult) -> dict:
    """Convert a benchmark result to a JSON-serializable dict."""
    scores: dict[str, object] = {
        "sps": round(result.sps, 6),
        "p_dist": round(result.p_dist, 6),
        "p_rank": round(result.p_rank, 6),
        "p_refuse": round(result.p_refuse, 6),
    }
    if result.p_sub is not None:
        scores["p_sub"] = round(result.p_sub, 6)
    if result.p_cond is not None:
        scores["p_cond"] = round(result.p_cond, 6)

    # Per-metric CIs
    per_metric_ci = {}
    for metric, (lo, hi) in result.per_metric_ci.items():
        per_metric_ci[metric] = [lo, hi]

    # Compute parse failure rate
    total_samples = sum(q.n_samples + q.n_parse_failures for q in result.questions)
    parse_failure_rate = (
        result.total_parse_failures / total_samples if total_samples > 0 else 0.0
    )

    aggregate_token_usage = _sum_per_question_usage(result.questions)

    return {
        "benchmark": "synthbench",
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "dataset": result.dataset_name,
            "provider": result.provider_name,
            **result.config,
            "question_set_hash": result.q_set_hash,
            "temperature": result.config.get("temperature"),
            "parse_failure_rate": round(parse_failure_rate, 6),
            "topic_filter": result.config.get("topic"),
        },
        "reproducibility": _build_reproducibility_block(result),
        "raw_responses": _build_raw_responses(result.questions),
        "scores": scores,
        "aggregate": {
            "mean_jsd": round(result.mean_jsd, 6),
            "median_jsd": round(result.median_jsd, 6),
            "mean_kendall_tau": round(result.mean_kendall_tau, 6),
            "composite_parity": round(result.composite_parity, 6),
            "n_questions": len(result.questions),
            "elapsed_seconds": round(result.elapsed_seconds, 1),
            "per_metric_ci": per_metric_ci,
            "question_set_hash": result.q_set_hash,
            "n_parse_failures": result.total_parse_failures,
            **(
                {
                    "contamination_sensitivity": round(
                        result.config["contamination_sensitivity"], 3
                    )
                }
                if "contamination_sensitivity" in result.config
                else {}
            ),
            **({"token_usage": aggregate_token_usage} if aggregate_token_usage else {}),
        },
        "demographic_breakdown": {
            attr: [
                {
                    "attribute": gr.attribute,
                    "group": gr.group,
                    "p_dist": round(gr.p_dist, 6),
                    "p_cond": round(gr.p_cond, 6),
                    "n_questions": gr.n_questions,
                }
                for gr in groups
            ]
            for attr, groups in result.demographic_breakdown.items()
        }
        if result.demographic_breakdown
        else {},
        "per_question": [
            {
                "key": q.key,
                "text": q.text,
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
                "n_parse_failures": q.n_parse_failures,
                "model_refusal_rate": round(q.model_refusal_rate, 6),
                "human_refusal_rate": round(q.human_refusal_rate, 6),
                "temporal_year": q.temporal_year,
                **({"token_usage": q.token_usage} if q.token_usage else {}),
            }
            for q in result.questions
        ],
        "temporal_breakdown": {
            str(year): data for year, data in result.temporal_breakdown.items()
        }
        if result.temporal_breakdown
        else {},
    }


def _bar(score: float, width: int = 10) -> str:
    """Render a score as a bar chart segment."""
    filled = round(score * width)
    return "\u2588" * filled + "\u2591" * (width - filled)


def _load_baselines(baselines_dir: Path | None) -> dict[str, dict]:
    """Load baseline result JSONs from a directory.

    Returns a dict mapping provider name to the result dict with the
    most n_evaluated questions.
    """
    if baselines_dir is None or not baselines_dir.is_dir():
        return {}

    baselines: dict[str, dict] = {}
    for jf in baselines_dir.glob("*.json"):
        try:
            with open(jf) as f:
                data = json.load(f)
        except (json.JSONDecodeError, KeyError):
            continue
        if data.get("benchmark") != "synthbench":
            continue
        provider = data.get("config", {}).get("provider", "")
        if provider not in ("random-baseline", "majority-baseline"):
            continue
        n_eval = data.get("config", {}).get("n_evaluated", 0)
        existing = baselines.get(provider)
        if existing is None or n_eval > existing.get("config", {}).get(
            "n_evaluated", 0
        ):
            baselines[provider] = data

    return baselines


def _vs_baselines_section(composite: float, baselines: dict[str, dict]) -> list[str]:
    """Generate the 'vs Baselines' markdown section."""
    if not baselines:
        return []

    lines = [
        "## vs Baselines",
        "",
        "| Baseline | Score | Delta | % |",
        "|----------|------:|------:|--:|",
    ]

    for name in sorted(baselines.keys()):
        base_cp = baselines[name].get("aggregate", {}).get("composite_parity", 0)
        delta = composite - base_cp
        pct = (delta / base_cp * 100) if base_cp > 0 else 0
        sign = "+" if delta >= 0 else ""
        lines.append(
            f"| {name} | {base_cp:.4f} | {sign}{delta:.4f} | {sign}{pct:.0f}% |"
        )

    lines.append("")
    return lines


def to_markdown(
    result: BenchmarkResult,
    baselines_dir: Path | None = None,
) -> str:
    """Generate a markdown score card with full SPS breakdown.

    If *baselines_dir* is provided (or defaults to ``leaderboard-results/``
    relative to cwd), includes a "vs Baselines" section showing deltas.
    """
    components = result.sps_components
    cis = result.per_metric_ci

    def _fmt_ci(key: str, score: float) -> str:
        if key in cis:
            lo, hi = cis[key]
            return f"{score:.4f} [{lo:.4f}, {hi:.4f}]"
        return f"{score:.4f}"

    # SPS CI
    sps_str = _fmt_ci("sps", result.sps)

    lines = [
        "# SynthBench Score Card",
        "",
        f"**Provider:** {result.provider_name}",
        f"**Dataset:** {result.dataset_name} ({len(result.questions)} questions)",
        f"**Samples per question:** {result.config.get('samples_per_question', '?')}",
        f"**Elapsed:** {result.elapsed_seconds:.1f}s",
        "",
        "## SynthBench Parity Score (SPS)",
        "",
        f"**SPS: {sps_str}** (from {len(components)} metrics)",
        "",
        "| Metric | Score | |",
        "|--------|------:|---|",
    ]

    metric_labels = {
        "p_dist": "P_dist  Distributional",
        "p_rank": "P_rank  Rank-Order",
        "p_cond": "P_cond  Conditioning",
        "p_sub": "P_sub   Subgroup",
        "p_refuse": "P_refuse Refusal Cal.",
    }
    for key in ("p_dist", "p_rank", "p_cond", "p_sub", "p_refuse"):
        if key in components:
            label = metric_labels[key]
            score = components[key]
            ci_str = _fmt_ci(key, score)
            lines.append(f"| {label} | {ci_str} | {_bar(score)} |")

    lines.extend(
        [
            "",
            "## Raw Metrics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Mean JSD | {result.mean_jsd:.4f} |",
            f"| Median JSD | {result.median_jsd:.4f} |",
            f"| Mean Kendall's tau | {result.mean_kendall_tau:.4f} |",
            f"| Composite Parity (legacy) | {result.composite_parity:.4f} |",
            "",
        ]
    )

    # vs Baselines section
    baselines = _load_baselines(baselines_dir)
    if not baselines:
        # Try default location
        default_dir = Path("leaderboard-results")
        if default_dir.is_dir():
            baselines = _load_baselines(default_dir)
    lines.extend(_vs_baselines_section(result.composite_parity, baselines))

    lines.extend(
        [
            "## What These Scores Mean",
            "",
            "- **SPS** (SynthBench Parity Score): The overall score — average of all "
            "metrics. 0 = random noise, 1 = indistinguishable from real humans.",
            "- **P_dist** (Distributional Parity): How closely does the AI's answer "
            "distribution match real humans? If 60% of humans say 'yes' and the AI says "
            "'yes' 60% of the time, that's a perfect match. 0 = completely different, "
            "1 = identical distributions.",
            "- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering "
            "right? If humans prefer A > B > C, does the AI agree — even if the exact "
            "percentages differ? 0 = reversed ordering, 1 = perfect agreement.",
            "- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at "
            "appropriate rates? Humans sometimes decline sensitive questions. An AI that "
            "never refuses, or refuses too often, is miscalibrated. 0 = rates completely "
            "off, 1 = perfect match.",
            "- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old "
            "conservative,' does the AI actually shift its answers? Higher = better "
            "demographic role-playing. (When available.)",
            "- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all "
            "demographics, or does it nail some groups and miss others? (When available.)",
            "",
        ]
    )

    # Demographic breakdown
    if result.demographic_breakdown:
        lines.extend(
            [
                "## Demographic Breakdown",
                "",
            ]
        )
        for attr, group_results in result.demographic_breakdown.items():
            sorted_groups = sorted(group_results, key=lambda g: g.p_dist, reverse=True)
            best = sorted_groups[0]
            worst = sorted_groups[-1]
            lines.extend(
                [
                    f"### {attr}",
                    "",
                    f"Best: {best.group} (P_dist={best.p_dist:.4f}) "
                    f"/ Worst: {worst.group} (P_dist={worst.p_dist:.4f})",
                    "",
                    "| Group | P_dist | P_cond | Questions |",
                    "|-------|--------|--------|-----------|",
                ]
            )
            for gr in sorted_groups:
                lines.append(
                    f"| {gr.group} | {gr.p_dist:.4f} | {gr.p_cond:.4f} | {gr.n_questions} |"
                )
            lines.append("")

    # Temporal breakdown (contamination analysis)
    temporal = result.temporal_breakdown
    if temporal:
        lines.extend(
            [
                "## Temporal Breakdown (by Survey Year)",
                "",
                "Scores stratified by Pew ATP survey wave year. "
                "Rising P_dist in recent years may indicate training-data contamination.",
                "",
                "| Year | P_dist | P_rank | Mean JSD | Questions |",
                "|------|--------|--------|----------|-----------|",
            ]
        )
        for year in sorted(temporal):
            d = temporal[year]
            lines.append(
                f"| {year} | {d['p_dist']:.4f} | {d['p_rank']:.4f} "
                f"| {d['mean_jsd']:.4f} | {d['n_questions']} |"
            )
        lines.append("")

    # Top 5 best and worst questions
    sorted_by_jsd = sorted(result.questions, key=lambda q: q.jsd)

    if len(sorted_by_jsd) >= 5:
        lines.extend(
            [
                "## Best Matches (lowest JSD)",
                "",
                "| Question | JSD | tau |",
                "|----------|-----|-----|",
            ]
        )
        for q in sorted_by_jsd[:5]:
            lines.append(f"| {q.text[:60]}... | {q.jsd:.4f} | {q.kendall_tau:.4f} |")

        lines.extend(
            [
                "",
                "## Worst Matches (highest JSD)",
                "",
                "| Question | JSD | tau |",
                "|----------|-----|-----|",
            ]
        )
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
