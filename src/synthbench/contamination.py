"""Cross-model convergence analysis for per-question contamination detection.

For each question across multiple model result files, computes the standard
deviation of model response distributions. Low cross-model variance suggests
contamination (all models recall the same memorized data). High variance
suggests genuine reasoning.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class QuestionContamination:
    """Contamination risk assessment for a single question."""

    key: str
    text: str
    options: list[str]
    mean_std: float  # Mean std across all options (lower = more suspicious)
    contamination_risk: float  # 0..1 score; 1 = highest risk (lowest variance)
    per_option_std: dict[str, float]  # std of each option's proportion across models
    n_models: int
    model_distributions: dict[str, dict[str, float]]  # model -> option -> proportion


@dataclass
class ConvergenceAnalysis:
    """Full convergence analysis across all questions and models."""

    questions: list[QuestionContamination]
    n_models: int
    n_questions: int
    model_names: list[str]
    mean_contamination_risk: float
    high_risk_count: int  # questions with contamination_risk >= 0.8
    medium_risk_count: int  # questions with 0.5 <= contamination_risk < 0.8
    low_risk_count: int  # questions with contamination_risk < 0.5


def _std(values: list[float]) -> float:
    """Population standard deviation (no scipy needed)."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


def load_result_distributions(
    path: Path,
) -> tuple[str, dict[str, dict[str, float]], dict[str, str]]:
    """Load per-question model distributions from a result JSON file.

    Returns:
        (provider_name, {question_key: {option: proportion}}, {question_key: text})
    """
    with open(path) as f:
        data = json.load(f)

    if data.get("benchmark") != "synthbench":
        raise ValueError(f"Not a synthbench result file: {path}")

    provider = data.get("config", {}).get("provider", str(path))
    distributions: dict[str, dict[str, float]] = {}
    texts: dict[str, str] = {}

    for q in data.get("per_question", []):
        key = q["key"]
        distributions[key] = q["model_distribution"]
        texts[key] = q.get("text", "")

    return provider, distributions, texts


def convergence_analysis(
    result_files: list[Path],
    *,
    min_models: int = 2,
) -> ConvergenceAnalysis:
    """Compute per-question contamination risk from cross-model convergence.

    For each question present in at least ``min_models`` result files, computes
    the standard deviation of each option's proportion across models. Low std
    means all models produce nearly identical distributions — a contamination
    signal.

    The contamination_risk score is 1 - normalized_mean_std, where
    normalized_mean_std is the mean option std divided by the theoretical
    maximum std for that number of models.

    Args:
        result_files: Paths to synthbench result JSON files.
        min_models: Minimum number of models a question must appear in.

    Returns:
        ConvergenceAnalysis with per-question contamination risk scores.
    """
    # Load all results
    model_data: dict[str, dict[str, dict[str, float]]] = {}  # model -> key -> dist
    all_texts: dict[str, str] = {}
    model_names: list[str] = []

    for path in result_files:
        provider, distributions, texts = load_result_distributions(path)
        # Deduplicate provider names by appending a counter if needed
        base_name = provider
        counter = 1
        while provider in model_data:
            counter += 1
            provider = f"{base_name}#{counter}"
        model_data[provider] = distributions
        model_names.append(provider)
        all_texts.update(texts)

    if len(model_names) < 2:
        raise ValueError(f"Need at least 2 model result files, got {len(model_names)}")

    # Collect all question keys that appear in >= min_models files
    key_counts: dict[str, int] = {}
    for distributions in model_data.values():
        for key in distributions:
            key_counts[key] = key_counts.get(key, 0) + 1

    eligible_keys = sorted(k for k, c in key_counts.items() if c >= min_models)

    if not eligible_keys:
        raise ValueError(f"No questions found in >= {min_models} result files")

    # For each eligible question, compute cross-model distribution std
    questions: list[QuestionContamination] = []

    for key in eligible_keys:
        # Collect all option names across models for this question
        all_options: set[str] = set()
        model_dists_for_key: dict[str, dict[str, float]] = {}

        for model, distributions in model_data.items():
            if key in distributions:
                dist = distributions[key]
                all_options.update(dist.keys())
                model_dists_for_key[model] = dist

        sorted_options = sorted(all_options)
        n_models_for_q = len(model_dists_for_key)

        # Compute std of each option's proportion across models
        per_option_std: dict[str, float] = {}
        for option in sorted_options:
            proportions = [
                dist.get(option, 0.0) for dist in model_dists_for_key.values()
            ]
            per_option_std[option] = _std(proportions)

        # Mean std across all options
        mean_std = (
            sum(per_option_std.values()) / len(per_option_std)
            if per_option_std
            else 0.0
        )

        # Theoretical max std for proportions with n models:
        # Max std for a binary proportion (0 or 1 split across models) is 0.5
        # when exactly half the models say 0 and half say 1.
        # For a uniform [0,1] distribution, max population std is 0.5.
        # We normalize mean_std by 0.5 to get a 0..1 scale.
        max_possible_std = 0.5
        normalized = (
            min(mean_std / max_possible_std, 1.0) if max_possible_std > 0 else 0.0
        )
        contamination_risk = round(1.0 - normalized, 6)

        questions.append(
            QuestionContamination(
                key=key,
                text=all_texts.get(key, ""),
                options=sorted_options,
                mean_std=round(mean_std, 6),
                contamination_risk=contamination_risk,
                per_option_std={k: round(v, 6) for k, v in per_option_std.items()},
                n_models=n_models_for_q,
                model_distributions=model_dists_for_key,
            )
        )

    # Aggregate stats
    mean_risk = sum(q.contamination_risk for q in questions) / len(questions)
    high_risk = sum(1 for q in questions if q.contamination_risk >= 0.8)
    medium_risk = sum(1 for q in questions if 0.5 <= q.contamination_risk < 0.8)
    low_risk = sum(1 for q in questions if q.contamination_risk < 0.5)

    return ConvergenceAnalysis(
        questions=questions,
        n_models=len(model_names),
        n_questions=len(questions),
        model_names=model_names,
        mean_contamination_risk=round(mean_risk, 6),
        high_risk_count=high_risk,
        medium_risk_count=medium_risk,
        low_risk_count=low_risk,
    )


def format_convergence_report(analysis: ConvergenceAnalysis) -> str:
    """Format a convergence analysis as a markdown report."""
    lines = [
        "# Cross-Model Convergence Analysis",
        "",
        f"**Models:** {analysis.n_models}",
        f"**Questions analyzed:** {analysis.n_questions}",
        f"**Mean contamination risk:** {analysis.mean_contamination_risk:.4f}",
        "",
        "## Risk Distribution",
        "",
        f"- High risk (>= 0.8): {analysis.high_risk_count} questions",
        f"- Medium risk (0.5-0.8): {analysis.medium_risk_count} questions",
        f"- Low risk (< 0.5): {analysis.low_risk_count} questions",
        "",
        "## Models",
        "",
    ]

    for name in analysis.model_names:
        lines.append(f"- {name}")

    lines.append("")

    # Top contamination risks
    sorted_q = sorted(
        analysis.questions, key=lambda q: q.contamination_risk, reverse=True
    )

    lines.extend(
        [
            "## Highest Contamination Risk (top 20)",
            "",
            "| Rank | Key | Risk | Mean Std | Models | Text |",
            "|------|-----|------|----------|--------|------|",
        ]
    )

    for i, q in enumerate(sorted_q[:20], 1):
        text_trunc = q.text[:60] + "..." if len(q.text) > 60 else q.text
        lines.append(
            f"| {i} | {q.key} | {q.contamination_risk:.4f} | "
            f"{q.mean_std:.4f} | {q.n_models} | {text_trunc} |"
        )

    lines.append("")

    # Lowest risk (genuine reasoning)
    lines.extend(
        [
            "## Lowest Contamination Risk (most divergent, top 20)",
            "",
            "| Rank | Key | Risk | Mean Std | Models | Text |",
            "|------|-----|------|----------|--------|------|",
        ]
    )

    for i, q in enumerate(reversed(sorted_q[-20:]), 1):
        text_trunc = q.text[:60] + "..." if len(q.text) > 60 else q.text
        lines.append(
            f"| {i} | {q.key} | {q.contamination_risk:.4f} | "
            f"{q.mean_std:.4f} | {q.n_models} | {text_trunc} |"
        )

    lines.append("")
    return "\n".join(lines)


def convergence_to_json(analysis: ConvergenceAnalysis) -> dict:
    """Serialize a convergence analysis to a JSON-compatible dict."""
    return {
        "benchmark": "synthbench",
        "type": "contamination_convergence",
        "n_models": analysis.n_models,
        "n_questions": analysis.n_questions,
        "model_names": analysis.model_names,
        "mean_contamination_risk": analysis.mean_contamination_risk,
        "high_risk_count": analysis.high_risk_count,
        "medium_risk_count": analysis.medium_risk_count,
        "low_risk_count": analysis.low_risk_count,
        "per_question": [
            {
                "key": q.key,
                "text": q.text,
                "options": q.options,
                "mean_std": q.mean_std,
                "contamination_risk": q.contamination_risk,
                "per_option_std": q.per_option_std,
                "n_models": q.n_models,
                "model_distributions": q.model_distributions,
            }
            for q in sorted(
                analysis.questions,
                key=lambda q: q.contamination_risk,
                reverse=True,
            )
        ],
    }
