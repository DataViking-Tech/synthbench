"""Population-average baseline — samples from aggregate human distribution."""

from __future__ import annotations

import random

from synthbench.datasets import DATASETS
from synthbench.providers.base import Distribution, PersonaSpec, Provider, Response


class PopulationAverageBaselineProvider(Provider):
    """Return the aggregate human distribution for each question.

    For each respond() call, looks up the human distribution for the given
    question and returns a weighted random sample. For get_distribution(),
    returns the human distribution directly.

    This isolates the "conditioning premium" — the gap between knowing the
    population average and actually conditioning on a specific persona.
    """

    def __init__(
        self,
        data_dir: str | None = None,
        dataset: str = "opinionsqa",
        seed: int = 42,
        **kwargs,
    ):
        self._rng = random.Random(seed)
        # Load dataset and build text -> distribution lookup
        ds_kwargs = {}
        if data_dir:
            ds_kwargs["data_dir"] = data_dir
        ds = DATASETS[dataset](**ds_kwargs)
        questions = ds.load()
        self._dist_by_text: dict[str, dict[str, float]] = {
            q.text: q.human_distribution for q in questions
        }

    @property
    def name(self) -> str:
        return "population-average-baseline"

    @property
    def supports_distribution(self) -> bool:
        return True

    async def respond(
        self, question: str, options: list[str], *, persona: PersonaSpec | None = None
    ) -> Response:
        dist = self._dist_by_text.get(question)
        if dist is None:
            # Question not found — fall back to uniform random
            idx = self._rng.randint(0, len(options) - 1)
            return Response(selected_option=options[idx], raw_text="Unknown question")

        # Weighted random sample from human distribution
        weights = [dist.get(opt, 0.0) for opt in options]
        total = sum(weights)
        if total <= 0:
            idx = self._rng.randint(0, len(options) - 1)
            return Response(selected_option=options[idx], raw_text="Zero-weight dist")

        chosen = self._rng.choices(options, weights=weights, k=1)[0]
        return Response(selected_option=chosen, raw_text="Population average sample")

    async def get_distribution(
        self,
        question: str,
        options: list[str],
        *,
        persona: PersonaSpec | None = None,
        n_samples: int | None = None,
    ) -> Distribution:
        dist = self._dist_by_text.get(question)
        if dist is None:
            # Unknown question — uniform
            n = len(options)
            return Distribution(
                probabilities=[1.0 / n] * n, method="population-average"
            )

        probs = [dist.get(opt, 0.0) for opt in options]
        total = sum(probs)
        if total > 0:
            probs = [p / total for p in probs]

        return Distribution(probabilities=probs, method="population-average")
