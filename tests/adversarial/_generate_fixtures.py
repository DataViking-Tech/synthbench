"""Deterministic generator for the adversarial fixture suite.

Every fixture under ``tests/adversarial/fixtures/`` is a static JSON file
that ``test_adversarial_suite.py`` replays against the validator. They are
committed to the repo so the suite is fully reproducible with no runtime
randomness — but when a new attack is added, or when distribution/aggregate
invariants change, regenerate the files by running::

    python -m tests.adversarial._generate_fixtures

The script is intentionally self-contained: it uses the production
``jensen_shannon_divergence`` / ``kendall_tau_b`` implementations so that
every fixture's per-question ``jsd`` / ``kendall_tau`` fields survive
Tier-2 recomputation — i.e. the attacks we encode are *numerically
self-consistent* and can only be caught by Tier-1 bounds, Tier-3
anomaly detectors, or explicit cross-checks (question set hash,
holdout coverage, aggregate arithmetic).

Fixture naming follows the attack taxonomy in
``docs/benchmark-hardening-analysis.md`` section 5.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from synthbench.metrics.distributional import jensen_shannon_divergence
from synthbench.metrics.ranking import kendall_tau_b
from synthbench.private_holdout import is_private_holdout
from synthbench.stats import question_set_hash

DATASET = "globalopinionqa"
PROVIDER = "openrouter/anthropic/claude-haiku-4-5"
N_QUESTIONS = 40  # >=25 after dropping private rows, still small enough to read

HERE = Path(__file__).parent
FIXTURE_DIR = HERE / "fixtures"


def _human_distributions(seed: int = 1) -> list[dict[str, float]]:
    """Generate N_QUESTIONS plausible 4-option human distributions."""
    rng = random.Random(seed)
    dists: list[dict[str, float]] = []
    options = ("A", "B", "C", "D")
    for _ in range(N_QUESTIONS):
        # Dirichlet-ish: draw 4 positive weights, normalize
        raw = [rng.uniform(0.05, 1.0) for _ in options]
        s = sum(raw)
        probs = [round(x / s, 4) for x in raw]
        # Fix rounding residual on last option
        probs[-1] = round(1.0 - sum(probs[:-1]), 4)
        dists.append(dict(zip(options, probs)))
    return dists


def _keys() -> list[str]:
    return [f"GOQA_ADV_{i:03d}" for i in range(N_QUESTIONS)]


def _per_question_entry(
    key: str,
    human: dict[str, float],
    model: dict[str, float],
    *,
    n_samples: int = 15,
    model_refusal_rate: float = 0.0,
    human_refusal_rate: float = 0.0,
) -> dict[str, Any]:
    jsd = round(jensen_shannon_divergence(human, model), 6)
    tau = round(kendall_tau_b(human, model), 6)
    parity = round((1.0 - jsd + (1.0 + tau) / 2.0) / 2.0, 6)
    return {
        "key": key,
        "text": "",
        "options": sorted(set(human) | set(model)),
        "human_distribution": human,
        "model_distribution": model,
        "jsd": jsd,
        "kendall_tau": tau,
        "parity": parity,
        "n_samples": n_samples,
        "n_parse_failures": 0,
        "model_refusal_rate": model_refusal_rate,
        "human_refusal_rate": human_refusal_rate,
        "temporal_year": 2024,
    }


def _assemble(
    per_question: list[dict[str, Any]],
    *,
    dataset: str = DATASET,
    provider: str = PROVIDER,
    override_aggregate: dict[str, float] | None = None,
    qset_hash_override: str | None = None,
    raw_responses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Assemble a complete submission dict around a per_question list."""
    jsds = [q["jsd"] for q in per_question]
    taus = [q["kendall_tau"] for q in per_question]
    mean_jsd = round(sum(jsds) / len(jsds), 6)
    mean_tau = round(sum(taus) / len(taus), 6)
    composite = round(0.5 * (1 - mean_jsd) + 0.5 * (1 + mean_tau) / 2, 6)

    aggregate = {
        "mean_jsd": mean_jsd,
        "median_jsd": round(sorted(jsds)[len(jsds) // 2], 6),
        "mean_kendall_tau": mean_tau,
        "composite_parity": composite,
        "n_questions": len(per_question),
        "n_parse_failures": 0,
    }
    if override_aggregate:
        aggregate.update(override_aggregate)

    keys = [q["key"] for q in per_question]
    canonical_hash = question_set_hash(keys)
    config = {
        "dataset": dataset,
        "provider": provider,
        "samples_per_question": 15,
        "n_requested": len(per_question),
        "n_evaluated": len(per_question),
        "question_set_hash": qset_hash_override or canonical_hash,
        "temperature": None,
        "parse_failure_rate": 0.0,
        "topic_filter": None,
    }
    submission: dict[str, Any] = {
        "benchmark": "synthbench",
        "version": "0.1.0",
        "timestamp": "2026-04-18T00:00:00+00:00",
        "config": config,
        "scores": {
            "sps": composite,
            "p_dist": round(1.0 - mean_jsd, 6),
            "p_rank": round((1.0 + mean_tau) / 2, 6),
            "p_refuse": 1.0,
        },
        "aggregate": aggregate,
        "per_question": per_question,
        "reproducibility": {
            "seed": 1,
            "model_revision_hash": "adv-fixture",
            "prompt_template_hash": "adv-fixture",
            "framework_version": "adversarial-suite",
            "submitted_at": "2026-04-18T00:00:00+00:00",
        },
    }
    if raw_responses is not None:
        submission["raw_responses"] = raw_responses
    return submission


def _write(name: str, submission: dict[str, Any]) -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIXTURE_DIR / f"{name}.json"
    path.write_text(json.dumps(submission, indent=2, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Fixture recipes
# ---------------------------------------------------------------------------


def pure_copy() -> dict[str, Any]:
    """model == human on every question. Trips ANOMALY_PERFECTION."""
    humans = _human_distributions(seed=11)
    keys = _keys()
    pq = [_per_question_entry(k, h, dict(h)) for k, h in zip(keys, humans)]
    return _assemble(pq)


def near_pure_copy() -> dict[str, Any]:
    """model == human + small uniform noise. Per-question JSD ~ 0 with
    tiny non-zero spread — survives a mean-based perfection check but the
    *public*-subset JSD is still a near-copy fingerprint."""
    rng = random.Random(22)
    humans = _human_distributions(seed=11)
    keys = _keys()
    pq: list[dict[str, Any]] = []
    for k, h in zip(keys, humans):
        noisy = {opt: max(1e-4, h[opt] + rng.uniform(-0.005, 0.005)) for opt in h}
        s = sum(noisy.values())
        noisy = {opt: round(v / s, 4) for opt, v in noisy.items()}
        # Fix rounding residual
        last = list(noisy)[-1]
        noisy[last] = round(1.0 - sum(v for o, v in noisy.items() if o != last), 4)
        pq.append(_per_question_entry(k, h, noisy))
    return _assemble(pq)


def public_copy_fake_private() -> dict[str, Any]:
    """Public rows copy human; private rows fabricated from marginal.

    Classic Berkeley-style attack: the submitter has access to the public
    20% of distributions and parrots them, then backfills the 20% private
    subset with a Dirichlet draw from the global marginal. Public SPS
    is near 1.0, private SPS falls back to the random-baseline floor,
    producing a large HOLDOUT_DIVERGENCE delta.
    """
    rng = random.Random(33)
    humans = _human_distributions(seed=11)
    keys = _keys()
    # Compute marginal across all humans (prior the attacker could see).
    marginal = {opt: 0.0 for opt in humans[0]}
    for h in humans:
        for opt, p in h.items():
            marginal[opt] += p / len(humans)
    pq: list[dict[str, Any]] = []
    for k, h in zip(keys, humans):
        if is_private_holdout(DATASET, k):
            # Fabricate a distribution drawn from the marginal +
            # uniform sampling noise. The attacker does NOT have
            # per-question ground truth.
            draws = [max(1e-4, marginal[opt] + rng.uniform(-0.1, 0.1)) for opt in h]
            s = sum(draws)
            fake = {opt: round(v / s, 4) for opt, v in zip(h, draws)}
            last = list(fake)[-1]
            fake[last] = round(1.0 - sum(v for o, v in fake.items() if o != last), 4)
            pq.append(_per_question_entry(k, h, fake))
        else:
            pq.append(_per_question_entry(k, h, dict(h)))
    return _assemble(pq)


def constant_offset() -> dict[str, Any]:
    """model[opt] = human[opt] + c, renormalized.

    A constant additive offset leaves the *rank order* of options intact
    (so Kendall tau stays perfect) and produces per-question JSD that
    depends only on distribution shape. The std of per-question JSD
    collapses relative to natural sampling noise — the fingerprint of
    the constant-offset family of attacks. Caught today by the std
    branch of ANOMALY_PERFECTION; in future by the dedicated
    constant-offset detector in doc section 3.3.
    """
    humans = _human_distributions(seed=11)
    keys = _keys()
    c = 0.02
    pq: list[dict[str, Any]] = []
    for k, h in zip(keys, humans):
        shifted = {opt: v + c for opt, v in h.items()}
        s = sum(shifted.values())
        m = {opt: round(v / s, 4) for opt, v in shifted.items()}
        last = list(m)[-1]
        m[last] = round(1.0 - sum(v for o, v in m.items() if o != last), 4)
        pq.append(_per_question_entry(k, h, m))
    return _assemble(pq)


def impossible_bounds() -> dict[str, Any]:
    """Aggregate fields violate their mathematical bounds.

    ``composite_parity = 1.5``, ``mean_jsd = -0.1``, and a per-question
    ``model_distribution`` option with negative probability. Hits three
    distinct BOUNDS_RANGE checks — the cheapest kind of fabrication and
    a regression test that the bounds gate still fires.
    """
    humans = _human_distributions(seed=11)
    keys = _keys()
    pq = [_per_question_entry(k, h, dict(h)) for k, h in zip(keys, humans)]
    submission = _assemble(pq)
    submission["aggregate"]["composite_parity"] = 1.5
    submission["aggregate"]["mean_jsd"] = -0.1
    submission["scores"]["p_dist"] = 1.2
    return submission


def lied_aggregate() -> dict[str, Any]:
    """Per-question distributions are honest; the aggregate block lies.

    A submitter with real per-question data who inflates
    aggregate.mean_jsd / mean_kendall_tau / composite_parity to a
    favorable value. Tier-2 aggregate recomputation must catch the
    delta on all three fields.
    """
    rng = random.Random(44)
    humans = _human_distributions(seed=11)
    keys = _keys()
    # Use a deliberately noisy, high-JSD model distribution (anti-human).
    pq: list[dict[str, Any]] = []
    for k, h in zip(keys, humans):
        opts = list(h)
        # Reverse preference: put mass on the human's least-likely option.
        worst = min(h, key=lambda o: h[o])
        others = [o for o in opts if o != worst]
        model = {worst: 0.7}
        for o in others:
            model[o] = round(0.1 + rng.uniform(-0.02, 0.02), 4)
        s = sum(model.values())
        model = {o: round(v / s, 4) for o, v in model.items()}
        last = list(model)[-1]
        model[last] = round(1.0 - sum(v for o, v in model.items() if o != last), 4)
        pq.append(_per_question_entry(k, h, model))
    submission = _assemble(pq)
    # Inflate the aggregate: claim great scores that the per-question data
    # doesn't support.
    submission["aggregate"]["mean_jsd"] = 0.02
    submission["aggregate"]["mean_kendall_tau"] = 0.95
    submission["aggregate"]["composite_parity"] = 0.97
    return submission


def zero_private_rows() -> dict[str, Any]:
    """Submit only public keys; private 20% omitted.

    Flags HOLDOUT_MISSING_PRIVATE — the private-subset coverage gate
    that already runs at ERROR severity.
    """
    humans = _human_distributions(seed=11)
    keys = _keys()
    pq: list[dict[str, Any]] = []
    for k, h in zip(keys, humans):
        if is_private_holdout(DATASET, k):
            continue
        pq.append(_per_question_entry(k, h, dict(h)))
    return _assemble(pq)


def wrong_keys() -> dict[str, Any]:
    """Fabricated rows use non-dataset keys + a mismatched reported hash.

    Fires QSET_HASH when the reported hash disagrees with the recomputed
    hash of the submission's own keys. A real dataset-canonical-hash
    cross-check (QSET_HASH_DATASET) additionally fires when the harness
    supplies ``expected_question_hash`` — the suite exercises that path
    too.
    """
    humans = _human_distributions(seed=11)
    # Keys that don't belong to any dataset (deliberately obvious).
    bogus_keys = [f"FAKE_KEY_{i:03d}" for i in range(N_QUESTIONS)]
    pq = [_per_question_entry(k, h, dict(h)) for k, h in zip(bogus_keys, humans)]
    # Report a hash that does NOT match the recomputed keys hash.
    submission = _assemble(pq, qset_hash_override="0" * 64)
    return submission


def null_agent() -> dict[str, Any]:
    """Uniform distribution on every question (the Berkeley 'null agent').

    Not a fabrication: a uniform-random baseline is a legitimate
    submission. The validator must **pass** it, and the suite uses it
    as a tripwire — if validation *fails* on uniform, a detector has
    false-positived on the benchmark floor. Assertion-level rather
    than validator-level per doc section 5.4.
    """
    humans = _human_distributions(seed=11)
    keys = _keys()
    pq: list[dict[str, Any]] = []
    for k, h in zip(keys, humans):
        u = 1.0 / len(h)
        uniform = {opt: round(u, 4) for opt in h}
        last = list(uniform)[-1]
        uniform[last] = round(1.0 - sum(v for o, v in uniform.items() if o != last), 4)
        pq.append(_per_question_entry(k, h, uniform))
    return _assemble(pq, provider="baseline/random")


def raw_response_desync() -> dict[str, Any]:
    """raw_responses.selected_option disagrees with model_distribution top.

    The submitter crafted believable distributions but their raw-sample
    log is internally inconsistent — ``raw_text`` and ``selected_option``
    say option "B" for questions whose model_distribution puts >99% of
    mass on "A". Fires RAW_RESPONSES_MODE (tier-3 WARNING).
    """
    humans = _human_distributions(seed=11)
    keys = _keys()
    pq: list[dict[str, Any]] = []
    raw: list[dict[str, Any]] = []
    for k, h in zip(keys, humans):
        # Sharply-peaked model distribution on option A.
        m = {opt: 0.01 for opt in h}
        m["A"] = round(1.0 - 0.01 * (len(h) - 1), 4)
        pq.append(_per_question_entry(k, h, m))
        # Raw samples that claim option B — desynchronized with distribution.
        raw.append(
            {
                "key": k,
                "raw_text": "B\n\nThe answer is B because survey respondents...",
                "selected_option": "B",
            }
        )
    return _assemble(pq, raw_responses=raw)


FIXTURES = {
    "pure_copy": pure_copy,
    "near_pure_copy": near_pure_copy,
    "public_copy_fake_private": public_copy_fake_private,
    "constant_offset": constant_offset,
    "impossible_bounds": impossible_bounds,
    "lied_aggregate": lied_aggregate,
    "zero_private_rows": zero_private_rows,
    "wrong_keys": wrong_keys,
    "null_agent": null_agent,
    "raw_response_desync": raw_response_desync,
}


def main() -> None:
    for name, builder in FIXTURES.items():
        _write(name, builder())
    print(f"wrote {len(FIXTURES)} fixtures to {FIXTURE_DIR}")


if __name__ == "__main__":
    main()
