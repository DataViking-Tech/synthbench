"""Tests for per-dataset redistribution policy declarations (sb-r8n).

Every adapter must declare an explicit ``redistribution_policy`` tier; the
publish pipeline reads this via :mod:`synthbench.datasets.policy` to decide
which per-question fields appear in public artifacts.
"""

from __future__ import annotations

import pytest

from synthbench.datasets import (
    DATASETS,
    EurobarometerConsumerDataset,
    GlobalOpinionQADataset,
    GSSDataset,
    MichiganSentimentDataset,
    NTIADataset,
    OpinionsQADataset,
    PewTechDataset,
    SubPOPDataset,
    WVSDataset,
)
from synthbench.datasets.base import Dataset
from synthbench.datasets.policy import (
    DatasetPolicy,
    all_policies,
    policy_for,
)

VALID_TIERS = {"full", "aggregates_only", "citation_only"}


# -- Per-adapter declaration ------------------------------------------------


@pytest.mark.parametrize("adapter", list(DATASETS.values()))
def test_every_adapter_declares_policy(adapter: type[Dataset]):
    """Every registered adapter exposes a valid tier + citation + URL."""
    assert adapter.redistribution_policy in VALID_TIERS, (
        f"{adapter.__name__} tier={adapter.redistribution_policy!r} not in {VALID_TIERS}"
    )
    # Citation + license URL are human-visible provenance; neither should be
    # missing for an adapter we actively ship.
    assert adapter.citation, f"{adapter.__name__} missing citation"
    assert adapter.license_url, f"{adapter.__name__} missing license_url"


def test_base_dataset_defaults_conservative():
    """The ABC default must be the safest tier so a new adapter that forgets
    to declare policy won't accidentally leak per-question human data."""
    assert Dataset.redistribution_policy == "aggregates_only"
    assert Dataset.license_url is None
    assert Dataset.citation is None


def test_ntia_is_full_redistribution():
    """NTIA is U.S. Government public-domain (17 USC 105) — the one `full`
    adapter currently shipped. If this flips, founder review must sign off
    via an updated audit."""
    assert NTIADataset.redistribution_policy == "full"
    assert "ntia.gov" in (NTIADataset.license_url or "")
    assert "17 USC 105" in (NTIADataset.citation or "")


@pytest.mark.parametrize(
    "adapter",
    [
        GlobalOpinionQADataset,
        GSSDataset,
        MichiganSentimentDataset,
        SubPOPDataset,
        WVSDataset,
        EurobarometerConsumerDataset,
        OpinionsQADataset,
        PewTechDataset,
    ],
)
def test_restricted_adapters_are_aggregates_only(adapter: type[Dataset]):
    """Every adapter whose upstream carries any restriction is tiered
    ``aggregates_only`` per the conservative rubric."""
    assert adapter.redistribution_policy == "aggregates_only"


# -- Policy lookup ----------------------------------------------------------


def test_policy_for_known_dataset():
    p = policy_for("opinionsqa")
    assert isinstance(p, DatasetPolicy)
    assert p.redistribution_policy == "aggregates_only"
    assert p.suppress_human_distribution is True
    assert p.suppress_per_question is False
    assert p.citation is not None
    assert p.license_url is not None


def test_policy_for_full_tier():
    p = policy_for("ntia")
    assert p.redistribution_policy == "full"
    assert p.suppress_human_distribution is False
    assert p.suppress_per_question is False


def test_policy_for_strips_filter_suffix():
    """`gss (2018)` should resolve to the same policy as `gss`."""
    base = policy_for("gss")
    filtered = policy_for("gss (2018)")
    assert base.redistribution_policy == filtered.redistribution_policy
    assert base.citation == filtered.citation


def test_policy_for_unknown_defaults_aggregates_only():
    """Unregistered dataset names fall back to the safest tier."""
    p = policy_for("does-not-exist")
    assert p.redistribution_policy == "aggregates_only"
    assert p.citation is None
    assert p.license_url is None
    assert p.suppress_human_distribution is True


def test_all_policies_covers_every_registered_dataset():
    names = {p.name for p in all_policies()}
    assert names == set(DATASETS.keys())


def test_dataset_policy_suppress_flags():
    """DatasetPolicy derives suppression booleans from the tier."""
    p_full = DatasetPolicy(
        name="n", redistribution_policy="full", license_url=None, citation=None
    )
    p_aggr = DatasetPolicy(
        name="n",
        redistribution_policy="aggregates_only",
        license_url=None,
        citation=None,
    )
    p_cite = DatasetPolicy(
        name="n",
        redistribution_policy="citation_only",
        license_url=None,
        citation=None,
    )
    assert p_full.suppress_human_distribution is False
    assert p_full.suppress_per_question is False
    assert p_aggr.suppress_human_distribution is True
    assert p_aggr.suppress_per_question is False
    assert p_cite.suppress_human_distribution is True
    assert p_cite.suppress_per_question is True
