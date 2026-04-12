# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** opinionsqa (175 questions)
**Samples per question:** 50
**Elapsed:** 204.2s

## SynthBench Parity Score (SPS)

**SPS: 0.8503 [0.7631, 0.8014]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7540 [0.7323, 0.7736] | ████████░░ |
| P_rank  Rank-Order | 0.8136 [0.7914, 0.8329] | ████████░░ |
| P_refuse Refusal Cal. | 0.9835 [0.9676, 0.9879] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2460 |
| Median JSD | 0.2419 |
| Mean Kendall's tau | 0.6272 |
| Composite Parity (legacy) | 0.7838 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2218 | +39% |
| random-baseline | 0.6495 | +0.1343 | +21% |

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
| 2017 | 0.7422 | 0.7792 | 0.2578 | 37 |
| 2018 | 0.7439 | 0.7955 | 0.2561 | 39 |
| 2019 | 0.7604 | 0.8521 | 0.2396 | 50 |
| 2020 | 0.7833 | 0.8516 | 0.2167 | 31 |
| 2022 | 0.7312 | 0.7511 | 0.2688 | 18 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you use any other social media sites?... | 0.0098 | 1.0000 |
| Still thinking ahead 30 years, which do you think is more li... | 0.0180 | 1.0000 |
| Please indicate whether or not each has happened to you beca... | 0.0188 | 1.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.0220 | 0.7071 |
| Do you use a password manager, such as LastPass or iCloud Ke... | 0.0252 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think science has had a mostly positive or mostly neg... | 0.6044 | 0.0000 |
| Do you personally know anyone who has lost a job, or had the... | 0.6144 | 0.0000 |
| Do you think it is very likely, somewhat likely, not very li... | 0.6324 | 0.3586 |
| How much health risk, if any, does eating fruits and vegetab... | 0.6579 | 0.0000 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
