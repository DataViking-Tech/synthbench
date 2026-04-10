"""Base dataset interface for SynthBench."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Question:
    """A survey question with ground-truth human response distribution."""

    key: str
    text: str
    options: list[str]
    human_distribution: dict[str, float]
    survey: str = ""
    topic: str = ""

    def __post_init__(self):
        total = sum(self.human_distribution.values())
        if abs(total - 1.0) > 0.01 and total > 0:
            # Renormalize
            self.human_distribution = {
                k: v / total for k, v in self.human_distribution.items()
            }


class Dataset(ABC):
    """Interface that all benchmark datasets implement."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def load(self, n: int | None = None) -> list[Question]:
        """Load questions. If n is set, return at most n questions."""
        ...

    @abstractmethod
    def info(self) -> dict:
        """Return metadata about the dataset (source, size, etc.)."""
        ...
