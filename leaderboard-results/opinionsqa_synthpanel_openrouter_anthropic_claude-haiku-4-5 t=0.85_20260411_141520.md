# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85
**Dataset:** opinionsqa (100 questions)
**Samples per question:** 30
**Elapsed:** 209.6s

## SynthBench Parity Score (SPS)

**SPS: 0.8549 [0.7559, 0.8141]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7704 [0.7379, 0.7986] | ████████░░ |
| P_rank  Rank-Order | 0.8041 [0.7701, 0.8308] | ████████░░ |
| P_refuse Refusal Cal. | 0.9901 [0.9795, 0.9943] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2296 |
| Median JSD | 0.1987 |
| Mean Kendall's tau | 0.6082 |
| Composite Parity (legacy) | 0.7873 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2253 | +40% |
| random-baseline | 0.6495 | +0.1377 | +21% |

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
| 2017 | 0.7693 | 0.8041 | 0.2307 | 99 |
| 2018 | 0.8843 | 0.7988 | 0.1157 | 1 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Regardless of whether or not you own a gun, have you ever fi... | 0.0027 | 1.0000 |
| Have you participated in any of these groups during the last... | 0.0045 | 1.0000 |
| Have you ever had your pay or hours reduced because your emp... | 0.0144 | 0.9129 |
| Do you feel that people in your local community tend to look... | 0.0177 | 1.0000 |
| Do you think the following are likely to happen as a result ... | 0.0212 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think it is very likely, somewhat likely, not very li... | 0.5625 | 0.2236 |
| Do you personally know anyone who has lost a job, or had the... | 0.6144 | 0.0000 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
| Do you think it is very likely, somewhat likely, not very li... | 0.7203 | 0.1195 |
| Compared to 50 years ago, do you think... | 0.7640 | -0.2357 |
