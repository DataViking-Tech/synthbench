# SynthBench Score Card

**Provider:** synthpanel/gpt-4o-mini
**Dataset:** opinionsqa (684 questions)
**Samples per question:** 50
**Elapsed:** 587.4s

## SynthBench Parity Score (SPS)

**SPS: 0.7705 [0.6583, 0.6631]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.8225 [0.8181, 0.8269] | ████████░░ |
| P_rank  Rank-Order | 0.4995 [0.4972, 0.5000] | █████░░░░░ |
| P_refuse Refusal Cal. | 0.9895 [0.9885, 0.9903] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.1775 |
| Median JSD | 0.1702 |
| Mean Kendall's tau | -0.0009 |
| Composite Parity (legacy) | 0.6610 |

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
| 2017 | 0.8025 | 0.5000 | 0.1975 | 99 |
| 2018 | 0.8317 | 0.5000 | 0.1683 | 124 |
| 2019 | 0.8232 | 0.4985 | 0.1768 | 218 |
| 2020 | 0.8079 | 0.5000 | 0.1921 | 101 |
| 2022 | 0.8379 | 0.5000 | 0.1621 | 142 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Which of the following, if any, do you restrict or limit eat... | 0.0005 | 0.0000 |
| Which of the following, if any, do you restrict or limit eat... | 0.0040 | 0.0000 |
| Which of the following, if any, do you restrict or limit eat... | 0.0129 | 0.0000 |
| Which of the following, if any, do you restrict or limit eat... | 0.0315 | 0.0000 |
| Which of the following, if any, do you restrict or limit eat... | 0.0436 | 0.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How important, if at all, do you think a good work ethic is ... | 0.4123 | 0.0000 |
| Thinking about elections in the country, how important, if a... | 0.4215 | 0.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.4420 | 0.0000 |
| Do you think of yourself as... | 0.4572 | 0.0000 |
| In general, would you say scientific experts are... | 0.5406 | -0.6325 |
