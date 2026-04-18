"""Generator for tier-3 adversarial fixtures.

Produces static JSON fixtures under ``tests/adversarial/fixtures/`` that
exercise fabrication attacks the tier-3 detectors are expected to catch.
Deterministic (fixed RNG seed) — running this script twice produces
byte-identical output, so the checked-in fixtures are reproducible.

Run from the repo root::

    PYTHONPATH=src python3 tests/adversarial/build_fixtures.py

The fixtures use a real leaderboard submission as their scaffold so that
dataset keys, options, and question metadata are authentic — only
``model_distribution`` is fabricated. Per-question metrics are then
recomputed so that tier-2 arithmetic checks pass; the only reason
these fixtures should fail validation is tier-3.
"""

from __future__ import annotations

import copy
import json
import random
import statistics
from pathlib import Path

from synthbench.metrics.composite import parity_score
from synthbench.metrics.distributional import jensen_shannon_divergence
from synthbench.metrics.ranking import kendall_tau_b
from synthbench.private_holdout import is_private_holdout

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
BASE_SUBMISSION = (
    REPO_ROOT
    / "leaderboard-results"
    / "globalopinionqa_openrouter_anthropic_claude-haiku-4-5_20260411_234610.json"
)

# Tight noise so public JSD lands well below NEAR_COPY_MEAN_JSD (0.02) and
# NEAR_COPY_STD_JSD (0.03). The analysis doc's reference attack uses
# epsilon ~ U(-0.02, 0.02); we use the same envelope.
COPY_NOISE = 0.02


def _add_noise_and_renormalize(
    dist: dict[str, float], rng: random.Random, noise: float
) -> dict[str, float]:
    """Additive uniform noise + renormalization, clamped non-negative."""
    noisy = {}
    for k, v in dist.items():
        perturbation = rng.uniform(-noise, noise)
        noisy[k] = max(0.0, float(v) + perturbation)
    total = sum(noisy.values())
    if total <= 0:
        return dict(dist)
    return {k: v / total for k, v in noisy.items()}


def _marginal_distribution(
    per_question: list[dict], options_key: str
) -> dict[str, float]:
    """Average the ``options_key`` distribution across every question.

    Used to fabricate private rows by sampling near the marginal — the
    same shortcut a real attacker would take when they lack private
    ground truth.
    """
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for q in per_question:
        for opt, p in (q.get(options_key) or {}).items():
            sums[opt] = sums.get(opt, 0.0) + float(p)
            counts[opt] = counts.get(opt, 0) + 1
    if not sums:
        return {}
    return {opt: sums[opt] / counts[opt] for opt in sums}


def _recompute_row(row: dict) -> dict:
    """Recompute jsd/kendall_tau/parity from human + model distributions.

    Tier-2 requires per-question metrics to reconcile with the
    distributions. Fixtures that fabricate ``model_distribution`` without
    recomputing would be rejected at tier-2 for the wrong reason; we want
    the failure to come from tier-3 so the detector is actually tested.
    """
    human = row["human_distribution"]
    model = row["model_distribution"]
    jsd = jensen_shannon_divergence(human, model)
    tau = kendall_tau_b(human, model)
    row["jsd"] = round(jsd, 6)
    row["kendall_tau"] = round(tau, 6)
    row["parity"] = round(parity_score(jsd, tau), 6)
    return row


def _recompute_aggregate(submission: dict) -> None:
    """Refresh aggregate + scores so tier-1/2 checks pass on the fabrication.

    Tier-2 cross-checks aggregates and top-level scores against the
    per-question data. Any fabrication that skips this step is rejected
    before tier-3 runs, which would defeat the purpose of the fixture —
    we want tier-3 to be the reason these fixtures fail.
    """
    pq = submission["per_question"]
    jsds = [float(q["jsd"]) for q in pq]
    taus = [float(q["kendall_tau"]) for q in pq]
    parities = [float(q["parity"]) for q in pq]
    p_dist = statistics.fmean(1.0 - j for j in jsds)
    p_rank = statistics.fmean((t + 1.0) / 2.0 for t in taus)

    agg = submission.setdefault("aggregate", {})
    agg["mean_jsd"] = round(statistics.fmean(jsds), 6)
    agg["median_jsd"] = round(statistics.median(jsds), 6)
    agg["mean_kendall_tau"] = round(statistics.fmean(taus), 6)
    agg["composite_parity"] = round(statistics.fmean(parities), 6)
    agg["n_questions"] = len(pq)

    scores = submission.setdefault("scores", {})
    scores["p_dist"] = round(p_dist, 6)
    scores["p_rank"] = round(p_rank, 6)
    scores["sps"] = round(0.5 * p_dist + 0.5 * p_rank, 6)


def build_near_pure_copy(base: dict, rng: random.Random) -> dict:
    """Fabrication #1: model = human + U(-0.02, 0.02) on every question.

    This attack trips both ``ANOMALY_PERFECTION`` (mean JSD near zero
    across the full dataset) and ``ANOMALY_NEAR_COPY_PUBLIC`` (public
    subset JSD below both thresholds). The latter promotes the failure
    from WARNING to ERROR.
    """
    sub = copy.deepcopy(base)
    sub["config"]["provider"] = "fabricator/near-pure-copy"
    for row in sub["per_question"]:
        row["model_distribution"] = _add_noise_and_renormalize(
            row["human_distribution"], rng, COPY_NOISE
        )
        _recompute_row(row)
    _recompute_aggregate(sub)
    return sub


def build_public_copy_fake_private(base: dict, rng: random.Random) -> dict:
    """Fabrication #2: public copied, private fabricated from marginal.

    The attacker has the public human distributions but not the private
    ones. They copy public and sample private rows from the public
    marginal — the best they can do without the answer key. Public JSD
    lands in the near-copy trap (caught by ANOMALY_NEAR_COPY_PUBLIC);
    private JSD is much higher so ``ANOMALY_PERFECTION`` on the full
    dataset would not fire on its own.
    """
    sub = copy.deepcopy(base)
    sub["config"]["provider"] = "fabricator/public-copy-fake-private"
    dataset = sub["config"]["dataset"]
    marginal = _marginal_distribution(sub["per_question"], "human_distribution")
    for row in sub["per_question"]:
        key = row["key"]
        if is_private_holdout(dataset, key):
            # Fabricate private: Dirichlet-ish draw from the marginal.
            fabricated = {}
            for opt, p in row["human_distribution"].items():
                fabricated[opt] = max(
                    0.0, marginal.get(opt, 0.0) + rng.uniform(-0.1, 0.1)
                )
            total = sum(fabricated.values())
            if total > 0:
                fabricated = {k: v / total for k, v in fabricated.items()}
            row["model_distribution"] = fabricated
        else:
            row["model_distribution"] = _add_noise_and_renormalize(
                row["human_distribution"], rng, COPY_NOISE
            )
        _recompute_row(row)
    _recompute_aggregate(sub)
    return sub


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    base = json.loads(BASE_SUBMISSION.read_text())

    fixtures = {
        "near_pure_copy.json": build_near_pure_copy(base, random.Random(20260418)),
        "public_copy_fake_private.json": build_public_copy_fake_private(
            base, random.Random(20260419)
        ),
    }

    for name, sub in fixtures.items():
        out = FIXTURES_DIR / name
        out.write_text(json.dumps(sub, indent=2, sort_keys=True) + "\n")
        print(f"wrote {out.relative_to(REPO_ROOT)} ({len(sub['per_question'])} rows)")


if __name__ == "__main__":
    main()
