# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** opinionsqa (80 questions)
**Samples per question:** 50
**Elapsed:** 84.1s

## SynthBench Parity Score (SPS)

**SPS: 0.8407 [0.7502, 0.8102]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7584 [0.7169, 0.7898] | ████████░░ |
| P_rank  Rank-Order | 0.8099 [0.7761, 0.8380] | ████████░░ |
| P_refuse Refusal Cal. | 0.9539 [0.9100, 0.9753] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2416 |
| Median JSD | 0.2082 |
| Mean Kendall's tau | 0.6197 |
| Composite Parity (legacy) | 0.7841 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2221 | +40% |
| random-baseline | 0.6495 | +0.1346 | +21% |

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
| 2017 | 0.7866 | 0.8251 | 0.2134 | 18 |
| 2018 | 0.7019 | 0.7680 | 0.2981 | 7 |
| 2019 | 0.7718 | 0.8263 | 0.2282 | 15 |
| 2020 | 0.7583 | 0.8601 | 0.2417 | 14 |
| 2022 | 0.7463 | 0.7740 | 0.2537 | 26 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Have you or anyone in your household received unemployment b... | 0.0070 | 1.0000 |
| Have you or anyone in your household received medicaid benef... | 0.0142 | 1.0000 |
| How often, if ever, do you visit websites about guns, huntin... | 0.0293 | 0.9487 |
| How often, if ever, do you listen to gun-oriented podcasts o... | 0.0320 | 0.8367 |
| Do you think the government of China respects the personal f... | 0.0355 | 0.8165 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| The next question is about local elections, such as for mayo... | 0.5062 | 0.3162 |
| Thinking about how the federal government spends money, do y... | 0.5160 | -0.2357 |
| Thinking about Joe Biden's ability to handle a number of thi... | 0.5436 | -0.3586 |
| Regardless of whether or not you own a gun, have you ever fi... | 0.5721 | 0.0000 |
| In order to address economic inequality in this country, do ... | 1.0000 | 0.0000 |
