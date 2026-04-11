# SynthBench Score Card

**Provider:** synthpanel/gemini-2.5-flash-lite
**Dataset:** opinionsqa (684 questions)
**Samples per question:** 50
**Elapsed:** 474.0s

## SynthBench Parity Score (SPS)

**SPS: 0.8160 [0.7452, 0.7671]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7490 [0.7362, 0.7602] | ███████░░░ |
| P_rank  Rank-Order | 0.7659 [0.7523, 0.7782] | ████████░░ |
| P_refuse Refusal Cal. | 0.9333 [0.9169, 0.9459] | █████████░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2510 |
| Median JSD | 0.2216 |
| Mean Kendall's tau | 0.5317 |
| Composite Parity (legacy) | 0.7574 |

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
| 2017 | 0.7687 | 0.7328 | 0.2313 | 99 |
| 2018 | 0.7670 | 0.8242 | 0.2330 | 124 |
| 2019 | 0.7569 | 0.7601 | 0.2431 | 218 |
| 2020 | 0.7162 | 0.7928 | 0.2838 | 101 |
| 2022 | 0.7304 | 0.7277 | 0.2696 | 142 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| If driverless vehicles become widespread, which of the follo... | 0.0024 | 1.0000 |
| Do you have a voice-controlled smart speaker in your home, s... | 0.0035 | 1.0000 |
| Do you think men and women are basically similar or basicall... | 0.0043 | 1.0000 |
| Has anyone ever used a gun to threaten or intimidate you or ... | 0.0058 | 1.0000 |
| Do you have the following type of loans or debt: A mortgage ... | 0.0063 | 0.8165 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How often are you asked to agree to the terms and conditions... | 1.0000 | 0.0000 |
| How confident are you, if at all, that companies will follow... | 1.0000 | 0.0000 |
| How comfortable are you, if at all, with companies using you... | 1.0000 | 0.0000 |
| How much do you feel you understand the laws and regulations... | 1.0000 | 0.0000 |
| Do you have the following type of loans or debt: Debt from m... | 1.0000 | 0.0000 |
