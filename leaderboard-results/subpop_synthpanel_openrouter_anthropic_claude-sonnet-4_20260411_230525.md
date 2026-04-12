# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-sonnet-4
**Dataset:** subpop (200 questions)
**Samples per question:** 30
**Elapsed:** 52.4s

## SynthBench Parity Score (SPS)

**SPS: 0.7700 [0.6632, 0.6711]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.8345 [0.8265, 0.8423] | ████████░░ |
| P_rank  Rank-Order | 0.5000 [0.5000, 0.5000] | █████░░░░░ |
| P_refuse Refusal Cal. | 0.9755 [0.9539, 0.9862] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.1655 |
| Median JSD | 0.1577 |
| Mean Kendall's tau | 0.0000 |
| Composite Parity (legacy) | 0.6673 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1053 | +19% |
| random-baseline | 0.6495 | +0.0178 | +3% |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Did you refuse to answer the previous question?... | 0.0293 | 0.0000 |
| Which president would you name as the second-best president ... | 0.0511 | 0.0000 |
| Which president would you name as the second-best president ... | 0.0521 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 0.0549 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 0.0584 | 0.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Thinking about the kind of people you hope your children bec... | 0.2929 | 0.0000 |
| When you see or hear news about terrible things happening to... | 0.3003 | 0.0000 |
| Have you heard of the social media site or app BitChute?... | 0.3185 | 0.0000 |
| Thinking about the kind of people you hope your children bec... | 0.3417 | 0.0000 |
| Did you refuse to answer the previous question?... | 0.3915 | 0.0000 |
