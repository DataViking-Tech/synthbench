# SynthBench Score Card

**Provider:** synthpanel/gpt-4o-mini
**Dataset:** opinionsqa (80 questions)
**Samples per question:** 50
**Elapsed:** 21.4s

## SynthBench Parity Score (SPS)

**SPS: 0.7686 [0.6490, 0.6647]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.8149 [0.7984, 0.8287] | ████████░░ |
| P_rank  Rank-Order | 0.5000 [0.5000, 0.5000] | █████░░░░░ |
| P_refuse Refusal Cal. | 0.9909 [0.9889, 0.9922] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.1851 |
| Median JSD | 0.1736 |
| Mean Kendall's tau | 0.0000 |
| Composite Parity (legacy) | 0.6575 |

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
| 2017 | 0.7929 | 0.5000 | 0.2071 | 18 |
| 2018 | 0.8580 | 0.5000 | 0.1420 | 7 |
| 2019 | 0.7986 | 0.5000 | 0.2014 | 15 |
| 2020 | 0.7895 | 0.5000 | 0.2105 | 14 |
| 2022 | 0.8418 | 0.5000 | 0.1582 | 26 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Still thinking about elections in the country, how confident... | 0.0822 | 0.0000 |
| Thinking about how the federal government spends money, do y... | 0.0887 | 0.0000 |
| Thinking about how the federal government spends money, do y... | 0.0915 | 0.0000 |
| Thinking about Joe Biden's ability to handle a number of thi... | 0.0969 | 0.0000 |
| Thinking about Joe Biden's ability to handle a number of thi... | 0.0983 | 0.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How often, if ever, do you attend gun shows... | 0.3137 | 0.0000 |
| Do you think the government of China respects the personal f... | 0.3186 | 0.0000 |
| Have you or anyone in your household received unemployment b... | 0.3477 | 0.0000 |
| How often, if ever, do you listen to gun-oriented podcasts o... | 0.3533 | 0.0000 |
| Thinking about elections in the country, how important, if a... | 0.4215 | 0.0000 |
