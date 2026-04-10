"""Random baseline — uniform random selection."""

from __future__ import annotations

import random

from synthbench.providers.base import PersonaSpec, Provider, Response


class RandomBaselineProvider(Provider):
    """Select a random option with uniform probability. Floor baseline."""

    def __init__(self, seed: int = 42, **kwargs):
        self._rng = random.Random(seed)

    @property
    def name(self) -> str:
        return "random-baseline"

    async def respond(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        idx = self._rng.randint(0, len(options) - 1)
        return Response(selected_option=options[idx], raw_text="Random selection")
