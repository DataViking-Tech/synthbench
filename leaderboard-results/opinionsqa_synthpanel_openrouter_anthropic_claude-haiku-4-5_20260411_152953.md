# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** opinionsqa (684 questions)
**Samples per question:** 50
**Elapsed:** 1274.1s

## SynthBench Parity Score (SPS)

**SPS: 0.8253 [0.7518, 0.7755]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7335 [0.7197, 0.7459] | ███████░░░ |
| P_rank  Rank-Order | 0.7952 [0.7828, 0.8061] | ████████░░ |
| P_refuse Refusal Cal. | 0.9471 [0.9324, 0.9579] | █████████░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2665 |
| Median JSD | 0.2459 |
| Mean Kendall's tau | 0.5903 |
| Composite Parity (legacy) | 0.7643 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2023 | +36% |
| random-baseline | 0.6495 | +0.1148 | +18% |

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
| 2017 | 0.7640 | 0.8040 | 0.2360 | 99 |
| 2018 | 0.7362 | 0.7821 | 0.2638 | 124 |
| 2019 | 0.7354 | 0.8059 | 0.2646 | 218 |
| 2020 | 0.7802 | 0.8252 | 0.2198 | 101 |
| 2022 | 0.6737 | 0.7626 | 0.3263 | 142 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please indicate whether or not each has happened to you beca... | 0.0012 | 1.0000 |
| Regardless of whether or not you own a gun, have you ever fi... | 0.0016 | 1.0000 |
| Have you ever avoided talking with someone because you thoug... | 0.0030 | 1.0000 |
| Has the issue of made-up news and information led you to red... | 0.0035 | 1.0000 |
| Which of the following, if any, do you restrict or limit eat... | 0.0037 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
| In general, would you say experts who study a subject for ma... | 1.0000 | 0.0000 |
