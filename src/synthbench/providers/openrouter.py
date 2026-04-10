"""OpenRouter provider — access many models through a single gateway.

Requires OPENROUTER_API_KEY environment variable.
Uses the openai SDK against the OpenRouter-compatible endpoint.
"""

from __future__ import annotations

import os
import re

from synthbench.providers.base import (
    PersonaSpec,
    Provider,
    Response,
    build_persona_system_prompt,
)

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

_SYSTEM = (
    "You are answering a survey. Select the single option that best reflects your view."
)

_PROMPT_TEMPLATE = """\
Question: {question}

Options:
{options_block}

Respond with ONLY the letter of your choice (e.g., "A"). Do not explain."""

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _build_prompt(question: str, options: list[str]) -> str:
    options_block = "\n".join(f"({_LETTERS[i]}) {opt}" for i, opt in enumerate(options))
    return _PROMPT_TEMPLATE.format(question=question, options_block=options_block)


def _parse_letter(text: str, options: list[str]) -> str | None:
    """Extract the selected option from model response."""
    text = text.strip()

    # Try to match a single letter
    match = re.match(r"^\(?([A-Z])\)?", text.upper())
    if match:
        idx = ord(match.group(1)) - ord("A")
        if 0 <= idx < len(options):
            return options[idx]

    # Try to match option text directly
    text_lower = text.lower()
    for opt in options:
        if opt.lower() in text_lower:
            return opt

    return None


class OpenRouterProvider(Provider):
    """Call models via OpenRouter with no persona framing."""

    def __init__(self, model: str = "openai/gpt-4o-mini", **kwargs):
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package required. Install with: "
                "pip install 'synthbench[openai]'"
            )

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY environment variable is required. "
                "Get one at https://openrouter.ai/keys"
            )

        self._model = model
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=_OPENROUTER_BASE_URL,
        )

    @property
    def name(self) -> str:
        return f"openrouter/{self._model}"

    async def respond(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        prompt = _build_prompt(question, options)
        system = build_persona_system_prompt(_SYSTEM, persona)

        resp = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=8,
            temperature=1.0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )

        raw_text = resp.choices[0].message.content or ""
        selected = _parse_letter(raw_text, options)

        if selected is None:
            selected = options[0]

        return Response(
            selected_option=selected,
            raw_text=raw_text,
            metadata={
                "model": self._model,
                "finish_reason": resp.choices[0].finish_reason,
            },
        )

    async def close(self) -> None:
        await self._client.close()
