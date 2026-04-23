"""Drift-guard for site/src/components/methodology/DatasetCards.astro (sb-newy).

The methodology page renders nine dataset cards from a hard-coded list in
``DatasetCards.astro``. If a new adapter is registered in
:data:`synthbench.datasets.DATASETS` without a matching card, or a card is
added without a corresponding adapter, the public methodology page silently
drifts out of sync with what the harness actually runs. This test pins that
set equality via each card's ``slug`` field.

The test also verifies each card declares a redistribution ``tier`` that
matches the adapter's :attr:`Dataset.redistribution_policy`, so the public
page never labels a ``gated`` dataset ``full`` (or vice versa) by accident.
"""

from __future__ import annotations

import re
from pathlib import Path

from synthbench.datasets import DATASETS

_COMPONENT_PATH = (
    Path(__file__).resolve().parent.parent
    / "site"
    / "src"
    / "components"
    / "methodology"
    / "DatasetCards.astro"
)


def _parse_card_entries() -> list[dict[str, str]]:
    """Extract ``(slug, tier)`` pairs from DatasetCards.astro.

    The component defines a ``datasets: DatasetCard[]`` array with object
    literals that begin ``{ slug: "...", name: "...", tier: "...", ...``.
    We parse only ``slug`` and ``tier`` strings; full TS-AST parsing would
    require a JS toolchain the Python suite doesn't otherwise need.
    """
    source = _COMPONENT_PATH.read_text()
    # Split on object boundaries that start with a `slug:` field. Each
    # entry is matched up to the next top-level `slug:` or the closing
    # `];` of the array, whichever comes first.
    entries: list[dict[str, str]] = []
    pattern = re.compile(
        r'slug:\s*"(?P<slug>[^"]+)"(?P<body>.*?)(?=slug:\s*"|\];)',
        re.DOTALL,
    )
    for match in pattern.finditer(source):
        tier_match = re.search(r'tier:\s*"(?P<tier>[^"]+)"', match.group("body"))
        assert tier_match, f"card slug={match.group('slug')!r} missing tier field"
        entries.append({"slug": match.group("slug"), "tier": tier_match.group("tier")})
    return entries


def test_component_lists_every_registered_dataset():
    """Every adapter in DATASETS must have exactly one card; no extras."""
    entries = _parse_card_entries()
    card_slugs = {e["slug"] for e in entries}
    registry_slugs = set(DATASETS.keys())

    missing_from_cards = registry_slugs - card_slugs
    extra_in_cards = card_slugs - registry_slugs
    assert not missing_from_cards, (
        f"DatasetCards.astro missing cards for registered adapters: "
        f"{sorted(missing_from_cards)}. Add a card entry in "
        f"site/src/components/methodology/DatasetCards.astro."
    )
    assert not extra_in_cards, (
        f"DatasetCards.astro has cards for un-registered adapters: "
        f"{sorted(extra_in_cards)}. Remove the stale entries or register the "
        f"adapter in src/synthbench/datasets/__init__.py."
    )
    # Card slug list must be unique — a duplicate would render two cards for
    # the same dataset and silently pass the set-equality check above.
    slugs = [e["slug"] for e in entries]
    assert len(slugs) == len(set(slugs)), (
        f"DatasetCards.astro has duplicate slugs: {slugs}"
    )


def test_component_tier_labels_match_adapter_policy():
    """Each card's tier label matches the adapter's redistribution_policy.

    Only ``full`` and ``gated`` datasets get cards on the methodology page;
    the card component's type system restricts ``tier`` to those two values.
    If an adapter switches to ``aggregates_only`` or ``citation_only`` it
    should either be removed from the cards or the card component must be
    extended to represent the suppressed tier.
    """
    entries_by_slug = {e["slug"]: e for e in _parse_card_entries()}
    for slug, adapter in DATASETS.items():
        policy = adapter.redistribution_policy
        card = entries_by_slug.get(slug)
        assert card is not None, f"no card for adapter {slug!r}"
        assert card["tier"] == policy, (
            f"card slug={slug!r} declares tier={card['tier']!r} but adapter "
            f"{adapter.__name__}.redistribution_policy={policy!r}. Update the "
            f"card or the adapter so both agree."
        )
