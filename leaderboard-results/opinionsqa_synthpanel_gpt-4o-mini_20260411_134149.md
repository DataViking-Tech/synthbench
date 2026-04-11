# SynthBench Score Card

**Provider:** synthpanel/gpt-4o-mini
**Dataset:** opinionsqa (200 questions)
**Samples per question:** 50
**Elapsed:** 116.8s

## SynthBench Parity Score (SPS)

**SPS: 0.7706 [0.6547, 0.6640]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.8192 [0.8090, 0.8279] | ████████░░ |
| P_rank  Rank-Order | 0.5000 [0.5000, 0.5000] | █████░░░░░ |
| P_refuse Refusal Cal. | 0.9927 [0.9913, 0.9936] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.1808 |
| Median JSD | 0.1719 |
| Mean Kendall's tau | 0.0000 |
| Composite Parity (legacy) | 0.6596 |

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
| 2018 | 0.8356 | 0.5000 | 0.1644 | 101 |

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
| How often, if ever, do you participate in online discussion ... | 0.3720 | 0.0000 |
| How important, if at all, do you think knowing how to get al... | 0.3869 | 0.0000 |
| Have you ever had your pay or hours reduced because your emp... | 0.4048 | 0.0000 |
| How important, if at all, do you think a good work ethic is ... | 0.4123 | 0.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.4420 | 0.0000 |
