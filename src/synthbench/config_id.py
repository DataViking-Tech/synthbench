"""Canonical config ID parsing for the run explorer.

Turns raw provider strings like
``synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85 tpl=current``
into a structured record (framework / base_provider / model / knobs) and a
stable slug ``framework--model--t<temp>--tpl<name>--<hash8>`` suitable for
use as a URL path segment.

Hash collisions are unlikely but protected against by including every
distinguishing field (dataset, samples_per_question, question_set_hash,
full knob map) in the hashed canonical JSON — so two runs that differ only
in a field the human-readable slug drops still land on different IDs.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BASELINE_SUFFIX = "-baseline"


@dataclass(frozen=True)
class ParsedConfig:
    """Structured breakdown of a provider string + run config."""

    framework: str
    base_provider: str | None
    model: str
    knobs: dict[str, str] = field(default_factory=dict)

    def as_canonical_dict(self) -> dict[str, Any]:
        """Return a dict with stable key ordering for hashing."""
        return {
            "framework": self.framework,
            "base_provider": self.base_provider,
            "model": self.model,
            "knobs": dict(sorted(self.knobs.items())),
        }


def _split_provider_and_knobs(provider: str) -> tuple[str, list[str]]:
    """Split the whitespace-separated provider/knob form.

    ``synthpanel/.../claude-haiku-4-5 t=0.85 tpl=current`` →
    (``synthpanel/.../claude-haiku-4-5``, [``t=0.85``, ``tpl=current``]).
    """
    tokens = provider.strip().split()
    if not tokens:
        return "", []
    return tokens[0], tokens[1:]


def _parse_knob_tokens(tokens: list[str]) -> dict[str, str]:
    """Turn ``[``t=0.85``, ``tpl=current``]`` into a dict."""
    knobs: dict[str, str] = {}
    for tok in tokens:
        if "=" not in tok:
            continue
        key, value = tok.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            knobs[key] = value
    return knobs


def _parse_path(path: str) -> tuple[str, str | None, str]:
    """Parse the slash-separated path component into (framework, base, model).

    Recognizes these shapes:
        random-baseline                 → ("baseline", None, "random-baseline")
        raw-anthropic/claude-haiku-4-5  → ("raw", "anthropic", "claude-haiku-4-5")
        ensemble/3-model-blend          → ("ensemble", None, "3-model-blend")
        synthpanel/gemini-flash-lite    → ("synthpanel", None, "gemini-flash-lite")
        openrouter/openai/gpt-4o-mini   → ("openrouter", "openai", "gpt-4o-mini")
        synthpanel/openrouter/anthropic/claude-haiku-4-5
                                        → ("synthpanel", "anthropic", "claude-haiku-4-5")
    """
    path = path.strip()
    if not path:
        return "unknown", None, "unknown"

    if path.endswith(BASELINE_SUFFIX) and "/" not in path:
        return "baseline", None, path

    parts = path.split("/")
    n = len(parts)

    if n == 1:
        return "raw", None, parts[0]

    first = parts[0]

    if first.startswith("raw-"):
        return "raw", first[4:], parts[-1]

    if n == 2:
        return first, None, parts[1]

    if n == 3:
        return first, parts[1], parts[2]

    # n >= 4 — treat second segment as a sub-framework we don't surface,
    # take the last two as (base, model).
    return first, parts[-2], parts[-1]


def parse_provider(provider: str) -> ParsedConfig:
    """Parse a provider string into a structured ParsedConfig.

    Whitespace-tolerant. Unknown shapes degrade gracefully to framework='raw'.
    """
    head, knob_tokens = _split_provider_and_knobs(provider)
    framework, base, model = _parse_path(head)
    knobs = _parse_knob_tokens(knob_tokens)
    return ParsedConfig(
        framework=framework,
        base_provider=base,
        model=model,
        knobs=knobs,
    )


_SLUG_UNSAFE = re.compile(r"[^a-z0-9.\-]+")


def _slugify(value: str) -> str:
    """Lowercase and strip characters that would break a URL segment.

    Preserves dots for version numbers (``t=0.85`` → ``t0.85``).
    """
    out = _SLUG_UNSAFE.sub("-", value.lower())
    return out.strip("-")


def _format_temperature(temp: str | float | int | None) -> str:
    """Render the temperature portion of the slug.

    ``0.85 → 't0.85'``, ``1.0 → 't1.0'``, ``None → 'tdefault'``.
    """
    if temp is None or temp == "":
        return "tdefault"
    if isinstance(temp, (int, float)):
        return f"t{temp}"
    return f"t{temp}"


def _format_template(tpl: str | None) -> str:
    if not tpl:
        return "tplcurrent"
    return f"tpl{_slugify(tpl)}"


def _hash_canonical(payload: dict[str, Any]) -> str:
    """Stable 8-char hex hash over a canonical JSON dump."""
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:8]


def build_config_id(
    provider: str,
    *,
    dataset: str | None = None,
    temperature: float | None = None,
    template: str | None = None,
    samples_per_question: int | None = None,
    question_set_hash: str | None = None,
    extra_knobs: dict[str, Any] | None = None,
) -> tuple[str, ParsedConfig]:
    """Return (config_id_slug, parsed) for a run.

    Accepts structured fields extracted from the result file's ``config``
    block. Values passed explicitly override knobs parsed from the provider
    string (e.g. ``t=0.85`` vs the real ``config.temperature``).
    """
    parsed = parse_provider(provider)

    # Normalize template: drop path + extension
    tpl_norm = None
    if template:
        tpl_norm = (
            Path(template).stem
            if ("/" in template or template.endswith(".md"))
            else template
        )
    elif "tpl" in parsed.knobs:
        tpl_norm = parsed.knobs["tpl"]

    # Temperature: prefer explicit config value over knob string
    temp_val: float | str | None = temperature
    if temp_val is None and "t" in parsed.knobs:
        try:
            temp_val = float(parsed.knobs["t"])
        except ValueError:
            temp_val = parsed.knobs["t"]

    # Canonicalize the full knob map for the hash
    canonical_knobs: dict[str, Any] = dict(parsed.knobs)
    if temp_val is not None:
        canonical_knobs["t"] = temp_val
    if tpl_norm is not None:
        canonical_knobs["tpl"] = tpl_norm
    if extra_knobs:
        canonical_knobs.update(extra_knobs)

    hash_payload: dict[str, Any] = {
        "framework": parsed.framework,
        "base_provider": parsed.base_provider,
        "model": parsed.model,
        "knobs": {k: canonical_knobs[k] for k in sorted(canonical_knobs)},
    }
    if dataset is not None:
        hash_payload["dataset"] = dataset
    if samples_per_question is not None:
        hash_payload["samples_per_question"] = samples_per_question
    if question_set_hash is not None:
        hash_payload["question_set_hash"] = question_set_hash

    hash8 = _hash_canonical(hash_payload)

    slug_model = _slugify(parsed.model)
    slug_framework = _slugify(parsed.framework)
    temp_part = _format_temperature(temp_val)
    tpl_part = _format_template(tpl_norm)

    slug = f"{slug_framework}--{slug_model}--{temp_part}--{tpl_part}--{hash8}"

    # Refresh parsed.knobs to include normalized t/tpl for downstream callers
    resolved_knobs: dict[str, str] = dict(parsed.knobs)
    if temp_val is not None:
        resolved_knobs["t"] = str(temp_val)
    if tpl_norm is not None:
        resolved_knobs["tpl"] = tpl_norm

    return slug, ParsedConfig(
        framework=parsed.framework,
        base_provider=parsed.base_provider,
        model=parsed.model,
        knobs=resolved_knobs,
    )
