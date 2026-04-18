# Null-agent baseline SPS drift log

Per [benchmark-hardening-analysis.md §5.4](./benchmark-hardening-analysis.md),
we track the composite parity ("SPS") of null-agent baseline submissions over
time. Upward drift on a stable dataset is a scoring-function bug, not a
success.

This file is the **persisted historical log** — a snapshot of the canonical
per-dataset null-agent floors observed in `leaderboard-results/` at the time
of the most recent change. The git log of this file *is* the baseline-drift
timeline; each delta is an intentional scoring-function change that should
be justified in the commit message.

The canonical floor is the max `composite_parity` across all runs for a
given (provider, dataset) — mirroring the leaderboard's own display logic
(`synthbench.leaderboard.build_baseline_scores`). That is the number a new
submission must beat to appear non-trivial, and so it is what the CI gate
enforces.

## Current canonical floors (sb-lhoh initial snapshot, 2026-04-18)

| Provider          | Dataset         | Canonical SPS | n_evaluated | Source file                                                 |
| ----------------- | --------------- | ------------- | ----------- | ----------------------------------------------------------- |
| random-baseline   | globalopinionqa | 0.7097        |          10 | `globalopinionqa_random-baseline_20260410_202817.json`      |
| random-baseline   | opinionsqa      | 0.7629        |         684 | `opinionsqa_random-baseline_20260410_220040.json`           |
| random-baseline   | subpop          | 0.7575        |         200 | `subpop_random-baseline_20260411_044250.json`               |
| majority-baseline | globalopinionqa | 0.6896        |         100 | `globalopinionqa_majority-baseline_20260412_015334.json`    |
| majority-baseline | opinionsqa      | 0.7145        |          80 | `opinionsqa_majority-baseline_20260410_205940.json`         |
| majority-baseline | subpop          | 0.6727        |         200 | `subpop_majority-baseline_20260411_044250.json`             |

## CI thresholds

Enforced by `tests/test_baseline_floors.py` (module
`synthbench.baseline_floors`):

| Provider          | Hard CI ceiling | Berkeley aspirational floor |
| ----------------- | --------------- | --------------------------- |
| random-baseline   | SPS < **0.80**  | SPS < 0.70                  |
| majority-baseline | SPS < **0.85**  | SPS < 0.85                  |

The Berkeley target of 0.70 for `random-baseline` is tighter than the
current empirical hard ceiling. SynthBench's composite parity weights
`p_refuse` (the agreement on DK/Refused rates), where a uniform-random
null agent naturally lands near the human refusal rate — pushing
`random-baseline` SPS to ~0.71–0.76 across production-scale runs. This
is a property of the scoring protocol, not a bug, but the gap between
0.70 and the observed ~0.76 is the ledger of how much headroom the
scoring function "donates" to an agent that does nothing. Closing that
gap is a separate scoring-protocol question; until then, the CI gate
enforces drift detection at 0.80 and the methodology page publishes
both the current floor and Berkeley's aspirational target.

## Regenerating this log

To re-print the full time-ordered history and current floors:

```bash
python3 scripts/baseline-floors-report.py --history
```

The CI gate (pytest `tests/test_baseline_floors.py`) runs on every PR
and surfaces any dataset whose canonical SPS has crept past its
configured ceiling. When a legitimate scoring-function change moves
the floor, raise the ceiling **deliberately** in
`synthbench.baseline_floors` and commit the new row to the table
above in the same patch, so `git log docs/baseline-floors-log.md` is
the audit trail.
