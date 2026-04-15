# SynthBench

Open benchmark harness for synthetic survey respondent quality.

**The MLPerf of synthetic UXR.**

SynthBench measures how well synthetic respondent systems (like [synthpanel](https://github.com/DataViking-Tech/SynthPanel), Ditto, Synthetic Users, or raw ChatGPT prompting) reproduce real human survey response patterns.

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

**[View the live leaderboard](https://dataviking-tech.github.io/synthbench/)**

Regenerate leaderboard data for the Astro site:
```bash
synthbench publish-data --results-dir ./leaderboard-results --output site/src/data/leaderboard.json
```

### Gated dataset uploads (R2)

`publish-runs` and `publish-questions` ship per-question/run/config JSONs for
gated-tier datasets (any dataset whose `redistribution_policy` is not `full`)
to a private Cloudflare R2 bucket. The catalog (`runs-index.json`) and
`leaderboard.json` always stay public.

R2 credentials are read from the environment:

| Var                    | Purpose                                |
| ---------------------- | -------------------------------------- |
| `R2_ACCOUNT_ID`        | Cloudflare account ID (endpoint host)  |
| `R2_ACCESS_KEY_ID`     | R2 API token's access key              |
| `R2_SECRET_ACCESS_KEY` | R2 API token's secret                  |
| `R2_BUCKET`            | Bucket name (e.g. `synthbench-data-prod`) |

When **any** of these are unset, the publish CLI falls back to writing every
artifact to `site/public/data/` — preserving the pre-gate behavior so local
development never depends on R2. Force this fallback explicitly with the
`--no-r2` flag:

```bash
synthbench publish-runs --results-dir leaderboard-results --output-dir site/public/data --no-r2
```

Install the R2 client extra when uploading from CI: `pip install -e .[r2]`.

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

Built on established academic datasets:
- [OpinionsQA](https://github.com/tatsu-lab/opinions_qa) (Santurkar et al., ICML 2023) — 1,498 questions from Pew American Trends Panel
- [GlobalOpinionQA](https://arxiv.org/abs/2306.16388) (Durmus et al., 2024) — cross-national opinion data

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
