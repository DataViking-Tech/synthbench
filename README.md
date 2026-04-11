# SynthBench

Open benchmark harness for synthetic survey respondent quality.

**The MLPerf of synthetic UXR.**

SynthBench measures how well synthetic respondent systems (like [synth-panel](https://github.com/DataViking-Tech/synth-panel), Ditto, Synthetic Users, or raw ChatGPT prompting) reproduce real human survey response patterns.

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

Regenerate from results:
```bash
synthbench publish --results-dir ./leaderboard-results --output docs/
```

## Submit Results

Want to add your provider to the leaderboard? Here's how:

1. **Fork** this repo.
2. **Run** SynthBench with your provider:
   ```bash
   synthbench run --provider <your-provider> --model <your-model> --suite full --output results/
   ```
3. **Copy** the result JSON into `leaderboard-results/`.
4. **Open a PR** against this repo.
5. **CI validates** the result JSON schema automatically.
6. **Maintainers review and merge** — your results appear on the leaderboard.

## Status

Phase 1 complete: OpinionsQA evaluation harness with CLI, multiple providers, and public leaderboard.

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
