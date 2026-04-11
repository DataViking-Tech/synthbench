# SynthBench Score Card

**Provider:** synthpanel/gemini-2.5-flash-lite
**Dataset:** opinionsqa (175 questions)
**Samples per question:** 50
**Elapsed:** 128.9s

## SynthBench Parity Score (SPS)

**SPS: 0.8293 [0.7553, 0.7977]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7422 [0.7171, 0.7634] | ███████░░░ |
| P_rank  Rank-Order | 0.8121 [0.7889, 0.8315] | ████████░░ |
| P_refuse Refusal Cal. | 0.9336 [0.9018, 0.9545] | █████████░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2578 |
| Median JSD | 0.2598 |
| Mean Kendall's tau | 0.6241 |
| Composite Parity (legacy) | 0.7771 |

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
| 2017 | 0.7440 | 0.7863 | 0.2560 | 37 |
| 2018 | 0.7505 | 0.8202 | 0.2495 | 39 |
| 2019 | 0.7558 | 0.8412 | 0.2442 | 50 |
| 2020 | 0.7472 | 0.8231 | 0.2528 | 31 |
| 2022 | 0.6741 | 0.7473 | 0.3259 | 18 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you have other connected items in your home that you can ... | 0.0033 | 1.0000 |
| Do you think the following are likely to happen as a result ... | 0.0036 | 1.0000 |
| Do you think the following are likely to happen as a result ... | 0.0058 | 1.0000 |
| Please indicate whether or not each has happened to you beca... | 0.0065 | 0.8165 |
| Please indicate whether or not each has happened to you beca... | 0.0066 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How much health risk, if any, does eating fruits and vegetab... | 0.5994 | 0.3586 |
| Do you think science has had a mostly positive or mostly neg... | 0.6044 | 0.0000 |
| Do you personally know anyone who has lost a job, or had the... | 0.6144 | 0.0000 |
| Thinking about your own household's financial situation, how... | 0.6193 | 0.0000 |
| How much, if at all, do you think how the stock market is do... | 0.8264 | -0.3162 |
