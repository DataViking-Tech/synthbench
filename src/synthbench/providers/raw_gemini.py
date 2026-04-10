"""Raw Google Gemini provider — no persona conditioning.

Uses Gemini's OpenAI-compatible endpoint so we can reuse the openai SDK.
Requires GEMINI_API_KEY environment variable.
"""

from __future__ import annotations

import os
import re

from synthbench.providers.base import PersonaSpec, Provider, Response

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

_SYSTEM = (
    "You are answering a survey. Select the single option that best reflects your view."
)

_PROMPT_TEMPLATE = """\
Question: {question}

Options:
{options_block}

Respond with ONLY the letter of your choice (e.g., "A"). Do not explain."""

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


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


class RawGeminiProvider(Provider):
    """Call Google Gemini directly with no persona framing.

    Uses the OpenAI-compatible endpoint so we need only the openai SDK.
    """

    def __init__(self, model: str = "gemini-2.5-flash-lite", **kwargs):
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package required. Install with: "
                "pip install 'synthbench[openai]'"
            )

        gemini_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is required. "
                "Get one at https://aistudio.google.com/apikey"
            )

        self._model = model
        self._client = openai.AsyncOpenAI(
            api_key=gemini_key,
            base_url=_GEMINI_BASE_URL,
        )

    @property
    def name(self) -> str:
        return f"raw-gemini/{self._model}"

    async def respond(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        prompt = _build_prompt(question, options)

        resp = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=8,
            temperature=1.0,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )

        raw_text = resp.choices[0].message.content or ""
        selected = _parse_letter(raw_text, options)

        if selected is None:
            # Fallback: pick first option (will show up as noise in metrics)
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
