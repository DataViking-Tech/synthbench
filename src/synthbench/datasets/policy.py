"""Dataset redistribution policy lookup.

Adapter classes in ``synthbench.datasets`` are the source of truth for
per-dataset redistribution policy via the ``redistribution_policy``,
``license_url``, and ``citation`` class attributes on each :class:`Dataset`
subclass. This module exposes a flat name-keyed lookup so the publish step
can resolve a policy from the dataset string stored in raw result files
without importing every adapter class at the call site.

Policy tiers are documented on :class:`synthbench.datasets.base.Dataset`.
The conservative default for any unknown or unregistered dataset name is
``aggregates_only`` — per-question ``human_distribution`` stays suppressed
unless an adapter explicitly opts in to ``full`` redistribution.
"""

from __future__ import annotations

from dataclasses import dataclass

from synthbench.datasets import DATASETS
from synthbench.datasets.base import RedistributionPolicy


@dataclass(frozen=True)
class DatasetPolicy:
    """Resolved redistribution policy + provenance for a dataset."""

    name: str
    redistribution_policy: RedistributionPolicy
    license_url: str | None
    citation: str | None

    @property
    def suppress_human_distribution(self) -> bool:
        """True if per-question human_distribution should be withheld."""
        return self.redistribution_policy != "full"

    @property
    def suppress_per_question(self) -> bool:
        """True if per-question payloads should not be published at all."""
        return self.redistribution_policy == "citation_only"


_DEFAULT_POLICY = DatasetPolicy(
    name="unknown",
    redistribution_policy="aggregates_only",
    license_url=None,
    citation=None,
)


def _base_name(dataset_name: str) -> str:
    """Strip ``(filter)`` suffix from dataset names like ``gss (2018)``.

    Country- and year-filtered adapter variants share the same license as
    their parent dataset, so policy lookup uses the base name.
    """
    return dataset_name.split(" ", 1)[0].strip()


def policy_for(dataset_name: str) -> DatasetPolicy:
    """Return the policy for a dataset name as it appears in result files.

    Falls back to ``aggregates_only`` for unknown datasets; this keeps the
    publish step conservative if a new adapter is added without registering
    a policy decision.
    """
    base = _base_name(dataset_name)
    adapter = DATASETS.get(base)
    if adapter is None:
        return DatasetPolicy(
            name=base,
            redistribution_policy=_DEFAULT_POLICY.redistribution_policy,
            license_url=None,
            citation=None,
        )
    return DatasetPolicy(
        name=base,
        redistribution_policy=adapter.redistribution_policy,
        license_url=adapter.license_url,
        citation=adapter.citation,
    )


def all_policies() -> list[DatasetPolicy]:
    """Return policies for every registered adapter, sorted by name.

    Used by the publish step to emit a dataset policy manifest and by the
    methodology page to render the provenance table.
    """
    out: list[DatasetPolicy] = []
    for name in sorted(DATASETS):
        out.append(policy_for(name))
    return out


__all__ = ["DatasetPolicy", "policy_for", "all_policies"]
