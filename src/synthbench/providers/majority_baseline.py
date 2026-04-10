"""Majority-class baseline — always selects the first option."""

from __future__ import annotations

from synthbench.providers.base import PersonaSpec, Provider, Response


class MajorityBaselineProvider(Provider):
    """Always select the first option. Naive baseline."""

    def __init__(self, **kwargs):
        pass

    @property
    def name(self) -> str:
        return "majority-baseline"

    async def respond(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        return Response(
            selected_option=options[0], raw_text="Always selects first option"
        )
