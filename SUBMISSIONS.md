# Submitting to the SynthBench Leaderboard

This document describes what every submission must look like, what the
automated validation pipeline checks, and how to run those checks
locally before you open a pull request.

## The short version

```bash
# Run your benchmark end-to-end; write a result JSON into ./results/.
synthbench run -p <provider> -d globalopinionqa -s 15 -n 100 -o results/

# Validate that file against the integrity rules that also run in CI.
synthbench validate results/<your-result>.json
```

If `synthbench validate` exits non-zero, CI will reject the submission.
Fix the issues — don't hand-edit numbers.

## What gets validated

The validator runs in **tiers**. Each tier gets stricter and more
expensive, but no submission ships to the public leaderboard without
passing tiers 1 and 2.

### Tier 1 — Schema and statistical plausibility (always in CI)

- **Schema** — the result file must carry `benchmark == "synthbench"`
  and the expected top-level keys (`config`, `aggregate`, `per_question`,
  ...). Missing or wrong-type fields fail immediately.
- **Bounds** — `composite_parity`, `mean_jsd`, and every key under
  `scores` live in `[0, 1]`. Kendall's tau lives in `[-1, 1]`.
  `parse_failure_rate` lives in `[0, 1]`.
- **Distributions** — every `human_distribution` and
  `model_distribution` must sum to `1.0` within `5e-3` and contain no
  negative probabilities.
- **Question-set integrity** — the SHA-256 hash of the sorted question
  keys must agree with the reported `question_set_hash`. In CI we also
  check the hash against the canonical dataset hash so you cannot ship
  scores for a tampered question set.
- **Count consistency** — `aggregate.n_questions` must equal
  `len(per_question)`.
- **Parse-failure plausibility** — a warning fires when a large run
  (≥500 samples, ≥50 questions) reports zero parse failures. That's not
  a rejection, just a signal for a reviewer to double-check that parse
  failures are being recorded rather than silently dropped.

### Tier 2 — Recomputation (always in CI)

Given the per-question distributions you submit, the validator
recomputes the metrics and compares them to what you reported:

- **Per-question JSD and Kendall's tau** — recomputed from
  `human_distribution` / `model_distribution`; mismatches above `1e-2`
  fail.
- **Aggregate mean JSD, mean tau, composite parity** — recomputed from
  `per_question`; mismatches above `1e-2` fail. `composite_parity`
  may be reported as either the 2-metric blend
  (`0.5 · (1 - JSD) + 0.5 · (1 + τ)/2`) or the SPS mean over available
  components; both are accepted so long as one of them matches.
- **`scores.p_dist` and `scores.p_rank`** — recomputed and checked
  against `aggregate` and the per-question data.

This is where fabricated submissions fail hardest: claiming a
composite_parity of `0.95` while shipping distributions that actually
yield `0.55` is caught at this step, regardless of how internally
self-consistent the rest of the file looks.

### Tier 3 — Spot-check reproducibility (manual/scheduled)

Out of band, maintainers occasionally re-run a randomly chosen subset
of questions against the claimed provider / model / temperature. The
resulting distributions should land within statistical tolerance of the
submitted ones. This is a human-in-the-loop step; there is no CI for
it yet.

### Tier 4 — Cryptographic attestation (future)

A future version will have providers sign result hashes end-to-end so
that the question set → run config → distributions → scores chain is
verifiable without needing to trust the submitter. Not in scope for the
current release.

## Running the validator locally

```bash
# Validate a single file, using tier 1 + tier 2:
synthbench validate results/myrun.json

# Validate every JSON in a directory (treats dir args as globs):
synthbench validate results/

# Skip the recompute step (tier 1 only — fastest):
synthbench validate --skip-recompute results/myrun.json

# Pin the expected question-set hash (matches what CI enforces):
synthbench validate --expected-question-hash <sha256> results/myrun.json

# JSON output for CI dashboards:
synthbench validate --json results/myrun.json

# Fail on warnings (zero-parse-failure heuristic, etc.):
synthbench validate --strict results/myrun.json
```

The CLI exits `0` when every file passes, `1` when any file fails.

## Common failure modes

| Code | Meaning | How to fix |
|------|---------|------------|
| `SCHEMA_MISSING` | A required field is absent. | Re-run with a current `synthbench` version. Don't hand-edit the file. |
| `BOUNDS_RANGE` | A score is outside `[0, 1]` (or tau outside `[-1, 1]`). | Numerical bug upstream — re-run. |
| `DIST_SUM` | A distribution does not sum to `1.0 ± 5e-3`. | Usually means parse failures were dropped without renormalizing. Re-run or renormalize the distribution before reporting. |
| `QSET_HASH` | Reported `question_set_hash` disagrees with the hash of your `per_question` keys. | Something modified the keys after the run. Regenerate. |
| `QSET_HASH_DATASET` | Your question keys don't match the canonical dataset hash. | You ran against a mutated dataset. Re-pull the upstream fixture. |
| `COUNT_MISMATCH` | `n_questions` disagrees with `len(per_question)`. | Truncated or merged file — regenerate. |
| `PER_Q_JSD` / `PER_Q_TAU` | Per-question metric doesn't match what the submitted distributions compute to. | Your metric code diverged from `synthbench`'s. Don't write your own metrics — use the harness's. |
| `AGG_MEAN_JSD` / `AGG_MEAN_TAU` / `AGG_COMPOSITE` | Aggregate metric doesn't match the per-question recomputation. | Same as above. |
| `PARSE_SUSPICIOUS` (warning) | Zero parse failures on a large run. | Double-check your parse pipeline isn't silently succeeding. |

## Non-goals

The validator does **not**:

- Check that you actually used the claimed provider / model. That's
  what Tier 3 is for.
- Recompute demographic breakdowns or conditioning scores (yet).
- Normalize distributions on your behalf — if they don't sum to 1 at
  the 5e-3 level, the submission is rejected.
