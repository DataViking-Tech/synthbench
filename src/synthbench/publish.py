"""Generate a static HTML leaderboard page from SynthBench result JSON files."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from html import escape


def generate_html(results: list[dict], version: str = "0.1.0") -> str:
    """Build a complete HTML leaderboard page from a list of result dicts.

    Results are de-duplicated (best n_evaluated per provider+dataset kept),
    then ranked by composite_parity descending.
    """
    # De-duplicate: keep the run with the most questions per provider+dataset
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

    # Sort by composite_parity descending
    ranked = sorted(
        best.values(),
        key=lambda r: r.get("aggregate", {}).get("composite_parity", 0),
        reverse=True,
    )

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
    <a href="https://github.com/DataViking-Tech/synthbench#methodology">Methodology</a>
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
