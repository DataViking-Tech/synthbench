"""Tests that providers populate Response.metadata['usage'] from SDK usage."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


# ---------- raw-anthropic ----------


@pytest.mark.asyncio
async def test_raw_anthropic_captures_usage(monkeypatch):
    pytest.importorskip("anthropic")
    from synthbench.providers.raw_anthropic import RawAnthropicProvider

    fake_message = SimpleNamespace(
        content=[SimpleNamespace(text="A")],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=42, output_tokens=3),
    )
    provider = RawAnthropicProvider(model="claude-haiku-4-5")
    provider._client = SimpleNamespace(
        messages=SimpleNamespace(create=AsyncMock(return_value=fake_message)),
        close=AsyncMock(),
    )

    resp = await provider.respond("Q?", ["alpha", "beta"])

    assert resp.metadata["usage"] == {"input_tokens": 42, "output_tokens": 3}
    assert resp.selected_option == "alpha"


@pytest.mark.asyncio
async def test_raw_anthropic_handles_missing_usage(monkeypatch):
    pytest.importorskip("anthropic")
    from synthbench.providers.raw_anthropic import RawAnthropicProvider

    fake_message = SimpleNamespace(
        content=[SimpleNamespace(text="A")],
        stop_reason="end_turn",
        usage=None,
    )
    provider = RawAnthropicProvider(model="claude-haiku-4-5")
    provider._client = SimpleNamespace(
        messages=SimpleNamespace(create=AsyncMock(return_value=fake_message)),
        close=AsyncMock(),
    )

    resp = await provider.respond("Q?", ["alpha", "beta"])
    assert resp.metadata["usage"] is None


# ---------- raw-openai ----------


def _fake_openai_resp(content: str, usage=None):
    choice = SimpleNamespace(
        message=SimpleNamespace(content=content),
        finish_reason="stop",
    )
    return SimpleNamespace(choices=[choice], usage=usage)


@pytest.mark.asyncio
async def test_raw_openai_captures_usage(monkeypatch):
    pytest.importorskip("openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    from synthbench.providers.raw_openai import RawOpenAIProvider

    fake_resp = _fake_openai_resp(
        "B", usage=SimpleNamespace(prompt_tokens=20, completion_tokens=4)
    )
    provider = RawOpenAIProvider(model="gpt-4o-mini")
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(return_value=fake_resp))
        ),
        close=AsyncMock(),
    )

    resp = await provider.respond("Q?", ["alpha", "beta"])
    assert resp.metadata["usage"] == {"input_tokens": 20, "output_tokens": 4}
    assert resp.selected_option == "beta"


@pytest.mark.asyncio
async def test_raw_openai_handles_missing_usage(monkeypatch):
    pytest.importorskip("openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    from synthbench.providers.raw_openai import RawOpenAIProvider

    fake_resp = _fake_openai_resp("A", usage=None)
    provider = RawOpenAIProvider(model="gpt-4o-mini")
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(return_value=fake_resp))
        ),
        close=AsyncMock(),
    )
    resp = await provider.respond("Q?", ["alpha", "beta"])
    assert resp.metadata["usage"] is None


# ---------- raw-gemini ----------


@pytest.mark.asyncio
async def test_raw_gemini_captures_usage(monkeypatch):
    pytest.importorskip("openai")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from synthbench.providers.raw_gemini import RawGeminiProvider

    fake_resp = _fake_openai_resp(
        "A", usage=SimpleNamespace(prompt_tokens=11, completion_tokens=2)
    )
    provider = RawGeminiProvider(model="gemini-2.5-flash-lite")
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(return_value=fake_resp))
        ),
        close=AsyncMock(),
    )

    resp = await provider.respond("Q?", ["alpha", "beta"])
    assert resp.metadata["usage"] == {"input_tokens": 11, "output_tokens": 2}


# ---------- openrouter ----------


@pytest.mark.asyncio
async def test_openrouter_captures_usage(monkeypatch):
    pytest.importorskip("openai")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    from synthbench.providers.openrouter import OpenRouterProvider

    fake_resp = _fake_openai_resp(
        "B", usage=SimpleNamespace(prompt_tokens=8, completion_tokens=1)
    )
    provider = OpenRouterProvider(model="openai/gpt-4o-mini")
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(return_value=fake_resp))
        ),
        close=AsyncMock(),
    )

    resp = await provider.respond("Q?", ["alpha", "beta"])
    assert resp.metadata["usage"] == {"input_tokens": 8, "output_tokens": 1}


# ---------- ollama ----------


@pytest.mark.asyncio
async def test_ollama_usage_none(monkeypatch):
    pytest.importorskip("openai")
    from synthbench.providers.ollama import OllamaProvider

    fake_resp = _fake_openai_resp(
        "A",
        usage=SimpleNamespace(prompt_tokens=99, completion_tokens=99),
    )
    provider = OllamaProvider(model="llama3")
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(return_value=fake_resp))
        ),
        close=AsyncMock(),
    )

    resp = await provider.respond("Q?", ["alpha", "beta"])
    # Ollama deliberately ignores any usage — keep null for type consistency.
    assert resp.metadata["usage"] is None


# ---------- prompt_template_source (sb-okdx) ----------
#
# Every provider that sends a prompt to a model must expose a non-empty
# prompt_template_source so the runner can derive a stable Tier-3
# prompt_template_hash. If a provider omits this, its submissions will
# silently hash to the empty-string digest and Tier-3 drift detection
# becomes useless.


def test_raw_anthropic_exposes_prompt_template_source(monkeypatch):
    pytest.importorskip("anthropic")
    from synthbench.providers.raw_anthropic import RawAnthropicProvider

    p = RawAnthropicProvider(model="claude-haiku-4-5")
    p._client = SimpleNamespace(close=AsyncMock())
    assert "Respond with ONLY the letter" in p.prompt_template_source


def test_raw_openai_exposes_prompt_template_source(monkeypatch):
    pytest.importorskip("openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    from synthbench.providers.raw_openai import RawOpenAIProvider

    p = RawOpenAIProvider(model="gpt-4o-mini")
    p._client = SimpleNamespace(close=AsyncMock())
    assert "Respond with ONLY the letter" in p.prompt_template_source


def test_baseline_providers_have_empty_template():
    """Baselines don't prompt a model — empty template is the honest answer."""
    from synthbench.providers.random_baseline import RandomBaselineProvider
    from synthbench.providers.majority_baseline import MajorityBaselineProvider

    assert RandomBaselineProvider().prompt_template_source == ""
    assert MajorityBaselineProvider().prompt_template_source == ""
