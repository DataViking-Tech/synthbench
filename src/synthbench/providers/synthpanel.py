"""SynthPanel full-pipeline provider.

Benchmarks the complete SynthPanel pipeline by shelling out to the
``synthpanel`` CLI.  For each respond() call, builds temporary persona
and instrument YAML files, runs ``synthpanel panel run``, and parses
the JSON output.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import tempfile
from pathlib import Path

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


def _build_instrument_yaml(question: str, options: list[str]) -> str:
    """Build a single-question instrument YAML string."""
    # Build options list as a YAML flow sequence
    opts_str = ", ".join(f'"{o}"' for o in options)
    return (
        "version: 3\n"
        "rounds:\n"
        '  - name: "q"\n'
        "    questions:\n"
        f'    - text: "{question}"\n'
        f"      options: [{opts_str}]\n"
        "      type: multiple_choice\n"
    )


def _build_persona_yaml(persona: PersonaSpec | None) -> str:
    """Build a persona YAML string from a PersonaSpec or a generic default."""
    if persona is None:
        return (
            "personas:\n"
            '  - name: "Survey Respondent"\n'
            "    demographics:\n"
            '      role: "general respondent"\n'
        )
    demo_lines = "\n".join(f'      {k}: "{v}"' for k, v in persona.demographics.items())
    name = persona.group or "Survey Respondent"
    parts = [
        "personas:\n",
        f'  - name: "{name}"\n',
        "    demographics:\n",
        f"{demo_lines}\n",
    ]
    if persona.biography:
        parts.append(f'    biography: "{persona.biography}"\n')
    return "".join(parts)


class SynthPanelProvider(Provider):
    """Benchmark the full SynthPanel pipeline via the CLI.

    Shells out to ``synthpanel panel run`` for each respond() call,
    using temporary instrument and persona YAML files.
    """

    def __init__(
        self, model: str = "haiku", synthpanel_path: str | None = None, **kwargs
    ):
        if synthpanel_path:
            self._synthpanel_bin = synthpanel_path
        else:
            found = shutil.which("synthpanel")
            if found is None:
                raise ImportError(
                    "synthpanel is not installed or not on PATH. "
                    "Install synthpanel or pass synthpanel_path= explicitly."
                )
            self._synthpanel_bin = found
        self._model = model

    @property
    def name(self) -> str:
        return f"synthpanel/{self._model}"

    async def respond(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        instrument_yaml = _build_instrument_yaml(question, options)
        persona_yaml = _build_persona_yaml(persona)

        with (
            tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", prefix="sb_inst_", delete=False
            ) as inst_f,
            tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", prefix="sb_pers_", delete=False
            ) as pers_f,
        ):
            inst_f.write(instrument_yaml)
            inst_path = inst_f.name
            pers_f.write(persona_yaml)
            pers_path = pers_f.name

        try:
            return await self._run_cli(inst_path, pers_path, options)
        finally:
            Path(inst_path).unlink(missing_ok=True)
            Path(pers_path).unlink(missing_ok=True)

    async def _run_cli(
        self, inst_path: str, pers_path: str, options: list[str]
    ) -> Response:
        """Execute synthpanel CLI and parse the JSON output."""
        proc = await asyncio.create_subprocess_exec(
            self._synthpanel_bin,
            "--model",
            self._model,
            "--output-format",
            "json",
            "panel",
            "run",
            "--personas",
            pers_path,
            "--instrument",
            inst_path,
            "--no-synthesis",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        raw_stdout = stdout.decode().strip()
        raw_stderr = stderr.decode().strip()

        if proc.returncode != 0:
            return Response(
                selected_option=options[0],
                raw_text="",
                metadata={
                    "error": f"synthpanel exited {proc.returncode}: {raw_stderr}",
                    "model": self._model,
                },
            )

        try:
            data = json.loads(raw_stdout)
        except json.JSONDecodeError:
            return Response(
                selected_option=options[0],
                raw_text=raw_stdout,
                metadata={
                    "error": "failed to parse synthpanel JSON output",
                    "model": self._model,
                },
            )

        # Extract the panelist response text
        raw_text = ""
        try:
            raw_text = data["rounds"][0]["results"][0]["responses"][0]["response"]
        except (KeyError, IndexError):
            pass

        selected = _parse_letter(raw_text, options)
        if selected is None:
            selected = options[0]

        # Gather metadata from synthpanel output
        panelist_result = {}
        try:
            panelist_result = data["rounds"][0]["results"][0]
        except (KeyError, IndexError):
            pass

        metadata: dict = {
            "model": data.get("model", self._model),
            "total_cost": data.get("total_cost"),
            "panelist_cost": data.get("panelist_cost"),
            "total_usage": data.get("total_usage"),
            "panelist_usage": panelist_result.get("usage"),
        }
        if panelist_result.get("error"):
            metadata["panelist_error"] = panelist_result["error"]

        return Response(
            selected_option=selected,
            raw_text=raw_text,
            metadata=metadata,
        )

    async def close(self) -> None:
        pass
