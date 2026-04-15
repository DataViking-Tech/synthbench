"""Base dataset interface for SynthBench."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

RedistributionPolicy = Literal["full", "aggregates_only", "citation_only"]


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
    """Interface that all benchmark datasets implement.

    Subclasses declare their redistribution policy and provenance so the
    publish step can honor upstream license terms. Three tiers:

    ``full``
        Per-question human distributions are OK to publish publicly. Use only
        when the upstream license is unambiguously permissive (e.g. U.S.
        Government public domain under 17 USC 105).

    ``aggregates_only`` (default)
        Only aggregate scores (SPS, JSD, cross-model metrics, ranks) are
        public. Per-question ``human_distribution`` and ``human_refusal_rate``
        are suppressed from published artifacts. This is the safe default for
        any license with redistribution restrictions, attribution-required
        terms, non-commercial clauses, or ambiguous/missing license info.

    ``citation_only``
        Only metadata (question text, options) public; both per-question and
        aggregate metrics are suppressed. Reserved for datasets where we have
        no redistribution rights at all.

    Provenance attributes (``license_url``, ``citation``) are surfaced on the
    per-question and methodology pages regardless of policy.
    """

    # Conservative default: if an adapter forgets to declare, nothing
    # per-question ships. Override on each concrete adapter.
    redistribution_policy: RedistributionPolicy = "aggregates_only"
    license_url: str | None = None
    citation: str | None = None

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
