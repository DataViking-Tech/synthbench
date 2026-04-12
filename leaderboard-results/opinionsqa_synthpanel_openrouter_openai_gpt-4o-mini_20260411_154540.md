# SynthBench Score Card

**Provider:** synthpanel/openrouter/openai/gpt-4o-mini
**Dataset:** opinionsqa (429 questions)
**Samples per question:** 50
**Elapsed:** 230.0s

## SynthBench Parity Score (SPS)

**SPS: 0.8223 [0.7268, 0.7552]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7049 [0.6910, 0.7188] | ███████░░░ |
| P_rank  Rank-Order | 0.7761 [0.7577, 0.7910] | ████████░░ |
| P_refuse Refusal Cal. | 0.9860 [0.9779, 0.9892] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2951 |
| Median JSD | 0.2883 |
| Mean Kendall's tau | 0.5522 |
| Composite Parity (legacy) | 0.7405 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1785 | +32% |
| random-baseline | 0.6495 | +0.0910 | +14% |

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
| 2017 | 0.7129 | 0.7731 | 0.2871 | 44 |
| 2018 | 0.6889 | 0.7166 | 0.3111 | 78 |
| 2019 | 0.7093 | 0.7920 | 0.2907 | 153 |
| 2020 | 0.7249 | 0.8101 | 0.2751 | 56 |
| 2022 | 0.6957 | 0.7806 | 0.3043 | 98 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| In the last 12 months, that is since September 2016, have yo... | 0.0016 | 1.0000 |
| Have you participated in any of these groups during the last... | 0.0025 | 1.0000 |
| Do you have the following type of loans or debt: Debt from m... | 0.0053 | 1.0000 |
| When it comes to important issues facing the US, people may ... | 0.0080 | 1.0000 |
| Which statement best describes how you get news?... | 0.0104 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please compare the US to other developed nations in a few di... | 0.6793 | 0.1155 |
| How much, if at all, is racism a problem in your local commu... | 0.6872 | -0.2357 |
| How often, if ever, did your family talk to you about challe... | 0.7101 | -0.3162 |
| When it comes to people who have immigrated to the U.S illeg... | 0.7325 | -0.3162 |
| Do you think the number of legal immigrants the U.S. admits ... | 0.7418 | -0.3464 |
