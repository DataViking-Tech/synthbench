# SynthBench Score Card

**Provider:** synthpanel/openrouter/openai/gpt-4o-mini
**Dataset:** opinionsqa (429 questions)
**Samples per question:** 50
**Elapsed:** 305.0s

## SynthBench Parity Score (SPS)

**SPS: 0.8219 [0.7260, 0.7543]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7033 [0.6897, 0.7168] | ███████░░░ |
| P_rank  Rank-Order | 0.7765 [0.7586, 0.7915] | ████████░░ |
| P_refuse Refusal Cal. | 0.9858 [0.9771, 0.9890] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2967 |
| Median JSD | 0.2920 |
| Mean Kendall's tau | 0.5531 |
| Composite Parity (legacy) | 0.7399 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1779 | +32% |
| random-baseline | 0.6495 | +0.0904 | +14% |

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
| 2017 | 0.6965 | 0.7657 | 0.3035 | 44 |
| 2018 | 0.6851 | 0.7174 | 0.3149 | 78 |
| 2019 | 0.7083 | 0.7907 | 0.2917 | 153 |
| 2020 | 0.7350 | 0.8198 | 0.2650 | 56 |
| 2022 | 0.6947 | 0.7817 | 0.3053 | 98 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you have the following type of loans or debt: Debt from m... | 0.0050 | 1.0000 |
| In the last 12 months, that is since September 2016, have yo... | 0.0056 | 1.0000 |
| Have you participated in any of these groups during the last... | 0.0069 | 1.0000 |
| When it comes to important issues facing the US, people may ... | 0.0109 | 1.0000 |
| In general, would you say the following statements describes... | 0.0120 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How much, if at all, is racism a problem in your local commu... | 0.6872 | -0.2357 |
| How often do you come across videos or images that have been... | 0.6996 | 0.0000 |
| How often, if ever, did your family talk to you about challe... | 0.7101 | -0.3162 |
| When it comes to people who have immigrated to the U.S illeg... | 0.7325 | -0.3162 |
| Do you think the number of legal immigrants the U.S. admits ... | 0.7418 | -0.3464 |
