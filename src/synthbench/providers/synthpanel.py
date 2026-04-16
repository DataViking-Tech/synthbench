"""SynthPanel full-pipeline provider.

Benchmarks the complete SynthPanel pipeline.  Prefers direct Python API
import when available (zero subprocess overhead); falls back to the
``synthpanel`` CLI.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from synthbench.providers.base import Distribution, PersonaSpec, Provider, Response

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# ---------------------------------------------------------------------------
# Optional direct API import (requires synth_panel on Python 3.10+)
# ---------------------------------------------------------------------------
try:
    from synth_panel.llm.client import LLMClient
    from synth_panel.llm.models import CompletionRequest, InputMessage, TextBlock

    _HAS_SYNTH_PANEL_API = True
except (ImportError, TypeError):
    _HAS_SYNTH_PANEL_API = False


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
        if str(opt).lower() in text_lower:
            return opt

    return None


def _yaml_escape(text: str) -> str:
    """Escape a string for embedding in double-quoted YAML."""
    text = str(text)  # Handle non-string options (e.g., floats from some datasets)
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _build_instrument_yaml(question: str, options: list[str]) -> str:
    """Build a single-question instrument YAML with natural presentation.

    Embeds the options in the question text so synthpanel sees a natural
    survey question rather than a forced-choice letter prompt.
    """
    opts_lines = "\\n".join(f"({_LETTERS[i]}) {opt}" for i, opt in enumerate(options))
    full_text = _yaml_escape(question) + "\\n\\n" + opts_lines
    opts_str = ", ".join(f'"{_yaml_escape(o)}"' for o in options)
    return (
        "version: 3\n"
        "rounds:\n"
        '  - name: "q"\n'
        "    questions:\n"
        f'    - text: "{full_text}"\n'
        f"      options: [{opts_str}]\n"
        "      type: multiple_choice\n"
    )


def _build_multi_question_instrument_yaml(
    questions: list[str], options_list: list[list[str]]
) -> str:
    """Build a multi-question instrument YAML for batch evaluation.

    Packs N questions into a single instrument so synthpanel processes
    them all in one invocation.
    """
    lines = [
        "version: 3\n",
        "rounds:\n",
        '  - name: "q"\n',
        "    questions:\n",
    ]
    for q_text, opts in zip(questions, options_list):
        opts_lines = "\\n".join(f"({_LETTERS[i]}) {opt}" for i, opt in enumerate(opts))
        full_text = _yaml_escape(q_text) + "\\n\\n" + opts_lines
        opts_str = ", ".join(f'"{_yaml_escape(o)}"' for o in opts)
        lines.append(f'    - text: "{full_text}"\n')
        lines.append(f"      options: [{opts_str}]\n")
        lines.append("      type: multiple_choice\n")
    return "".join(lines)


def _build_persona_yaml(persona: PersonaSpec | None, count: int = 1) -> str:
    """Build persona YAML with full conditioning context.

    When *count* > 1, replicates the persona to enable batch runs
    through a single synthpanel invocation.
    """
    if persona is None:
        block = (
            '  - name: "Survey Respondent"\n'
            '    occupation: "survey respondent"\n'
            '    background: "A general survey respondent."\n'
            '    personality_traits: "Responds thoughtfully and authentically."\n'
        )
        return "personas:\n" + block * count

    # Build descriptive name from demographics
    demo_parts = [f"{k}: {v}" for k, v in persona.demographics.items()]
    demo_summary = ", ".join(demo_parts)
    name_base = f"Respondent ({demo_summary})"

    # Build background from biography or demographics
    background = persona.biography or f"A person with {demo_summary.lower()}."

    entries: list[str] = []
    for i in range(count):
        suffix = f" {i + 1}" if count > 1 else ""
        lines = [f'  - name: "{_yaml_escape(name_base)}{suffix}"\n']
        for k, v in persona.demographics.items():
            lines.append(f'    {k.lower()}: "{_yaml_escape(v)}"\n')
        lines.append('    occupation: "survey respondent"\n')
        lines.append(f'    background: "{_yaml_escape(background)}"\n')
        lines.append(
            '    personality_traits: "Responds authentically based on their'
            ' demographic background."\n'
        )
        entries.append("".join(lines))

    return "personas:\n" + "".join(entries)


# ---------------------------------------------------------------------------
# Prompt helpers for the direct API path
# ---------------------------------------------------------------------------


def _build_system_prompt(persona: PersonaSpec | None) -> str:
    """Build a system prompt matching synthpanel's ``persona_system_prompt``."""
    if persona is None:
        return (
            "You are role-playing as Survey Respondent. "
            "Occupation: survey respondent. "
            "Background: A general survey respondent. "
            "Personality traits: Responds thoughtfully and authentically. "
            "Answer questions in character. Be authentic to this persona's "
            "perspective, experiences, and communication style. "
            "Give concise, direct answers."
        )

    demo_parts = [f"{k}: {v}" for k, v in persona.demographics.items()]
    demo_summary = ", ".join(demo_parts)
    name = f"Respondent ({demo_summary})"
    background = persona.biography or f"A person with {demo_summary.lower()}."

    parts = [f"You are role-playing as {name}."]
    for k, v in persona.demographics.items():
        parts.append(f"{k.capitalize()}: {v}.")
    parts.append("Occupation: survey respondent.")
    parts.append(f"Background: {background}.")
    parts.append(
        "Personality traits: Responds authentically based on their "
        "demographic background."
    )
    parts.append(
        "Answer questions in character. Be authentic to this persona's "
        "perspective, experiences, and communication style. "
        "Give concise, direct answers."
    )
    return " ".join(parts)


def _build_question_text(question: str, options: list[str]) -> str:
    """Build question prompt with lettered options."""
    opts_lines = "\n".join(f"({_LETTERS[i]}) {opt}" for i, opt in enumerate(options))
    return f"{question}\n\n{opts_lines}"


class SynthPanelProvider(Provider):
    """Benchmark the full SynthPanel pipeline.

    When ``synth_panel`` is importable, uses the Python API directly —
    no subprocess overhead (~1s saved per call).  Otherwise falls back
    to ``synthpanel panel run`` via subprocess.

    Supports synthpanel v0.6.0+ flags: --models, --temperature, --profile.
    """

    def __init__(
        self,
        model: str = "haiku",
        temperature: float | None = None,
        profile: str | None = None,
        prompt_template: str | None = None,
        synthpanel_path: str | None = None,
        **kwargs,
    ):
        self._model = model
        self._temperature = temperature
        self._profile = profile
        self._prompt_template = prompt_template
        self._use_api = _HAS_SYNTH_PANEL_API
        self._client: Any = None
        self._executor: ThreadPoolExecutor | None = None

        if self._use_api:
            self._client = LLMClient()
            self._executor = ThreadPoolExecutor(max_workers=16)
        else:
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

    @property
    def name(self) -> str:
        parts = [f"synthpanel/{self._model}"]
        if self._temperature is not None:
            parts.append(f"t={self._temperature}")
        if self._profile:
            parts.append(f"profile={self._profile}")
        if self._prompt_template:
            # Extract template name from path
            from pathlib import Path

            tname = Path(self._prompt_template).stem
            parts.append(f"tpl={tname}")
        return " ".join(parts)

    @property
    def supports_distribution(self) -> bool:
        return True

    @property
    def supports_batch(self) -> bool:
        return True

    @property
    def prompt_template_source(self) -> str:
        """Hash-stable representation of the prompt surface.

        Uses a sentinel question + options so we capture the full literal
        shape of the user prompt without depending on runtime question data.
        When ``--prompt-template`` points to a file, its contents are
        appended so the hash reflects that override too.
        """
        sentinel_q = "__synthbench_prompt_template_hash_probe__"
        sentinel_opts = ["__opt_A__", "__opt_B__"]
        system = _build_system_prompt(None)
        user_text = _build_question_text(sentinel_q, sentinel_opts)
        base = system + "\n" + user_text
        if self._prompt_template:
            try:
                override = Path(self._prompt_template).read_text()
            except OSError:
                override = ""
            base += "\n---template---\n" + override
        return base

    # ==================================================================
    # respond()
    # ==================================================================

    async def respond(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        if self._use_api:
            return await self._respond_api(question, options, persona)
        return await self._respond_cli(question, options, persona)

    # ── Direct API path ──────────────────────────────────────────

    async def _respond_api(
        self, question: str, options: list[str], persona: PersonaSpec | None
    ) -> Response:
        """Direct LLM call — no subprocess overhead."""
        system = _build_system_prompt(persona)
        user_text = _build_question_text(question, options)

        request = CompletionRequest(
            model=self._model,
            max_tokens=1024,
            messages=[InputMessage(role="user", content=[TextBlock(text=user_text)])],
            system=system,
            temperature=self._temperature,
        )

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            self._executor, self._client.send, request
        )

        raw_text = response.text
        selected = _parse_letter(raw_text, options)
        if selected is None:
            selected = options[0]

        return Response(
            selected_option=selected,
            raw_text=raw_text,
            metadata={
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            },
        )

    # ── CLI fallback path ────────────────────────────────────────

    async def _respond_cli(
        self, question: str, options: list[str], persona: PersonaSpec | None
    ) -> Response:
        """CLI subprocess fallback for a single question."""
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

    # ==================================================================
    # get_distribution()
    # ==================================================================

    async def get_distribution(
        self,
        question: str,
        options: list[str],
        *,
        persona: PersonaSpec | None = None,
        n_samples: int | None = None,
    ) -> Distribution:
        if self._use_api:
            return await self._get_distribution_api(
                question, options, persona, n_samples
            )
        return await self._get_distribution_cli(question, options, persona, n_samples)

    # ── Direct API path ──────────────────────────────────────────

    async def _get_distribution_api(
        self,
        question: str,
        options: list[str],
        persona: PersonaSpec | None,
        n_samples: int | None,
    ) -> Distribution:
        """Concurrent direct API calls — no subprocess overhead."""
        effective_samples = n_samples if n_samples is not None else 30
        system = _build_system_prompt(persona)
        user_text = _build_question_text(question, options)

        request = CompletionRequest(
            model=self._model,
            max_tokens=1024,
            messages=[InputMessage(role="user", content=[TextBlock(text=user_text)])],
            system=system,
            temperature=self._temperature,
        )

        loop = asyncio.get_running_loop()
        futures = [
            loop.run_in_executor(self._executor, self._client.send, request)
            for _ in range(effective_samples)
        ]
        results = await asyncio.gather(*futures, return_exceptions=True)

        responses: list[str] = []
        refusals = 0
        input_tokens_total = 0
        output_tokens_total = 0
        usage_calls = 0
        for result in results:
            if isinstance(result, Exception):
                refusals += 1
                continue
            raw_text = result.text
            selected = _parse_letter(raw_text, options)
            if selected is None:
                refusals += 1
            else:
                responses.append(selected)
            usage = getattr(result, "usage", None)
            if usage is not None:
                input_tokens_total += getattr(usage, "input_tokens", 0) or 0
                output_tokens_total += getattr(usage, "output_tokens", 0) or 0
                usage_calls += 1

        total = len(responses) + refusals
        counts = Counter(responses)
        probs = [counts.get(opt, 0) / max(total, 1) for opt in options]
        refusal_prob = refusals / max(total, 1)

        metadata: dict | None = None
        if usage_calls > 0:
            metadata = {
                "usage": {
                    "input_tokens": input_tokens_total,
                    "output_tokens": output_tokens_total,
                    "call_count": usage_calls,
                }
            }

        return Distribution(
            probabilities=probs,
            refusal_probability=refusal_prob,
            method="sampling",
            n_samples=total,
            metadata=metadata,
        )

    # ── CLI fallback path ────────────────────────────────────────

    async def _get_distribution_cli(
        self,
        question: str,
        options: list[str],
        persona: PersonaSpec | None,
        n_samples: int | None,
    ) -> Distribution:
        """Batch N identical personas into one synthpanel invocation."""
        effective_samples = n_samples if n_samples is not None else 30
        instrument_yaml = _build_instrument_yaml(question, options)
        persona_yaml = _build_persona_yaml(persona, count=effective_samples)

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
            return await self._run_batch(
                inst_path, pers_path, options, effective_samples
            )
        finally:
            Path(inst_path).unlink(missing_ok=True)
            Path(pers_path).unlink(missing_ok=True)

    # ==================================================================
    # batch_respond() — multi-question, single invocation
    # ==================================================================

    async def batch_respond(
        self,
        questions: list[str],
        options_list: list[list[str]],
        *,
        persona: PersonaSpec | None = None,
    ) -> list[Response]:
        """Answer multiple questions in a single synthpanel invocation.

        Packs all questions into one multi-question instrument, runs
        synthpanel once, and returns per-question Response objects.
        """
        if self._use_api:
            return await self._batch_respond_api(questions, options_list, persona)
        return await self._batch_respond_cli(questions, options_list, persona)

    async def _batch_respond_api(
        self,
        questions: list[str],
        options_list: list[list[str]],
        persona: PersonaSpec | None,
    ) -> list[Response]:
        """API path: gather individual respond calls concurrently."""
        tasks = [
            self._respond_api(q, opts, persona)
            for q, opts in zip(questions, options_list)
        ]
        return list(await asyncio.gather(*tasks))

    async def _batch_respond_cli(
        self,
        questions: list[str],
        options_list: list[list[str]],
        persona: PersonaSpec | None,
    ) -> list[Response]:
        """CLI path: multi-question instrument in one subprocess call."""
        instrument_yaml = _build_multi_question_instrument_yaml(questions, options_list)
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
            return await self._run_multi_cli(inst_path, pers_path, options_list)
        finally:
            Path(inst_path).unlink(missing_ok=True)
            Path(pers_path).unlink(missing_ok=True)

    # ==================================================================
    # batch_get_distribution() — multi-question distributions
    # ==================================================================

    async def batch_get_distribution(
        self,
        questions: list[str],
        options_list: list[list[str]],
        *,
        persona: PersonaSpec | None = None,
        n_samples: int | None = None,
    ) -> list[Distribution]:
        """Get distributions for multiple questions in a single invocation.

        CLI path: packs questions into one multi-question instrument with
        N personas, runs synthpanel once, and extracts per-question
        distributions from the results.

        API path: gathers individual get_distribution calls concurrently.
        """
        if self._use_api:
            return await self._batch_get_distribution_api(
                questions, options_list, persona, n_samples
            )
        return await self._batch_get_distribution_cli(
            questions, options_list, persona, n_samples
        )

    async def _batch_get_distribution_api(
        self,
        questions: list[str],
        options_list: list[list[str]],
        persona: PersonaSpec | None,
        n_samples: int | None,
    ) -> list[Distribution]:
        """API path: gather individual distribution calls concurrently."""
        tasks = [
            self._get_distribution_api(q, opts, persona, n_samples)
            for q, opts in zip(questions, options_list)
        ]
        return list(await asyncio.gather(*tasks))

    async def _batch_get_distribution_cli(
        self,
        questions: list[str],
        options_list: list[list[str]],
        persona: PersonaSpec | None,
        n_samples: int | None,
    ) -> list[Distribution]:
        """CLI path: multi-question instrument + N personas in one call."""
        effective_samples = n_samples if n_samples is not None else 30
        instrument_yaml = _build_multi_question_instrument_yaml(questions, options_list)
        persona_yaml = _build_persona_yaml(persona, count=effective_samples)

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
            return await self._run_multi_batch(
                inst_path, pers_path, options_list, effective_samples
            )
        finally:
            Path(inst_path).unlink(missing_ok=True)
            Path(pers_path).unlink(missing_ok=True)

    # ==================================================================
    # CLI subprocess helpers
    # ==================================================================

    def _build_cmd(self, inst_path: str, pers_path: str) -> list[str]:
        """Build the synthpanel CLI command (no --no-synthesis)."""
        cmd = [
            self._synthpanel_bin,
            "--output-format",
            "json",
        ]
        if self._profile:
            cmd.extend(["--profile", self._profile])
        cmd.extend(
            [
                "panel",
                "run",
                "--personas",
                pers_path,
                "--instrument",
                inst_path,
                "--models",
                f"{self._model}:1.0",
            ]
        )
        if self._temperature is not None:
            cmd.extend(["--temperature", str(self._temperature)])
        if self._prompt_template is not None:
            cmd.extend(["--prompt-template", self._prompt_template])
        return cmd

    async def _run_cli(
        self, inst_path: str, pers_path: str, options: list[str]
    ) -> Response:
        """Execute synthpanel CLI and parse the JSON output."""
        cmd = self._build_cmd(inst_path, pers_path)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
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

    async def _run_batch(
        self,
        inst_path: str,
        pers_path: str,
        options: list[str],
        n_samples: int,
    ) -> Distribution:
        """Run a batch of personas and build a distribution."""
        cmd = self._build_cmd(inst_path, pers_path)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        raw_stdout = stdout.decode().strip()

        if proc.returncode != 0:
            n = len(options)
            return Distribution(
                probabilities=[1.0 / n] * n,
                method="sampling",
                n_samples=0,
            )

        try:
            data = json.loads(raw_stdout)
        except json.JSONDecodeError:
            n = len(options)
            return Distribution(
                probabilities=[1.0 / n] * n,
                method="sampling",
                n_samples=0,
            )

        # Extract all panelist responses from the batch
        responses: list[str] = []
        refusals = 0
        try:
            results = data["rounds"][0]["results"]
            for result in results:
                for resp in result.get("responses", []):
                    raw_text = resp.get("response", "")
                    selected = _parse_letter(raw_text, options)
                    if selected is None:
                        refusals += 1
                    else:
                        responses.append(selected)
        except (KeyError, IndexError):
            pass

        total = len(responses) + refusals
        counts = Counter(responses)
        probs = [counts.get(opt, 0) / max(total, 1) for opt in options]
        refusal_prob = refusals / max(total, 1)

        return Distribution(
            probabilities=probs,
            refusal_probability=refusal_prob,
            method="sampling",
            n_samples=total,
        )

    async def _run_multi_cli(
        self, inst_path: str, pers_path: str, options_list: list[list[str]]
    ) -> list[Response]:
        """Execute synthpanel with a multi-question instrument (single persona)."""
        cmd = self._build_cmd(inst_path, pers_path)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        raw_stdout = stdout.decode().strip()
        raw_stderr = stderr.decode().strip()

        n_questions = len(options_list)

        if proc.returncode != 0:
            return [
                Response(
                    selected_option=opts[0],
                    raw_text="",
                    metadata={
                        "error": f"synthpanel exited {proc.returncode}: {raw_stderr}",
                        "model": self._model,
                    },
                )
                for opts in options_list
            ]

        try:
            data = json.loads(raw_stdout)
        except json.JSONDecodeError:
            return [
                Response(
                    selected_option=opts[0],
                    raw_text=raw_stdout,
                    metadata={
                        "error": "failed to parse synthpanel JSON output",
                        "model": self._model,
                    },
                )
                for opts in options_list
            ]

        # Extract per-question responses from the single persona result
        responses: list[Response] = []
        try:
            persona_responses = data["rounds"][0]["results"][0].get("responses", [])
        except (KeyError, IndexError):
            persona_responses = []

        for q_idx in range(n_questions):
            opts = options_list[q_idx]
            if q_idx < len(persona_responses):
                raw_text = persona_responses[q_idx].get("response", "")
                selected = _parse_letter(raw_text, opts)
                if selected is None:
                    selected = opts[0]
                responses.append(
                    Response(
                        selected_option=selected,
                        raw_text=raw_text,
                        metadata={"model": data.get("model", self._model)},
                    )
                )
            else:
                responses.append(
                    Response(
                        selected_option=opts[0],
                        raw_text="",
                        metadata={
                            "error": "no response for question",
                            "model": self._model,
                        },
                    )
                )

        return responses

    async def _run_multi_batch(
        self,
        inst_path: str,
        pers_path: str,
        options_list: list[list[str]],
        n_samples: int,
    ) -> list[Distribution]:
        """Run multi-question instrument with N personas, return per-Q distributions."""
        cmd = self._build_cmd(inst_path, pers_path)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        raw_stdout = stdout.decode().strip()

        n_questions = len(options_list)

        if proc.returncode != 0:
            return [
                Distribution(
                    probabilities=[1.0 / len(opts)] * len(opts),
                    method="sampling",
                    n_samples=0,
                )
                for opts in options_list
            ]

        try:
            data = json.loads(raw_stdout)
        except json.JSONDecodeError:
            return [
                Distribution(
                    probabilities=[1.0 / len(opts)] * len(opts),
                    method="sampling",
                    n_samples=0,
                )
                for opts in options_list
            ]

        # Collect per-question responses across all personas
        per_q_selected: list[list[str]] = [[] for _ in range(n_questions)]
        per_q_refusals: list[int] = [0] * n_questions

        try:
            results = data["rounds"][0]["results"]
            for persona_result in results:
                persona_responses = persona_result.get("responses", [])
                for q_idx in range(n_questions):
                    if q_idx < len(persona_responses):
                        raw_text = persona_responses[q_idx].get("response", "")
                        selected = _parse_letter(raw_text, options_list[q_idx])
                        if selected is None:
                            per_q_refusals[q_idx] += 1
                        else:
                            per_q_selected[q_idx].append(selected)
                    else:
                        per_q_refusals[q_idx] += 1
        except (KeyError, IndexError):
            pass

        # Build Distribution for each question
        distributions: list[Distribution] = []
        for q_idx in range(n_questions):
            selected = per_q_selected[q_idx]
            refusals = per_q_refusals[q_idx]
            total = len(selected) + refusals
            counts = Counter(selected)
            opts = options_list[q_idx]
            probs = [counts.get(opt, 0) / max(total, 1) for opt in opts]
            refusal_prob = refusals / max(total, 1)
            distributions.append(
                Distribution(
                    probabilities=probs,
                    refusal_probability=refusal_prob,
                    method="sampling",
                    n_samples=total,
                )
            )

        return distributions

    async def close(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=False)
