# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** opinionsqa (80 questions)
**Samples per question:** 50
**Elapsed:** 178.7s

## SynthBench Parity Score (SPS)

**SPS: 0.8407 [0.7471, 0.8087]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7557 [0.7155, 0.7873] | ████████░░ |
| P_rank  Rank-Order | 0.8070 [0.7756, 0.8376] | ████████░░ |
| P_refuse Refusal Cal. | 0.9594 [0.9143, 0.9786] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2443 |
| Median JSD | 0.2131 |
| Mean Kendall's tau | 0.6140 |
| Composite Parity (legacy) | 0.7813 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2194 | +39% |
| random-baseline | 0.6495 | +0.1318 | +20% |

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
| 2017 | 0.7864 | 0.8333 | 0.2136 | 18 |
| 2018 | 0.7079 | 0.7544 | 0.2921 | 7 |
| 2019 | 0.7713 | 0.8310 | 0.2287 | 15 |
| 2020 | 0.7608 | 0.8704 | 0.2392 | 14 |
| 2022 | 0.7355 | 0.7549 | 0.2645 | 26 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Have you or anyone in your household received unemployment b... | 0.0071 | 1.0000 |
| Have you or anyone in your household received medicaid benef... | 0.0153 | 1.0000 |
| In presenting the news dealing with political and social iss... | 0.0154 | 1.0000 |
| Do you think the government of China respects the personal f... | 0.0355 | 0.8165 |
| How often, if ever, do you visit websites about guns, huntin... | 0.0407 | 0.9487 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| In general, would you say the quality of the candidates runn... | 0.4984 | 0.3586 |
| The next question is about local elections, such as for mayo... | 0.5062 | 0.3162 |
| Thinking about Joe Biden's ability to handle a number of thi... | 0.5102 | -0.1054 |
| Regardless of whether or not you own a gun, have you ever fi... | 0.5721 | 0.0000 |
| In order to address economic inequality in this country, do ... | 1.0000 | 0.0000 |
