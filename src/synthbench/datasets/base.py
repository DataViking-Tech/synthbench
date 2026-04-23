"""Base dataset interface for SynthBench."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

RedistributionPolicy = Literal["full", "gated", "aggregates_only", "citation_only"]


@dataclass
class MicrodataRow:
    """One survey respondent's individual-level answers.

    Microdata enables real-sampling convergence analysis: drawing a random
    subsample of N actual respondents (without replacement) and measuring
    JSD vs. the full-population distribution. Aggregates alone cannot
    support this -- once the per-respondent row is collapsed, the
    population-heterogeneity signal is gone.

    Attributes:
        respondent_id: Stable identifier within the dataset (need not be
            unique across datasets). Used for sub-sampling without
            replacement and reproducibility.
        survey_wave: Wave / year identifier (e.g. ``"GSS:2022"``,
            ``"WVS:wave7"``). Free-form per dataset.
        responses: ``question_key -> option_key`` answers from this
            respondent. Sparse: questions the respondent skipped or were not
            asked are simply absent.
        subgroup: Optional demographic / cell labels (``age_band``,
            ``region``, ``education``, ...). Reserved for future stratified
            convergence; the base sub-sampling pass ignores this field.
    """

    respondent_id: str
    survey_wave: str
    responses: dict[str, str]
    subgroup: dict[str, str] = field(default_factory=dict)


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
    publish step can honor upstream license terms. Four tiers:

    ``full``
        Per-question human distributions are OK to publish publicly. Use only
        when the upstream license is unambiguously permissive (e.g. U.S.
        Government public domain under 17 USC 105, or explicit public-domain
        release). Per-question/run/config JSONs ship to the static site.

    ``gated``
        Redistribution is permitted only under a research-use license that
        requires controlled distribution. Per-question/run/config artifacts
        ship to a private Cloudflare R2 bucket fronted by a JWT-authenticated
        Worker; authenticated users who identify themselves can see the full
        per-question ``human_distribution``. Anonymous visitors see a
        sign-in gate.

    ``aggregates_only`` (default)
        Only aggregate scores (SPS, JSD, cross-model metrics, ranks) are
        public. No per-question/run/config artifact ships — neither to the
        static site nor to R2. This is the safe default for any license with
        ambiguous/missing redistribution rights, where even gated
        distribution would exceed the permission granted.

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

    def load_microdata(self, n: int | None = None) -> list[MicrodataRow]:
        """Return per-respondent rows. Optional capability.

        Datasets that only ship aggregate distributions raise
        :class:`MicrodataNotAvailable`. Adapters that ingest microdata
        override to return a list (truncated to ``n`` if given).
        """
        raise MicrodataNotAvailable(
            f"dataset {self.name!r} does not provide individual-level microdata"
        )

    def load_microdata_for_question(self, key: str) -> list[MicrodataRow]:
        """Rows whose ``responses`` include the given question key.

        Default implementation filters :meth:`load_microdata`. Adapters with
        a more efficient column-oriented store should override.
        """
        return [r for r in self.load_microdata() if key in r.responses]


class MicrodataNotAvailable(NotImplementedError):
    """Raised by adapters that do not ship individual-level microdata."""


class DatasetDownloadError(Exception):
    """Raised when an adapter cannot fetch or load its raw data files.

    Shared across all adapters so callers can catch a single class rather
    than importing per-adapter variants or duck-typing on class name.
    """
