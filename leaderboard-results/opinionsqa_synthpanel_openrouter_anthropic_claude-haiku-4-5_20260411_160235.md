# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** opinionsqa (80 questions)
**Samples per question:** 50
**Elapsed:** 294.0s

## SynthBench Parity Score (SPS)

**SPS: 0.8443 [0.7598, 0.8174]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7691 [0.7384, 0.7996] | ████████░░ |
| P_rank  Rank-Order | 0.8087 [0.7752, 0.8350] | ████████░░ |
| P_refuse Refusal Cal. | 0.9551 [0.9124, 0.9753] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2309 |
| Median JSD | 0.2147 |
| Mean Kendall's tau | 0.6174 |
| Composite Parity (legacy) | 0.7889 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2269 | +40% |
| random-baseline | 0.6495 | +0.1394 | +21% |

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
| 2017 | 0.7884 | 0.8362 | 0.2116 | 18 |
| 2018 | 0.7109 | 0.7092 | 0.2891 | 7 |
| 2019 | 0.7716 | 0.8195 | 0.2284 | 15 |
| 2020 | 0.8425 | 0.9094 | 0.1575 | 14 |
| 2022 | 0.7305 | 0.7560 | 0.2695 | 26 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Have you or anyone in your household received medicaid benef... | 0.0029 | 1.0000 |
| Have you or anyone in your household received unemployment b... | 0.0042 | 0.8165 |
| How often, if ever, do you visit websites about guns, huntin... | 0.0298 | 0.9487 |
| Do you think the government of China respects the personal f... | 0.0355 | 0.8165 |
| How often, if ever, do you listen to gun-oriented podcasts o... | 0.0359 | 0.8367 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How much, if at all, do you think the ease with which people... | 0.4785 | 0.6325 |
| The next question is about local elections, such as for mayo... | 0.5062 | 0.3162 |
| Regardless of whether or not you own a gun, have you ever fi... | 0.5079 | 0.3333 |
| In general, would you say the quality of the candidates runn... | 0.5350 | 0.3586 |
| Thinking about Joe Biden's ability to handle a number of thi... | 0.5640 | -0.3586 |
