# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** opinionsqa (200 questions)
**Samples per question:** 30
**Elapsed:** 211.0s

## SynthBench Parity Score (SPS)

**SPS: 0.8345 [0.7419, 0.7865]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7428 [0.7163, 0.7656] | ███████░░░ |
| P_rank  Rank-Order | 0.7880 [0.7620, 0.8100] | ████████░░ |
| P_refuse Refusal Cal. | 0.9728 [0.9496, 0.9845] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2572 |
| Median JSD | 0.2388 |
| Mean Kendall's tau | 0.5760 |
| Composite Parity (legacy) | 0.7654 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2034 | +36% |
| random-baseline | 0.6495 | +0.1159 | +18% |

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
| 2017 | 0.7633 | 0.8008 | 0.2367 | 99 |
| 2018 | 0.7228 | 0.7754 | 0.2772 | 101 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Which of the following, if any, do you restrict or limit eat... | 0.0037 | 1.0000 |
| How important, if at all, do you think work skills learned o... | 0.0049 | 0.9129 |
| Regardless of whether or not you own a gun, have you ever fi... | 0.0058 | 1.0000 |
| Do you think the following are likely to happen as a result ... | 0.0086 | 1.0000 |
| If driverless vehicles become widespread, which of the follo... | 0.0102 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How much health risk, if any, does eating fruits and vegetab... | 0.6579 | 0.0000 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
| Compared to 50 years ago, do you think... | 0.7640 | -0.2357 |
| Do you think it is very likely, somewhat likely, not very li... | 0.7666 | 0.1195 |
| Which statement comes closer to your view, even if neither i... | 1.0000 | 0.0000 |
