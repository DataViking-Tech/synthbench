"""Tests for synthbench.config_id — provider parsing and canonical slugging."""

from __future__ import annotations

from synthbench.config_id import (
    ParsedConfig,
    build_config_id,
    parse_provider,
)


class TestParseProvider:
    def test_openrouter_three_parts(self):
        p = parse_provider("openrouter/openai/gpt-4o-mini")
        assert p == ParsedConfig(
            framework="openrouter",
            base_provider="openai",
            model="gpt-4o-mini",
            knobs={},
        )

    def test_synthpanel_nested_four_parts(self):
        p = parse_provider("synthpanel/openrouter/anthropic/claude-haiku-4-5")
        assert p.framework == "synthpanel"
        assert p.base_provider == "anthropic"
        assert p.model == "claude-haiku-4-5"
        assert p.knobs == {}

    def test_raw_anthropic_two_parts(self):
        p = parse_provider("raw-anthropic/claude-haiku-4-5-20251001")
        assert p.framework == "raw"
        assert p.base_provider == "anthropic"
        assert p.model == "claude-haiku-4-5-20251001"

    def test_raw_gemini(self):
        p = parse_provider("raw-gemini/gemini-2.5-flash-lite")
        assert p.framework == "raw"
        assert p.base_provider == "gemini"
        assert p.model == "gemini-2.5-flash-lite"

    def test_ensemble(self):
        p = parse_provider("ensemble/3-model-blend")
        assert p.framework == "ensemble"
        assert p.base_provider is None
        assert p.model == "3-model-blend"

    def test_random_baseline(self):
        p = parse_provider("random-baseline")
        assert p.framework == "baseline"
        assert p.base_provider is None
        assert p.model == "random-baseline"

    def test_majority_baseline(self):
        p = parse_provider("majority-baseline")
        assert p.framework == "baseline"
        assert p.base_provider is None
        assert p.model == "majority-baseline"

    def test_synthpanel_direct(self):
        p = parse_provider("synthpanel/claude-haiku-4-5-20251001")
        assert p.framework == "synthpanel"
        assert p.base_provider is None
        assert p.model == "claude-haiku-4-5-20251001"

    def test_knobs_parsed(self):
        p = parse_provider(
            "synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85 tpl=current"
        )
        assert p.knobs == {"t": "0.85", "tpl": "current"}

    def test_knobs_order_independent(self):
        a = parse_provider("synthpanel/x/y/z t=0.5 tpl=minimal")
        b = parse_provider("synthpanel/x/y/z tpl=minimal t=0.5")
        assert a.knobs == b.knobs

    def test_malformed_knob_ignored(self):
        p = parse_provider("synthpanel/x/y/z notakey t=0.5")
        assert p.knobs == {"t": "0.5"}

    def test_empty_string(self):
        p = parse_provider("")
        assert p.framework == "unknown"
        assert p.model == "unknown"

    def test_extra_whitespace_tolerated(self):
        p = parse_provider("  openrouter/openai/gpt-4o-mini   t=0.7  ")
        assert p.model == "gpt-4o-mini"
        assert p.knobs == {"t": "0.7"}


class TestBuildConfigId:
    def test_slug_shape(self):
        slug, _ = build_config_id(
            "synthpanel/openrouter/anthropic/claude-haiku-4-5",
            dataset="opinionsqa",
            temperature=0.85,
            template="current",
        )
        # framework--model--t<temp>--tpl<name>--<hash8>
        parts = slug.split("--")
        assert len(parts) == 5
        assert parts[0] == "synthpanel"
        assert parts[1] == "claude-haiku-4-5"
        assert parts[2] == "t0.85"
        assert parts[3] == "tplcurrent"
        assert len(parts[4]) == 8
        assert all(c in "0123456789abcdef" for c in parts[4])

    def test_hash_deterministic(self):
        args = {
            "provider": "synthpanel/openrouter/openai/gpt-4o-mini",
            "dataset": "opinionsqa",
            "temperature": 0.5,
            "template": "current",
        }
        s1, _ = build_config_id(**args)
        s2, _ = build_config_id(**args)
        assert s1 == s2

    def test_knob_order_does_not_affect_hash(self):
        """Same canonical config from different provider-string orderings
        must produce the same slug."""
        s1, _ = build_config_id(
            "synthpanel/x/y/z t=0.85 tpl=current",
            dataset="opinionsqa",
        )
        s2, _ = build_config_id(
            "synthpanel/x/y/z tpl=current t=0.85",
            dataset="opinionsqa",
        )
        assert s1 == s2

    def test_collision_resistance_on_samples(self):
        """Two runs identical in framework/model/temp/template but differing
        in samples_per_question must produce different config IDs."""
        s1, _ = build_config_id(
            "synthpanel/x/y/z",
            dataset="opinionsqa",
            temperature=0.85,
            template="current",
            samples_per_question=30,
        )
        s2, _ = build_config_id(
            "synthpanel/x/y/z",
            dataset="opinionsqa",
            temperature=0.85,
            template="current",
            samples_per_question=100,
        )
        assert s1 != s2
        # But only the hash suffix differs — the human slug stays readable
        assert s1.split("--")[:4] == s2.split("--")[:4]

    def test_collision_resistance_on_question_set(self):
        s1, _ = build_config_id(
            "synthpanel/x/y/z",
            dataset="opinionsqa",
            temperature=0.85,
            template="current",
            question_set_hash="abc123",
        )
        s2, _ = build_config_id(
            "synthpanel/x/y/z",
            dataset="opinionsqa",
            temperature=0.85,
            template="current",
            question_set_hash="def456",
        )
        assert s1 != s2

    def test_collision_resistance_on_dataset(self):
        s_oqa, _ = build_config_id(
            "synthpanel/x/y/z",
            dataset="opinionsqa",
            temperature=0.85,
            template="current",
        )
        s_sub, _ = build_config_id(
            "synthpanel/x/y/z",
            dataset="subpop",
            temperature=0.85,
            template="current",
        )
        assert s_oqa != s_sub

    def test_default_temperature(self):
        slug, _ = build_config_id(
            "random-baseline",
            dataset="opinionsqa",
            temperature=None,
            template=None,
        )
        parts = slug.split("--")
        assert parts[2] == "tdefault"
        assert parts[3] == "tplcurrent"

    def test_explicit_temperature_overrides_knob(self):
        """The real config.temperature should win over knob ``t=`` in the
        provider string — the knob is advisory and may lag the actual run."""
        slug, parsed = build_config_id(
            "synthpanel/x/y/z t=0.3",
            dataset="opinionsqa",
            temperature=0.85,
            template="current",
        )
        assert "t0.85" in slug
        assert parsed.knobs["t"] == "0.85"

    def test_template_path_stripped(self):
        """Template stored as a file path should have extension/dir stripped."""
        slug, _ = build_config_id(
            "synthpanel/x/y/z",
            dataset="opinionsqa",
            temperature=0.85,
            template="templates/minimal.md",
        )
        parts = slug.split("--")
        assert parts[3] == "tplminimal"

    def test_baseline_slug(self):
        slug, parsed = build_config_id(
            "random-baseline",
            dataset="opinionsqa",
        )
        assert slug.startswith("baseline--random-baseline--")
        assert parsed.framework == "baseline"

    def test_ensemble_slug(self):
        slug, parsed = build_config_id(
            "ensemble/3-model-blend",
            dataset="opinionsqa",
            temperature=0.0,
        )
        assert slug.startswith("ensemble--3-model-blend--")
        assert parsed.framework == "ensemble"
