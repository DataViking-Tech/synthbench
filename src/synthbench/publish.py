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
    """Return HTML section explaining each metric."""
    return """
  <h2 class="section-title">Metric Explanations</h2>
  <div class="about">
    <p><strong>Composite Parity</strong> combines distributional similarity and rank-order
       agreement into a single 0&ndash;1 score. <code>(1 - JSD + (1 + tau)/2) / 2</code>. Higher is better.</p>
    <p><strong>P_dist (Distributional Parity)</strong> = <code>1 - mean(JSD)</code>.
       Measures how closely a provider's response distribution matches the human distribution.
       Jensen-Shannon divergence is bounded [0, 1], symmetric, and handles zero entries.
       A perfect match yields P_dist = 1.</p>
    <p><strong>P_rank (Rank-Order Parity)</strong> = <code>(1 + mean(tau)) / 2</code>.
       Kendall's tau-b on probability rankings, normalized to [0, 1].
       Captures whether the provider gets the <em>ordering</em> of options right,
       even when exact proportions differ.</p>
    <p><strong>P_refuse (Refusal Calibration)</strong> = <code>1 - mean(|R_provider - R_human|)</code>.
       Whether the provider's refusal rate matches human refusal patterns.
       Human refusal patterns carry signal: questions about religion see higher refusals
       from non-religious respondents; income questions see higher refusals from high earners.</p>
    <p><strong>Mean JSD</strong>: Average Jensen-Shannon divergence across all questions. Lower is better (0 = identical distributions).</p>
    <p><strong>Kendall's tau</strong>: Rank correlation between human and model response option rankings.
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


def generate_html(results: list[dict], version: str = "0.1.0") -> str:
    """Build a complete HTML leaderboard page from a list of result dicts.

    Results are de-duplicated (best n_evaluated per provider+dataset kept),
    then ranked by composite_parity descending. Includes SVG charts,
    baseline comparison table, and metric explanations.
    """
    deduped = _dedup_results(results)

    # Sort by composite_parity descending
    ranked = sorted(
        deduped,
        key=lambda r: r.get("aggregate", {}).get("composite_parity", 0),
        reverse=True,
    )

    models, baselines = _split_baselines(ranked)

    rows_html = []
    medals = {1: "&#x1f947;", 2: "&#x1f948;", 3: "&#x1f949;"}
    for rank, r in enumerate(ranked, 1):
        cfg = r.get("config", {})
        agg = r.get("aggregate", {})
        ts = r.get("timestamp", "")
        date_str = escape(ts[:10]) if len(ts) >= 10 else "--"

        provider_raw = cfg.get("provider", "unknown")
        # Split provider/model if present
        if "/" in provider_raw:
            provider_name, model_name = provider_raw.split("/", 1)
        else:
            provider_name = provider_raw
            model_name = None

        medal = medals.get(rank, "")
        medal_html = f'<span class="medal">{medal}</span>' if medal else ""

        model_display = escape(model_name) if model_name else "&mdash;"

        composite = agg.get("composite_parity", 0)
        mean_jsd = agg.get("mean_jsd", 0)
        mean_tau = agg.get("mean_kendall_tau", 0)
        n = cfg.get("n_evaluated", 0)
        dataset_name = escape(cfg.get("dataset", "unknown"))

        rows_html.append(
            f"      <tr>\n"
            f'        <td class="rank num">{medal_html}{rank}</td>\n'
            f'        <td><span class="provider-name">{escape(provider_name)}</span>'
            f'<br><span class="model-name">{model_display}</span></td>\n'
            f"        <td>{dataset_name}</td>\n"
            f'        <td class="num">{n}</td>\n'
            f'        <td class="num composite">{composite:.4f}</td>\n'
            f'        <td class="num">{mean_jsd:.4f}</td>\n'
            f'        <td class="num">{mean_tau:.4f}</td>\n'
            f"        <td>{date_str}</td>\n"
            f"      </tr>"
        )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tbody = "\n".join(rows_html)

    # Generate chart sections
    sps_chart = _svg_sps_bars(ranked)
    metric_chart = _svg_metric_bars(ranked)
    baseline_table = _baseline_delta_html(ranked, baselines)
    explanations = _metric_explanations_html()

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
        <th class="num">JSD</th>
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

{explanations}
</div>

<footer>
  <p>Generated by <a href="https://github.com/DataViking-Tech/synthbench">SynthBench</a> v{escape(version)}</p>
  <p>Last updated: {today}</p>
</footer>

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
