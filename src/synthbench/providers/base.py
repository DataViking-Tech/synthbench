"""Base provider interface for SynthBench."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass


@dataclass
class PersonaSpec:
    """Specification for persona conditioning."""

    demographics: dict[str, str]
    attribute: str = ""
    group: str = ""
    biography: str | None = None
    conditioning_style: str = "default"


@dataclass
class Distribution:
    """A probability distribution over options."""

    probabilities: list[float]
    refusal_probability: float = 0.0
    method: str = "sampling"
    n_samples: int | None = None
    metadata: dict | None = None


@dataclass
class Response:
    """A single response from a provider."""

    selected_option: str
    raw_text: str = ""
    metadata: dict | None = None
    refusal: bool = False


class Provider(ABC):
    """Interface that all synthetic respondent providers implement.

    Providers answer survey questions by selecting from given options.
    The harness calls respond() multiple times per question to build
    an empirical distribution, or get_distribution() for providers that
    return distributions natively.
    """

    @abstractmethod
    async def respond(
        self,
        question: str,
        options: list[str],
        *,
        persona: PersonaSpec | None = None,
    ) -> Response:
        """Answer a survey question by selecting one option.

        Args:
            question: The survey question text.
            options: List of answer choices.
            persona: Optional persona conditioning.

        Returns:
            Response with the selected option text.
        """
        ...

    async def get_distribution(
        self,
        question: str,
        options: list[str],
        *,
        persona: PersonaSpec | None = None,
        n_samples: int | None = None,
    ) -> Distribution:
        """Get a probability distribution over options.

        Default implementation calls respond() n_samples times and builds
        an empirical distribution. Override for providers that return
        distributions natively (e.g., via logprobs or direct probability output).

        Args:
            n_samples: Number of samples. Defaults to 30 for sampling providers.
                Logprob providers ignore this parameter.
        """
        effective_samples = n_samples if n_samples is not None else 30
        tasks = [
            self.respond(question, options, persona=persona)
            for _ in range(effective_samples)
        ]
        results = await asyncio.gather(*tasks)

        refusals = sum(1 for r in results if r.refusal)
        responses = [r.selected_option for r in results if not r.refusal]

        total = len(results)
        counts = Counter(responses)
        probs = [counts.get(opt, 0) / max(total, 1) for opt in options]
        refusal_prob = refusals / max(total, 1)

        return Distribution(
            probabilities=probs,
            refusal_probability=refusal_prob,
            method="sampling",
            n_samples=total,
        )

    @property
    def supports_distribution(self) -> bool:
        """Whether this provider natively supports distribution output.

        Override to return True if get_distribution() has a native
        implementation (not just repeated sampling).
        """
        return False

    @property
    def prompt_template_source(self) -> str:
        """Deterministic representation of the prompt surface this provider uses.

        Used by the harness to derive ``reproducibility.prompt_template_hash``
        so Tier-3 validation can detect prompt drift between submissions.
        Providers that send text to a model should override this to return
        the literal system + user template strings. Providers that don't
        send a prompt (baselines) can leave it empty.
        """
        return ""

    async def close(self) -> None:
        """Clean up resources (HTTP clients, etc.)."""
        pass

    @property
    @abstractmethod
    def name(self) -> str: ...


def build_persona_system_prompt(base_system: str, persona: PersonaSpec | None) -> str:
    """Build system prompt with optional persona conditioning.

    When persona is provided, replaces the base system prompt with a
    demographics-aware framing that instructs the model to respond
    as a person with those demographic characteristics.
    """
    if persona is None:
        return base_system
    demo_parts = [f"{k}: {v}" for k, v in persona.demographics.items()]
    return (
        f"You are a survey respondent. Demographics: {', '.join(demo_parts)}. "
        "Answer as this person would."
    )
