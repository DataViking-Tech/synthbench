# SynthBench Score Card

**Provider:** synthpanel/gemini-2.5-flash-lite
**Dataset:** opinionsqa (80 questions)
**Samples per question:** 50
**Elapsed:** 95.3s

## SynthBench Parity Score (SPS)

**SPS: 0.8395 [0.7284, 0.7922]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7375 [0.7030, 0.7713] | ███████░░░ |
| P_rank  Rank-Order | 0.7905 [0.7567, 0.8207] | ████████░░ |
| P_refuse Refusal Cal. | 0.9904 [0.9880, 0.9920] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2625 |
| Median JSD | 0.2490 |
| Mean Kendall's tau | 0.5811 |
| Composite Parity (legacy) | 0.7640 |

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
| 2017 | 0.7574 | 0.8249 | 0.2426 | 18 |
| 2018 | 0.7129 | 0.7875 | 0.2871 | 7 |
| 2019 | 0.7440 | 0.8076 | 0.2560 | 15 |
| 2020 | 0.8348 | 0.8442 | 0.1652 | 14 |
| 2022 | 0.6742 | 0.7289 | 0.3258 | 26 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think adequate housing is something the federal gover... | 0.0237 | 1.0000 |
| Have you or anyone in your household received unemployment b... | 0.0251 | 0.8165 |
| Do you think the government of China respects the personal f... | 0.0355 | 0.8165 |
| How much of a priority should the following be for the feder... | 0.0371 | 0.8367 |
| Do you think adequate income in retirement is something the ... | 0.0387 | 0.3333 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| In general, how comfortable do you think Republicans in this... | 0.5251 | 0.1195 |
| How well does the Republican party represent the interests o... | 0.5636 | 0.0000 |
| Regardless of whether or not you own a gun, have you ever fi... | 0.5721 | 0.0000 |
| How much confidence do you have in us President Joe Biden to... | 0.6833 | -0.3162 |
| How often, if ever, do you listen to gun-oriented podcasts o... | 0.7285 | 0.3162 |
