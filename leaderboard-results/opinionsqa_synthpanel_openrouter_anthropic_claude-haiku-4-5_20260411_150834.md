# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** opinionsqa (684 questions)
**Samples per question:** 50
**Elapsed:** 876.5s

## SynthBench Parity Score (SPS)

**SPS: 0.8289 [0.7545, 0.7768]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7359 [0.7239, 0.7480] | ███████░░░ |
| P_rank  Rank-Order | 0.7952 [0.7830, 0.8061] | ████████░░ |
| P_refuse Refusal Cal. | 0.9557 [0.9410, 0.9661] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2641 |
| Median JSD | 0.2460 |
| Mean Kendall's tau | 0.5904 |
| Composite Parity (legacy) | 0.7656 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2036 | +36% |
| random-baseline | 0.6495 | +0.1161 | +18% |

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
| 2017 | 0.7675 | 0.8079 | 0.2325 | 99 |
| 2018 | 0.7383 | 0.7892 | 0.2617 | 124 |
| 2019 | 0.7355 | 0.8023 | 0.2645 | 218 |
| 2020 | 0.7608 | 0.8196 | 0.2392 | 101 |
| 2022 | 0.6949 | 0.7635 | 0.3051 | 142 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please indicate whether or not each has happened to you beca... | 0.0006 | 1.0000 |
| Have you participated in any of these groups during the last... | 0.0027 | 1.0000 |
| Has the issue of made-up news and information led you to red... | 0.0033 | 1.0000 |
| Regardless of whether or not you own a gun, have you ever fi... | 0.0043 | 1.0000 |
| Have you ever shared news and information that you later fou... | 0.0046 | 0.8165 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Thinking again about colleges and universities which of the ... | 1.0000 | 0.0000 |
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
| Would you prefer to live in a community where the houses are... | 1.0000 | 0.0000 |
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
