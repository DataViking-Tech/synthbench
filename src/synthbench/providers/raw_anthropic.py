"""Raw Anthropic Claude provider — no persona conditioning."""

from __future__ import annotations

import re

from synthbench.providers.base import Provider, Response

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

_SYSTEM = "You are answering a survey. Select the single option that best reflects your view."

_PROMPT_TEMPLATE = """\
Question: {question}

Options:
{options_block}

Respond with ONLY the letter of your choice (e.g., "A"). Do not explain."""


def _build_prompt(question: str, options: list[str]) -> str:
    options_block = "\n".join(
        f"({_LETTERS[i]}) {opt}" for i, opt in enumerate(options)
    )
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


class RawAnthropicProvider(Provider):
    """Call Claude directly with no persona framing."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001", **kwargs):
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package required. Install with: "
                "pip install 'synthbench[anthropic]'"
            )
        self._model = model
        self._client = anthropic.AsyncAnthropic()

    @property
    def name(self) -> str:
        return f"raw-anthropic/{self._model}"

    async def respond(self, question: str, options: list[str]) -> Response:
        prompt = _build_prompt(question, options)

        message = await self._client.messages.create(
            model=self._model,
            max_tokens=8,
            temperature=1.0,  # Sample, don't argmax
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = message.content[0].text if message.content else ""
        selected = _parse_letter(raw_text, options)

        if selected is None:
            # Fallback: pick first option (will show up as noise in metrics)
            selected = options[0]

        return Response(
            selected_option=selected,
            raw_text=raw_text,
            metadata={"model": self._model, "stop_reason": message.stop_reason},
        )

    async def close(self) -> None:
        await self._client.close()
