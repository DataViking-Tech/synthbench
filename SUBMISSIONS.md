# Submitting to the SynthBench Leaderboard

This document describes what every submission must look like, what the
automated validation pipeline checks, and how to get your run onto the
public leaderboard.

## Two submission paths

1. **Web upload (recommended, Tier-1 MVP — sb-me0f).** Sign in at
   [synthbench.org/account](https://synthbench.org/account/), then drop
   your result JSON into [/submit/upload](https://synthbench.org/submit/upload/).
   Validation runs server-side; you can track status on
   [/account/submissions](https://synthbench.org/account/submissions/).
   Successful runs land on the leaderboard within ~5 minutes.
2. **GitHub PR (power-user path).** Fork the repo, drop your file in
   `leaderboard-results/`, open a PR. The same validators that guard the
   web upload also run in the `validate-submissions` CI gate.

## The short version

```bash
# Run your benchmark end-to-end; write a result JSON into ./results/.
synthbench run -p <provider> -d globalopinionqa -s 15 -n 100 -o results/

# Validate that file against the integrity rules that also run in CI.
synthbench validate results/<your-result>.json
```

If `synthbench validate` exits non-zero, the server will reject the
submission (web upload) or CI will reject the PR. Fix the issues — don't
hand-edit numbers.

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

### Tier 3 — Statistical integrity + reproducibility metadata (opt-in CI)

Tier 3 adds cheap anomaly detection on the per-question data the
submitter already supplies, plus two new schema blocks that enable
out-of-band audits. Issues in this tier are emitted as **warnings by
default** — pass `--strict --tier3` at the CLI to fail the run on any
warning, which is what the `validate-submissions` CI gate does for new
leaderboard PRs.

Enable locally with:

```bash
synthbench validate --tier3 results/myrun.json
# include peer runs for the cross-run outlier detector:
synthbench validate --tier3 --peers leaderboard-results/ results/myrun.json
```

**Anomaly detectors.** Each returns a warning-severity issue when fired:

- `ANOMALY_PERFECTION` — per-question JSD has `mean < 0.005` or `std <
  0.005`. Real models show meaningful spread; a copy of the human
  answer key yields JSD ≈ 0 with near-zero variance.
- `ANOMALY_NO_REFUSAL` — submission reports
  `model_refusal_rate = 0` on every question while at least three
  questions have `human_refusal_rate >= 0.05`. Real LLMs refuse
  sometimes; an all-zero refusal rate on a refuseable dataset
  typically means either a fabricated run or a bug that drops
  refusals silently.
- `ANOMALY_PEER_OUTLIER` — when peer submissions are supplied via
  `--peers`, the submission's per-question JSD on overlapping
  questions differs from the same-family peer mean by more than
  `0.15`. Catches submissions that claim a particular model but were
  generated by something else.

**Raw-response sample requirement.** Submissions should include a
top-level `raw_responses` list with at least 10% of questions
covered:

```json
"raw_responses": [
  {
    "key": "GOQA_0_adeba4f8",
    "raw_text": "I would say the most likely answer is 'Has too much influence'...",
    "selected_option": "Has too much influence"
  }
]
```

The validator warns on:

- `RAW_RESPONSES_MISSING` / `RAW_RESPONSES_TYPE` — missing or wrong
  shape.
- `RAW_RESPONSES_COVERAGE` — fewer than 10% of questions covered.
- `RAW_RESPONSES_SHAPE` / `RAW_RESPONSES_EMPTY` — sample missing
  `key` / `raw_text`, or `raw_text` is blank.
- `RAW_RESPONSES_MODE` — the sample's `selected_option` is not in
  the top-probability set of the reported `model_distribution`.
- `RAW_RESPONSES_LENGTH` / `RAW_RESPONSES_LENGTH_SHORT` /
  `RAW_RESPONSES_LENGTH_LONG` — individual samples over 10,000
  characters, or the entire sample set consists of 1-character or
  10,000-character outputs.

The harness's runner populates `raw_responses` automatically when the
provider returns raw model text (`Response.raw_text`). Providers that
expose only distributions (logprobs) can attach a sample via
`Distribution.metadata["raw_sample"]`.

**Reproducibility metadata.** A new top-level `reproducibility` block
is required:

```json
"reproducibility": {
  "seed": 42,
  "model_revision_hash": "sha256:...",
  "prompt_template_hash": "sha256:...",
  "framework_version": "0.1.0",
  "submitted_at": "2026-04-15T00:00:00+00:00"
}
```

`framework_version` and `submitted_at` are auto-populated from the
running harness when `synthbench run` writes the result file.
`seed`, `model_revision_hash`, and `prompt_template_hash` must be
supplied in the harness config so that auditors can spot-check by
rerunning a randomly chosen question. Missing or empty fields emit
`REPRO_FIELD_MISSING` / `REPRO_FIELD_EMPTY` warnings.

**Graduation plan.** The current release keeps Tier 3 soft
(warnings) so that existing leaderboard entries stay valid. Once all
active submitters have migrated their tooling, `--tier3 --strict`
will become the default on new PRs and the detectors promote to
errors.

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

# Run Tier-3 (anomaly detection + raw_responses + reproducibility):
synthbench validate --tier3 --strict results/myrun.json

# Tier-3 with same-family peer comparison:
synthbench validate --tier3 --peers leaderboard-results/ results/myrun.json
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
| `ANOMALY_PERFECTION` (warning, tier 3) | Per-question JSD has mean or std below 0.005. | You almost certainly copied the human answer key. Re-run against the actual model. |
| `ANOMALY_NO_REFUSAL` (warning, tier 3) | Never refused despite humans refusing on ≥3 questions. | Check whether your pipeline is silently dropping refusals, or whether the model really never refuses in your prompt. |
| `ANOMALY_PEER_OUTLIER` (warning, tier 3) | Per-question JSD is >0.15 from same-family peers on overlapping questions. | Confirm the claimed model matches the one that generated the submission. |
| `RAW_RESPONSES_MISSING` (warning, tier 3) | No `raw_responses` field in the submission. | Add a list with ≥10% coverage. See `SUBMISSIONS.md` for the schema. |
| `RAW_RESPONSES_COVERAGE` (warning, tier 3) | Fewer than 10% of questions have raw samples. | Include more samples so auditors can spot-check. |
| `RAW_RESPONSES_MODE` (warning, tier 3) | Sample's `selected_option` doesn't match the top of the model distribution. | Usually a serialization bug — regenerate. |
| `REPRO_MISSING` / `REPRO_FIELD_*` (warning, tier 3) | Missing `reproducibility` block or field. | Populate `seed`, `model_revision_hash`, `prompt_template_hash`, `framework_version`, `submitted_at`. |

## Changelog

**2026-04-15 (sb-1rn)** — Tier 3 added. New schema fields
`raw_responses` and `reproducibility` are warnings when missing so
existing leaderboard entries stay valid. CI will graduate them to
errors after the ecosystem has migrated. New `synthbench validate`
flags: `--tier3`, `--peers <dir>`.

## Non-goals

The validator does **not**:

- Check that you actually used the claimed provider / model. That's
  what Tier 3 is for.
- Recompute demographic breakdowns or conditioning scores (yet).
- Normalize distributions on your behalf — if they don't sum to 1 at
  the 5e-3 level, the submission is rejected.
