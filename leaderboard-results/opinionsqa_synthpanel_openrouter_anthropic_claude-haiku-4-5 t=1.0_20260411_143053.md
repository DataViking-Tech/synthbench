# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=1.0
**Dataset:** opinionsqa (100 questions)
**Samples per question:** 30
**Elapsed:** 176.0s

## SynthBench Parity Score (SPS)

**SPS: 0.8366 [0.7589, 0.8174]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7750 [0.7422, 0.8029] | ████████░░ |
| P_rank  Rank-Order | 0.8069 [0.7731, 0.8344] | ████████░░ |
| P_refuse Refusal Cal. | 0.9278 [0.9091, 0.9423] | █████████░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2250 |
| Median JSD | 0.1923 |
| Mean Kendall's tau | 0.6137 |
| Composite Parity (legacy) | 0.7909 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2289 | +41% |
| random-baseline | 0.6495 | +0.1414 | +22% |

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
| 2017 | 0.7736 | 0.8069 | 0.2264 | 99 |
| 2018 | 0.9092 | 0.7988 | 0.0908 | 1 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Have you participated in any of these groups during the last... | 0.0026 | 1.0000 |
| Regardless of whether or not you own a gun, have you ever fi... | 0.0027 | 1.0000 |
| Do you think the following are likely to happen as a result ... | 0.0036 | 1.0000 |
| Have you ever had your pay or hours reduced because your emp... | 0.0143 | 0.9129 |
| If driverless vehicles become widespread, which of the follo... | 0.0187 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How likely is it that, at some point in your life, you will ... | 0.5318 | 0.3464 |
| Do you personally know anyone who has lost a job, or had the... | 0.6144 | 0.0000 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
| Compared to 50 years ago, do you think... | 0.7640 | -0.2357 |
| Do you think it is very likely, somewhat likely, not very li... | 0.7935 | 0.1195 |
