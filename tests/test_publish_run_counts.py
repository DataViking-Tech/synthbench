"""Tests for run_count / dataset_coverage_count annotation in publish.py.

These fields let the leaderboard's default view hide under-replicated
variant configs without re-grouping in JS (sb-9xw).
"""

from __future__ import annotations

from synthbench.publish import _annotate_run_counts


def _result(
    provider: str,
    dataset: str,
    *,
    temperature: float | None = None,
    prompt_template: str | None = None,
) -> dict:
    cfg: dict = {"provider": provider, "dataset": dataset}
    if temperature is not None:
        cfg["temperature"] = temperature
    if prompt_template is not None:
        cfg["prompt_template"] = prompt_template
    return {"config": cfg}


def _entry(
    model: str,
    framework: str,
    dataset: str,
    *,
    temperature: float | None = None,
    template: str | None = None,
) -> dict:
    e: dict = {"model": model, "framework": framework, "dataset": dataset}
    if temperature is not None:
        e["temperature"] = temperature
    if template is not None:
        e["template"] = template
    return e


def test_run_count_equals_matching_replicates():
    # Three replicates of the same (model, dataset, default temp/tpl) config.
    results = [
        _result("openrouter/openai/gpt-4o-mini", "opinionsqa"),
        _result("openrouter/openai/gpt-4o-mini", "opinionsqa"),
        _result("openrouter/openai/gpt-4o-mini", "opinionsqa"),
    ]
    entries = [_entry("GPT-4o-mini", "raw", "opinionsqa")]
    _annotate_run_counts(entries, results)

    assert entries[0]["run_count"] == 3
    assert entries[0]["dataset_coverage_count"] == 1


def test_run_count_is_zero_when_no_match():
    # Entry references a model with no raw results — survivable, count 0.
    entries = [_entry("Ghost Model", "raw", "opinionsqa")]
    _annotate_run_counts(entries, [])

    assert entries[0]["run_count"] == 0
    assert entries[0]["dataset_coverage_count"] == 0


def test_variants_are_bucketed_by_temperature_and_template():
    # Two runs at t=0.85, one at t=1.0, on the same dataset.
    results = [
        _result("openrouter/openai/gpt-4o-mini", "opinionsqa", temperature=0.85),
        _result("openrouter/openai/gpt-4o-mini", "opinionsqa", temperature=0.85),
        _result("openrouter/openai/gpt-4o-mini", "opinionsqa", temperature=1.0),
    ]
    entries = [
        _entry("GPT-4o-mini", "raw", "opinionsqa", temperature=0.85),
        _entry("GPT-4o-mini", "raw", "opinionsqa", temperature=1.0),
    ]
    _annotate_run_counts(entries, results)

    assert entries[0]["run_count"] == 2
    assert entries[1]["run_count"] == 1
    # Both variants only touched one dataset.
    assert entries[0]["dataset_coverage_count"] == 1
    assert entries[1]["dataset_coverage_count"] == 1


def test_dataset_coverage_counts_distinct_datasets_per_config():
    # Same variant config spans two datasets. Coverage should reflect that
    # independent of per-dataset run counts.
    results = [
        _result("openrouter/openai/gpt-4o-mini", "opinionsqa", temperature=0.85),
        _result("openrouter/openai/gpt-4o-mini", "subpop", temperature=0.85),
    ]
    entries = [
        _entry("GPT-4o-mini", "raw", "opinionsqa", temperature=0.85),
        _entry("GPT-4o-mini", "raw", "subpop", temperature=0.85),
    ]
    _annotate_run_counts(entries, results)

    assert entries[0]["run_count"] == 1
    assert entries[1]["run_count"] == 1
    assert entries[0]["dataset_coverage_count"] == 2
    assert entries[1]["dataset_coverage_count"] == 2


def test_template_stem_matches_entry_template_field():
    # publish.py's _build_entry stores template as Path(tpl).stem, so
    # _annotate_run_counts must stem the raw path to match.
    results = [
        _result(
            "openrouter/openai/gpt-4o-mini",
            "opinionsqa",
            prompt_template="prompts/conditioned/v2.md",
        ),
        _result(
            "openrouter/openai/gpt-4o-mini",
            "opinionsqa",
            prompt_template="prompts/conditioned/v2.md",
        ),
    ]
    entries = [
        _entry("GPT-4o-mini", "raw", "opinionsqa", template="v2"),
    ]
    _annotate_run_counts(entries, results)

    assert entries[0]["run_count"] == 2
    assert entries[0]["dataset_coverage_count"] == 1


def test_suffixed_providers_collapse_to_display_name():
    # Providers suffixed with ' t=... tpl=...' should normalize via
    # display_provider_name and count against the base model row.
    results = [
        _result(
            "synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85 tpl=current",
            "opinionsqa",
            temperature=0.85,
            prompt_template="current",
        ),
        _result(
            "synthpanel/openrouter/anthropic/claude-haiku-4-5",
            "opinionsqa",
            temperature=0.85,
            prompt_template="current",
        ),
    ]
    entries = [
        _entry(
            "SynthPanel (Haiku 4.5)",
            "product",
            "opinionsqa",
            temperature=0.85,
            template="current",
        ),
    ]
    _annotate_run_counts(entries, results)

    assert entries[0]["run_count"] == 2
