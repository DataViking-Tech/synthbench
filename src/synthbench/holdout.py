"""Temporal holdout validation — post-cutoff product concept evaluation.

Evaluates model ability to assess product concepts for products launched
after the model's training cutoff. Because the model hasn't seen these
products, its evaluation is contamination-free.

Each prompt describes a 2026 product WITHOUT naming it. The model evaluates
the concept's market viability. Scores compare model assessment against
actual market reception.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


HOLDOUT_DIR = Path(__file__).parent / ".." / ".." / "suites"
HOLDOUT_DIR = HOLDOUT_DIR.resolve()

VALID_OUTCOMES = ("success", "mixed", "failure")

EVALUATION_PROMPT_TEMPLATE = """\
You are evaluating a product concept. Based solely on the description below, \
assess its likely market reception.

PRODUCT CONCEPT:
{concept}

Evaluate this concept and respond with exactly one of these three verdicts:
- SUCCESS: The product will likely achieve strong market adoption and positive reception.
- MIXED: The product will likely see partial success with significant challenges.
- FAILURE: The product will likely fail to gain meaningful traction.

Respond with only the single word: SUCCESS, MIXED, or FAILURE."""


@dataclass
class HoldoutPrompt:
    """A single holdout product concept prompt with ground truth."""

    id: str
    sector: str
    launch_quarter: str
    concept: str
    ground_truth: str  # success | mixed | failure
    reception_summary: str

    def __post_init__(self):
        if self.ground_truth not in VALID_OUTCOMES:
            raise ValueError(
                f"Invalid ground_truth '{self.ground_truth}' for {self.id}. "
                f"Must be one of {VALID_OUTCOMES}"
            )


@dataclass
class HoldoutResult:
    """Result of evaluating a single holdout prompt."""

    prompt_id: str
    sector: str
    ground_truth: str
    model_verdict: str
    correct: bool
    raw_response: str


@dataclass
class HoldoutSuiteResult:
    """Aggregate results from a full holdout suite evaluation."""

    provider_name: str
    suite_version: str
    results: list[HoldoutResult] = field(default_factory=list)

    @property
    def n_total(self) -> int:
        return len(self.results)

    @property
    def n_correct(self) -> int:
        return sum(1 for r in self.results if r.correct)

    @property
    def accuracy(self) -> float:
        if not self.results:
            return 0.0
        return self.n_correct / self.n_total

    @property
    def per_outcome_accuracy(self) -> dict[str, float]:
        """Accuracy broken down by ground truth outcome."""
        counts: dict[str, list[bool]] = {}
        for r in self.results:
            counts.setdefault(r.ground_truth, []).append(r.correct)
        return {
            outcome: sum(vals) / len(vals) for outcome, vals in sorted(counts.items())
        }

    @property
    def per_sector_accuracy(self) -> dict[str, float]:
        """Accuracy broken down by sector."""
        counts: dict[str, list[bool]] = {}
        for r in self.results:
            counts.setdefault(r.sector, []).append(r.correct)
        return {
            sector: sum(vals) / len(vals) for sector, vals in sorted(counts.items())
        }

    @property
    def confusion_matrix(self) -> dict[str, dict[str, int]]:
        """Confusion matrix: ground_truth -> model_verdict -> count."""
        matrix: dict[str, dict[str, int]] = {
            gt: {mv: 0 for mv in VALID_OUTCOMES} for gt in VALID_OUTCOMES
        }
        for r in self.results:
            if r.model_verdict in VALID_OUTCOMES:
                matrix[r.ground_truth][r.model_verdict] += 1
        return matrix

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "benchmark": "synthbench",
            "type": "holdout",
            "provider": self.provider_name,
            "suite_version": self.suite_version,
            "aggregate": {
                "n_total": self.n_total,
                "n_correct": self.n_correct,
                "accuracy": round(self.accuracy, 4),
                "per_outcome_accuracy": {
                    k: round(v, 4) for k, v in self.per_outcome_accuracy.items()
                },
                "per_sector_accuracy": {
                    k: round(v, 4) for k, v in self.per_sector_accuracy.items()
                },
                "confusion_matrix": self.confusion_matrix,
            },
            "per_prompt": [
                {
                    "id": r.prompt_id,
                    "sector": r.sector,
                    "ground_truth": r.ground_truth,
                    "model_verdict": r.model_verdict,
                    "correct": r.correct,
                }
                for r in self.results
            ],
        }


def load_holdout_suite(
    name: str = "temporal_holdout",
) -> tuple[dict, list[HoldoutPrompt]]:
    """Load a holdout suite YAML and return (meta, prompts).

    Args:
        name: Suite filename (without .yaml extension).

    Returns:
        Tuple of (metadata dict, list of HoldoutPrompt).

    Raises:
        FileNotFoundError: If the suite YAML doesn't exist.
        ValueError: If prompts have invalid ground truth values.
    """
    path = HOLDOUT_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Holdout suite not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    meta = data.get("meta", {})
    raw_prompts = data.get("prompts", [])

    prompts = [
        HoldoutPrompt(
            id=p["id"],
            sector=p["sector"],
            launch_quarter=p["launch_quarter"],
            concept=p["concept"].strip(),
            ground_truth=p["ground_truth"],
            reception_summary=p.get("reception_summary", ""),
        )
        for p in raw_prompts
    ]

    return meta, prompts


def parse_verdict(raw: str) -> str:
    """Extract a verdict (success/mixed/failure) from a model response.

    Handles responses that include explanation text around the verdict.
    Returns the verdict in lowercase, or 'unparseable' if no match.
    """
    cleaned = raw.strip().upper()

    # Direct match
    if cleaned in ("SUCCESS", "MIXED", "FAILURE"):
        return cleaned.lower()

    # Search for verdict word in the response
    match = re.search(r"\b(SUCCESS|MIXED|FAILURE)\b", cleaned)
    if match:
        return match.group(1).lower()

    return "unparseable"


async def evaluate_prompt(
    prompt: HoldoutPrompt,
    provider,
    semaphore: asyncio.Semaphore,
) -> HoldoutResult:
    """Evaluate a single holdout prompt against a provider.

    The provider must implement a `respond` method compatible with
    synthbench.providers.base.Provider.
    """
    evaluation_text = EVALUATION_PROMPT_TEMPLATE.format(concept=prompt.concept)
    options = ["SUCCESS", "MIXED", "FAILURE"]

    async with semaphore:
        response = await provider.respond(evaluation_text, options)

    raw = response.selected_option
    verdict = parse_verdict(raw)
    correct = verdict == prompt.ground_truth

    return HoldoutResult(
        prompt_id=prompt.id,
        sector=prompt.sector,
        ground_truth=prompt.ground_truth,
        model_verdict=verdict,
        correct=correct,
        raw_response=raw,
    )


async def run_holdout_suite(
    provider,
    suite_name: str = "temporal_holdout",
    concurrency: int = 10,
) -> HoldoutSuiteResult:
    """Run the full holdout validation suite against a provider.

    Args:
        provider: A synthbench Provider instance.
        suite_name: Name of the holdout suite YAML.
        concurrency: Max concurrent API requests.

    Returns:
        HoldoutSuiteResult with per-prompt results and aggregate metrics.
    """
    meta, prompts = load_holdout_suite(suite_name)
    semaphore = asyncio.Semaphore(concurrency)

    tasks = [evaluate_prompt(p, provider, semaphore) for p in prompts]
    results = await asyncio.gather(*tasks)

    return HoldoutSuiteResult(
        provider_name=provider.name,
        suite_version=meta.get("version", "unknown"),
        results=list(results),
    )


def format_holdout_report(result: HoldoutSuiteResult) -> str:
    """Format a holdout suite result as a human-readable report."""
    lines = [
        "# Temporal Holdout Validation Report",
        "",
        f"**Provider:** {result.provider_name}",
        f"**Suite version:** {result.suite_version}",
        f"**Prompts evaluated:** {result.n_total}",
        "",
        "## Accuracy",
        "",
        f"**Overall:** {result.accuracy:.1%} ({result.n_correct}/{result.n_total})",
        "",
        "### By Outcome",
        "",
        "| Outcome | Accuracy |",
        "|---------|----------|",
    ]

    for outcome, acc in result.per_outcome_accuracy.items():
        lines.append(f"| {outcome} | {acc:.1%} |")

    lines.extend(
        [
            "",
            "### By Sector",
            "",
            "| Sector | Accuracy |",
            "|--------|----------|",
        ]
    )

    for sector, acc in result.per_sector_accuracy.items():
        lines.append(f"| {sector} | {acc:.1%} |")

    # Confusion matrix
    cm = result.confusion_matrix
    lines.extend(
        [
            "",
            "### Confusion Matrix",
            "",
            "| Ground Truth \\ Model | success | mixed | failure |",
            "|----------------------|---------|-------|---------|",
        ]
    )
    for gt in VALID_OUTCOMES:
        row = cm.get(gt, {})
        lines.append(
            f"| {gt} | {row.get('success', 0)} | {row.get('mixed', 0)} "
            f"| {row.get('failure', 0)} |"
        )

    # Per-prompt details
    lines.extend(
        [
            "",
            "### Per-Prompt Results",
            "",
            "| ID | Sector | Truth | Model | Correct |",
            "|----|--------|-------|-------|---------|",
        ]
    )

    for r in result.results:
        mark = "Y" if r.correct else "N"
        lines.append(
            f"| {r.prompt_id} | {r.sector} | {r.ground_truth} "
            f"| {r.model_verdict} | {mark} |"
        )

    return "\n".join(lines)
