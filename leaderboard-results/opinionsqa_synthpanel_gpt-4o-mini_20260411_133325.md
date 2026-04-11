# SynthBench Score Card

**Provider:** synthpanel/gpt-4o-mini
**Dataset:** opinionsqa (175 questions)
**Samples per question:** 50
**Elapsed:** 125.4s

## SynthBench Parity Score (SPS)

**SPS: 0.7698 [0.6559, 0.6650]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.8216 [0.8124, 0.8303] | ████████░░ |
| P_rank  Rank-Order | 0.5000 [0.5000, 0.5000] | █████░░░░░ |
| P_refuse Refusal Cal. | 0.9880 [0.9850, 0.9903] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.1784 |
| Median JSD | 0.1714 |
| Mean Kendall's tau | 0.0000 |
| Composite Parity (legacy) | 0.6608 |

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
| 2017 | 0.7996 | 0.5000 | 0.2004 | 37 |
| 2018 | 0.8139 | 0.5000 | 0.1861 | 39 |
| 2019 | 0.8428 | 0.5000 | 0.1572 | 50 |
| 2020 | 0.8031 | 0.5000 | 0.1969 | 31 |
| 2022 | 0.8560 | 0.5000 | 0.1440 | 18 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Still thinking ahead 30 years, which do you think is more li... | 0.0695 | 0.0000 |
| Still thinking ahead 30 years, which do you think is more li... | 0.0715 | 0.0000 |
| Still thinking ahead 30 years, which do you think is more li... | 0.0721 | 0.0000 |
| Overall, how much has your family's financial situation when... | 0.0745 | 0.0000 |
| Still thinking ahead 30 years, which do you think is more li... | 0.0775 | 0.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| In the last 12 months, have you had someone attempt to open ... | 0.3373 | 0.0000 |
| In the last 12 months, have you had someone take over your s... | 0.3457 | 0.0000 |
| Have you ever had your pay or hours reduced because your emp... | 0.4048 | 0.0000 |
| How important, if at all, do you think a good work ethic is ... | 0.4123 | 0.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.4420 | 0.0000 |
