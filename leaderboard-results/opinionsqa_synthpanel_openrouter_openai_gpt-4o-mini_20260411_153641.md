# SynthBench Score Card

**Provider:** synthpanel/openrouter/openai/gpt-4o-mini
**Dataset:** opinionsqa (80 questions)
**Samples per question:** 50
**Elapsed:** 161.0s

## SynthBench Parity Score (SPS)

**SPS: 0.8389 [0.7362, 0.7889]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7157 [0.6854, 0.7453] | ███████░░░ |
| P_rank  Rank-Order | 0.8103 [0.7835, 0.8330] | ████████░░ |
| P_refuse Refusal Cal. | 0.9909 [0.9889, 0.9922] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2843 |
| Median JSD | 0.2867 |
| Mean Kendall's tau | 0.6205 |
| Composite Parity (legacy) | 0.7630 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2010 | +36% |
| random-baseline | 0.6495 | +0.1135 | +17% |

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
| 2017 | 0.7480 | 0.8368 | 0.2520 | 18 |
| 2018 | 0.7350 | 0.8382 | 0.2650 | 7 |
| 2019 | 0.6904 | 0.7726 | 0.3096 | 15 |
| 2020 | 0.7828 | 0.8488 | 0.2172 | 14 |
| 2022 | 0.6666 | 0.7854 | 0.3334 | 26 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| In order to address economic inequality in this country, do ... | 0.0243 | 1.0000 |
| Have you or anyone in your household received unemployment b... | 0.0251 | 0.8165 |
| Do you think the government of China respects the personal f... | 0.0355 | 0.8165 |
| How much of a priority should the following be for the feder... | 0.0479 | 0.8367 |
| Thinking about elections in the country, how important, if a... | 0.0553 | 0.6325 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How much, if anything, do you think having more women in top... | 0.4651 | 0.3162 |
| How much, if at all, do you think the ease with which people... | 0.4785 | 0.6325 |
| How well does the Republican party represent the interests o... | 0.4855 | 0.3162 |
| How much confidence do you have in us President Joe Biden to... | 0.5012 | 0.3162 |
| How often, if ever, do you listen to gun-oriented podcasts o... | 0.7285 | 0.3162 |
