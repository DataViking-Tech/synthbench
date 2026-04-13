"""Generate a static HTML leaderboard page from SynthBench result JSON files."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from html import escape

from synthbench.leaderboard import display_provider_name

BASELINE_PROVIDERS = {"random-baseline", "majority-baseline"}
SYNTHPANEL_PREFIX = "synthpanel/"
N_THRESHOLD = 50
FULL_SPS_METRICS = {"p_dist", "p_rank", "p_refuse", "p_cond", "p_sub"}
NEAR_BASELINE_THRESHOLD = 0.01


def _sps_metric_count(result: dict) -> int:
    """Count how many of the 5 SPS component metrics are present in a result."""
    per_ci = result.get("aggregate", {}).get("per_metric_ci", {})
    return len(FULL_SPS_METRICS & set(per_ci.keys()))


def _is_partial_sps(result: dict) -> bool:
    """Return True if SPS was computed from fewer than 5 metrics."""
    return _sps_metric_count(result) < 5


def _sps_label(result: dict) -> str:
    """Return 'SPS' or 'SPS*' depending on metric completeness."""
    return "SPS*" if _is_partial_sps(result) else "SPS"


def _is_near_baseline(sps: float, random_sps: float) -> bool:
    """Return True if sps is within NEAR_BASELINE_THRESHOLD of random baseline."""
    return abs(sps - random_sps) <= NEAR_BASELINE_THRESHOLD


def _extract_metrics(result: dict) -> dict[str, float]:
    """Extract SPS component metrics from a result dict.

    Computes P_dist and P_rank from aggregate data. Returns a dict with
    keys: composite_parity, p_dist, p_rank, mean_jsd, mean_kendall_tau.
    """
    agg = result.get("aggregate", {})
    mean_jsd = agg.get("mean_jsd", 0)
    mean_tau = agg.get("mean_kendall_tau", 0)
    return {
        "composite_parity": agg.get("composite_parity", 0),
        "p_dist": 1.0 - mean_jsd,
        "p_rank": (1.0 + mean_tau) / 2.0,
        "mean_jsd": mean_jsd,
        "mean_kendall_tau": mean_tau,
    }


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


def _split_baselines(
    ranked: list[dict],
) -> tuple[list[dict], dict[str, dict]]:
    """Separate model results from baseline results."""
    models = []
    baselines: dict[str, dict] = {}
    for r in ranked:
        provider = r.get("config", {}).get("provider", "unknown")
        if provider in BASELINE_PROVIDERS:
            baselines[provider] = r
        else:
            models.append(r)
    return models, baselines


def _is_synthpanel(provider: str) -> bool:
    """Check if a provider is a synthpanel adapter."""
    return provider.startswith(SYNTHPANEL_PREFIX)


def _display_provider_name(provider: str) -> str:
    """Map provider strings to human-friendly display names via MODEL_MAP."""
    from synthbench.leaderboard import display_provider_name

    return display_provider_name(provider)


def _ci_whisker_svg(ci_low: float, ci_high: float, point: float) -> str:
    """Render a tiny inline SVG showing CI range with a dot at the point estimate.

    The SVG is 60px wide and shows the CI range as a horizontal line
    with a dot at the point estimate, scaled to [0, 1].
    """
    w = 60
    h = 16
    # Scale to SVG coordinates (0-1 range mapped to 2..w-2)
    usable = w - 4
    x_low = 2 + ci_low * usable
    x_high = 2 + ci_high * usable
    x_point = 2 + point * usable
    y_mid = h / 2
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'style="vertical-align:middle;margin-left:4px">'
        f'<line x1="{x_low:.1f}" y1="{y_mid}" x2="{x_high:.1f}" y2="{y_mid}" '
        f'class="chart-muted" stroke-width="1.5"/>'
        f'<line x1="{x_low:.1f}" y1="{y_mid - 3}" x2="{x_low:.1f}" y2="{y_mid + 3}" '
        f'class="chart-muted" stroke-width="1"/>'
        f'<line x1="{x_high:.1f}" y1="{y_mid - 3}" x2="{x_high:.1f}" y2="{y_mid + 3}" '
        f'class="chart-muted" stroke-width="1"/>'
        f'<circle cx="{x_point:.1f}" cy="{y_mid}" r="3" class="chart-accent"/>'
        f"</svg>"
    )


def _topic_bars_svg(
    scores: dict[str, float], topics: list[str], colors: list[str]
) -> str:
    """Render tiny inline SVG grouped bars for topic scores.

    Shows one bar per topic, colored distinctly, all within a 48x16 SVG.
    """
    n = len(topics)
    if n == 0:
        return "&mdash;"
    w = 48
    h = 16
    bar_w = max(2, (w - (n + 1) * 2) // n)
    parts = []
    for i, t in enumerate(topics):
        val = scores.get(t)
        if val is None:
            continue
        x = 2 + i * (bar_w + 2)
        bar_h = max(1, val * (h - 2))
        y = h - 1 - bar_h
        color = colors[i % len(colors)]
        parts.append(
            f'<rect x="{x}" y="{y:.1f}" width="{bar_w}" height="{bar_h:.1f}" '
            f'rx="1" style="fill:{color}"/>'
        )
    if not parts:
        return "&mdash;"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'style="vertical-align:middle">' + "".join(parts) + "</svg>"
    )


def _hero_model_name(provider: str) -> str:
    """Extract a short, readable model name for the hero chart."""
    if provider in BASELINE_PROVIDERS:
        return provider.replace("-", " ").title()
    if provider.startswith(SYNTHPANEL_PREFIX):
        return "SynthPanel"
    name = provider.rsplit("/", 1)[-1]
    name = re.sub(r"-\d{8,}$", "", name)
    name = name.replace("-", " ").title()
    # Fix common abbreviations that title() mangles
    for old, new in [("Gpt ", "GPT-"), ("4O ", "4o "), ("4O", "4o")]:
        name = name.replace(old, new)
    # Convert trailing "X Y" digit pairs to "X.Y" (version numbers)
    name = re.sub(r"(\d) (\d)$", r"\1.\2", name)
    return name


def _hero_svg(
    ranked: list[dict],
    baselines: dict[str, dict],
    dataset_label: str = "All Datasets",
) -> str:
    """Generate a bold hero SVG with horizontal dots and baseline zone banding.

    Sits above the leaderboard table. Models ranked by SPS with background
    zones: GREEN (above baseline+0.05), AMBER (within 0.05), RED (below).
    """
    # Separate models from baselines
    models: list[tuple[dict, float, str]] = []
    for r in ranked:
        provider = r.get("config", {}).get("provider", "")
        if provider not in BASELINE_PROVIDERS:
            cp = r.get("aggregate", {}).get("composite_parity", 0)
            models.append((r, cp, provider))

    if not models:
        return ""

    # Random baseline SPS — anchor for zone banding.
    # Pick the random-baseline with the most data (highest n_evaluated)
    # since _split_baselines may have kept the wrong dataset entry.
    random_sps = 0.65
    best_n = -1
    for r in ranked:
        cfg = r.get("config", {})
        if cfg.get("provider") == "random-baseline":
            n = cfg.get("n_evaluated", 0)
            if n > best_n:
                best_n = n
                random_sps = r.get("aggregate", {}).get("composite_parity", 0)

    # Zone boundaries
    amber_lo = random_sps - 0.05
    amber_hi = random_sps + 0.05

    # SVG layout
    label_w = 180
    chart_w = 560
    pad_r = 60
    total_w = label_w + chart_w + pad_r

    row_h = 28
    top_pad = 52
    bot_pad = 50
    n = len(models)
    chart_h = n * row_h
    total_h = top_pad + chart_h + bot_pad

    # SPS range for x-axis (pad slightly beyond data range)
    all_sps = [cp for _, cp, _ in models] + [random_sps]
    sps_min = min(all_sps) - 0.03
    sps_max = max(all_sps) + 0.025
    sps_range = sps_max - sps_min

    def x(sps: float) -> float:
        return label_w + ((sps - sps_min) / sps_range) * chart_w

    chart_top = top_pad
    chart_bot = top_pad + chart_h

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} {total_h}" '
        f'width="100%" style="font-family:-apple-system,BlinkMacSystemFont,'
        f"'Segoe UI',sans-serif;max-width:{total_w}px\">"
    ]

    # ── Zone banding (smooth gradient transitions) ──
    zone_x_start = x(sps_min)
    zone_width = chart_w

    def zone_pct(sps_val: float) -> float:
        return max(0.0, min(100.0, ((sps_val - sps_min) / sps_range) * 100))

    p_lo = zone_pct(amber_lo)
    p_hi = zone_pct(amber_hi)
    tw = 3.0  # transition width in percent for soft edges

    parts.append("<defs>")
    parts.append('<linearGradient id="zone-grad" x1="0%" y1="0%" x2="100%" y2="0%">')
    parts.append(
        '<stop offset="0%" style="stop-color:var(--red)" stop-opacity="0.15"/>'
    )
    if p_lo > tw:
        parts.append(
            f'<stop offset="{p_lo - tw:.1f}%" style="stop-color:var(--red)" stop-opacity="0.15"/>'
        )
    parts.append(
        f'<stop offset="{min(p_lo + tw, 100):.1f}%" style="stop-color:var(--gold)" stop-opacity="0.25"/>'
    )
    if p_hi > p_lo + 2 * tw:
        parts.append(
            f'<stop offset="{max(p_hi - tw, 0):.1f}%" style="stop-color:var(--gold)" stop-opacity="0.25"/>'
        )
    parts.append(
        f'<stop offset="{min(p_hi + tw, 100):.1f}%" style="stop-color:var(--green)" stop-opacity="0.15"/>'
    )
    parts.append(
        '<stop offset="100%" style="stop-color:var(--green)" stop-opacity="0.15"/>'
    )
    parts.append("</linearGradient>")
    parts.append("</defs>")

    parts.append(
        f'<rect x="{zone_x_start:.1f}" y="{chart_top}" '
        f'width="{zone_width:.1f}" height="{chart_h}" '
        f'fill="url(#zone-grad)"/>'
    )

    # ── Subtle vertical grid lines at 0.1 SPS intervals ──
    grid_step = 0.1
    grid_val = round(sps_min / grid_step) * grid_step
    while grid_val <= sps_max + 0.001:
        if grid_val >= sps_min:
            gx = x(grid_val)
            parts.append(
                f'<line x1="{gx:.1f}" y1="{chart_top}" '
                f'x2="{gx:.1f}" y2="{chart_bot}" '
                f'style="stroke:var(--text-muted)" stroke-width="0.5" '
                f'opacity="0.15" stroke-dasharray="3,3"/>'
            )
        grid_val += grid_step

    # ── Random baseline vertical line ──
    bl_x = x(random_sps)
    parts.append(
        f'<line x1="{bl_x:.1f}" y1="{chart_top - 5}" '
        f'x2="{bl_x:.1f}" y2="{chart_bot + 5}" '
        f'style="stroke:var(--red)" stroke-width="2" '
        f'stroke-dasharray="6,3" opacity="0.7"/>'
    )
    parts.append(
        f'<text x="{bl_x:.1f}" y="{chart_top - 10}" text-anchor="middle" '
        f'font-size="10" style="fill:var(--red)" font-weight="600">'
        f"Random Baseline ({random_sps:.0%})</text>"
    )

    # ── Model dots and labels ──
    # Check if multiple datasets present — if so, add dataset suffix to labels
    datasets_in_chart = {r.get("config", {}).get("dataset", "") for r, _, _ in models}
    multi_dataset = len(datasets_in_chart) > 1
    _ds_abbrev = {"opinionsqa": "OQA", "subpop": "SubPOP", "globalopinionqa": "GQA"}

    for i, (_r, cp, provider) in enumerate(models):
        y = top_pad + i * row_h + row_h / 2
        dot_x = x(cp)
        name = _hero_model_name(provider)
        full_name = display_provider_name(provider)
        if full_name != provider:
            name = full_name
        if multi_dataset:
            ds = _r.get("config", {}).get("dataset", "")
            name += f" ({_ds_abbrev.get(ds, ds)})"

        # Zone-based dot color
        if cp > amber_hi:
            dot_fill = "var(--green)"
        elif cp >= amber_lo:
            dot_fill = "var(--gold)"
        else:
            dot_fill = "var(--red)"

        is_first = i == 0
        radius = 7 if is_first else 4.5
        fw = "700" if is_first else "400"
        fs = "12" if is_first else "11"

        # Model label (left of chart)
        parts.append(
            f'<text x="{label_w - 10}" y="{y + 4}" text-anchor="end" '
            f'font-size="{fs}" style="fill:var(--text)" font-weight="{fw}">'
            f"{escape(name)}</text>"
        )
        # Dot
        parts.append(
            f'<circle cx="{dot_x:.1f}" cy="{y:.1f}" r="{radius}" '
            f'style="fill:{dot_fill}" opacity="0.9"/>'
        )
        # Score label (right of dot)
        parts.append(
            f'<text x="{dot_x + radius + 5:.1f}" y="{y + 3.5}" '
            f'font-size="10" style="fill:var(--text-muted)">{cp:.2%}</text>'
        )

    # ── Title and annotation ──
    best_name = _hero_model_name(models[0][2])
    best_pct = models[0][1]

    parts.append(
        f'<text x="{total_w / 2}" y="20" text-anchor="middle" '
        f'font-size="14" style="fill:var(--text)" font-weight="700">'
        f"How Well Does AI Reproduce Human Survey Responses?</text>"
    )
    annotation = (
        f"Best: {best_name} at {best_pct:.0%} human parity"
        f"  \u00b7  Random chance: {random_sps:.0%}"
        f"  \u00b7  {dataset_label}"
    )
    parts.append(
        f'<text x="{total_w / 2}" y="38" text-anchor="middle" '
        f'font-size="11" style="fill:var(--text-muted)">'
        f"{escape(annotation)}</text>"
    )

    # ── Zone labels at bottom ──
    zone_y = chart_bot + 18
    red_x1 = x(sps_min)
    red_x2 = x(min(amber_lo, sps_max))
    if red_x2 > red_x1:
        mid = (red_x1 + red_x2) / 2
        parts.append(
            f'<text x="{mid:.1f}" y="{zone_y}" text-anchor="middle" '
            f'font-size="9" style="fill:var(--red)" opacity="0.8">'
            f"Below baseline</text>"
        )
    amb_x1 = x(max(amber_lo, sps_min))
    amb_x2 = x(min(amber_hi, sps_max))
    if amb_x2 > amb_x1:
        mid = (amb_x1 + amb_x2) / 2
        parts.append(
            f'<text x="{mid:.1f}" y="{zone_y}" text-anchor="middle" '
            f'font-size="9" style="fill:var(--gold)" opacity="0.8">'
            f"Near baseline</text>"
        )
    grn_x1 = x(max(amber_hi, sps_min))
    grn_x2 = x(sps_max)
    if grn_x2 > grn_x1:
        mid = (grn_x1 + grn_x2) / 2
        parts.append(
            f'<text x="{mid:.1f}" y="{zone_y}" text-anchor="middle" '
            f'font-size="9" style="fill:var(--green)" opacity="0.8">'
            f"Above baseline</text>"
        )

    # ── SPS axis ticks ──
    tick_y = chart_bot + 35
    step = 0.05
    tick_val = round(sps_min / step) * step
    while tick_val <= sps_max + 0.001:
        if tick_val >= sps_min:
            tx = x(tick_val)
            parts.append(
                f'<line x1="{tx:.1f}" y1="{chart_bot}" '
                f'x2="{tx:.1f}" y2="{chart_bot + 4}" '
                f'style="stroke:var(--text-muted)" stroke-width="0.5" opacity="0.5"/>'
            )
            parts.append(
                f'<text x="{tx:.1f}" y="{tick_y}" text-anchor="middle" '
                f'font-size="9" style="fill:var(--text-muted)">{tick_val:.0%}</text>'
            )
        tick_val += step

    # Axis label
    parts.append(
        f'<text x="{label_w + chart_w / 2}" y="{tick_y + 12}" text-anchor="middle" '
        f'font-size="9" style="fill:var(--text-muted)">SPS (SynthBench Parity Score)</text>'
    )

    parts.append("</svg>")
    return "\n".join(parts)


def _dot_plot_svg(ranked: list[dict], baselines: dict[str, dict]) -> str:
    """Generate a horizontal dot-plot with CI whiskers and baseline reference lines."""
    n = len(ranked)
    if n == 0:
        return ""

    row_h = 32
    gap = 4
    label_w = 220
    chart_w = 400
    w = label_w + chart_w + 40
    h = n * (row_h + gap) + 50

    # Baseline reference lines
    ref_lines = []
    for name, r in baselines.items():
        cp = r.get("aggregate", {}).get("composite_parity", 0)
        x = label_w + cp * chart_w
        color = "var(--red)" if "random" in name else "var(--gold)"
        label = "Random" if "random" in name else "Majority"
        ref_lines.append(
            f'<line x1="{x:.1f}" y1="30" x2="{x:.1f}" y2="{h - 15}" '
            f'style="stroke:{color}" stroke-width="1" stroke-dasharray="4,3" opacity="0.6"/>'
            f'<text x="{x:.1f}" y="24" text-anchor="middle" font-size="9" '
            f'style="fill:{color}" opacity="0.8">{label}</text>'
        )

    dots = []
    for i, r in enumerate(ranked):
        cfg = r.get("config", {})
        provider = cfg.get("provider", "unknown")
        cp = r.get("aggregate", {}).get("composite_parity", 0)
        is_baseline = provider in BASELINE_PROVIDERS

        y = i * (row_h + gap) + 40
        x_dot = label_w + cp * chart_w
        dot_class = "chart-muted" if is_baseline else "chart-accent"
        text_class = "chart-muted" if is_baseline else "chart-text"

        display_name = _display_provider_name(provider)
        dots.append(
            f'<text x="{label_w - 8}" y="{y + row_h * 0.6}" '
            f'text-anchor="end" font-size="11" class="{text_class}">'
            f"{escape(display_name)}</text>"
        )

        # CI whisker
        ci = r.get("aggregate", {}).get("per_metric_ci", {}).get("sps")
        if ci and len(ci) == 2:
            x_lo = label_w + ci[0] * chart_w
            x_hi = label_w + ci[1] * chart_w
            dots.append(
                f'<line x1="{x_lo:.1f}" y1="{y + row_h * 0.5}" '
                f'x2="{x_hi:.1f}" y2="{y + row_h * 0.5}" '
                f'class="{dot_class}" stroke-width="2" opacity="0.5"/>'
                f'<line x1="{x_lo:.1f}" y1="{y + row_h * 0.3}" '
                f'x2="{x_lo:.1f}" y2="{y + row_h * 0.7}" '
                f'class="{dot_class}" stroke-width="1" opacity="0.5"/>'
                f'<line x1="{x_hi:.1f}" y1="{y + row_h * 0.3}" '
                f'x2="{x_hi:.1f}" y2="{y + row_h * 0.7}" '
                f'class="{dot_class}" stroke-width="1" opacity="0.5"/>'
            )

        dots.append(
            f'<circle cx="{x_dot:.1f}" cy="{y + row_h * 0.5}" r="4" class="{dot_class}"/>'
        )
        dots.append(
            f'<text x="{x_dot + 8:.1f}" y="{y + row_h * 0.6}" '
            f'font-size="10" class="{text_class}">{cp:.4f}</text>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="100%" style="font-family:sans-serif;max-width:{w}px">\n'
        f'<text x="{w / 2}" y="18" text-anchor="middle" font-size="14" '
        f'class="chart-text" font-weight="600">SPS by Model</text>\n'
        + "\n".join(ref_lines)
        + "\n"
        + "\n".join(dots)
        + "\n</svg>"
    )


def _convergence_line_svg(convergence_data: dict[str, list[dict]]) -> str:
    """Generate a line chart showing SPS convergence across sample sizes.

    X-axis: samples per question, Y-axis: SPS.
    One colored line per model with dots and min/max error bars.
    """
    # Only include providers with 3+ sample sizes (true convergence curves)
    conv_providers = {
        p: sweeps for p, sweeps in convergence_data.items() if len(sweeps) >= 3
    }
    if not conv_providers:
        return ""

    # Chart dimensions
    pad_l = 55
    pad_r = 160
    pad_t = 40
    pad_b = 50
    chart_w = 500
    chart_h = 220
    total_w = pad_l + chart_w + pad_r
    total_h = pad_t + chart_h + pad_b

    # Collect all data points for axis scaling
    all_samples: set[int] = set()
    all_sps: list[float] = []
    for sweeps in conv_providers.values():
        for s in sweeps:
            all_samples.add(s["samples"])
            all_sps.extend(s["runs"])

    sorted_samples = sorted(all_samples)
    n_pts = len(sorted_samples)
    sample_idx = {s: i for i, s in enumerate(sorted_samples)}

    # Y-axis range (round to nice 0.05 boundaries)
    sps_lo = max(0, round((min(all_sps) - 0.02) * 20) / 20)
    sps_hi = min(1, round((max(all_sps) + 0.02) * 20 + 0.5) / 20)
    sps_span = sps_hi - sps_lo if sps_hi > sps_lo else 0.1

    def cx(idx: int) -> float:
        if n_pts <= 1:
            return pad_l + chart_w / 2
        return pad_l + idx * chart_w / (n_pts - 1)

    def cy(sps: float) -> float:
        return pad_t + chart_h - ((sps - sps_lo) / sps_span) * chart_h

    colors = [
        "var(--accent)",
        "var(--green)",
        "var(--gold)",
        "var(--red)",
        "var(--topic-4)",
        "var(--text-muted)",
    ]

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} {total_h}" '
        f'width="100%" style="font-family:-apple-system,BlinkMacSystemFont,'
        f"'Segoe UI',sans-serif;max-width:{total_w}px\">"
    ]

    # Title
    parts.append(
        f'<text x="{pad_l + chart_w / 2}" y="20" text-anchor="middle" '
        f'font-size="14" style="fill:var(--text)" font-weight="700">'
        f"Score Convergence by Sample Size</text>"
    )

    # Chart border
    parts.append(
        f'<rect x="{pad_l}" y="{pad_t}" width="{chart_w}" height="{chart_h}" '
        f'fill="none" style="stroke:var(--border)" stroke-width="1"/>'
    )

    # Y-axis grid lines and labels (0.05 steps)
    y_val = sps_lo
    while y_val <= sps_hi + 0.001:
        yy = cy(y_val)
        parts.append(
            f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{pad_l + chart_w}" y2="{yy:.1f}" '
            f'style="stroke:var(--text-muted)" stroke-width="0.5" opacity="0.2"/>'
        )
        parts.append(
            f'<text x="{pad_l - 8}" y="{yy + 4:.1f}" text-anchor="end" '
            f'font-size="10" style="fill:var(--text-muted)">{y_val:.2f}</text>'
        )
        y_val += 0.05

    # X-axis labels and subtle grid
    for s in sorted_samples:
        xx = cx(sample_idx[s])
        parts.append(
            f'<line x1="{xx:.1f}" y1="{pad_t}" x2="{xx:.1f}" y2="{pad_t + chart_h}" '
            f'style="stroke:var(--text-muted)" stroke-width="0.5" opacity="0.1"/>'
        )
        parts.append(
            f'<text x="{xx:.1f}" y="{pad_t + chart_h + 18}" text-anchor="middle" '
            f'font-size="10" style="fill:var(--text-muted)">{s}</text>'
        )

    # X-axis label
    parts.append(
        f'<text x="{pad_l + chart_w / 2}" y="{pad_t + chart_h + 38}" '
        f'text-anchor="middle" font-size="10" style="fill:var(--text-muted)">'
        f"Samples per Question</text>"
    )

    # Lines, dots, and error bars per provider
    for pi, (provider, sweeps) in enumerate(sorted(conv_providers.items())):
        color = colors[pi % len(colors)]
        name = _hero_model_name(provider)

        # Build line from mean values at each sample count
        points: list[tuple[float, float]] = []
        for sweep in sweeps:
            idx = sample_idx[sweep["samples"]]
            runs = sweep["runs"]
            mean_val = sum(runs) / len(runs)
            points.append((cx(idx), cy(mean_val)))

        if len(points) > 1:
            path_d = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in points)
            parts.append(
                f'<path d="{path_d}" fill="none" style="stroke:{color}" '
                f'stroke-width="2" opacity="0.85"/>'
            )

        # Dots and min/max error bars
        for sweep in sweeps:
            idx = sample_idx[sweep["samples"]]
            runs = sweep["runs"]
            mean_val = sum(runs) / len(runs)
            dx = cx(idx)
            dy = cy(mean_val)

            if len(runs) > 1:
                y_lo = cy(min(runs))
                y_hi = cy(max(runs))
                parts.append(
                    f'<line x1="{dx:.1f}" y1="{y_lo:.1f}" '
                    f'x2="{dx:.1f}" y2="{y_hi:.1f}" '
                    f'style="stroke:{color}" stroke-width="1.5" opacity="0.4"/>'
                )
                for cap_y in (y_lo, y_hi):
                    parts.append(
                        f'<line x1="{dx - 3:.1f}" y1="{cap_y:.1f}" '
                        f'x2="{dx + 3:.1f}" y2="{cap_y:.1f}" '
                        f'style="stroke:{color}" stroke-width="1" opacity="0.4"/>'
                    )

            parts.append(
                f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="3.5" '
                f'style="fill:{color}" opacity="0.9"/>'
            )

        # Legend entry
        ly = pad_t + 10 + pi * 18
        lx = pad_l + chart_w + 15
        parts.append(
            f'<line x1="{lx}" y1="{ly}" x2="{lx + 16}" y2="{ly}" '
            f'style="stroke:{color}" stroke-width="2"/>'
        )
        parts.append(f'<circle cx="{lx + 8}" cy="{ly}" r="2.5" style="fill:{color}"/>')
        parts.append(
            f'<text x="{lx + 22}" y="{ly + 4}" font-size="10" '
            f'style="fill:var(--text-muted)">{escape(name)}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def _topic_grouped_bar_svg(
    topic_scores: dict[str, dict[str, float]],
    topics: list[str],
    topic_colors: list[str],
) -> str:
    """Generate a grouped horizontal bar chart showing per-topic SPS for each model.

    Only includes models that have scores for all topics.
    """
    complete = {
        p: scores
        for p, scores in topic_scores.items()
        if all(t in scores for t in topics) and p not in BASELINE_PROVIDERS
    }
    if not complete or not topics:
        return ""

    n_models = len(complete)
    n_topics = len(topics)

    # Layout
    pad_l = 180
    pad_r = 60
    pad_t = 40
    pad_b = 45
    chart_w = 400
    bar_h = 14
    bar_gap = 3
    group_gap = 14
    group_h = n_topics * (bar_h + bar_gap) + group_gap
    chart_h = n_models * group_h
    total_w = pad_l + chart_w + pad_r
    total_h = pad_t + chart_h + pad_b

    # X-axis range
    all_vals = [s for scores in complete.values() for s in scores.values()]
    val_max = min(1.0, max(all_vals) + 0.05) if all_vals else 1.0

    def bar_w(val: float) -> float:
        return (val / val_max) * chart_w

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} {total_h}" '
        f'width="100%" style="font-family:-apple-system,BlinkMacSystemFont,'
        f"'Segoe UI',sans-serif;max-width:{total_w}px\">"
    ]

    # Title
    parts.append(
        f'<text x="{total_w / 2}" y="20" text-anchor="middle" '
        f'font-size="14" style="fill:var(--text)" font-weight="700">'
        f"SPS by Topic</text>"
    )

    # Vertical grid lines
    for gv in (0.2, 0.4, 0.6, 0.8, 1.0):
        if gv <= val_max:
            gx = pad_l + bar_w(gv)
            parts.append(
                f'<line x1="{gx:.1f}" y1="{pad_t}" x2="{gx:.1f}" '
                f'y2="{pad_t + chart_h}" '
                f'style="stroke:var(--text-muted)" stroke-width="0.5" opacity="0.15"/>'
            )
            parts.append(
                f'<text x="{gx:.1f}" y="{pad_t + chart_h + 15}" text-anchor="middle" '
                f'font-size="9" style="fill:var(--text-muted)">{gv:.1f}</text>'
            )

    # Bars per model
    sorted_models = sorted(complete.items(), key=lambda x: -max(x[1].values()))
    for mi, (provider, scores) in enumerate(sorted_models):
        name = _hero_model_name(provider)
        group_y = pad_t + mi * group_h

        parts.append(
            f'<text x="{pad_l - 10}" y="{group_y + group_h / 2 + 4}" '
            f'text-anchor="end" font-size="11" style="fill:var(--text)">'
            f"{escape(name)}</text>"
        )

        for ti, topic in enumerate(topics):
            val = scores.get(topic, 0)
            color = topic_colors[ti % len(topic_colors)]
            by = group_y + ti * (bar_h + bar_gap) + 2
            bw = bar_w(val)

            parts.append(
                f'<rect x="{pad_l}" y="{by:.1f}" width="{bw:.1f}" '
                f'height="{bar_h}" rx="2" '
                f'style="fill:{color}" opacity="0.8"/>'
            )
            parts.append(
                f'<text x="{pad_l + bw + 5:.1f}" y="{by + bar_h - 2:.1f}" '
                f'font-size="9" style="fill:var(--text-muted)">{val:.3f}</text>'
            )

    # Legend
    legend_y = pad_t + chart_h + 28
    legend_x = pad_l
    for ti, topic in enumerate(topics):
        color = topic_colors[ti % len(topic_colors)]
        lx = legend_x + ti * 120
        parts.append(
            f'<rect x="{lx}" y="{legend_y}" width="12" height="12" rx="2" '
            f'style="fill:{color}" opacity="0.8"/>'
        )
        parts.append(
            f'<text x="{lx + 16}" y="{legend_y + 10}" font-size="10" '
            f'style="fill:var(--text-muted)">{escape(topic.capitalize())}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def _per_metric_dot_svg(ranked: list[dict], baselines: dict[str, dict]) -> str:
    """Generate a dot plot showing P_dist, P_rank, P_refuse per model on a shared 0-1 axis.

    Includes baseline reference lines and CI whiskers where available.
    """
    models = [
        r
        for r in ranked
        if r.get("config", {}).get("provider", "") not in BASELINE_PROVIDERS
    ]
    if not models:
        return ""

    metrics = ["p_dist", "p_rank", "p_refuse"]
    metric_labels = {"p_dist": "P_dist", "p_rank": "P_rank", "p_refuse": "P_refuse"}
    metric_colors = {
        "p_dist": "var(--accent)",
        "p_rank": "var(--green)",
        "p_refuse": "var(--gold)",
    }

    # Layout
    pad_l = 180
    pad_r = 30
    pad_t = 45
    pad_b = 55
    chart_w = 450
    row_h = 32
    n = len(models)
    chart_h = n * row_h
    total_w = pad_l + chart_w + pad_r
    total_h = pad_t + chart_h + pad_b

    def sx(val: float) -> float:
        return pad_l + val * chart_w

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} {total_h}" '
        f'width="100%" style="font-family:-apple-system,BlinkMacSystemFont,'
        f"'Segoe UI',sans-serif;max-width:{total_w}px\">"
    ]

    # Title
    parts.append(
        f'<text x="{total_w / 2}" y="20" text-anchor="middle" '
        f'font-size="14" style="fill:var(--text)" font-weight="700">'
        f"Per-Metric Breakdown</text>"
    )

    # Baseline reference lines
    for bl_name, bl_r in baselines.items():
        bl_sps = bl_r.get("aggregate", {}).get("composite_parity", 0)
        bx = sx(bl_sps)
        color = "var(--red)" if "random" in bl_name else "var(--text-muted)"
        label = "Random" if "random" in bl_name else "Majority"
        parts.append(
            f'<line x1="{bx:.1f}" y1="{pad_t}" x2="{bx:.1f}" y2="{pad_t + chart_h}" '
            f'style="stroke:{color}" stroke-width="1" stroke-dasharray="4,3" opacity="0.5"/>'
        )
        parts.append(
            f'<text x="{bx:.1f}" y="{pad_t - 6}" text-anchor="middle" '
            f'font-size="9" style="fill:{color}" opacity="0.7">{label}</text>'
        )

    # X-axis grid and labels
    for tick in (0, 0.2, 0.4, 0.6, 0.8, 1.0):
        tx = sx(tick)
        parts.append(
            f'<line x1="{tx:.1f}" y1="{pad_t}" x2="{tx:.1f}" y2="{pad_t + chart_h}" '
            f'style="stroke:var(--text-muted)" stroke-width="0.5" opacity="0.12"/>'
        )
        parts.append(
            f'<text x="{tx:.1f}" y="{pad_t + chart_h + 15}" text-anchor="middle" '
            f'font-size="9" style="fill:var(--text-muted)">{tick:.1f}</text>'
        )

    # Model rows
    for i, r in enumerate(models):
        cfg = r.get("config", {})
        provider = cfg.get("provider", "unknown")
        agg = r.get("aggregate", {})
        name = _hero_model_name(provider)
        y_center = pad_t + i * row_h + row_h / 2

        # Model label
        parts.append(
            f'<text x="{pad_l - 10}" y="{y_center + 4}" text-anchor="end" '
            f'font-size="11" style="fill:var(--text)">{escape(name)}</text>'
        )

        # Row separator
        if i > 0:
            parts.append(
                f'<line x1="{pad_l}" y1="{pad_t + i * row_h}" '
                f'x2="{pad_l + chart_w}" y2="{pad_t + i * row_h}" '
                f'style="stroke:var(--border)" stroke-width="0.5" opacity="0.3"/>'
            )

        # Compute metric point estimates
        mean_jsd = agg.get("mean_jsd", 0)
        mean_tau = agg.get("mean_kendall_tau", 0)
        per_ci = agg.get("per_metric_ci", {})

        metric_vals: dict[str, float | None] = {
            "p_dist": 1.0 - mean_jsd,
            "p_rank": (1.0 + mean_tau) / 2.0,
        }
        p_refuse_ci = per_ci.get("p_refuse")
        if p_refuse_ci and len(p_refuse_ci) == 2:
            metric_vals["p_refuse"] = (p_refuse_ci[0] + p_refuse_ci[1]) / 2
        else:
            metric_vals["p_refuse"] = None

        # Draw dots and CI whiskers for each metric
        for mi, metric in enumerate(metrics):
            val = metric_vals.get(metric)
            if val is None:
                continue
            color = metric_colors[metric]
            dot_x = sx(val)
            dy_offset = (mi - 1) * 6  # vertical offset to avoid overlap
            dot_y = y_center + dy_offset

            # CI whisker
            ci = per_ci.get(metric)
            if ci and len(ci) == 2:
                x_lo = sx(ci[0])
                x_hi = sx(ci[1])
                parts.append(
                    f'<line x1="{x_lo:.1f}" y1="{dot_y}" '
                    f'x2="{x_hi:.1f}" y2="{dot_y}" '
                    f'style="stroke:{color}" stroke-width="1.5" opacity="0.35"/>'
                )
                for cap_x in (x_lo, x_hi):
                    parts.append(
                        f'<line x1="{cap_x:.1f}" y1="{dot_y - 3}" '
                        f'x2="{cap_x:.1f}" y2="{dot_y + 3}" '
                        f'style="stroke:{color}" stroke-width="1" opacity="0.35"/>'
                    )

            parts.append(
                f'<circle cx="{dot_x:.1f}" cy="{dot_y}" r="3.5" '
                f'style="fill:{color}" opacity="0.85"/>'
            )

    # Legend
    legend_y = pad_t + chart_h + 32
    legend_x = pad_l
    for mi, metric in enumerate(metrics):
        color = metric_colors[metric]
        label = metric_labels[metric]
        lx = legend_x + mi * 120
        parts.append(
            f'<circle cx="{lx + 5}" cy="{legend_y}" r="4" '
            f'style="fill:{color}" opacity="0.85"/>'
        )
        parts.append(
            f'<text x="{lx + 14}" y="{legend_y + 4}" font-size="10" '
            f'style="fill:var(--text-muted)">{label}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def _baseline_delta_html(ranked: list[dict], baselines: dict[str, dict]) -> str:
    """Build an HTML table showing delta vs each baseline."""
    if not baselines:
        return ""

    models = [
        r
        for r in ranked
        if r.get("config", {}).get("provider", "") not in BASELINE_PROVIDERS
    ]
    if not models:
        return ""

    baseline_names = sorted(baselines.keys())
    baseline_scores = {
        name: baselines[name].get("aggregate", {}).get("composite_parity", 0)
        for name in baseline_names
    }

    header_cells = "".join(
        f'<th class="num" colspan="2">{escape(name)}</th>' for name in baseline_names
    )
    subheader_cells = "".join(
        '<th class="num">Delta</th><th class="num">%</th>' for _ in baseline_names
    )

    rows = []
    for r in models:
        cfg = r.get("config", {})
        provider = cfg.get("provider", "unknown")
        cp = r.get("aggregate", {}).get("composite_parity", 0)

        display_name = _display_provider_name(provider)
        cells = f'<td class="provider-name">{escape(display_name)}</td>'
        cells += f'<td class="num composite">{cp:.4f}</td>'

        for name in baseline_names:
            base_cp = baseline_scores[name]
            delta = cp - base_cp
            pct = (delta / base_cp * 100) if base_cp > 0 else 0
            sign = "+" if delta >= 0 else ""
            color = "var(--green)" if delta > 0 else "var(--red)"
            cells += (
                f'<td class="num" style="color:{color}">{sign}{delta:.4f}</td>'
                f'<td class="num" style="color:{color}">{sign}{pct:.0f}%</td>'
            )

        rows.append(f"      <tr>{cells}</tr>")

    rows_html = "\n".join(rows)
    return f"""
  <h2 class="section-title">vs Baselines</h2>
  <table class="leaderboard-table">
    <thead>
      <tr>
        <th>Provider</th>
        <th class="num">SPS</th>
        {header_cells}
      </tr>
      <tr>
        <th></th><th></th>
        {subheader_cells}
      </tr>
    </thead>
    <tbody>
{rows_html}
    </tbody>
  </table>"""


def _metric_legend_html(
    topic_legend_inline: str = "", *, partial_sps: bool = False
) -> str:
    """Return a compact metric callout card to appear ABOVE the main table."""
    vs_defs = (
        '<p style="margin-top:0.5rem;font-size:0.88rem">'
        "<strong>vs Random</strong> &mdash; SPS improvement over uniform random baseline. "
        "<strong>vs Majority</strong> &mdash; SPS improvement over always-pick-the-mode baseline.</p>"
    )
    partial_note = ""
    if partial_sps:
        partial_note = (
            '<p style="margin-top:0.5rem;font-size:0.88rem">'
            "<strong>SPS*</strong> &mdash; Computed from available metrics only. "
            "Full SPS requires P_cond and P_sub from persona-conditioned runs.</p>"
        )
    return f"""
  <div class="about metric-legend">
    <p><strong>{"SPS*" if partial_sps else "SPS"}</strong> (SynthBench Parity Score) measures how well AI reproduces human survey responses.
       Higher is better (0&nbsp;=&nbsp;random, 1&nbsp;=&nbsp;human-identical).</p>
    <p style="margin-top:0.5rem;font-size:0.88rem">
       <strong>P_dist</strong> &mdash; distributional match (1 &minus; JSD).
       <strong>P_rank</strong> &mdash; rank-order agreement (normalized Kendall&rsquo;s &tau;).
       <strong>P_refuse</strong> &mdash; refusal-rate calibration (1 &minus; mean |&Delta;refusal|).
       All [0,&thinsp;1]; higher = better.</p>
    {vs_defs}
    {partial_note}
    {topic_legend_inline}
  </div>"""


def _metric_explanations_html() -> str:
    """Return HTML section explaining each metric in plain English."""
    return """
  <h2 class="section-title">Understanding the Scores</h2>
  <div class="about">
    <p><strong>SPS &mdash; SynthBench Parity Score</strong><br>
       The overall score &mdash; average of all metrics below. <strong>0</strong> = random noise,
       <strong>1</strong> = indistinguishable from real humans.<br>
       <em>Example: An SPS of 0.72 means the AI reproduces about 72% of the fidelity
       of actual human survey responses.</em></p>

    <p><strong>P_dist &mdash; Distributional Parity</strong><br>
       How closely does the AI&rsquo;s answer distribution match real humans?
       If 60% of humans say &ldquo;yes&rdquo; and the AI says &ldquo;yes&rdquo; 60% of the time,
       that&rsquo;s a perfect match.<br>
       <strong>0</strong> = completely different distributions.
       <strong>1</strong> = identical distributions.<br>
       <em>Example: On &ldquo;Do you support renewable energy?&rdquo; humans split 70/30. If the AI
       also splits 70/30, P_dist is near 1. If the AI splits 50/50, P_dist drops.</em></p>

    <p><strong>P_rank &mdash; Rank-Order Parity</strong><br>
       Does the AI get the preference ordering right? If humans prefer A&nbsp;&gt;&nbsp;B&nbsp;&gt;&nbsp;C,
       does the AI agree &mdash; even if the exact percentages differ?<br>
       <strong>0</strong> = reversed or random ordering.
       <strong>1</strong> = perfect rank agreement.<br>
       <em>Example: Humans rank &ldquo;economy&rdquo; &gt; &ldquo;healthcare&rdquo; &gt; &ldquo;education&rdquo; as top priorities.
       The AI agrees on that ordering even though its percentages are slightly off &mdash;
       that&rsquo;s high P_rank.</em></p>

    <p><strong>P_refuse &mdash; Refusal Calibration</strong><br>
       Does the AI refuse to answer at appropriate rates? Humans sometimes decline
       sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated.<br>
       <strong>0</strong> = refusal rates are completely off.
       <strong>1</strong> = refusal rates match humans exactly.<br>
       <em>Example: 15% of humans decline to answer about income. If the AI also declines
       ~15% of the time, P_refuse is high. If it always answers, P_refuse drops.</em></p>

    <p><strong>P_cond &mdash; Conditioning Fidelity</strong><br>
       When we tell the AI &ldquo;respond as a 65-year-old conservative,&rdquo; does its answer
       actually shift to match that demographic? Higher means better demographic role-playing.<br>
       <strong>0</strong> = personas have no effect on answers.
       <strong>1</strong> = perfect demographic conditioning.<br>
       <em>Example: Young liberals and older conservatives answer differently in real life.
       If the AI shifts its answers appropriately when given each persona, P_cond is high.</em></p>

    <p><strong>P_sub &mdash; Subgroup Consistency</strong><br>
       Is the AI equally accurate across all demographics, or does it nail some groups
       and miss others?<br>
       <strong>0</strong> = wildly uneven accuracy across groups.
       <strong>1</strong> = equally accurate for every demographic.<br>
       <em>Example: An AI that nails young liberals but misrepresents older conservatives
       gets penalized. Consistent accuracy across all groups earns a high P_sub.</em></p>
  </div>

  <h2 class="section-title">Technical Details</h2>
  <div class="about">
    <p><strong>SPS</strong> = equal-weighted mean of active component metrics.
       <code>SPS = mean(P_dist, P_rank, P_refuse[, P_cond, P_sub])</code></p>
    <p><strong>P_dist</strong> = <code>1 - mean(JSD)</code>.
       Jensen-Shannon divergence is bounded [0, 1], symmetric, and handles zero entries.</p>
    <p><strong>P_rank</strong> = <code>(1 + mean(tau)) / 2</code>.
       Kendall&rsquo;s tau-b on probability rankings, normalized to [0, 1].</p>
    <p><strong>P_refuse</strong> = <code>1 - mean(|R_provider - R_human|)</code>.</p>
    <p><strong>P_cond</strong>: Improvement from persona conditioning vs. unconditioned baseline.</p>
    <p><strong>P_sub</strong>: Variance across per-group P_dist scores, inverted so higher is better.</p>
    <p><strong>Mean JSD</strong>: Average Jensen-Shannon divergence across all questions.
       Lower is better (0 = identical distributions).</p>
    <p><strong>Kendall&rsquo;s tau</strong>: Rank correlation between human and model response option rankings.
       Range [-1, 1]. 1 = perfect agreement, 0 = no correlation.</p>
  </div>
  <div class="about" style="margin-top:1rem">
    <p><strong>Baselines</strong> give meaning to scores:</p>
    <p><strong>Random Baseline</strong>: Uniform distribution over all options. The absolute floor &mdash;
       any provider scoring at or below random is adding negative value.</p>
    <p><strong>Majority-Class Baseline</strong>: Always picks the mode of the population distribution.
       Scores well on consensus questions, poorly on divisive ones. Shows the value of
       distributional modeling.</p>
    <p>See <a href="https://github.com/DataViking-Tech/synthbench/blob/main/METHODOLOGY.md">METHODOLOGY.md</a>
       for the full metric framework and design rationale.</p>
  </div>"""


def _collect_topic_scores(
    results: list[dict],
) -> tuple[dict[str, dict[str, float]], list[str]]:
    """Collect per-topic composite parity scores from topic-tagged results.

    Returns (provider_topic_scores, sorted_topic_names).
    """
    topic_scores: dict[str, dict[str, float]] = {}
    topics_seen: set[str] = set()
    for r in results:
        cfg = r.get("config", {})
        topic = cfg.get("topic")
        if not topic:
            continue
        provider = cfg.get("provider", "unknown")
        cp = r.get("aggregate", {}).get("composite_parity", 0)
        topic_scores.setdefault(provider, {})[topic] = round(cp, 4)
        topics_seen.add(topic)
    return topic_scores, sorted(topics_seen)


# ---------------------------------------------------------------------------
# Multi-dataset helpers: heatmap, fitness notes, per-dataset tables
# ---------------------------------------------------------------------------

DATASET_LABELS: dict[str, str] = {
    "opinionsqa": "OpinionsQA",
    "globalopinionqa": "GlobalOpinionQA",
    "subpop": "SubPOP",
}


def _sps_bg_style(sps: float | None) -> str:
    """Return inline background style for a heatmap cell coloured by SPS."""
    if sps is None:
        return "background:var(--surface);color:var(--text-muted)"
    intensity = max(0.0, min(1.0, (sps - 0.5) / 0.3))
    return f"background:rgba(63,185,80,{intensity * 0.25 + 0.05})"


def _fitness_note(provider_topics: dict[str, float]) -> str:
    """Generate a model-topic fitness note.

    - If political SPS < consumer SPS by 2%+: "Avoid politically charged surveys"
    - If consistent across topics: "Consistent across all topics"
    """
    if not provider_topics or len(provider_topics) < 2:
        return ""
    political = provider_topics.get("political")
    consumer = provider_topics.get("consumer")
    if political is not None and consumer is not None:
        if consumer - political >= 0.02:
            return "Avoid politically charged surveys"
    values = list(provider_topics.values())
    spread = max(values) - min(values)
    if spread < 0.02:
        return "Consistent across all topics"
    return ""


def _build_heatmap_data(
    summary_entries: list[dict],
    datasets: list[str],
    topic_scores: dict[str, dict[str, float]],
) -> list[dict]:
    """Build heatmap rows: one per model (deduplicated by display name).

    Returns list sorted by aggregate SPS descending with keys:
    name, provider, datasets, aggregate, count, total, fitness.
    """
    from synthbench.leaderboard import display_provider_name

    model_data: dict[str, dict] = {}
    for e in summary_entries:
        provider = e["provider"]
        if provider in BASELINE_PROVIDERS:
            continue
        name = display_provider_name(provider)
        dataset = e["dataset"]
        sps = e["composite_parity"]
        if name not in model_data:
            model_data[name] = {"name": name, "provider": provider, "datasets": {}}
        model_data[name]["datasets"][dataset] = sps

    rows = []
    for name, data in model_data.items():
        scores = [data["datasets"][ds] for ds in datasets if ds in data["datasets"]]
        aggregate = sum(scores) / len(scores) if scores else 0
        fitness = _fitness_note(topic_scores.get(data["provider"], {}))
        rows.append(
            {
                "name": name,
                "provider": data["provider"],
                "datasets": data["datasets"],
                "aggregate": round(aggregate, 4),
                "count": len(scores),
                "total": len(datasets),
                "fitness": fitness,
            }
        )

    rows.sort(key=lambda r: r["aggregate"], reverse=True)
    return rows


def _heatmap_html(
    heatmap_rows: list[dict], datasets: list[str], *, partial_sps: bool = False
) -> str:
    """Generate heatmap matrix table HTML for the overview tab."""
    ds_headers = "".join(
        f'<th class="num mob-hide">{escape(DATASET_LABELS.get(ds, ds))}</th>'
        for ds in datasets
    )

    medals = {0: "&#x1f947;", 1: "&#x1f948;", 2: "&#x1f949;"}
    trs: list[str] = []
    for i, row in enumerate(heatmap_rows):
        medal_html = f'<span class="medal">{medals[i]}</span>' if i in medals else ""

        cells = f'<td class="rank num">{medal_html}{i + 1}</td>'
        cells += f'<td class="provider-name">{escape(row["name"])}</td>'

        for ds in datasets:
            sps = row["datasets"].get(ds)
            if sps is not None:
                style = _sps_bg_style(sps)
                cells += f'<td class="num heatmap-cell mob-hide" style="{style}">{sps:.4f}</td>'
            else:
                cells += (
                    '<td class="num heatmap-cell mob-hide" '
                    'style="background:var(--surface);color:var(--text-muted)">'
                    "&mdash;</td>"
                )

        cells += f'<td class="num composite">{row["aggregate"]:.4f}</td>'

        badge_color = "var(--green)" if row["count"] == row["total"] else "var(--gold)"
        cells += (
            f'<td><span class="dataset-badge" style="color:{badge_color}">'
            f"{row['count']}/{row['total']} datasets</span></td>"
        )

        if row["fitness"]:
            cells += f'<td class="fitness-note mob-hide">{escape(row["fitness"])}</td>'
        else:
            cells += '<td class="fitness-note mob-hide">&mdash;</td>'

        trs.append(f"      <tr>{cells}</tr>")

    return (
        '<table class="leaderboard-table heatmap-table">\n'
        "  <thead><tr>\n"
        '    <th class="rank">Rank</th><th>Model</th>\n'
        f"    {ds_headers}\n"
        f'    <th class="num">Aggregate {"SPS*" if partial_sps else "SPS"}</th><th>Coverage</th>'
        '<th class="mob-hide">Strengths</th>\n'
        "  </tr></thead>\n"
        "  <tbody>\n" + "\n".join(trs) + "\n  </tbody>\n"
        "</table>"
    )


def _dataset_table_html(
    summary_entries: list[dict],
    dataset: str,
    baseline_data: dict[str, dict],
    *,
    partial_sps: bool = False,
    random_sps: float = 0.65,
) -> str:
    """Generate a ranked leaderboard table filtered to one dataset."""
    from synthbench.leaderboard import display_provider_name, provider_framework

    ds_entries = [e for e in summary_entries if e["dataset"] == dataset]
    if not ds_entries:
        return '<p class="about">No results for this dataset yet.</p>'

    raw = []
    products = []
    baselines_list: list[dict] = []
    for e in ds_entries:
        fw = e.get("framework") or provider_framework(e["provider"])
        if fw == "baseline":
            baselines_list.append(e)
        elif fw == "product":
            products.append(e)
        else:
            raw.append(e)

    raw.sort(key=lambda e: e["composite_parity"], reverse=True)
    products.sort(key=lambda e: e["composite_parity"], reverse=True)

    has_bl = bool(baseline_data)
    n_cols = 7 + (2 if has_bl else 0)

    medal_map = {1: "&#x1f947;", 2: "&#x1f948;", 3: "&#x1f949;"}
    trs: list[str] = []

    def _add_section(label: str) -> None:
        trs.append(
            f'<tr class="section-divider"><td colspan="{n_cols}">'
            f'<span class="section-label">{escape(label)}</span></td></tr>'
        )

    def _add_row(
        e: dict,
        rank: int | None = None,
        css_class: str = "",
    ) -> None:
        name = display_provider_name(e["provider"])
        medal = medal_map.get(rank, "") if rank else ""
        medal_html = f'<span class="medal">{medal}</span>' if medal else ""
        rank_display = str(rank) if rank else ""

        bl_cells = ""
        if has_bl:
            vs_r = e.get("vs_random")
            vs_m = e.get("vs_majority")
            for vs in (vs_r, vs_m):
                if vs:
                    dv = float(vs)
                    c = "var(--green)" if dv > 0 else "var(--red)"
                    bl_cells += f'<td class="num mob-hide" style="color:{c}">{vs}</td>'
                else:
                    bl_cells += '<td class="num mob-hide">&mdash;</td>'

        near_bl = (
            _is_near_baseline(e["composite_parity"], random_sps)
            and e["provider"] not in BASELINE_PROVIDERS
        )
        near_bl_cls = " near-baseline" if near_bl else ""
        near_bl_attr = ' title="Within margin of random baseline"' if near_bl else ""
        row_cls = f"{css_class}{near_bl_cls}".strip()

        trs.append(
            f'<tr class="{row_cls}"{near_bl_attr}>'
            f'<td class="rank num">{medal_html}{rank_display}</td>'
            f'<td class="provider-name">{escape(name)}</td>'
            f'<td class="num">{e.get("n", 0)}</td>'
            f'<td class="num composite">{e["composite_parity"]:.4f}</td>'
            f"{bl_cells}"
            f'<td class="num">{e["mean_jsd"]:.4f}</td>'
            f'<td class="num">{e["mean_kendall_tau"]:.4f}</td>'
            f'<td class="mob-hide">{e["date"]}</td>'
            f"</tr>"
        )

    if raw:
        _add_section("Raw LLMs")
        for rank, e in enumerate(raw, 1):
            _add_row(e, rank=rank)

    if products:
        _add_section("Products")
        for e in products:
            _add_row(e, css_class="product-row")

    if baselines_list:
        _add_section("Baselines")
        for e in baselines_list:
            _add_row(e, css_class="baseline-row")

    bl_th = ""
    if has_bl:
        bl_th = '<th class="num mob-hide">vs Random</th><th class="num mob-hide">vs Majority</th>'

    return (
        '<table class="leaderboard-table">\n'
        "  <thead><tr>\n"
        '    <th class="rank">Rank</th><th>Provider</th>'
        f'<th class="num">N</th><th class="num">{"SPS*" if partial_sps else "SPS"}</th>'
        f"{bl_th}"
        '<th class="num">JSD</th><th class="num">Tau</th>'
        '<th class="mob-hide">Date</th>\n'
        "  </tr></thead>\n"
        "  <tbody>\n" + "\n".join(trs) + "\n  </tbody>\n"
        "</table>"
    )


def generate_html(results: list[dict], version: str = "0.1.0") -> str:
    """Build a complete HTML leaderboard page from a list of result dicts.

    Generates a two-tier leaderboard: summary rows (best per provider+dataset)
    with expandable detail sub-rows (all runs). Includes SVG charts,
    baseline delta columns, convergence data table, metric explanations,
    and per-topic columns when topic-tagged results are available.
    """
    from synthbench.leaderboard import build_leaderboard

    # Get structured leaderboard data
    _md, lb_json = build_leaderboard(results)
    summary_entries = lb_json.get("summary", [])
    detail_entries = lb_json.get("detail", [])
    baseline_data = lb_json.get("baselines", {})
    convergence_data = lb_json.get("convergence", {})

    # Separate overall from topic-tagged results for charts
    overall_results = [r for r in results if not r.get("config", {}).get("topic")]
    topic_results = [r for r in results if r.get("config", {}).get("topic")]

    topic_scores, topics_present = _collect_topic_scores(topic_results)
    topic_colors = [
        "var(--topic-0)",
        "var(--topic-1)",
        "var(--topic-2)",
        "var(--topic-3)",
        "var(--topic-4)",
    ]

    deduped = _dedup_results(overall_results if overall_results else results)
    ranked = sorted(
        deduped,
        key=lambda r: r.get("aggregate", {}).get("composite_parity", 0),
        reverse=True,
    )

    _models, baselines = _split_baselines(ranked)

    # Compute random baseline SPS for near-baseline detection
    random_sps_val = 0.65
    best_n_random = -1
    for r in ranked:
        cfg = r.get("config", {})
        if cfg.get("provider") == "random-baseline":
            n_eval = cfg.get("n_evaluated", 0)
            if n_eval > best_n_random:
                best_n_random = n_eval
                random_sps_val = r.get("aggregate", {}).get("composite_parity", 0)

    # Detect if any result has partial SPS (fewer than 5 metrics)
    any_partial_sps = any(_is_partial_sps(r) for r in ranked)

    # Group detail entries by provider+dataset for expandable sub-rows
    detail_by_key: dict[tuple[str, str], list[dict]] = {}
    for d in detail_entries:
        key = (d["provider"], d["dataset"])
        detail_by_key.setdefault(key, []).append(d)

    has_baselines = bool(baseline_data)

    # Separate summary_entries into 3 sections: raw LLMs, products, baselines
    from synthbench.leaderboard import provider_framework

    raw_entries = []
    product_entries = []
    baseline_entries = []
    for e in summary_entries:
        fw = e.get("framework") or provider_framework(e["provider"])
        if fw == "baseline":
            baseline_entries.append(e)
        elif fw == "product":
            product_entries.append(e)
        else:
            raw_entries.append(e)
    provider_entries = raw_entries

    # Build provider table rows
    rows_html = []

    # Section divider helper (defined early so all sections can use it)
    def _make_section_divider(label: str) -> str:
        n_cols = 10
        if has_baselines:
            n_cols += 2
        if topics_present:
            n_cols += 1
        return (
            f'      <tr class="section-divider"><td colspan="{n_cols}">'
            f'<span class="section-label">{escape(label)}</span></td></tr>'
        )

    if provider_entries:
        rows_html.append(_make_section_divider("Raw LLMs"))

    medals = {1: "&#x1f947;", 2: "&#x1f948;", 3: "&#x1f949;"}
    for rank, e in enumerate(provider_entries, 1):
        provider_raw = e["provider"]
        display_name = _display_provider_name(provider_raw)

        medal = medals.get(rank, "")
        medal_html = f'<span class="medal">{medal}</span>' if medal else ""
        # Model info is now part of display_name via MODEL_MAP
        # Extract framework badge from MODEL_MAP
        from synthbench.leaderboard import MODEL_MAP

        _entry = MODEL_MAP.get(provider_raw)
        framework = _entry[1] if _entry else "raw"
        framework_badge = {
            "raw": "raw",
            "product": "product",
            "baseline": "baseline",
        }.get(framework, "")
        model_display = (
            f'<span class="framework-badge">{framework_badge}</span>'
            if framework_badge
            else "&mdash;"
        )

        n_eval = e.get("n", 0)

        # #6 N-threshold: muted styling for n < 50
        low_n = n_eval < N_THRESHOLD
        low_n_class = " low-n" if low_n else ""
        n_display = (
            f'{n_eval}<span class="low-n-marker">*</span>' if low_n else str(n_eval)
        )

        # Composite score + CI whisker (#3) + P_refuse extraction
        cp = e["composite_parity"]
        ci_svg = ""
        p_refuse_val = None
        # Find the result dict for this entry to get CI data
        for r in ranked:
            r_cfg = r.get("config", {})
            if (
                r_cfg.get("provider") == provider_raw
                and r_cfg.get("dataset") == e["dataset"]
            ):
                per_ci = r.get("aggregate", {}).get("per_metric_ci", {})
                ci = per_ci.get("sps")
                if ci and len(ci) == 2:
                    ci_svg = _ci_whisker_svg(ci[0], ci[1], cp)
                else:
                    ci_svg = '<span style="font-size:0.75rem;color:var(--text-muted);margin-left:4px">1 run</span>'
                # Extract P_refuse from CI midpoint
                p_refuse_ci = per_ci.get("p_refuse")
                if p_refuse_ci and len(p_refuse_ci) == 2:
                    p_refuse_val = (p_refuse_ci[0] + p_refuse_ci[1]) / 2
                break

        topic_cells = ""
        if topics_present:
            provider_topics = e.get("topic_scores", {})
            topic_cell_svg = _topic_bars_svg(
                provider_topics, topics_present, topic_colors
            )
            topic_cells = f'        <td class="num mob-hide">{topic_cell_svg}</td>\n'

        p_refuse_cell = ""
        if p_refuse_val is not None:
            p_refuse_cell = (
                f'        <td class="num mob-hide">{p_refuse_val:.4f}</td>\n'
            )
        else:
            p_refuse_cell = '        <td class="num mob-hide">&mdash;</td>\n'

        baseline_cells = ""
        if has_baselines:
            vs_r = e.get("vs_random")
            vs_m = e.get("vs_majority")
            if vs_r:
                delta_val = float(vs_r)
                color = "var(--green)" if delta_val > 0 else "var(--red)"
                baseline_cells += f'        <td class="num mob-hide" style="color:{color}">{vs_r}</td>\n'
            else:
                baseline_cells += '        <td class="num mob-hide">&mdash;</td>\n'
            if vs_m:
                delta_val = float(vs_m)
                color = "var(--green)" if delta_val > 0 else "var(--red)"
                baseline_cells += f'        <td class="num mob-hide" style="color:{color}">{vs_m}</td>\n'
            else:
                baseline_cells += '        <td class="num mob-hide">&mdash;</td>\n'

        # #10 expandable detail toggle
        toggle_html = ""
        detail_key = (provider_raw, e["dataset"])
        sub_runs = detail_by_key.get(detail_key, [])
        has_details = len(sub_runs) > 1
        if has_details:
            toggle_html = (
                f'<span class="chevron" data-provider="{escape(provider_raw)}_{escape(e["dataset"])}" '
                f'title="Show details">&#x25B6;</span>'
            )

        # Near-baseline detection
        near_bl = (
            _is_near_baseline(cp, random_sps_val)
            and provider_raw not in BASELINE_PROVIDERS
        )
        near_bl_class = " near-baseline" if near_bl else ""
        near_bl_title = ' title="Within margin of random baseline"' if near_bl else ""
        row_classes = f"{low_n_class}{near_bl_class}".strip()

        rows_html.append(
            f'      <tr class="{row_classes}"{near_bl_title} data-sps="{cp:.4f}" data-n="{n_eval}" '
            f'data-jsd="{e["mean_jsd"]:.4f}" data-tau="{e["mean_kendall_tau"]:.4f}">\n'
            f'        <td class="rank num">{toggle_html}{medal_html}{rank}</td>\n'
            f'        <td class="provider-name">{escape(display_name)}</td>\n'
            f'        <td class="mob-hide"><span class="model-name">{model_display}</span></td>\n'
            f'        <td class="mob-hide">{escape(e["dataset"])}</td>\n'
            f'        <td class="num">{n_display}</td>\n'
            f'        <td class="num composite">{cp:.4f}{ci_svg}</td>\n'
            f"{baseline_cells}"
            f"{topic_cells}"
            f"{p_refuse_cell}"
            f'        <td class="num">{e["mean_jsd"]:.4f}</td>\n'
            f'        <td class="num">{e["mean_kendall_tau"]:.4f}</td>\n'
            f'        <td class="mob-hide">{e["date"]}</td>\n'
            f"      </tr>"
        )

        # #10 Hidden expandable detail sub-rows
        if has_details:
            # Find convergence data for sparkline
            conv = convergence_data.get(provider_raw, [])
            conv_html = ""
            if conv:
                spark_vals = [s["runs"][0] for s in conv if s.get("runs")]
                if spark_vals:
                    spark_max = max(spark_vals) if spark_vals else 1
                    spark_min = min(spark_vals) if spark_vals else 0
                    spark_range = spark_max - spark_min if spark_max > spark_min else 1
                    spark_w = 80
                    spark_h = 20
                    points = []
                    for si, sv in enumerate(spark_vals):
                        sx = 2 + si * ((spark_w - 4) / max(1, len(spark_vals) - 1))
                        sy = (
                            spark_h
                            - 2
                            - ((sv - spark_min) / spark_range) * (spark_h - 4)
                        )
                        points.append(f"{sx:.1f},{sy:.1f}")
                    polyline = " ".join(points)
                    conv_html = (
                        f'<svg xmlns="http://www.w3.org/2000/svg" width="{spark_w}" height="{spark_h}" '
                        f'style="vertical-align:middle">'
                        f'<polyline points="{polyline}" fill="none" style="stroke:var(--accent)" stroke-width="1.5"/>'
                        f"</svg>"
                    )

            n_cols = 10  # rank + provider + model + dataset + N + SPS + P_refuse + JSD + tau + date
            if has_baselines:
                n_cols += 2
            if topics_present:
                n_cols += 1

            detail_content = ""
            for sub in sub_runs:
                detail_content += (
                    f'<div class="detail-item">'
                    f"n={sub['n']} samples={sub['samples_per_question']} "
                    f"SPS={sub['composite_parity']:.4f} "
                    f"JSD={sub['mean_jsd']:.4f} tau={sub['mean_kendall_tau']:.4f}"
                    f"</div>"
                )

            rows_html.append(
                f'      <tr class="detail-row" data-provider="{escape(provider_raw)}_{escape(e["dataset"])}" style="display:none">\n'
                f'        <td colspan="{n_cols}" class="detail-cell">\n'
                f'          <div class="detail-content">\n'
                f'            <div class="detail-section"><strong>Runs:</strong> {detail_content}</div>\n'
                f'            <div class="detail-section"><strong>Convergence:</strong> {conv_html if conv_html else "N/A"}</div>\n'
                f"          </div>\n"
                f"        </td>\n"
                f"      </tr>"
            )

    # #4 Products section
    if product_entries:
        rows_html.append(_make_section_divider("Products"))
        for pi, e in enumerate(product_entries, 1):
            provider_raw = e["provider"]
            cp = e["composite_parity"]
            display_name = _display_provider_name(provider_raw)

            n_cols = 10
            if has_baselines:
                n_cols += 2
            if topics_present:
                n_cols += 1

            baseline_cells = ""
            if has_baselines:
                vs_r = e.get("vs_random")
                vs_m = e.get("vs_majority")
                if vs_r:
                    delta_val = float(vs_r)
                    color = "var(--green)" if delta_val > 0 else "var(--red)"
                    baseline_cells += f'        <td class="num mob-hide" style="color:{color}">{vs_r}</td>\n'
                else:
                    baseline_cells += '        <td class="num mob-hide">&mdash;</td>\n'
                if vs_m:
                    delta_val = float(vs_m)
                    color = "var(--green)" if delta_val > 0 else "var(--red)"
                    baseline_cells += f'        <td class="num mob-hide" style="color:{color}">{vs_m}</td>\n'
                else:
                    baseline_cells += '        <td class="num mob-hide">&mdash;</td>\n'

            topic_cells = ""
            if topics_present:
                provider_topics = e.get("topic_scores", {})
                topic_cell_svg = _topic_bars_svg(
                    provider_topics, topics_present, topic_colors
                )
                topic_cells = (
                    f'        <td class="num mob-hide">{topic_cell_svg}</td>\n'
                )

            near_bl = _is_near_baseline(cp, random_sps_val)
            near_bl_class = " near-baseline" if near_bl else ""
            near_bl_title = (
                ' title="Within margin of random baseline"' if near_bl else ""
            )

            rows_html.append(
                f'      <tr class="product-row{near_bl_class}"{near_bl_title} data-sps="{cp:.4f}" data-n="{e.get("n", 0)}" '
                f'data-jsd="{e["mean_jsd"]:.4f}" data-tau="{e["mean_kendall_tau"]:.4f}">\n'
                f'        <td class="rank num"></td>\n'
                f'        <td class="provider-name">{escape(display_name)}</td>\n'
                f'        <td class="mob-hide"></td>\n'
                f'        <td class="mob-hide">{escape(e["dataset"])}</td>\n'
                f'        <td class="num">{e.get("n", 0)}</td>\n'
                f'        <td class="num composite">{cp:.4f}</td>\n'
                f"{baseline_cells}"
                f"{topic_cells}"
                f'        <td class="num mob-hide">&mdash;</td>\n'
                f'        <td class="num">{e["mean_jsd"]:.4f}</td>\n'
                f'        <td class="num">{e["mean_kendall_tau"]:.4f}</td>\n'
                f'        <td class="mob-hide">{e["date"]}</td>\n'
                f"      </tr>"
            )

    # Baseline divider + baseline rows
    if baseline_entries:
        rows_html.append(_make_section_divider("Baselines"))
        for e in baseline_entries:
            provider_raw = e["provider"]
            cp = e["composite_parity"]
            display_name = _display_provider_name(provider_raw)
            rows_html.append(
                f'      <tr class="baseline-row" data-sps="{cp:.4f}" data-n="{e.get("n", 0)}" '
                f'data-jsd="{e["mean_jsd"]:.4f}" data-tau="{e["mean_kendall_tau"]:.4f}">\n'
                f'        <td class="rank num"></td>\n'
                f'        <td class="provider-name baseline-name">{escape(display_name)}</td>\n'
                f'        <td class="mob-hide"></td>\n'
                f'        <td class="mob-hide">{escape(e["dataset"])}</td>\n'
                f'        <td class="num">{e.get("n", 0)}</td>\n'
                f'        <td class="num composite">{cp:.4f}</td>\n'
                + (
                    '        <td class="num mob-hide"></td>\n        <td class="num mob-hide"></td>\n'
                    if has_baselines
                    else ""
                )
                + ('        <td class="num mob-hide"></td>\n' if topics_present else "")
                + '        <td class="num mob-hide"></td>\n'  # P_refuse (empty for baselines)
                + f'        <td class="num">{e["mean_jsd"]:.4f}</td>\n'
                f'        <td class="num">{e["mean_kendall_tau"]:.4f}</td>\n'
                f'        <td class="mob-hide">{e["date"]}</td>\n'
                f"      </tr>"
            )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tbody = "\n".join(rows_html)

    # #7 Single "Topics" column header (replaces per-topic columns)
    topic_th = ""
    topic_legend_inline = ""
    if topics_present:
        topic_th = '        <th class="num mob-hide">Topics</th>\n'
        legend_items = []
        for i, t in enumerate(topics_present):
            color = topic_colors[i % len(topic_colors)]
            legend_items.append(
                f'<span style="display:inline-flex;align-items:center;gap:0.25rem;margin-right:0.75rem">'
                f'<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:{color}"></span>'
                f'<span style="font-size:0.8rem;color:var(--text-muted)">{escape(t.capitalize())}</span></span>'
            )
        topic_legend_inline = (
            f'<p style="margin-top:0.5rem;font-size:0.88rem">'
            f"<strong>Topics</strong> &mdash; {''.join(legend_items)}</p>"
        )

    # P_refuse column header
    p_refuse_th = '        <th class="num mob-hide" title="Refusal calibration: 1 − mean |Δrefusal|">P_refuse</th>\n'

    # Baseline column headers
    baseline_th = ""
    if has_baselines:
        baseline_th = '        <th class="num sortable mob-hide" data-sort="vs-random" title="SPS improvement over uniform random baseline">vs Random</th>\n        <th class="num sortable mob-hide" data-sort="vs-majority" title="SPS improvement over always-pick-the-mode baseline">vs Majority</th>\n'

    # Generate chart sections
    chart_datasets = sorted(
        {r.get("config", {}).get("dataset", "") for r in ranked} - {""}
    )
    ds_label = (
        ", ".join(DATASET_LABELS.get(d, d) for d in chart_datasets)
        if chart_datasets
        else "All Datasets"
    )
    hero_chart = _hero_svg(ranked, baselines, dataset_label=ds_label)
    dot_plot = _dot_plot_svg(ranked, baselines)
    per_metric_dot = _per_metric_dot_svg(ranked, baselines)
    topic_bar = _topic_grouped_bar_svg(topic_scores, topics_present, topic_colors)
    explanations = _metric_explanations_html()
    metric_legend = _metric_legend_html(
        topic_legend_inline, partial_sps=any_partial_sps
    )

    # Compute hero headline: best model SPS vs random baseline SPS
    best_sps = 0.0
    for r in ranked:
        provider = r.get("config", {}).get("provider", "")
        if provider not in BASELINE_PROVIDERS:
            cp = r.get("aggregate", {}).get("composite_parity", 0)
            if cp > best_sps:
                best_sps = cp
    delta_points = round((best_sps - random_sps_val) * 100)
    hero_headline = (
        f'<h2 class="hero-headline">The best AI is only '
        f"{delta_points}&nbsp;points above random chance.</h2>"
    )

    # Convergence section — line chart for convergence, table for replicates
    convergence_line = _convergence_line_svg(convergence_data)
    convergence_html = ""
    if convergence_data:
        replicate_rows = []
        for provider, sweeps in sorted(convergence_data.items()):
            if len(sweeps) >= 3:
                continue  # convergence providers handled by line chart
            display_name = _display_provider_name(provider)
            for sweep in sweeps:
                samples = sweep["samples"]
                runs = sweep["runs"]
                mean_cp = sum(runs) / len(runs)
                replicate_rows.append(
                    f"      <tr>\n"
                    f'        <td class="provider-name">{escape(display_name)}</td>\n'
                    f'        <td class="num">{samples}</td>\n'
                    f'        <td class="num">{len(runs)}</td>\n'
                    f'        <td class="num composite">{mean_cp:.4f}</td>\n'
                    f'        <td class="num">{min(runs):.4f}</td>\n'
                    f'        <td class="num">{max(runs):.4f}</td>\n'
                    f"      </tr>"
                )

        if convergence_line:
            convergence_html += f"""
    <details class="collapsible">
      <summary>Convergence</summary>
      <div class="collapsible-body">
        <div class="about">
          <p>How scores change as sample count increases. Dots show mean SPS; error bars span min/max across runs.</p>
        </div>
        <div class="chart-section">
{convergence_line}
        </div>
      </div>
    </details>"""

        if replicate_rows:
            rep_tbody = "\n".join(replicate_rows)
            convergence_html += f"""
    <details class="collapsible">
      <summary>Replicate Runs</summary>
      <div class="collapsible-body">
        <div class="about">
          <p>Repeated runs at the same sample size. Useful for measuring score variance, not convergence trends.</p>
        </div>
        <table class="leaderboard-table">
    <thead>
      <tr>
        <th>Provider</th>
        <th class="num">Samples/q</th>
        <th class="num">Runs</th>
        <th class="num">Mean SPS</th>
        <th class="num">Min</th>
        <th class="num">Max</th>
      </tr>
    </thead>
          <tbody>
{rep_tbody}
          </tbody>
        </table>
      </div>
    </details>"""

    # #1 synthpanel footnote
    has_synthpanel = any(_is_synthpanel(e["provider"]) for e in summary_entries)
    synthpanel_footnote = ""
    if has_synthpanel:
        synthpanel_footnote = (
            '<p class="footnote"><strong>Adapter test:</strong> '
            "SynthPanel entries use an early, untuned adapter integration and are "
            "not representative of production SynthPanel quality. Included for "
            "transparency and baseline comparison.</p>"
        )

    # #6 low-N footnote
    has_low_n = any(e.get("n", 0) < N_THRESHOLD for e in provider_entries)
    low_n_footnote = ""
    if has_low_n:
        low_n_footnote = (
            '<p class="footnote">* Scores from small samples (N&nbsp;&lt;&nbsp;50) '
            "have higher variance and should be interpreted with caution.</p>"
        )

    # Partial SPS footnote
    partial_sps_footnote = ""
    if any_partial_sps:
        partial_sps_footnote = (
            '<p class="footnote"><strong>SPS*</strong> &mdash; Computed from available metrics only. '
            "Full SPS requires P_cond and P_sub from persona-conditioned runs.</p>"
        )

    # Near-baseline footnote
    has_near_bl = any(
        _is_near_baseline(e["composite_parity"], random_sps_val)
        and e["provider"] not in BASELINE_PROVIDERS
        for e in summary_entries
    )
    near_baseline_footnote = ""
    if has_near_bl:
        near_baseline_footnote = (
            '<p class="footnote" style="border-left-color:var(--gold)">'
            '<span style="color:var(--gold)">&#x26A0;</span> '
            "Highlighted rows are within 0.01 SPS of the random baseline.</p>"
        )

    # ── Multi-dataset tabs ──
    all_datasets = sorted(
        {e["dataset"] for e in summary_entries if e["dataset"] != "unknown"}
    )

    # Tab bar buttons
    tab_buttons = ['<button class="tab active" data-tab="overview">Overview</button>']
    for ds in all_datasets:
        label = DATASET_LABELS.get(ds, ds)
        tab_buttons.append(
            f'<button class="tab" data-tab="{escape(ds)}">{escape(label)}</button>'
        )
    tab_bar_html = (
        '<div class="tab-bar" id="dataset-tabs">' + "".join(tab_buttons) + "</div>"
    )

    # Overview panel: heatmap
    heatmap_rows = _build_heatmap_data(summary_entries, all_datasets, topic_scores)
    overview_panel = (
        '<div class="tab-panel active" id="panel-overview">\n'
        + _heatmap_html(heatmap_rows, all_datasets, partial_sps=any_partial_sps)
        + "\n</div>"
    )

    # Per-dataset panels
    dataset_panels = []
    for ds in all_datasets:
        panel_html = _dataset_table_html(
            summary_entries,
            ds,
            baseline_data,
            partial_sps=any_partial_sps,
            random_sps=random_sps_val,
        )
        dataset_panels.append(
            f'<div class="tab-panel" id="panel-{escape(ds)}">\n{panel_html}\n</div>'
        )
    dataset_panels_html = "\n".join(dataset_panels)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta property="og:title" content="SynthBench Leaderboard">
<meta property="og:description" content="Open benchmark measuring how well AI reproduces human survey responses. Ranked by SPS (SynthBench Parity Score).">
<meta property="og:type" content="website">
<meta property="og:url" content="https://dataviking-tech.github.io/synthbench/">
<meta property="og:image" content="https://dataviking-tech.github.io/synthbench/og-hero.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://dataviking-tech.github.io/synthbench/og-hero.png">
<meta name="twitter:title" content="SynthBench Leaderboard">
<meta name="twitter:description" content="Open benchmark measuring how well AI reproduces human survey responses.">
<title>SynthBench Leaderboard</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#0d1117;--surface:#161b22;--border:#30363d;
  --text:#e6edf3;--text-muted:#8b949e;--accent:#58a6ff;
  --gold:#f0c040;--silver:#c0c0c0;--bronze:#cd7f32;
  --green:#3fb950;--red:#f85149;
  --topic-0:#3fb950;--topic-1:#58a6ff;--topic-2:#f0c040;--topic-3:#f85149;--topic-4:#bc8cff;
}}
@media(prefers-color-scheme:light){{
  :root{{
    --bg:#ffffff;--surface:#f6f8fa;--border:#d0d7de;
    --text:#1f2328;--text-muted:#57606a;--accent:#0969da;
    --gold:#bf8700;--silver:#8b949e;--bronze:#9a6700;
    --green:#1a7f37;--red:#cf222e;
    --topic-0:#1a7f37;--topic-1:#0969da;--topic-2:#9a6700;--topic-3:#cf222e;--topic-4:#8250df;
  }}
}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;line-height:1.6;padding:0}}
a{{color:var(--accent);text-decoration:none}}
a:hover{{text-decoration:underline}}

.container{{max-width:1200px;margin:0 auto;padding:2rem 1.5rem}}

header{{text-align:center;padding:3rem 1rem 2rem}}
header h1{{font-size:2.2rem;font-weight:700;letter-spacing:-0.5px}}
header h1 span{{color:var(--accent)}}
header .tagline{{color:var(--text-muted);font-size:1.05rem;margin-top:0.5rem}}

.hero-headline{{font-size:2.5rem;font-weight:800;text-align:center;margin-bottom:1.5rem;color:var(--text);line-height:1.2}}
.hero-chart{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:1.5rem;margin-bottom:2rem}}
.hero-chart svg{{display:block;margin:0 auto}}

.about{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:1.5rem;margin-bottom:2rem;font-size:0.95rem;color:var(--text-muted)}}
.about p+p{{margin-top:0.75rem}}
.about strong{{color:var(--text)}}
.about code{{background:var(--bg);padding:0.15rem 0.4rem;border-radius:4px;font-size:0.88rem}}

.metric-legend{{border-left:3px solid var(--accent);margin-bottom:1.5rem}}

.section-title{{font-size:1.3rem;font-weight:600;margin:2.5rem 0 1rem;padding-bottom:0.5rem;border-bottom:1px solid var(--border)}}

.chart-section{{margin:2rem 0;padding:1.5rem;background-color:var(--bg);border:1px solid var(--border);border-radius:8px}}

.leaderboard-table{{width:100%;border-collapse:collapse;font-size:0.9rem}}
.leaderboard-table thead{{position:sticky;top:0;z-index:10}}
.leaderboard-table th{{
  background:var(--surface);color:var(--text-muted);font-weight:600;
  text-transform:uppercase;font-size:0.75rem;letter-spacing:0.05em;
  padding:0.75rem 1rem;text-align:left;border-bottom:2px solid var(--border);
}}
.leaderboard-table th.num{{text-align:right}}
.leaderboard-table th:nth-child(5),.leaderboard-table td:nth-child(5){{border-left:1px solid var(--border)}}
.leaderboard-table th.sortable{{cursor:pointer;user-select:none}}
.leaderboard-table th.sortable:hover{{color:var(--accent)}}
.leaderboard-table th .sort-arrow{{font-size:0.65rem;margin-left:0.25rem;opacity:0.5}}
.leaderboard-table td{{padding:0.65rem 1rem;border-bottom:1px solid var(--border)}}
.leaderboard-table td.num{{text-align:right;font-variant-numeric:tabular-nums}}
.leaderboard-table tbody tr:hover{{background:rgba(88,166,255,0.06)}}

.rank{{font-weight:700;width:3.5rem}}
.medal{{font-size:1.1rem;margin-right:0.25rem}}
.provider-name{{font-weight:600;color:var(--text)}}
.model-name{{color:var(--text-muted);font-size:0.85rem}}
.composite{{font-weight:700;color:var(--green);font-size:1rem}}

.chevron{{cursor:pointer;font-size:0.7rem;margin-right:0.4rem;color:var(--accent);transition:transform 0.2s}}
.chevron.open{{transform:rotate(90deg)}}

.detail-row{{background:var(--surface)}}
.detail-cell{{padding:0.75rem 1.5rem !important}}
.detail-content{{display:flex;gap:2rem;flex-wrap:wrap;font-size:0.85rem;color:var(--text-muted)}}
.detail-section{{min-width:200px}}
.detail-item{{margin:0.25rem 0}}

.section-divider td{{padding:0.5rem 1rem !important;background:var(--surface);border-bottom:2px solid var(--border);border-top:2px solid var(--border)}}
.section-label{{font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--text-muted)}}
.baseline-row td{{color:var(--text-muted)}}
.baseline-row .composite{{color:var(--text-muted);font-weight:400}}
.baseline-name{{font-weight:400 !important;color:var(--text-muted) !important}}
.product-row td{{color:var(--text)}}
.product-row .composite{{font-weight:600}}

.low-n td{{opacity:0.7}}
.low-n-marker{{color:var(--red);font-weight:700;margin-left:1px}}

.near-baseline td{{color:var(--gold)}}
.near-baseline .composite{{color:var(--gold) !important;font-weight:600}}
.near-baseline .provider-name{{color:var(--gold) !important}}

.chart-text{{fill:var(--text)}}
.chart-muted{{fill:var(--text-muted);stroke:var(--text-muted)}}
.chart-accent{{fill:var(--accent)}}

.footnote{{font-size:0.85rem;color:var(--text-muted);margin-top:0.75rem;padding-left:0.5rem;border-left:2px solid var(--border)}}

.tab-bar{{display:flex;gap:0;border-bottom:2px solid var(--border);margin-bottom:1.5rem;overflow-x:auto}}
.tab{{padding:0.6rem 1.2rem;border:none;background:none;color:var(--text-muted);font-size:0.9rem;font-weight:600;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;transition:color 0.2s,border-color 0.2s;white-space:nowrap}}
.tab:hover{{color:var(--text)}}
.tab.active{{color:var(--accent);border-bottom-color:var(--accent)}}
.tab-panel{{display:none}}
.tab-panel.active{{display:block}}

.heatmap-table .heatmap-cell{{font-variant-numeric:tabular-nums;border-radius:4px;padding:0.5rem 0.8rem}}
.dataset-badge{{font-size:0.8rem;font-weight:600}}
.fitness-note{{font-size:0.82rem;color:var(--text-muted);font-style:italic;max-width:220px}}

.secondary-panel{{margin-top:2.5rem}}
details.collapsible{{background:var(--surface);border:1px solid var(--border);border-radius:8px;margin-top:1.5rem;overflow:hidden}}
details.collapsible>summary{{padding:1rem 1.5rem;cursor:pointer;font-size:1.1rem;font-weight:600;color:var(--text);list-style:none;display:flex;align-items:center;gap:0.5rem;user-select:none}}
details.collapsible>summary::-webkit-details-marker{{display:none}}
details.collapsible>summary::before{{content:'\\25B8';font-size:0.75rem;color:var(--accent);transition:transform 0.2s}}
details.collapsible[open]>summary::before{{transform:rotate(90deg)}}
details.collapsible .collapsible-body{{padding:0 1.5rem 1.5rem}}
details.collapsible .chart-section{{margin:0;border:none;border-radius:0;background:transparent;padding:0}}
details.collapsible .leaderboard-table{{font-size:0.85rem}}
details.collapsible .about{{margin-bottom:0.75rem}}
.explanation-section{{border-top:2px solid var(--accent);margin-top:3rem;padding-top:0.5rem}}

.transparency{{margin-top:1rem;font-size:0.85rem;color:var(--text-muted);font-style:italic}}

.bibtex{{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1rem;font-family:monospace;font-size:0.8rem;white-space:pre-wrap;color:var(--text-muted);margin-top:1rem;overflow-x:auto}}

footer{{text-align:center;padding:2rem 1rem;color:var(--text-muted);font-size:0.85rem;border-top:1px solid var(--border);margin-top:3rem}}
footer a{{color:var(--accent)}}

.links{{display:flex;gap:1.5rem;justify-content:center;margin-top:1rem;flex-wrap:wrap}}
.links a{{
  display:inline-flex;align-items:center;gap:0.4rem;
  padding:0.4rem 1rem;border:1px solid var(--border);border-radius:6px;
  font-size:0.85rem;color:var(--text-muted);transition:border-color 0.2s;
}}
.links a:hover{{border-color:var(--accent);color:var(--accent);text-decoration:none}}

@media(max-width:700px){{
  .container{{padding:1rem 0.75rem}}
  header h1{{font-size:1.6rem}}
  .hero-headline{{font-size:1.5rem}}
  .mob-hide{{display:none}}
  .leaderboard-table{{font-size:0.8rem}}
  .leaderboard-table th,.leaderboard-table td{{padding:0.5rem 0.6rem}}
  .tab-panel,.collapsible-body{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
  .hero-chart{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
  .hero-chart svg{{min-width:600px}}
  .chart-section{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
  .chart-section svg{{min-width:480px;height:auto}}
  .chevron{{display:inline-flex;align-items:center;justify-content:center;min-width:44px;min-height:44px;font-size:1rem}}
  .tab{{padding:0.75rem 1rem;min-height:44px}}
  .detail-content{{flex-direction:column;gap:0.5rem}}
  details.collapsible>summary{{padding:0.75rem 1rem;font-size:1rem}}
}}
</style>
</head>
<body>

<header>
  <h1><span>Synth</span>Bench</h1>
  <p class="tagline">Open benchmark for synthetic survey respondent quality</p>
  <div class="links">
    <a href="https://github.com/DataViking-Tech/synthbench">GitHub</a>
    <a href="https://github.com/DataViking-Tech/synthbench/blob/main/METHODOLOGY.md">Methodology</a>
    <a href="https://github.com/DataViking-Tech/synthbench#submit-results">Submit Results</a>
  </div>
</header>

<div class="container">
{hero_headline}
  <div class="hero-chart">
{hero_chart}
  </div>

  <div class="about">
    <p>SynthBench measures how well synthetic respondent systems reproduce real human survey response distributions.
       Scores are computed against ground-truth data from multiple datasets including
       <strong>OpinionsQA</strong> (Santurkar et al., ICML 2023),
       <strong>GlobalOpinionQA</strong>, and <strong>SubPOP</strong>.</p>
    <p class="transparency">SynthBench is maintained by DataViking-Tech, which also develops SynthPanel.
       All results use identical evaluation methodology.</p>
  </div>

{metric_legend}

{tab_bar_html}
{overview_panel}
{dataset_panels_html}
  {synthpanel_footnote}
  {low_n_footnote}
  {partial_sps_footnote}
  {near_baseline_footnote}

  <details class="collapsible">
    <summary>Full Leaderboard (All Datasets)</summary>
    <div class="collapsible-body">
  <table class="leaderboard-table" id="leaderboard">
    <thead>
      <tr>
        <th class="rank">Rank</th>
        <th class="sortable" data-sort="provider">Provider</th>
        <th class="mob-hide">Model</th>
        <th class="mob-hide">Dataset</th>
        <th class="num sortable" data-sort="n">N</th>
        <th class="num sortable" data-sort="sps" title="SynthBench Parity Score: overall fidelity (0=random, 1=human-identical)">{"SPS*" if any_partial_sps else "SPS"} <span class="sort-arrow">&#x25BC;</span></th>
{baseline_th}{topic_th}{p_refuse_th}        <th class="num sortable" data-sort="jsd" title="Mean Jensen-Shannon divergence (lower = closer to human distributions)">JSD</th>
        <th class="num sortable" data-sort="tau" title="Mean Kendall&rsquo;s tau-b rank correlation (higher = better rank agreement)">Tau</th>
        <th class="mob-hide">Date</th>
      </tr>
    </thead>
    <tbody id="leaderboard-body">
{tbody}
    </tbody>
  </table>
    </div>
  </details>

  <div class="secondary-panel">
    <details class="collapsible">
      <summary>SPS by Model</summary>
      <div class="collapsible-body">
        <div class="chart-section">
{dot_plot}
        </div>
      </div>
    </details>

    <details class="collapsible">
      <summary>Per-Metric Breakdown</summary>
      <div class="collapsible-body">
        <div class="about">
          <p>Each model&rsquo;s P_dist, P_rank, and P_refuse on a shared 0&ndash;1 axis. Whiskers show bootstrap 95% CI where available.</p>
        </div>
        <div class="chart-section">
{per_metric_dot}
        </div>
      </div>
    </details>

    <details class="collapsible">
      <summary>SPS by Topic</summary>
      <div class="collapsible-body">
        <div class="about">
          <p>Topic-level SPS for models evaluated on consumer, neutral, and political question subsets.</p>
        </div>
        <div class="chart-section">
{topic_bar}
        </div>
      </div>
    </details>

{convergence_html}
  </div>

  <div class="explanation-section">
{explanations}
  </div>
</div>

<footer>
  <p>Generated by <a href="https://github.com/DataViking-Tech/synthbench">SynthBench</a> v{escape(version)}</p>
  <p>Last updated: {today}</p>
  <details style="margin-top:1rem;text-align:left;max-width:600px;margin-left:auto;margin-right:auto">
    <summary style="cursor:pointer;color:var(--accent)">Cite SynthBench</summary>
    <pre style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1rem;margin-top:0.5rem;font-size:0.8rem;overflow-x:auto;text-align:left">@misc{{synthbench2026,
  title={{SynthBench: Open Benchmark for Synthetic Survey Respondent Quality}},
  author={{DataViking-Tech}},
  year={{2026}},
  url={{https://github.com/DataViking-Tech/synthbench}},
  note={{SPS (SynthBench Parity Score) evaluation framework}}
}}</pre>
  </details>
</footer>

<script>
document.addEventListener('DOMContentLoaded',function(){{
  // Tab switching
  document.querySelectorAll('.tab').forEach(function(btn){{
    btn.addEventListener('click',function(){{
      var tab=this.dataset.tab;
      document.querySelectorAll('.tab').forEach(function(t){{t.classList.remove('active')}});
      document.querySelectorAll('.tab-panel').forEach(function(p){{p.classList.remove('active')}});
      this.classList.add('active');
      var panel=document.getElementById('panel-'+tab);
      if(panel)panel.classList.add('active');
    }});
  }});

  // Expandable detail rows via chevron
  document.querySelectorAll('.chevron').forEach(function(el){{
    el.addEventListener('click',function(){{
      var key=this.dataset.provider;
      var rows=document.querySelectorAll('.detail-row[data-provider="'+key+'"]');
      var showing=rows[0]&&rows[0].style.display!=='none';
      rows.forEach(function(r){{r.style.display=showing?'none':'table-row'}});
      this.classList.toggle('open',!showing);
    }});
  }});

  // Column sorting
  var table=document.getElementById('leaderboard');
  var tbody=document.getElementById('leaderboard-body');
  var sortDir={{}};
  document.querySelectorAll('.sortable').forEach(function(th){{
    th.addEventListener('click',function(){{
      var col=this.dataset.sort;
      var dir=sortDir[col]==='asc'?'desc':'asc';
      sortDir[col]=dir;
      // Update arrows
      document.querySelectorAll('.sort-arrow').forEach(function(a){{a.remove()}});
      var arrow=document.createElement('span');
      arrow.className='sort-arrow';
      arrow.innerHTML=dir==='asc'?'&#x25B2;':'&#x25BC;';
      this.appendChild(arrow);
      // Collect sortable rows (not section dividers, detail rows, baselines, or products)
      var rows=Array.from(tbody.querySelectorAll('tr:not(.detail-row):not(.section-divider):not(.baseline-row):not(.product-row)'));
      var detailRows=Array.from(tbody.querySelectorAll('.detail-row'));
      var dividers=Array.from(tbody.querySelectorAll('.section-divider'));
      var productRows=Array.from(tbody.querySelectorAll('.product-row'));
      var baselineRows=Array.from(tbody.querySelectorAll('.baseline-row'));
      rows.sort(function(a,b){{
        var va,vb;
        if(col==='provider'){{
          va=a.querySelector('.provider-name')?.textContent||'';
          vb=b.querySelector('.provider-name')?.textContent||'';
          return dir==='asc'?va.localeCompare(vb):vb.localeCompare(va);
        }}
        va=parseFloat(a.dataset[col])||0;
        vb=parseFloat(b.dataset[col])||0;
        return dir==='asc'?va-vb:vb-va;
      }});
      // Re-insert: Raw LLMs divider, sorted rows+details, Products divider+rows, Baselines divider+rows
      if(dividers[0])tbody.appendChild(dividers[0]);
      rows.forEach(function(r){{
        tbody.appendChild(r);
        var key=r.querySelector('.chevron')?.dataset.provider;
        if(key){{
          detailRows.filter(function(d){{return d.dataset.provider===key}}).forEach(function(d){{tbody.appendChild(d)}});
        }}
      }});
      if(dividers[1])tbody.appendChild(dividers[1]);
      productRows.forEach(function(r){{tbody.appendChild(r)}});
      if(dividers[2])tbody.appendChild(dividers[2]);
      baselineRows.forEach(function(r){{tbody.appendChild(r)}});
      // Re-number ranks (only raw LLM rows)
      var rank=1;
      tbody.querySelectorAll('tr:not(.detail-row):not(.section-divider):not(.baseline-row):not(.product-row)').forEach(function(r){{
        var cell=r.querySelector('.rank');
        if(cell){{
          var medal='';
          if(rank===1)medal='<span class="medal">&#x1f947;</span>';
          else if(rank===2)medal='<span class="medal">&#x1f948;</span>';
          else if(rank===3)medal='<span class="medal">&#x1f949;</span>';
          var chevron=cell.querySelector('.chevron');
          var chevronHtml=chevron?chevron.outerHTML:'';
          cell.innerHTML=chevronHtml+medal+rank;
          rank++;
        }}
      }});
    }});
  }});
}});
</script>

</body>
</html>"""


def publish_leaderboard(
    results_dir: Path, output_dir: Path, version: str = "0.1.0"
) -> Path:
    """Load all result JSONs from results_dir and write docs/index.html.

    Returns the path to the generated index.html.
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

    output_dir.mkdir(parents=True, exist_ok=True)
    html = generate_html(results, version=version)
    out_path = output_dir / "index.html"
    out_path.write_text(html)
    return out_path


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
