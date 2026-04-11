"""Generate a static HTML leaderboard page from SynthBench result JSON files."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from html import escape

BASELINE_PROVIDERS = {"random-baseline", "majority-baseline"}


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


def _svg_sps_bars(ranked: list[dict]) -> str:
    """Generate an inline SVG horizontal bar chart of Composite Parity scores."""
    n = len(ranked)
    if n == 0:
        return ""

    bar_h = 28
    gap = 6
    label_w = 220
    chart_w = 400
    w = label_w + chart_w + 60
    h = n * (bar_h + gap) + 40

    bars = []
    for i, r in enumerate(ranked):
        cfg = r.get("config", {})
        provider = cfg.get("provider", "unknown")
        cp = r.get("aggregate", {}).get("composite_parity", 0)
        is_baseline = provider in BASELINE_PROVIDERS

        y = i * (bar_h + gap) + 30
        bar_width = cp * chart_w
        color = "#8b949e" if is_baseline else "#58a6ff"

        bars.append(
            f'<text x="{label_w - 8}" y="{y + bar_h * 0.7}" '
            f'text-anchor="end" font-size="12" fill="#e6edf3">'
            f"{escape(provider)}</text>"
        )
        bars.append(
            f'<rect x="{label_w}" y="{y}" width="{bar_width:.1f}" '
            f'height="{bar_h}" rx="3" fill="{color}" opacity="0.85" />'
        )
        bars.append(
            f'<text x="{label_w + bar_width + 6}" y="{y + bar_h * 0.7}" '
            f'font-size="11" fill="#e6edf3">{cp:.4f}</text>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="100%" style="font-family:sans-serif;max-width:{w}px">\n'
        f'<text x="{w / 2}" y="18" text-anchor="middle" font-size="14" '
        f'fill="#e6edf3" font-weight="600">Composite Parity by Model</text>\n'
        + "\n".join(bars)
        + "\n</svg>"
    )


def _svg_metric_bars(ranked: list[dict]) -> str:
    """Generate inline SVG grouped bars for P_dist, P_rank per model."""
    models = [
        r
        for r in ranked
        if r.get("config", {}).get("provider", "") not in BASELINE_PROVIDERS
    ]
    if not models:
        return ""

    n = len(models)
    group_h = 50
    gap = 12
    label_w = 220
    chart_w = 400
    w = label_w + chart_w + 60
    h = n * (group_h + gap) + 60

    colors = {"P_dist": "#3fb950", "P_rank": "#58a6ff"}
    bar_h = 20

    bars = []
    for i, r in enumerate(models):
        cfg = r.get("config", {})
        provider = cfg.get("provider", "unknown")
        m = _extract_metrics(r)
        y_base = i * (group_h + gap) + 40

        bars.append(
            f'<text x="{label_w - 8}" y="{y_base + group_h * 0.5}" '
            f'text-anchor="end" font-size="12" fill="#e6edf3">'
            f"{escape(provider)}</text>"
        )

        for j, (key, label) in enumerate([("p_dist", "P_dist"), ("p_rank", "P_rank")]):
            val = m[key]
            y = y_base + j * (bar_h + 4)
            bw = val * chart_w
            bars.append(
                f'<rect x="{label_w}" y="{y}" width="{bw:.1f}" '
                f'height="{bar_h}" rx="2" fill="{colors[label]}" opacity="0.8" />'
            )
            bars.append(
                f'<text x="{label_w + bw + 5}" y="{y + bar_h * 0.72}" '
                f'font-size="10" fill="#e6edf3">{label} {val:.4f}</text>'
            )

    # Legend
    legend_y = h - 12
    bars.append(
        f'<rect x="{label_w}" y="{legend_y}" width="12" height="12" fill="#3fb950" />'
        f'<text x="{label_w + 16}" y="{legend_y + 10}" font-size="10" fill="#8b949e">'
        f"P_dist (1 - JSD)</text>"
    )
    bars.append(
        f'<rect x="{label_w + 140}" y="{legend_y}" width="12" height="12" fill="#58a6ff" />'
        f'<text x="{label_w + 156}" y="{legend_y + 10}" font-size="10" fill="#8b949e">'
        f"P_rank ((1+tau)/2)</text>"
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="100%" style="font-family:sans-serif;max-width:{w}px">\n'
        f'<text x="{w / 2}" y="22" text-anchor="middle" font-size="14" '
        f'fill="#e6edf3" font-weight="600">Per-Metric Breakdown</text>\n'
        + "\n".join(bars)
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

        cells = f'<td class="provider-name">{escape(provider)}</td>'
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
        <th class="num">Composite</th>
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

    # Build table rows
    rows_html = []
    medals = {1: "&#x1f947;", 2: "&#x1f948;", 3: "&#x1f949;"}
    for rank, e in enumerate(summary_entries, 1):
        provider_raw = e["provider"]
        if "/" in provider_raw:
            provider_name, model_name = provider_raw.split("/", 1)
        else:
            provider_name = provider_raw
            model_name = None

        medal = medals.get(rank, "")
        medal_html = f'<span class="medal">{medal}</span>' if medal else ""
        model_display = escape(model_name) if model_name else "&mdash;"

        n_runs = e.get("n_runs", 1)
        toggle = (
            f'<span class="toggle" data-provider="{escape(provider_raw)}_{escape(e["dataset"])}">'
            f"[{n_runs} runs]</span>"
            if n_runs > 1
            else ""
        )

        topic_cells = ""
        if topics_present:
            provider_topics = e.get("topic_scores", {})
            for t in topics_present:
                score = provider_topics.get(t)
                if score is not None:
                    topic_cells += f'        <td class="num">{score:.4f}</td>\n'
                else:
                    topic_cells += '        <td class="num">&mdash;</td>\n'

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

        rows_html.append(
            f"      <tr>\n"
            f'        <td class="rank num">{medal_html}{rank}</td>\n'
            f'        <td><span class="provider-name">{escape(provider_name)}</span>'
            f'<br><span class="model-name">{model_display}</span> {toggle}</td>\n'
            f"        <td>{escape(e['dataset'])}</td>\n"
            f'        <td class="num">{e["n"]}</td>\n'
            f'        <td class="num composite">{e["composite_parity"]:.4f}</td>\n'
            f"{baseline_cells}"
            f"{topic_cells}"
            f'        <td class="num">{e["mean_jsd"]:.4f}</td>\n'
            f'        <td class="num">{e["mean_kendall_tau"]:.4f}</td>\n'
            f"        <td>{e['date']}</td>\n"
            f"      </tr>"
        )

        # Add hidden detail sub-rows
        detail_key = (provider_raw, e["dataset"])
        sub_runs = detail_by_key.get(detail_key, [])
        if len(sub_runs) > 1:
            for sub in sub_runs:
                baseline_sub = ""
                if has_baselines:
                    baseline_sub = '        <td class="num"></td>\n' * 2
                topic_sub = ""
                if topics_present:
                    topic_sub = '        <td class="num"></td>\n' * len(topics_present)
                rows_html.append(
                    f'      <tr class="detail-row" data-provider="{escape(provider_raw)}_{escape(e["dataset"])}" style="display:none">\n'
                    f'        <td class="num"></td>\n'
                    f'        <td class="model-name" style="padding-left:2rem">n={sub["n"]} s={sub["samples_per_question"]}</td>\n'
                    f"        <td></td>\n"
                    f'        <td class="num">{sub["n"]}</td>\n'
                    f'        <td class="num">{sub["composite_parity"]:.4f}</td>\n'
                    f"{baseline_sub}"
                    f"{topic_sub}"
                    f'        <td class="num">{sub["mean_jsd"]:.4f}</td>\n'
                    f'        <td class="num">{sub["mean_kendall_tau"]:.4f}</td>\n'
                    f"        <td>{sub['date']}</td>\n"
                    f"      </tr>"
                )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tbody = "\n".join(rows_html)

    # Build topic column headers
    topic_th = ""
    if topics_present:
        for t in topics_present:
            topic_th += f'        <th class="num">{escape(t.capitalize())}</th>\n'

    # Baseline column headers
    baseline_th = ""
    if has_baselines:
        baseline_th = '        <th class="num">vs Random</th>\n        <th class="num">vs Majority</th>\n'

    # Generate chart sections
    sps_chart = _svg_sps_bars(ranked)
    metric_chart = _svg_metric_bars(ranked)
    baseline_table = _baseline_delta_html(ranked, baselines)
    explanations = _metric_explanations_html()

    # Convergence section
    convergence_html = ""
    if convergence_data:
        conv_rows = []
        for provider, sweeps in sorted(convergence_data.items()):
            for sweep in sweeps:
                samples = sweep["samples"]
                runs = sweep["runs"]
                mean_cp = sum(runs) / len(runs)
                conv_rows.append(
                    f"      <tr>\n"
                    f'        <td class="provider-name">{escape(provider)}</td>\n'
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
        <th class="num">Mean Parity</th>
        <th class="num">Min</th>
        <th class="num">Max</th>
      </tr>
    </thead>
    <tbody>
{conv_tbody}
    </tbody>
  </table>"""

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
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;line-height:1.6;padding:0}}
a{{color:var(--accent);text-decoration:none}}
a:hover{{text-decoration:underline}}

.container{{max-width:1100px;margin:0 auto;padding:2rem 1.5rem}}

header{{text-align:center;padding:3rem 1rem 2rem}}
header h1{{font-size:2.2rem;font-weight:700;letter-spacing:-0.5px}}
header h1 span{{color:var(--accent)}}
header .tagline{{color:var(--text-muted);font-size:1.05rem;margin-top:0.5rem}}

.about{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:1.5rem;margin-bottom:2rem;font-size:0.95rem;color:var(--text-muted)}}
.about p+p{{margin-top:0.75rem}}
.about strong{{color:var(--text)}}
.about code{{background:var(--bg);padding:0.15rem 0.4rem;border-radius:4px;font-size:0.88rem}}

.section-title{{font-size:1.3rem;font-weight:600;margin:2.5rem 0 1rem;padding-bottom:0.5rem;border-bottom:1px solid var(--border)}}

.chart-section{{margin:2rem 0;padding:1.5rem;background:var(--surface);border:1px solid var(--border);border-radius:8px}}

.leaderboard-table{{width:100%;border-collapse:collapse;font-size:0.9rem}}
.leaderboard-table thead{{position:sticky;top:0}}
.leaderboard-table th{{
  background:var(--surface);color:var(--text-muted);font-weight:600;
  text-transform:uppercase;font-size:0.75rem;letter-spacing:0.05em;
  padding:0.75rem 1rem;text-align:left;border-bottom:2px solid var(--border);
}}
.leaderboard-table th.num{{text-align:right}}
.leaderboard-table td{{padding:0.65rem 1rem;border-bottom:1px solid var(--border)}}
.leaderboard-table td.num{{text-align:right;font-variant-numeric:tabular-nums}}
.leaderboard-table tbody tr:hover{{background:rgba(88,166,255,0.06)}}

.rank{{font-weight:700;width:3.5rem}}
.medal{{font-size:1.1rem;margin-right:0.25rem}}
.provider-name{{font-weight:600;color:var(--text)}}
.model-name{{color:var(--text-muted);font-size:0.85rem}}
.composite{{font-weight:700;color:var(--green);font-size:1rem}}
.toggle{{color:var(--accent);cursor:pointer;font-size:0.8rem;margin-left:0.5rem}}
.toggle:hover{{text-decoration:underline}}
.detail-row{{background:var(--surface)}}

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
    <p><strong>Composite Parity</strong> combines distributional similarity (Jensen-Shannon Divergence) and rank-order
       agreement (Kendall's tau) into a single 0&ndash;1 score. Higher is better.</p>
  </div>

  <table class="leaderboard-table">
    <thead>
      <tr>
        <th class="rank">Rank</th>
        <th>Provider</th>
        <th>Dataset</th>
        <th class="num">N</th>
        <th class="num">Composite Parity</th>
{baseline_th}{topic_th}        <th class="num">JSD</th>
        <th class="num">Tau</th>
        <th>Date</th>
      </tr>
    </thead>
    <tbody>
{tbody}
    </tbody>
  </table>

  <div class="chart-section">
{sps_chart}
  </div>

  <div class="chart-section">
{metric_chart}
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
  url={{https://github.com/DataViking-Tech/synthbench}}
}}</pre>
  </details>
</footer>

<script>
document.addEventListener('DOMContentLoaded',function(){{
  document.querySelectorAll('.toggle').forEach(function(el){{
    el.addEventListener('click',function(){{
      var key=this.dataset.provider;
      var rows=document.querySelectorAll('.detail-row[data-provider="'+key+'"]');
      var showing=rows[0]&&rows[0].style.display!=='none';
      rows.forEach(function(r){{r.style.display=showing?'none':'table-row'}});
      this.textContent=showing?this.textContent.replace('-','+').replace('hide','runs'):
        this.textContent.replace('+','-');
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
