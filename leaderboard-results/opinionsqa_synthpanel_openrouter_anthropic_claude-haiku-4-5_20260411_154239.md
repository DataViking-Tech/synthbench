# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** opinionsqa (684 questions)
**Samples per question:** 50
**Elapsed:** 761.9s

## SynthBench Parity Score (SPS)

**SPS: 0.8264 [0.7504, 0.7741]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7309 [0.7171, 0.7438] | ███████░░░ |
| P_rank  Rank-Order | 0.7931 [0.7803, 0.8045] | ████████░░ |
| P_refuse Refusal Cal. | 0.9551 [0.9403, 0.9655] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2691 |
| Median JSD | 0.2419 |
| Mean Kendall's tau | 0.5862 |
| Composite Parity (legacy) | 0.7620 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2000 | +36% |
| random-baseline | 0.6495 | +0.1125 | +17% |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Temporal Breakdown (by Survey Year)

Scores stratified by Pew ATP survey wave year. Rising P_dist in recent years may indicate training-data contamination.

| Year | P_dist | P_rank | Mean JSD | Questions |
|------|--------|--------|----------|-----------|
| 2017 | 0.7675 | 0.8060 | 0.2325 | 99 |
| 2018 | 0.7362 | 0.7807 | 0.2638 | 124 |
| 2019 | 0.7358 | 0.8056 | 0.2642 | 218 |
| 2020 | 0.7618 | 0.8196 | 0.2382 | 101 |
| 2022 | 0.6713 | 0.7568 | 0.3287 | 142 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please indicate whether or not each has happened to you beca... | 0.0012 | 1.0000 |
| Regardless of whether or not you own a gun, have you ever fi... | 0.0025 | 1.0000 |
| Have you ever shared news and information that you later fou... | 0.0046 | 0.8165 |
| Do you have the following type of loans or debt: Debt from m... | 0.0051 | 1.0000 |
| Do you think the following are likely to happen as a result ... | 0.0057 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
| In general, would you say experts who study a subject for ma... | 1.0000 | 0.0000 |
