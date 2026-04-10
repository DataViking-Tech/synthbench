"""SynthPanel full-pipeline provider.

Unlike the raw-* providers, this benchmarks the complete SynthPanel
pipeline: persona conditioning, survey instruments, response extraction,
and any other processing SynthPanel applies.

Tries to use the synthpanel Python API first; falls back to shelling
out to the ``synthpanel`` CLI tool.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil

from synthbench.providers.base import PersonaSpec, Provider, Response

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _parse_letter(text: str, options: list[str]) -> str | None:
    """Extract the selected option from response text."""
    text = text.strip()

    match = re.match(r"^\(?([A-Z])\)?", text.upper())
    if match:
        idx = ord(match.group(1)) - ord("A")
        if 0 <= idx < len(options):
            return options[idx]

    text_lower = text.lower()
    for opt in options:
        if opt.lower() in text_lower:
            return opt

    return None


class SynthPanelProvider(Provider):
    """Benchmark the full SynthPanel pipeline.

    Resolution order:
      1. ``import synthpanel`` and use its Python API.
      2. Shell out to the ``synthpanel`` CLI.
      3. Raise ImportError with guidance.
    """

    def __init__(self, model: str = "haiku", **kwargs):
        self._model = model
        self._use_library = False
        self._synthpanel = None

        # Attempt 1: try the Python library
        try:
            import synthpanel  # type: ignore[import-untyped]

            self._synthpanel = synthpanel
            self._use_library = True
            return
        except ImportError:
            pass

        # Attempt 2: check for the CLI
        if shutil.which("synthpanel") is not None:
            self._use_library = False
            return

        raise ImportError(
            "synthpanel is not available. Install the synthpanel package "
            "or ensure the 'synthpanel' CLI is on your PATH."
        )

    @property
    def name(self) -> str:
        return f"synthpanel/{self._model}"

    # ------------------------------------------------------------------
    # Library path
    # ------------------------------------------------------------------
    async def _respond_library(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        """Use the synthpanel Python API."""
        sp = self._synthpanel

        # synthpanel may expose ask(), respond(), or a Panel class.
        # Try the most common patterns.
        if hasattr(sp, "ask"):
            result = sp.ask(
                question=question,
                options=options,
                model=self._model,
            )
            # If the library returns a coroutine, await it
            if asyncio.iscoroutine(result):
                result = await result

        elif hasattr(sp, "Panel"):
            panel = sp.Panel(model=self._model)
            result = panel.ask(question=question, options=options)
            if asyncio.iscoroutine(result):
                result = await result
        else:
            raise RuntimeError(
                "synthpanel module found but has no usable API "
                "(expected ask() function or Panel class)"
            )

        # Normalise result to a Response
        if isinstance(result, dict):
            selected = result.get("selected_option", result.get("answer", ""))
            raw_text = result.get("raw_text", str(result))
            metadata = result.get("metadata")
        elif isinstance(result, str):
            selected = result
            raw_text = result
            metadata = None
        else:
            # Assume it's a dataclass / object with attributes
            selected = getattr(
                result, "selected_option", getattr(result, "answer", str(result))
            )
            raw_text = getattr(result, "raw_text", str(result))
            metadata = getattr(result, "metadata", None)

        if selected not in options:
            parsed = _parse_letter(str(selected), options)
            selected = parsed if parsed is not None else options[0]

        return Response(
            selected_option=selected,
            raw_text=str(raw_text),
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # CLI path
    # ------------------------------------------------------------------
    async def _respond_cli(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        """Shell out to the synthpanel CLI."""
        options_str = ",".join(options)

        proc = await asyncio.create_subprocess_exec(
            "synthpanel",
            "ask",
            "--question",
            question,
            "--options",
            options_str,
            "--model",
            self._model,
            "--format",
            "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(
                f"synthpanel CLI exited with code {proc.returncode}: "
                f"{stderr.decode().strip()}"
            )

        raw_text = stdout.decode().strip()

        try:
            data = json.loads(raw_text)
            selected = data.get("selected_option", data.get("answer", ""))
            metadata = data.get("metadata")
        except json.JSONDecodeError:
            # CLI returned non-JSON — try to parse a letter
            selected = ""
            metadata = None

        if selected not in options:
            parsed = _parse_letter(raw_text, options)
            selected = parsed if parsed is not None else options[0]

        return Response(
            selected_option=selected,
            raw_text=raw_text,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    async def respond(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        if self._use_library:
            return await self._respond_library(question, options, persona=persona)
        return await self._respond_cli(question, options, persona=persona)

    async def close(self) -> None:
        # Clean up library resources if applicable
        if self._use_library and self._synthpanel is not None:
            close_fn = getattr(self._synthpanel, "close", None)
            if close_fn is not None:
                result = close_fn()
                if asyncio.iscoroutine(result):
                    await result
