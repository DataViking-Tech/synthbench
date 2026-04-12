# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** opinionsqa (429 questions)
**Samples per question:** 50
**Elapsed:** 295.0s

## SynthBench Parity Score (SPS)

**SPS: 0.7820 [0.6766, 0.6944]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.8049 [0.7939, 0.8137] | ████████░░ |
| P_rank  Rank-Order | 0.5650 [0.5514, 0.5804] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.9760 [0.9648, 0.9807] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.1951 |
| Median JSD | 0.1733 |
| Mean Kendall's tau | 0.1299 |
| Composite Parity (legacy) | 0.6849 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1229 | +22% |
| random-baseline | 0.6495 | +0.0354 | +5% |

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
| 2017 | 0.7808 | 0.6214 | 0.2192 | 44 |
| 2018 | 0.8137 | 0.5931 | 0.1863 | 78 |
| 2019 | 0.8085 | 0.5383 | 0.1915 | 153 |
| 2020 | 0.7795 | 0.6238 | 0.2205 | 56 |
| 2022 | 0.8175 | 0.5253 | 0.1825 | 98 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Which of the following, if any, do you restrict or limit eat... | 0.0032 | -1.0000 |
| Do you have the following type of loans or debt: Student loa... | 0.0052 | 1.0000 |
| Do you have the following type of loans or debt: Debt from m... | 0.0060 | 1.0000 |
| Do you have the following type of loans or debt: Car loan... | 0.0063 | 1.0000 |
| Please choose the statement that comes closer to your own vi... | 0.0105 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think race or ethnicity should be a major factor, min... | 0.5672 | 0.1826 |
| In general, how important, if at all, is having a lot of mon... | 0.5926 | 0.1826 |
| According to the U.S. Census Bureau, in the next 25 to 30 ye... | 0.6100 | -0.1826 |
| Thinking about the adults in your life, who is the person yo... | 0.7559 | -0.0362 |
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
