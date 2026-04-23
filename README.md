# SynthBench

[![CI](https://github.com/DataViking-Tech/synthbench/actions/workflows/ci.yml/badge.svg)](https://github.com/DataViking-Tech/synthbench/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)
[![Leaderboard](https://img.shields.io/badge/leaderboard-live-success)](https://synthbench.org/)

Open benchmark harness for synthetic survey respondent quality.

**The MLPerf of synthetic UXR.**

SynthBench measures how well synthetic respondent systems (like [synthpanel](https://github.com/DataViking-Tech/SynthPanel), Ditto, Synthetic Users, or raw ChatGPT prompting) reproduce real human survey response patterns against real Pew American Trends Panel and GlobalOpinionQA ground truth — so "it sounds plausible" gets replaced with a measurable similarity score.

## Quick Start

Run your first benchmark in 3 commands:

```bash
pip install synthbench
synthbench run --provider random --suite smoke --output results/
synthbench leaderboard --results-dir results/
```

Try with a real model (requires API key):

```bash
export OPENROUTER_API_KEY=your-key
synthbench run --provider openrouter --model openai/gpt-4o-mini --suite core --samples 50
```

See [`notebooks/getting_started.ipynb`](notebooks/getting_started.ipynb) for a guided walkthrough.

## Leaderboard

**[View the live leaderboard](https://synthbench.org/)** — see also the
[methodology](https://synthbench.org/methodology/) and
[findings](https://synthbench.org/findings/) pages.

Regenerate leaderboard data for the Astro site:
```bash
synthbench publish-data --results-dir ./leaderboard-results --output site/src/data/leaderboard.json
```

### Contributor note: gated data publishing

Most contributors do **not** need to publish gated artifacts. If you're running
benchmarks locally or contributing via PR, focus on `synthbench run`,
`synthbench validate`, and result submission.

The gated data publication path is maintainer infrastructure and is handled by
project deployment workflows.

## Development

After cloning, enable the repo-tracked git hooks so pushes that would fail CI's
`ruff format --check` are caught locally:

```bash
./scripts/install-hooks.sh   # one-time: wires .githooks/ via core.hooksPath
```

The `pre-push` hook only checks Python files changed in the commits being
pushed, so already-formatted branches add no meaningful overhead. Run
`./scripts/format-check.sh` anytime to mirror the full CI lint job. Emergency
bypass: `git push --no-verify`.

For contribution workflow and PR expectations, see
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Submit Results

Three ways to land a run on the leaderboard, in order of friction:

### 1. CLI (recommended for repeat submissions)

Mint an API key at [synthbench.org/account](https://synthbench.org/account/),
then:

```bash
export SYNTHBENCH_API_KEY=sb_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
synthbench run --provider openrouter --model gpt-4o-mini --suite full -o results/
synthbench submit results/openrouter_gpt-4o-mini_opinionsqa.json
```

#### End-to-end: run + submit in one command (`--submit`)

Collapse the two steps above into a single invocation. The CLI saves the
result JSON locally (so a validation rejection doesn't lose your run) and
then POSTs it to the leaderboard. With `--wait`, the process blocks until
the validator reaches a terminal state and the exit code mirrors the
outcome — suitable for dropping into a CI pipeline that gates on
leaderboard publication:

```bash
export SYNTHBENCH_API_KEY=sb_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
synthbench run \
  --provider raw-anthropic --model claude-haiku-4-5 \
  --dataset globalopinionqa --samples 30 -n 100 \
  --submit --wait \
  --submit-message "first pass with new prompt template"
```

Exit codes with `--wait`:

| Code | Meaning |
|-----:|---------|
| 0    | Published — result is live on the leaderboard |
| 1    | Rejected by the validator OR hard error (bad key, 5xx, etc.) |
| 2    | Poll deadline exceeded (validation is still running server-side; check [/account/submissions/](https://synthbench.org/account/submissions/)) |

Without `--wait`, the upload exits 0 as soon as the Worker accepts the
submission (status = `validating`) — useful for fire-and-forget runs
where you'll check the web dashboard later.

`--submit-message` is optional; it's stored alongside the uploaded JSON
so you can label experiments (e.g. "v2 prompt", "temp=1.0 sweep") without
touching your `config` fields and perturbing the `config_id` hash.

The Worker validates the submission, stages it to R2, and dispatches the
GitHub Actions pipeline. Successful runs publish within ~5 minutes. Keys
are rate-limited to 60 submissions/hour. See
[SUBMISSIONS.md → API key flow](SUBMISSIONS.md#api-key-flow-cli-submission).

### 2. Web upload

Sign in at [/account](https://synthbench.org/account/) and drag your result
JSON into [/submit/upload](https://synthbench.org/submit/upload/). Same
validation pipeline, no key required.

### 3. GitHub PR (power-user path)

1. **Fork** this repo.
2. **Run** SynthBench with your provider:
   ```bash
   synthbench run --provider <your-provider> --model <your-model> --suite full --output results/
   ```
3. **Validate locally** before opening a PR:
   ```bash
   synthbench validate results/<your-result>.json
   ```
4. **Copy** the result JSON into `leaderboard-results/`.
5. **Open a PR** against this repo.
6. **CI validates** schema, bounds, distributions, and recomputes every metric against the per-question data. Fabricated or inconsistent submissions are rejected.
7. **Maintainers review and merge** — your results appear on the leaderboard.

See [SUBMISSIONS.md](SUBMISSIONS.md) for the full list of integrity checks and common failure modes.

## Key Research Findings

Our benchmarking experiments across 3 models, 3 datasets, and 200+ runs reveal:

| Finding | Impact |
|---------|--------|
| **3-model ensemble hits SPS 0.90** | Equal-weight average of Haiku + Gemini + GPT-4o-mini beats any single model by +5-7 pts |
| **Temperature is model-specific** | Gemini benefits from high temp (+4.5%), Haiku is insensitive, GPT-4o-mini mild |
| **Demographic conditioning quantifies LLM bias** | Republican conditioning 2.4x stronger than Democrat — model defaults approximate liberal responses |
| **Persona template matters** | Default template beats stripped/broken templates by +11 SPS pts |

See [FINDINGS.md](FINDINGS.md) for the full experimental report with methodology, replications, and per-metric breakdowns.

## Status

Phase 2 complete: Multi-model benchmarking, ensemble blending, temperature sweeps, and demographic conditioning analysis across OpinionsQA, SubPOP, and GlobalOpinionQA.

## Ground Truth

Built on nine registered survey datasets. Each adapter declares a
redistribution policy; `full` ships `human_distribution` publicly, `gated`
routes per-question artifacts to a JWT-authenticated Cloudflare R2 origin,
and `aggregates_only` / `citation_only` contribute to leaderboard aggregates
only. Canonical source of truth is the `redistribution_policy` attribute on
each adapter in `src/synthbench/datasets/` (see
[`src/synthbench/datasets/policy.py`](src/synthbench/datasets/policy.py)).

| Dataset | Tier | Source |
|---------|------|--------|
| [OpinionsQA](https://github.com/tatsu-lab/opinions_qa) (Santurkar et al., ICML 2023) | gated | Pew American Trends Panel, 1,498 questions |
| [GlobalOpinionQA](https://arxiv.org/abs/2306.16388) (Durmus et al., 2024) | gated | Pew Global Attitudes, 138 countries |
| GSS (General Social Survey) | full | NORC, microdata-capable |
| NTIA Internet Use Supplement | full | US Census / NTIA |
| SubPOP | gated | 22 US subpopulations, 3,362 questions |
| WVS (World Values Survey) | gated | WVSA, cross-national |
| Eurobarometer | gated | European Commission |
| Michigan (Surveys of Consumers) | gated | U. of Michigan |
| Pew Technology | gated | Pew Research |

GSS and NTIA ship with full per-question distributions; the remaining seven
require a signed-in account to reach per-question payloads.

## Cost tracking

The leaderboard JSON carries per-row cost fields and a top-level
`pricing_snapshot` object:

- Each row exposes `cost_usd`, `cost_per_100q`, `cost_per_sps_point`, and
  `is_cost_estimated`. Ensemble rows sum `cost_usd` across constituent
  runs listed in `config.ensemble_sources`.
- `pricing_snapshot` records the per-model `input_per_1m` / `output_per_1m`
  rates used for this publish run, the `snapshot_date` anchor comment, and
  the installed `synth_panel_version` that produced the rates.

This lets downstream consumers audit which pricing table produced which
`cost_usd` and reconcile against provider-reported billing without guessing
at rate drift. See [sb-x8t] and `src/synthbench/publish.py::_build_pricing_snapshot`.

## Convergence analysis

`synthbench convergence bootstrap` computes theoretical ~1/√n convergence
curves for every question in a dataset by multinomial resampling from the
aggregate `human_distribution`. `synthbench convergence real` runs the same
curve shape over individual-level microdata (GSS today; WVS / Eurobarometer
microdata adapters are a follow-on). `synthbench convergence compare` emits
both curves side-by-side.

See [`docs/convergence-analysis.md`](docs/convergence-analysis.md) for the
JSON schema, CLI flags, and the `load_convergence_baseline` integration
surface that synthpanel's `--calibrate-against DATASET:QUESTION` flag
consumes.

## Citation

If you use SynthBench in your research, please cite:

```bibtex
@misc{synthbench2026,
  title={SynthBench: Open Benchmark for Synthetic Survey Respondent Quality},
  author={DataViking-Tech},
  year={2026},
  url={https://github.com/DataViking-Tech/synthbench}
}
```

## License

MIT
