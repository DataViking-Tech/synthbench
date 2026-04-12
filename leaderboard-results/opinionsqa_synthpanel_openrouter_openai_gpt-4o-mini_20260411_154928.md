# SynthBench Score Card

**Provider:** synthpanel/openrouter/openai/gpt-4o-mini
**Dataset:** opinionsqa (429 questions)
**Samples per question:** 50
**Elapsed:** 226.0s

## SynthBench Parity Score (SPS)

**SPS: 0.8227 [0.7266, 0.7548]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7043 [0.6900, 0.7177] | ███████░░░ |
| P_rank  Rank-Order | 0.7771 [0.7587, 0.7918] | ████████░░ |
| P_refuse Refusal Cal. | 0.9867 [0.9797, 0.9892] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2957 |
| Median JSD | 0.2896 |
| Mean Kendall's tau | 0.5542 |
| Composite Parity (legacy) | 0.7407 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1787 | +32% |
| random-baseline | 0.6495 | +0.0912 | +14% |

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
| 2017 | 0.7025 | 0.7758 | 0.2975 | 44 |
| 2018 | 0.6882 | 0.7182 | 0.3118 | 78 |
| 2019 | 0.7095 | 0.7935 | 0.2905 | 153 |
| 2020 | 0.7314 | 0.8107 | 0.2686 | 56 |
| 2022 | 0.6944 | 0.7797 | 0.3056 | 98 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you regularly wear a smart watch or a wearable fitness tr... | 0.0031 | 1.0000 |
| When it comes to important issues facing the US, people may ... | 0.0041 | 1.0000 |
| Which statement best describes how you get news?... | 0.0082 | 1.0000 |
| In the last 12 months, that is since September 2016, have yo... | 0.0128 | 1.0000 |
| In general, would you say the following statements describes... | 0.0136 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please compare the US to other developed nations in a few di... | 0.6793 | 0.1155 |
| How much, if at all, is racism a problem in your local commu... | 0.6872 | -0.2357 |
| How often do you come across videos or images that have been... | 0.6996 | 0.0000 |
| When it comes to people who have immigrated to the U.S illeg... | 0.7325 | -0.3162 |
| Do you think the number of legal immigrants the U.S. admits ... | 0.7418 | -0.3464 |
