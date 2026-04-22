# Convergence Analysis — Bootstrap Curves

This document explains the bootstrap convergence analysis shipped in
`src/synthbench/convergence/` and exposed as
`synthbench convergence bootstrap`.

## What it does

Given a SynthBench `Question` with a known aggregate `human_distribution`
(option → probability), we compute a theoretical convergence curve:

1. For each sample size **n** in the configured grid (default
   20, 50, 100, 200, 500, 1000, 2000, 5000, 10000), draw **B** bootstrap
   samples of size **n** from the aggregate distribution via a multinomial
   draw. Default **B = 500**.
2. For each draw, normalize the counts into an empirical distribution and
   compute `JSD(empirical_sample, full_distribution)` using the existing
   `synthbench.metrics.distributional.jensen_shannon_divergence`.
3. Summarize the B bootstraps at that n as `{jsd_mean, jsd_p10, jsd_p90}`.

Plotting `jsd_mean` against `n` produces the familiar ~1/√n curve.

A "convergence n" per question is then the smallest n at which:

* `jsd_mean(n) < ε` (default **ε = 0.02**), and
* the curve has flattened — no subsequent sample size within the next two
  grid points lowers `jsd_mean` by more than **δ** (default **δ = 0.005**).

Because the flat-tail check needs two follow-up points, the last two entries
in a sample-size grid can never qualify as the convergence n. Shrink ε or
extend the grid if a question fails to stabilize.

## Why this matters

The curve is the **theoretical floor** an idealized i.i.d. sampler from the
aggregate distribution would achieve. Anything real — human surveys or
synthetic respondents — must beat this floor or something is wrong with the
mixing, the sampling, or the instrument.

Use it for three things:

1. **Lower-bound reference.** Overlay real-sample convergence against the
   bootstrap curve to see how close real samples get to the i.i.d. floor.
2. **Budget planning.** If the bootstrap `convergence_n` is 2000 for a
   question, no amount of synthpanel traffic below 2000 will approximate the
   true distribution — and that is before accounting for heterogeneity.
3. **Question triage.** Questions with pathologically large `convergence_n`
   (or no convergence on the default grid) are expensive to evaluate and
   often signal low-entropy or degenerate distributions worth flagging.

## How it differs from "real human convergence"

This analysis uses **aggregate** distributions. Every bootstrap draw is i.i.d.
from that aggregate. That means:

* No sampling frame bias (real samples are not i.i.d. from any aggregate).
* No population heterogeneity (the same aggregate is assumed to generate all
  respondents).
* No design effects (stratification, weighting, clustering are all absent).

The true human-convergence question — *how fast does a realistic survey
design converge under actual population heterogeneity* — requires
individual-level microdata. That work lives in the microdata adapter bead
(sibling issue `sb-gh1n`). The bootstrap curve here is the **lower-bound
abstraction** that the microdata path eventually gets compared to.

## Output schema

```json
{
  "dataset": "gss",
  "redistribution_policy": "full",
  "license_url": "...",
  "citation": "...",
  "parameters": {
    "sample_sizes": [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000],
    "bootstrap_B": 500,
    "epsilon": 0.02,
    "delta": 0.005
  },
  "summary": {
    "n_questions": 42,
    "n_converged": 38,
    "n_unconverged": 4,
    "convergence_n_p50": 500,
    "convergence_n_p90": 2000,
    "convergence_n_p99": 5000
  },
  "questions": [
    {
      "key": "ABANY",
      "text": "Should abortion be legal …",
      "human_distribution": {"Yes": 0.62, "No": 0.38},
      "curve": [
        {"n": 20, "jsd_mean": 0.03, "jsd_p10": 0.01, "jsd_p90": 0.06, "bootstrap_B": 500},
        ...
      ],
      "convergence_n": 500
    }
  ]
}
```

## Redistribution policy

Each dataset declares a `redistribution_policy` on its adapter class. The
bootstrap CLI honors it:

| Tier              | `summary` | per-question `questions[]`                     |
|-------------------|-----------|-------------------------------------------------|
| `full`            | present   | present with full `human_distribution` + curve |
| `gated`           | present   | present; routes to R2 at publish time          |
| `aggregates_only` | present   | empty; payload carries a `suppressed` notice   |
| `citation_only`   | null      | empty; payload carries a `suppressed` notice   |

Only `full` and `gated` ship per-question artifacts. `gated` relies on the
SynthBench publish step to route those artifacts to the JWT-authenticated
Cloudflare R2 origin — the CLI output itself is identical to `full`.

## CLI

```bash
synthbench convergence bootstrap \
    --dataset opinionsqa \
    --output /tmp/opinionsqa-convergence.json \
    --plot
```

Flags:

* `--dataset / -d` (required) — one of the nine registered datasets.
* `--question / -q` — restrict to one question key.
* `--output / -o` — JSON path; if omitted, JSON is echoed to stdout.
* `--plot` — emit a multi-page PDF alongside `--output` (requires
  `synthbench[viz]`). Page 1 is the `convergence_n` histogram; subsequent
  pages plot each question's mean curve with a p10–p90 shaded band.
* `--bootstraps / -b` — override B (default 500).
* `--sample-sizes` — override the grid (e.g. `100,500,2000,10000`).
* `--epsilon`, `--delta` — override the convergence-n thresholds.
* `--seed` — deterministic bootstraps.
* `--n` — limit to first N questions (useful for smoke tests).

## Cross-reference

* Sibling bead `sb-gh1n` — microdata adapters for real-population convergence.
* `src/synthbench/metrics/distributional.py` — the JSD implementation reused
  here.
* `src/synthbench/datasets/policy.py` — redistribution-policy lookup.
