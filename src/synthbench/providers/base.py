"""Base provider interface for SynthBench."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Response:
    """A single response from a provider."""

    selected_option: str
    raw_text: str = ""
    metadata: dict | None = None


class Provider(ABC):
    """Interface that all synthetic respondent providers implement.

    Providers answer survey questions by selecting from given options.
    The harness calls respond() multiple times per question to build
    an empirical distribution.
    """

    @abstractmethod
    async def respond(self, question: str, options: list[str]) -> Response:
        """Answer a survey question by selecting one option.

        Args:
            question: The survey question text.
            options: List of answer choices.

        Returns:
            Response with the selected option text.
        """
        ...

    async def close(self) -> None:
        """Clean up resources (HTTP clients, etc.)."""
        pass

    @property
    @abstractmethod
    def name(self) -> str: ...
