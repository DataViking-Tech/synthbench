"""Generate a static HTML leaderboard page from SynthBench result JSON files."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from html import escape

BASELINE_PROVIDERS = {"random-baseline", "majority-baseline"}
SYNTHPANEL_PREFIX = "synthpanel/"
N_THRESHOLD = 50


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
    """De-duplicate results: keep the run with the most n_evaluated per provider+dataset."""
    best: dict[tuple[str, str], dict] = {}
    for r in results:
        cfg = r.get("config", {})
        provider = cfg.get("provider", "unknown")
        dataset = cfg.get("dataset", "unknown")
        n_eval = cfg.get("n_evaluated", 0)
        key = (provider, dataset)
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
    """Annotate synthpanel providers with adapter test context."""
    if _is_synthpanel(provider):
        return provider + " (adapter test, n=20)"
    return provider


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
        f'stroke="#8b949e" stroke-width="1.5"/>'
        f'<line x1="{x_low:.1f}" y1="{y_mid - 3}" x2="{x_low:.1f}" y2="{y_mid + 3}" '
        f'stroke="#8b949e" stroke-width="1"/>'
        f'<line x1="{x_high:.1f}" y1="{y_mid - 3}" x2="{x_high:.1f}" y2="{y_mid + 3}" '
        f'stroke="#8b949e" stroke-width="1"/>'
        f'<circle cx="{x_point:.1f}" cy="{y_mid}" r="3" fill="#58a6ff"/>'
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
            f'rx="1" fill="{color}" opacity="0.85"/>'
        )
    if not parts:
        return "&mdash;"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'style="vertical-align:middle">' + "".join(parts) + "</svg>"
    )


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
        color = "#f85149" if "random" in name else "#f0c040"
        label = "Random" if "random" in name else "Majority"
        ref_lines.append(
            f'<line x1="{x:.1f}" y1="30" x2="{x:.1f}" y2="{h - 15}" '
            f'stroke="{color}" stroke-width="1" stroke-dasharray="4,3" opacity="0.6"/>'
            f'<text x="{x:.1f}" y="24" text-anchor="middle" font-size="9" '
            f'fill="{color}" opacity="0.8">{label}</text>'
        )

    dots = []
    for i, r in enumerate(ranked):
        cfg = r.get("config", {})
        provider = cfg.get("provider", "unknown")
        cp = r.get("aggregate", {}).get("composite_parity", 0)
        is_baseline = provider in BASELINE_PROVIDERS

        y = i * (row_h + gap) + 40
        x_dot = label_w + cp * chart_w
        color = "#8b949e" if is_baseline else "#58a6ff"
        text_color = "#8b949e" if is_baseline else "#e6edf3"

        display_name = _display_provider_name(provider)
        dots.append(
            f'<text x="{label_w - 8}" y="{y + row_h * 0.6}" '
            f'text-anchor="end" font-size="11" fill="{text_color}">'
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
                f'stroke="{color}" stroke-width="2" opacity="0.5"/>'
                f'<line x1="{x_lo:.1f}" y1="{y + row_h * 0.3}" '
                f'x2="{x_lo:.1f}" y2="{y + row_h * 0.7}" '
                f'stroke="{color}" stroke-width="1" opacity="0.5"/>'
                f'<line x1="{x_hi:.1f}" y1="{y + row_h * 0.3}" '
                f'x2="{x_hi:.1f}" y2="{y + row_h * 0.7}" '
                f'stroke="{color}" stroke-width="1" opacity="0.5"/>'
            )

        dots.append(
            f'<circle cx="{x_dot:.1f}" cy="{y + row_h * 0.5}" r="4" fill="{color}"/>'
        )
        dots.append(
            f'<text x="{x_dot + 8:.1f}" y="{y + row_h * 0.6}" '
            f'font-size="10" fill="{text_color}">{cp:.4f}</text>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="100%" style="font-family:sans-serif;max-width:{w}px">\n'
        f'<text x="{w / 2}" y="18" text-anchor="middle" font-size="14" '
        f'fill="#e6edf3" font-weight="600">SPS by Model</text>\n'
        + "\n".join(ref_lines)
        + "\n"
        + "\n".join(dots)
        + "\n</svg>"
    )


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


def _metric_legend_html() -> str:
    """Return a compact metric callout card to appear ABOVE the main table."""
    return """
  <div class="about metric-legend">
    <p><strong>SPS</strong> (SynthBench Parity Score) measures how well AI reproduces human survey responses.
       Higher is better (0&nbsp;=&nbsp;random, 1&nbsp;=&nbsp;human-identical).
       Scores below show SPS and component metrics P_dist, P_rank, P_refuse.</p>
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
    topic_colors = ["#3fb950", "#58a6ff", "#f0c040", "#f85149", "#bc8cff"]

    deduped = _dedup_results(overall_results if overall_results else results)
    ranked = sorted(
        deduped,
        key=lambda r: r.get("aggregate", {}).get("composite_parity", 0),
        reverse=True,
    )

    _models, baselines = _split_baselines(ranked)

    # Group detail entries by provider+dataset for expandable sub-rows
    detail_by_key: dict[tuple[str, str], list[dict]] = {}
    for d in detail_entries:
        key = (d["provider"], d["dataset"])
        detail_by_key.setdefault(key, []).append(d)

    has_baselines = bool(baseline_data)

    # Separate summary_entries into providers and baselines
    provider_entries = []
    baseline_entries = []
    for e in summary_entries:
        if e["provider"] in BASELINE_PROVIDERS:
            baseline_entries.append(e)
        else:
            provider_entries.append(e)

    # Build provider table rows
    rows_html = []
    medals = {1: "&#x1f947;", 2: "&#x1f948;", 3: "&#x1f949;"}
    for rank, e in enumerate(provider_entries, 1):
        provider_raw = e["provider"]
        if "/" in provider_raw:
            provider_name, model_name = provider_raw.split("/", 1)
        else:
            provider_name = provider_raw
            model_name = None

        # #1 synthpanel label
        if _is_synthpanel(provider_raw):
            provider_name = provider_name + " (adapter test)"
            if model_name:
                model_name = model_name + " n=20"

        medal = medals.get(rank, "")
        medal_html = f'<span class="medal">{medal}</span>' if medal else ""
        model_display = escape(model_name) if model_name else "&mdash;"

        n_eval = e.get("n", 0)

        # #6 N-threshold: muted styling for n < 50
        low_n = n_eval < N_THRESHOLD
        low_n_class = " low-n" if low_n else ""
        n_display = (
            f'{n_eval}<span class="low-n-marker">*</span>' if low_n else str(n_eval)
        )

        # Composite score + CI whisker (#3)
        cp = e["composite_parity"]
        ci_svg = ""
        # Find the result dict for this entry to get CI data
        for r in ranked:
            r_cfg = r.get("config", {})
            if (
                r_cfg.get("provider") == provider_raw
                and r_cfg.get("dataset") == e["dataset"]
            ):
                ci = r.get("aggregate", {}).get("per_metric_ci", {}).get("sps")
                if ci and len(ci) == 2:
                    ci_svg = _ci_whisker_svg(ci[0], ci[1], cp)
                break

        topic_cells = ""
        if topics_present:
            provider_topics = e.get("topic_scores", {})
            topic_cell_svg = _topic_bars_svg(
                provider_topics, topics_present, topic_colors
            )
            topic_cells = f'        <td class="num">{topic_cell_svg}</td>\n'

        baseline_cells = ""
        if has_baselines:
            vs_r = e.get("vs_random")
            vs_m = e.get("vs_majority")
            if vs_r:
                delta_val = float(vs_r)
                color = "var(--green)" if delta_val > 0 else "var(--red)"
                baseline_cells += (
                    f'        <td class="num" style="color:{color}">{vs_r}</td>\n'
                )
            else:
                baseline_cells += '        <td class="num">&mdash;</td>\n'
            if vs_m:
                delta_val = float(vs_m)
                color = "var(--green)" if delta_val > 0 else "var(--red)"
                baseline_cells += (
                    f'        <td class="num" style="color:{color}">{vs_m}</td>\n'
                )
            else:
                baseline_cells += '        <td class="num">&mdash;</td>\n'

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

        rows_html.append(
            f'      <tr class="{low_n_class}" data-sps="{cp:.4f}" data-n="{n_eval}" '
            f'data-jsd="{e["mean_jsd"]:.4f}" data-tau="{e["mean_kendall_tau"]:.4f}">\n'
            f'        <td class="rank num">{toggle_html}{medal_html}{rank}</td>\n'
            f'        <td class="provider-name">{escape(provider_name)}</td>\n'
            f'        <td><span class="model-name">{model_display}</span></td>\n'
            f"        <td>{escape(e['dataset'])}</td>\n"
            f'        <td class="num">{n_display}</td>\n'
            f'        <td class="num composite">{cp:.4f}{ci_svg}</td>\n'
            f"{baseline_cells}"
            f"{topic_cells}"
            f'        <td class="num">{e["mean_jsd"]:.4f}</td>\n'
            f'        <td class="num">{e["mean_kendall_tau"]:.4f}</td>\n'
            f"        <td>{e['date']}</td>\n"
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
                        f'<polyline points="{polyline}" fill="none" stroke="#58a6ff" stroke-width="1.5"/>'
                        f"</svg>"
                    )

            n_cols = 9  # rank + provider + model + dataset + N + SPS + JSD + tau + date
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

    # #4 Baseline divider + baseline rows
    if baseline_entries:
        n_cols = 9
        if has_baselines:
            n_cols += 2
        if topics_present:
            n_cols += 1
        rows_html.append(
            f'      <tr class="baseline-divider"><td colspan="{n_cols}"></td></tr>'
        )
        for e in baseline_entries:
            provider_raw = e["provider"]
            cp = e["composite_parity"]
            rows_html.append(
                f'      <tr class="baseline-row" data-sps="{cp:.4f}" data-n="{e.get("n", 0)}" '
                f'data-jsd="{e["mean_jsd"]:.4f}" data-tau="{e["mean_kendall_tau"]:.4f}">\n'
                f'        <td class="rank num"></td>\n'
                f'        <td class="provider-name baseline-name">{escape(provider_raw)}</td>\n'
                f"        <td></td>\n"
                f"        <td>{escape(e['dataset'])}</td>\n"
                f'        <td class="num">{e.get("n", 0)}</td>\n'
                f'        <td class="num composite">{cp:.4f}</td>\n'
                + (
                    '        <td class="num"></td>\n        <td class="num"></td>\n'
                    if has_baselines
                    else ""
                )
                + ('        <td class="num"></td>\n' if topics_present else "")
                + f'        <td class="num">{e["mean_jsd"]:.4f}</td>\n'
                f'        <td class="num">{e["mean_kendall_tau"]:.4f}</td>\n'
                f"        <td>{e['date']}</td>\n"
                f"      </tr>"
            )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tbody = "\n".join(rows_html)

    # #7 Single "Topics" column header (replaces per-topic columns)
    topic_th = ""
    if topics_present:
        topic_th = '        <th class="num">Topics</th>\n'

    # Baseline column headers
    baseline_th = ""
    if has_baselines:
        baseline_th = '        <th class="num sortable" data-sort="vs-random">vs Random</th>\n        <th class="num sortable" data-sort="vs-majority">vs Majority</th>\n'

    # Generate chart section: dot-plot instead of bar charts (#9)
    dot_plot = _dot_plot_svg(ranked, baselines)
    baseline_table = _baseline_delta_html(ranked, baselines)
    explanations = _metric_explanations_html()
    metric_legend = _metric_legend_html()

    # Convergence section
    convergence_html = ""
    if convergence_data:
        conv_rows = []
        for provider, sweeps in sorted(convergence_data.items()):
            for sweep in sweeps:
                samples = sweep["samples"]
                runs = sweep["runs"]
                mean_cp = sum(runs) / len(runs)
                display_name = _display_provider_name(provider)
                conv_rows.append(
                    f"      <tr>\n"
                    f'        <td class="provider-name">{escape(display_name)}</td>\n'
                    f'        <td class="num">{samples}</td>\n'
                    f'        <td class="num">{len(runs)}</td>\n'
                    f'        <td class="num composite">{mean_cp:.4f}</td>\n'
                    f'        <td class="num">{min(runs):.4f}</td>\n'
                    f'        <td class="num">{max(runs):.4f}</td>\n'
                    f"      </tr>"
                )
        conv_tbody = "\n".join(conv_rows)
        convergence_html = f"""
  <h2 class="section-title">Convergence Data</h2>
  <div class="about" style="margin-bottom:1rem">
    <p>How scores change as sample count increases. Providers with runs at 2+ different sample counts are shown.</p>
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
{conv_tbody}
    </tbody>
  </table>"""

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

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SynthBench Leaderboard</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#0d1117;--surface:#161b22;--border:#30363d;
  --text:#e6edf3;--text-muted:#8b949e;--accent:#58a6ff;
  --gold:#f0c040;--silver:#c0c0c0;--bronze:#cd7f32;
  --green:#3fb950;--red:#f85149;
}}
@media(prefers-color-scheme:light){{
  :root{{
    --bg:#ffffff;--surface:#f6f8fa;--border:#d0d7de;
    --text:#1f2328;--text-muted:#656d76;--accent:#0969da;
    --gold:#bf8700;--silver:#8b949e;--bronze:#9a6700;
    --green:#1a7f37;--red:#cf222e;
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

.about{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:1.5rem;margin-bottom:2rem;font-size:0.95rem;color:var(--text-muted)}}
.about p+p{{margin-top:0.75rem}}
.about strong{{color:var(--text)}}
.about code{{background:var(--bg);padding:0.15rem 0.4rem;border-radius:4px;font-size:0.88rem}}

.metric-legend{{border-left:3px solid var(--accent);margin-bottom:1.5rem}}

.section-title{{font-size:1.3rem;font-weight:600;margin:2.5rem 0 1rem;padding-bottom:0.5rem;border-bottom:1px solid var(--border)}}

.chart-section{{margin:2rem 0;padding:1.5rem;background:var(--surface);border:1px solid var(--border);border-radius:8px}}

.leaderboard-table{{width:100%;border-collapse:collapse;font-size:0.9rem}}
.leaderboard-table thead{{position:sticky;top:0;z-index:10}}
.leaderboard-table th{{
  background:var(--surface);color:var(--text-muted);font-weight:600;
  text-transform:uppercase;font-size:0.75rem;letter-spacing:0.05em;
  padding:0.75rem 1rem;text-align:left;border-bottom:2px solid var(--border);
}}
.leaderboard-table th.num{{text-align:right}}
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

.baseline-divider td{{height:2px;padding:0 !important;background:var(--border)}}
.baseline-row td{{color:var(--text-muted)}}
.baseline-row .composite{{color:var(--text-muted);font-weight:400}}
.baseline-name{{font-weight:400 !important;color:var(--text-muted) !important}}

.low-n td{{opacity:0.7}}
.low-n-marker{{color:var(--red);font-weight:700;margin-left:1px}}

.footnote{{font-size:0.85rem;color:var(--text-muted);margin-top:0.75rem;padding-left:0.5rem;border-left:2px solid var(--border)}}

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
  .leaderboard-table{{font-size:0.8rem}}
  .leaderboard-table th,.leaderboard-table td{{padding:0.5rem 0.6rem}}
  .detail-content{{flex-direction:column;gap:0.5rem}}
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
  <div class="about">
    <p>SynthBench measures how well synthetic respondent systems reproduce real human survey response distributions.
       Scores are computed against ground-truth data from <strong>OpinionsQA</strong> (Santurkar et al., ICML 2023) &mdash;
       1,498 questions from the Pew American Trends Panel.</p>
    <p class="transparency">SynthBench is maintained by DataViking-Tech, which also develops SynthPanel.
       All results use identical evaluation methodology.</p>
  </div>

{metric_legend}

  <table class="leaderboard-table" id="leaderboard">
    <thead>
      <tr>
        <th class="rank">Rank</th>
        <th class="sortable" data-sort="provider">Provider</th>
        <th>Model</th>
        <th>Dataset</th>
        <th class="num sortable" data-sort="n">N</th>
        <th class="num sortable" data-sort="sps">SPS <span class="sort-arrow">&#x25BC;</span></th>
{baseline_th}{topic_th}        <th class="num sortable" data-sort="jsd">JSD</th>
        <th class="num sortable" data-sort="tau">Tau</th>
        <th>Date</th>
      </tr>
    </thead>
    <tbody id="leaderboard-body">
{tbody}
    </tbody>
  </table>
  {synthpanel_footnote}
  {low_n_footnote}

  <div class="chart-section">
{dot_plot}
  </div>

{baseline_table}

{convergence_html}

{explanations}
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
      // Collect provider rows (not baseline or detail rows)
      var rows=Array.from(tbody.querySelectorAll('tr:not(.detail-row):not(.baseline-divider):not(.baseline-row)'));
      var detailRows=Array.from(tbody.querySelectorAll('.detail-row'));
      var divider=tbody.querySelector('.baseline-divider');
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
      // Re-insert sorted rows, then details, divider, baselines
      rows.forEach(function(r){{
        tbody.appendChild(r);
        var key=r.querySelector('.chevron')?.dataset.provider;
        if(key){{
          detailRows.filter(function(d){{return d.dataset.provider===key}}).forEach(function(d){{tbody.appendChild(d)}});
        }}
      }});
      if(divider)tbody.appendChild(divider);
      baselineRows.forEach(function(r){{tbody.appendChild(r)}});
      // Re-number ranks
      var rank=1;
      tbody.querySelectorAll('tr:not(.detail-row):not(.baseline-divider):not(.baseline-row)').forEach(function(r){{
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
