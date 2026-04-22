"""CLI-facing orchestration for ``synthbench convergence bootstrap``.

Loads a dataset, computes per-question convergence curves, builds a
dataset-wide summary, honors the dataset's ``redistribution_policy``, writes
JSON (and optionally a matplotlib PDF), and returns the payload for CLI
echoing.

Kept as a thin orchestration layer so it can be exercised directly by tests
without going through click.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from synthbench.convergence.curves import (
    DEFAULT_BOOTSTRAP_B,
    DEFAULT_SAMPLE_SIZES,
    compute_curve,
    curve_to_dicts,
)
from synthbench.convergence.thresholds import (
    DEFAULT_DELTA,
    DEFAULT_EPSILON,
    find_convergence_n,
)
from synthbench.datasets import DATASETS
from synthbench.datasets.base import Question
from synthbench.datasets.policy import policy_for


@dataclass
class QuestionReport:
    """One question's curve + convergence_n, pre-policy filtering."""

    key: str
    text: str
    human_distribution: dict[str, float]
    curve: list[dict]
    convergence_n: int | None


def _parse_sample_sizes(spec: str | None) -> tuple[int, ...]:
    if not spec:
        return DEFAULT_SAMPLE_SIZES
    sizes: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            n = int(part)
        except ValueError as exc:
            raise ValueError(f"invalid sample size: {part!r}") from exc
        if n < 1:
            raise ValueError(f"sample sizes must be positive, got {n}")
        sizes.append(n)
    if not sizes:
        raise ValueError("sample sizes is empty")
    return tuple(sizes)


def compute_reports(
    questions: Sequence[Question],
    sample_sizes: Sequence[int] = DEFAULT_SAMPLE_SIZES,
    B: int = DEFAULT_BOOTSTRAP_B,
    epsilon: float = DEFAULT_EPSILON,
    delta: float = DEFAULT_DELTA,
    rng: np.random.Generator | int | None = None,
) -> list[QuestionReport]:
    """Compute curves + convergence_n for each question."""
    if isinstance(rng, np.random.Generator):
        gen = rng
    else:
        gen = np.random.default_rng(rng)

    reports: list[QuestionReport] = []
    for q in questions:
        curve = compute_curve(
            q.human_distribution, sample_sizes=sample_sizes, B=B, rng=gen
        )
        conv_n = find_convergence_n(curve, epsilon=epsilon, delta=delta)
        reports.append(
            QuestionReport(
                key=q.key,
                text=q.text,
                human_distribution=dict(q.human_distribution),
                curve=curve_to_dicts(curve),
                convergence_n=conv_n,
            )
        )
    return reports


def _percentile_or_none(values: list[int], p: float) -> int | None:
    if not values:
        return None
    return int(np.percentile(values, p))


def summarize(reports: Sequence[QuestionReport]) -> dict:
    """Dataset-wide summary: count of convergent questions + percentiles.

    Only questions where convergence was reached contribute to percentiles.
    Non-converging questions are counted separately so downstream consumers
    can flag datasets that never stabilize within the sample-size grid.
    """
    ns = [r.convergence_n for r in reports if r.convergence_n is not None]
    return {
        "n_questions": len(reports),
        "n_converged": len(ns),
        "n_unconverged": len(reports) - len(ns),
        "convergence_n_p50": _percentile_or_none(ns, 50),
        "convergence_n_p90": _percentile_or_none(ns, 90),
        "convergence_n_p99": _percentile_or_none(ns, 99),
    }


def build_payload(
    dataset_name: str,
    reports: Sequence[QuestionReport],
    sample_sizes: Sequence[int],
    B: int,
    epsilon: float,
    delta: float,
) -> dict:
    """Render the final JSON payload, honoring redistribution policy.

    Tier behavior:
      * ``full``            -- include full per-question curves + distributions
      * ``gated``           -- include full per-question curves + distributions
                               (gated artifacts route to R2 at publish time;
                               the payload itself remains intact)
      * ``aggregates_only`` -- drop per-question entries; keep summary only
      * ``citation_only``   -- drop per-question AND summary stats; emit a
                               notice explaining the suppression
    """
    policy = policy_for(dataset_name)
    summary = summarize(reports)

    payload: dict = {
        "dataset": dataset_name,
        "redistribution_policy": policy.redistribution_policy,
        "license_url": policy.license_url,
        "citation": policy.citation,
        "parameters": {
            "sample_sizes": list(sample_sizes),
            "bootstrap_B": B,
            "epsilon": epsilon,
            "delta": delta,
        },
    }

    if policy.redistribution_policy == "citation_only":
        payload["questions"] = []
        payload["summary"] = None
        payload["suppressed"] = (
            "redistribution_policy=citation_only: per-question curves and "
            "aggregate stats are suppressed. Only dataset metadata ships."
        )
        return payload

    payload["summary"] = summary

    if policy.redistribution_policy == "aggregates_only":
        payload["questions"] = []
        payload["suppressed"] = (
            "redistribution_policy=aggregates_only: per-question curves "
            "suppressed; only dataset-wide summary shipped."
        )
    else:
        # full or gated
        payload["questions"] = [asdict(r) for r in reports]

    return payload


def _render_plot(
    payload: dict,
    reports: Sequence[QuestionReport],
    pdf_path: Path,
) -> None:
    """Render per-question convergence curves to a single multi-page PDF.

    Matches the plotting style used in ``synthbench.visualize``: Agg backend,
    log-scaled x-axis (since sample sizes span orders of magnitude), mean as
    the main line, p10/p90 as a shaded band.
    """
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
    except ImportError as exc:
        raise RuntimeError(
            "--plot requires matplotlib. Install with: pip install synthbench[viz]"
        ) from exc

    if not reports:
        raise ValueError("no questions to plot (policy may have suppressed them)")

    with PdfPages(pdf_path) as pdf:
        # Summary page: convergence_n distribution across the dataset
        conv_ns = [r.convergence_n for r in reports if r.convergence_n is not None]
        fig, ax = plt.subplots(figsize=(8, 5))
        if conv_ns:
            ax.hist(conv_ns, bins=20)
            ax.set_xscale("log")
            ax.set_xlabel("convergence n (log)")
            ax.set_ylabel("question count")
            ax.set_title(
                f"{payload['dataset']}: convergence n distribution "
                f"({len(conv_ns)} of {len(reports)} questions converged)"
            )
        else:
            ax.text(
                0.5,
                0.5,
                "No questions converged under ε/δ thresholds",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
            ax.set_title(f"{payload['dataset']}: no convergence")
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # Per-question curves
        for r in reports:
            fig, ax = plt.subplots(figsize=(8, 5))
            ns = [p["n"] for p in r.curve]
            means = [p["jsd_mean"] for p in r.curve]
            p10s = [p["jsd_p10"] for p in r.curve]
            p90s = [p["jsd_p90"] for p in r.curve]
            ax.plot(ns, means, marker="o", label="JSD mean")
            ax.fill_between(ns, p10s, p90s, alpha=0.2, label="p10–p90")
            ax.set_xscale("log")
            ax.set_xlabel("sample size n (log)")
            ax.set_ylabel("JSD(sample, full)")
            title_text = r.text[:80] + ("…" if len(r.text) > 80 else "")
            conv_label = (
                f"convergence n = {r.convergence_n}"
                if r.convergence_n is not None
                else "no convergence under ε/δ"
            )
            ax.set_title(f"{r.key}: {title_text}\n{conv_label}")
            ax.legend()
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)


def run_bootstrap(
    dataset_name: str,
    question_key: str | None = None,
    output: Path | None = None,
    plot: bool = False,
    bootstraps: int | None = None,
    sample_sizes: str | None = None,
    epsilon: float | None = None,
    delta: float | None = None,
    seed: int | None = None,
    n_limit: int | None = None,
) -> tuple[dict, Path | None]:
    """Top-level entry used by the CLI. Returns (payload, optional PDF path)."""
    if dataset_name not in DATASETS:
        known = ", ".join(sorted(DATASETS))
        raise ValueError(f"unknown dataset {dataset_name!r}; known datasets: {known}")

    sizes = _parse_sample_sizes(sample_sizes)
    B = DEFAULT_BOOTSTRAP_B if bootstraps is None else int(bootstraps)
    eps = DEFAULT_EPSILON if epsilon is None else float(epsilon)
    dlt = DEFAULT_DELTA if delta is None else float(delta)
    if B < 1:
        raise ValueError(f"--bootstraps must be >= 1, got {B}")

    dataset = DATASETS[dataset_name]()
    questions = dataset.load(n=n_limit)
    if question_key:
        questions = [q for q in questions if q.key == question_key]
        if not questions:
            raise ValueError(
                f"no question with key {question_key!r} in dataset {dataset_name!r}"
            )

    reports = compute_reports(
        questions,
        sample_sizes=sizes,
        B=B,
        epsilon=eps,
        delta=dlt,
        rng=seed,
    )
    payload = build_payload(
        dataset_name=dataset_name,
        reports=reports,
        sample_sizes=sizes,
        B=B,
        epsilon=eps,
        delta=dlt,
    )

    pdf_path: Path | None = None
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2))
        if plot:
            pdf_path = output.with_suffix(".pdf")
            # For plot purposes use the reports directly; respect suppression
            # by skipping the plot when no per-question entries would ship.
            if payload["questions"]:
                _render_plot(payload, reports, pdf_path)
            else:
                pdf_path = None
    elif plot:
        raise ValueError(
            "--plot requires --output (the PDF is written alongside the JSON)"
        )

    return payload, pdf_path


__all__ = [
    "QuestionReport",
    "compute_reports",
    "summarize",
    "build_payload",
    "run_bootstrap",
]
