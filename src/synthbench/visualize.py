"""Chart generation for SynthBench results.

Uses matplotlib when available; falls back to inline SVG generation.
"""

from __future__ import annotations

from pathlib import Path

try:
    import matplotlib

    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_charts(
    result_json: dict | list[dict],
    output_dir: Path,
) -> list[Path]:
    """Generate charts from one or more benchmark result dicts.

    If *result_json* is a single dict, generates a JSD histogram and parity
    scatter.  If it is a list of dicts, also generates a comparison bar chart.

    Returns a list of file paths that were written.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Normalise input
    if isinstance(result_json, dict):
        results = [result_json]
    else:
        results = list(result_json)

    paths: list[Path] = []

    # 1. JSD histogram (first result)
    if results:
        p = _jsd_histogram(results[0], output_dir)
        if p:
            paths.append(p)

    # 2. Comparison bar chart (when multiple results)
    if len(results) >= 2:
        p = _comparison_bar(results, output_dir)
        if p:
            paths.append(p)

    # 3. Parity scatter (first result)
    if results:
        p = _parity_scatter(results[0], output_dir)
        if p:
            paths.append(p)

    return paths


def embed_charts_in_markdown(markdown: str, chart_paths: list[Path]) -> str:
    """Append a Charts section with image links to existing markdown."""
    if not chart_paths:
        return markdown

    lines = [
        markdown.rstrip(),
        "",
        "## Charts",
        "",
    ]
    for cp in chart_paths:
        name = cp.stem.replace("_", " ").title()
        lines.append(f"![{name}]({cp})")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Matplotlib implementations
# ---------------------------------------------------------------------------


def _jsd_histogram(result: dict, output_dir: Path) -> Path | None:
    """Distribution of per-question JSD values."""
    questions = result.get("per_question", [])
    if not questions:
        return None

    jsd_values = [q["jsd"] for q in questions]
    provider = result.get("config", {}).get("provider", "unknown")
    mean_jsd = result.get("aggregate", {}).get("mean_jsd", 0)

    path = output_dir / "jsd_histogram.png"

    if HAS_MATPLOTLIB:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(
            jsd_values,
            bins=20,
            range=(0, 1),
            color="#4f8fba",
            edgecolor="#2d5f7a",
            alpha=0.85,
        )
        ax.axvline(
            mean_jsd,
            color="#e74c3c",
            linestyle="--",
            linewidth=1.5,
            label=f"Mean = {mean_jsd:.4f}",
        )
        ax.set_xlabel("JSD")
        ax.set_ylabel("Count")
        ax.set_title(f"JSD Distribution -- {provider} (mean={mean_jsd:.4f})")
        ax.legend()
        ax.set_xlim(0, 1)
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
    else:
        svg = _svg_histogram(jsd_values, provider, mean_jsd)
        path = output_dir / "jsd_histogram.svg"
        path.write_text(svg)

    return path


def _comparison_bar(results: list[dict], output_dir: Path) -> Path | None:
    """Grouped bar chart of Parity, 1-JSD, tau for each model."""
    if not results:
        return None

    labels = []
    parity_vals = []
    one_minus_jsd = []
    tau_vals = []

    for r in results:
        cfg = r.get("config", {})
        agg = r.get("aggregate", {})
        provider = cfg.get("provider", "unknown")
        n = cfg.get("n_evaluated", "?")
        labels.append(f"{provider}\n(n={n})")
        parity_vals.append(agg.get("composite_parity", 0))
        one_minus_jsd.append(1.0 - agg.get("mean_jsd", 0))
        tau_vals.append(agg.get("mean_kendall_tau", 0))

    path = output_dir / "comparison.png"

    if HAS_MATPLOTLIB:
        import numpy as np

        x = np.arange(len(labels))
        width = 0.25

        fig, ax = plt.subplots(figsize=(max(8, len(labels) * 3), 5))
        ax.bar(x - width, parity_vals, width, label="Parity", color="#2ecc71")
        ax.bar(x, one_minus_jsd, width, label="1 - JSD", color="#3498db")
        ax.bar(x + width, tau_vals, width, label="Kendall's tau", color="#e67e22")

        ax.set_ylabel("Score")
        ax.set_title("Model Comparison")
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylim(0, 1)
        ax.legend()
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
    else:
        svg = _svg_comparison_bars(labels, parity_vals, one_minus_jsd, tau_vals)
        path = output_dir / "comparison.svg"
        path.write_text(svg)

    return path


def _parity_scatter(result: dict, output_dir: Path) -> Path | None:
    """Scatter of JSD vs tau, coloured by parity, with best/worst highlighted."""
    questions = result.get("per_question", [])
    if not questions:
        return None

    jsd_vals = [q["jsd"] for q in questions]
    tau_vals = [q["kendall_tau"] for q in questions]
    parity_vals = [q["parity"] for q in questions]

    # Identify top-5 best (lowest JSD) and worst (highest JSD)
    sorted_indices = sorted(range(len(jsd_vals)), key=lambda i: jsd_vals[i])
    best_5 = set(sorted_indices[:5])
    worst_5 = set(sorted_indices[-5:])

    provider = result.get("config", {}).get("provider", "unknown")
    path = output_dir / "parity_scatter.png"

    if HAS_MATPLOTLIB:
        fig, ax = plt.subplots(figsize=(8, 6))

        sc = ax.scatter(
            jsd_vals,
            tau_vals,
            c=parity_vals,
            cmap="RdYlGn",
            vmin=0,
            vmax=1,
            s=40,
            alpha=0.7,
            edgecolors="none",
        )

        # Highlight best/worst
        for idx in best_5:
            ax.scatter(
                jsd_vals[idx],
                tau_vals[idx],
                s=100,
                facecolors="none",
                edgecolors="#27ae60",
                linewidths=2,
            )
        for idx in worst_5:
            ax.scatter(
                jsd_vals[idx],
                tau_vals[idx],
                s=100,
                facecolors="none",
                edgecolors="#c0392b",
                linewidths=2,
            )

        ax.set_xlabel("JSD")
        ax.set_ylabel("Kendall's tau")
        ax.set_title(f"Per-Question Parity -- {provider}")
        cbar = fig.colorbar(sc, ax=ax)
        cbar.set_label("Parity")

        # Legend entries for best/worst markers
        from matplotlib.lines import Line2D

        legend_elements = [
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="none",
                markeredgecolor="#27ae60",
                markersize=10,
                markeredgewidth=2,
                label="Top 5 best",
            ),
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="none",
                markeredgecolor="#c0392b",
                markersize=10,
                markeredgewidth=2,
                label="Top 5 worst",
            ),
        ]
        ax.legend(handles=legend_elements, loc="lower left")

        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
    else:
        svg = _svg_scatter(jsd_vals, tau_vals, parity_vals, best_5, worst_5, provider)
        path = output_dir / "parity_scatter.svg"
        path.write_text(svg)

    return path


# ---------------------------------------------------------------------------
# SVG fallback implementations
# ---------------------------------------------------------------------------


def _svg_histogram(values: list[float], provider: str, mean: float) -> str:
    """Simple SVG bar-chart histogram for JSD values."""
    n_bins = 20
    bins = [0] * n_bins
    for v in values:
        idx = min(int(v * n_bins), n_bins - 1)
        bins[idx] += 1

    max_count = max(bins) if bins else 1
    w, h = 600, 300
    bar_w = w / n_bins
    margin_bottom = 40
    margin_top = 30
    chart_h = h - margin_bottom - margin_top

    bars_svg = []
    for i, count in enumerate(bins):
        bar_h = (count / max_count) * chart_h if max_count > 0 else 0
        x = i * bar_w
        y = margin_top + chart_h - bar_h
        bars_svg.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w - 1:.1f}" '
            f'height="{bar_h:.1f}" fill="#4f8fba" />'
        )

    # Mean line
    mean_x = mean * w
    bars_svg.append(
        f'<line x1="{mean_x:.1f}" y1="{margin_top}" x2="{mean_x:.1f}" '
        f'y2="{margin_top + chart_h}" stroke="#e74c3c" stroke-width="2" '
        f'stroke-dasharray="5,3" />'
    )

    title = f"JSD Distribution -- {provider} (mean={mean:.4f})"

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" style="font-family:sans-serif">\n'
        f'<text x="{w / 2}" y="20" text-anchor="middle" font-size="14">{title}</text>\n'
        + "\n".join(bars_svg)
        + f'\n<text x="{w / 2}" y="{h - 5}" text-anchor="middle" font-size="11">JSD (0-1)</text>'
        + "\n</svg>"
    )


def _svg_comparison_bars(
    labels: list[str],
    parity: list[float],
    one_jsd: list[float],
    tau: list[float],
) -> str:
    """Simple SVG grouped bar chart for model comparison."""
    n = len(labels)
    w = max(400, n * 150)
    h = 300
    margin_bottom = 60
    margin_top = 30
    chart_h = h - margin_bottom - margin_top
    group_w = w / n
    bar_w = group_w / 5

    colors = ["#2ecc71", "#3498db", "#e67e22"]
    metric_names = ["Parity", "1-JSD", "tau"]
    all_series = [parity, one_jsd, tau]

    rects = []
    for gi in range(n):
        gx = gi * group_w + bar_w * 0.5
        for si, series in enumerate(all_series):
            val = series[gi]
            bar_h = val * chart_h
            x = gx + si * bar_w
            y = margin_top + chart_h - bar_h
            rects.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w - 1:.1f}" '
                f'height="{bar_h:.1f}" fill="{colors[si]}" />'
            )
        # Label
        lx = gx + 1.5 * bar_w
        ly = h - margin_bottom + 15
        clean_label = labels[gi].replace("\n", " ")
        rects.append(
            f'<text x="{lx:.1f}" y="{ly}" text-anchor="middle" font-size="10">'
            f"{clean_label}</text>"
        )

    # Legend
    legend_parts = []
    for si in range(3):
        lx = 10 + si * 100
        legend_parts.append(
            f'<rect x="{lx}" y="{h - 15}" width="12" height="12" fill="{colors[si]}" />'
            f'<text x="{lx + 16}" y="{h - 5}" font-size="10">{metric_names[si]}</text>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" style="font-family:sans-serif">\n'
        f'<text x="{w / 2}" y="20" text-anchor="middle" font-size="14">Model Comparison</text>\n'
        + "\n".join(rects)
        + "\n"
        + "\n".join(legend_parts)
        + "\n</svg>"
    )


def _svg_scatter(
    jsd: list[float],
    tau: list[float],
    parity: list[float],
    best_5: set[int],
    worst_5: set[int],
    provider: str,
) -> str:
    """Simple SVG scatter plot of JSD vs tau."""
    w, h = 500, 400
    margin = 50
    chart_w = w - 2 * margin
    chart_h = h - 2 * margin

    def to_x(v: float) -> float:
        return margin + v * chart_w

    def to_y(v: float) -> float:
        # tau can range -1 to 1; map to chart
        return margin + chart_h - ((v + 1) / 2) * chart_h

    def parity_color(p: float) -> str:
        r = int(255 * (1 - p))
        g = int(200 * p)
        return f"rgb({r},{g},80)"

    dots = []
    for i in range(len(jsd)):
        cx = to_x(jsd[i])
        cy = to_y(tau[i])
        color = parity_color(parity[i])
        dots.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="{color}" opacity="0.7" />'
        )

        if i in best_5:
            dots.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="8" fill="none" '
                f'stroke="#27ae60" stroke-width="2" />'
            )
        if i in worst_5:
            dots.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="8" fill="none" '
                f'stroke="#c0392b" stroke-width="2" />'
            )

    title = f"Per-Question Parity -- {provider}"

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" style="font-family:sans-serif">\n'
        f'<text x="{w / 2}" y="20" text-anchor="middle" font-size="14">{title}</text>\n'
        f'<text x="{w / 2}" y="{h - 5}" text-anchor="middle" font-size="11">JSD</text>\n'
        f'<text x="12" y="{h / 2}" text-anchor="middle" font-size="11" '
        f'transform="rotate(-90,12,{h / 2})">Kendall tau</text>\n'
        + "\n".join(dots)
        + "\n</svg>"
    )
