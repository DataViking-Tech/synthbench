# Submitting to the SynthBench Leaderboard

This document describes what every submission must look like, what the
automated validation pipeline checks, and how to get your run onto the
public leaderboard.

## Three submission paths

1. **Web upload (Tier-1 MVP — sb-me0f).** Sign in at
   [synthbench.org/account](https://synthbench.org/account/), then drop
   your result JSON into [/submit/upload](https://synthbench.org/submit/upload/).
   Validation runs server-side; you can track status on
   [/account/submissions](https://synthbench.org/account/submissions/).
   Successful runs land on the leaderboard within ~5 minutes.
2. **CLI submit with API key (recommended for automation — sb-t61h).** Mint
   a key at [/account](https://synthbench.org/account/), export it, and
   `synthbench submit run.json` from the same machine that produced the
   benchmark output. No browser needed; same server-side validation as the
   web flow. Rate-limited to 60 submissions/hour per key. See the
   [API key flow](#api-key-flow-cli-submission) section below.
3. **GitHub PR (power-user path).** Fork the repo, drop your file in
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

## API key flow (CLI submission)

`synthbench submit` lets you upload directly from the machine that ran the
benchmark. Designed for CI pipelines and scripted experiment runners — no
browser tab required.

### One-time setup

1. Sign in at [synthbench.org/account](https://synthbench.org/account/) and
   open the **API Keys** section.
2. Click **Generate new key**, give it a recognizable name
   (e.g. `laptop-cli`), and pick a scope:
   - **Submit runs** — write-only; can call `/submit` but not read gated data.
     Recommended for CI.
   - **Read gated data** — read-only; can fetch gated-tier datasets via the
     Worker but cannot upload.
   - **Read + submit** — both. Use only if you genuinely need both verbs from
     the same key.
3. Copy the displayed key. **You will not be able to see it again** — the
   server stores only its sha256 hash. If you lose it, revoke and mint a new one.
4. Store it as a secret on the machine that will use it (e.g. shell rc file,
   GitHub Actions secret, `1Password` item).

You can have up to **5 active keys** per account; revoke unused ones to make
room.

### Submitting a run

```bash
export SYNTHBENCH_API_KEY=sb_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Default — POSTs to https://api.synthbench.org/submit
synthbench submit results/openrouter_gpt-4o-mini_opinionsqa.json

# Override the base URL (preview deploys, self-hosted Workers):
synthbench submit run.json --api-url https://api.preview.synthbench.org

# Pipe-friendly machine output:
synthbench submit run.json --json-out
```

You can also pass the key inline if you don't want it in the env:

```bash
synthbench submit run.json --api-key "$(security find-generic-password -s synthbench)"
```

### Run + submit in one command (`--submit` / `--wait`)

`synthbench run --submit` collapses the benchmark + submit steps into a single
invocation. With `--wait`, the process polls the Worker's
`GET /submit/<id>` endpoint until the validator reaches a terminal state
and exits with a code that reflects the outcome (0 = published,
1 = rejected/error, 2 = timeout). Use this in CI to gate a release on
leaderboard publication:

```bash
# Fire-and-forget: exit 0 once the Worker accepts the upload
synthbench run -p raw-anthropic -m haiku -s 30 -n 100 --submit

# Block until validation completes
synthbench run -p raw-anthropic -m haiku -s 30 -n 100 --submit --wait \
  --submit-message "v2 prompt sweep"

# Tighter polling cadence for interactive use
synthbench run -p raw-anthropic -m haiku --submit --wait \
  --poll-interval 5 --poll-timeout 600
```

`--submit-message` is an optional free-form note that gets stamped on the
uploaded JSON so you can tag experiments without touching `config`
fields (which would change the `config_id` hash). The result file on
disk is not rewritten — the annotation lives only in the staged R2 copy
and the Worker's record of what was uploaded. If the upload fails for
any reason, the locally-saved JSON is intact and can be re-submitted
later with `synthbench submit`.

The status endpoint (`GET /submit/<id>`) is the same surface the
`--wait` poller uses; it requires an `sb_` API key with `submit` scope
and only returns rows owned by the key holder.

### Equivalent curl

The Worker endpoint is a plain `POST application/json` so any HTTP client
works:

```bash
curl -X POST https://api.synthbench.org/submit \
  -H "Authorization: Bearer $SYNTHBENCH_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @results/myrun.json
```

A successful submission returns HTTP 202:

```json
{
  "submission_id": 423,
  "status": "validating",
  "file_path": "submissions/2026/04/15/<user-id>/...json",
  "submitted_at": "2026-04-15T12:34:56Z"
}
```

### Rate limit and quotas

| Limit | Value | Behavior on hit |
|-------|-------|-----------------|
| Submissions per key | 60/hour | HTTP 429 with `rate limit exceeded` body |
| Submission body size | 2 MB | HTTP 413 |
| Active keys per user | 5 | UI disables **Generate new key** until you revoke one |

The rate limit is computed against the Supabase `submissions` table, not an
in-memory counter, so it survives Worker cold starts and is consistent
across edge nodes.

### Auth error reference

| Status | Body | Meaning | Action |
|--------|------|---------|--------|
| 401 | `unknown api key` | Key not in DB or hash mismatch. | Re-check the env var; the key may have been rotated. |
| 401 | `api key revoked` | Key is in DB but flagged revoked. | Mint a new one at /account. |
| 401 | `api key expired` | `expires_at` has passed. | Mint a new one. |
| 403 | `api key lacks submit scope` | Key was generated read-only. | Generate a new key with `submit` or `both` scope. |
| 429 | `rate limit exceeded: 60 submissions/hour per key` | Per-key ceiling. | Wait or use a second key. |

### Security model

- **Plaintext is never persisted.** Only `sha256(key)` and the first 8 chars
  (the lookup prefix) live in Supabase. Even a database leak cannot recover
  a usable key.
- **Constant-time hash compare** in the Worker prevents timing-based key
  enumeration.
- **Per-user RLS** on the `api_keys` table means even a compromised user
  account can only list and revoke that user's keys.
- **Audit trail** — every submission stores `api_key_id` so post-hoc you
  can trace which key uploaded what. Browser-flow uploads have
  `api_key_id = NULL`.

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
