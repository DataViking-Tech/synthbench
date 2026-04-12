# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** opinionsqa (175 questions)
**Samples per question:** 50
**Elapsed:** 228.3s

## SynthBench Parity Score (SPS)

**SPS: 0.8497 [0.7612, 0.7996]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7502 [0.7292, 0.7696] | ████████░░ |
| P_rank  Rank-Order | 0.8133 [0.7913, 0.8330] | ████████░░ |
| P_refuse Refusal Cal. | 0.9858 [0.9778, 0.9888] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2498 |
| Median JSD | 0.2514 |
| Mean Kendall's tau | 0.6265 |
| Composite Parity (legacy) | 0.7817 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2197 | +39% |
| random-baseline | 0.6495 | +0.1322 | +20% |

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
| 2017 | 0.7486 | 0.7913 | 0.2514 | 37 |
| 2018 | 0.7430 | 0.8013 | 0.2570 | 39 |
| 2019 | 0.7508 | 0.8466 | 0.2492 | 50 |
| 2020 | 0.7706 | 0.8365 | 0.2294 | 31 |
| 2022 | 0.7324 | 0.7516 | 0.2676 | 18 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please indicate whether or not each has happened to you beca... | 0.0082 | 1.0000 |
| Do you use a password manager, such as LastPass or iCloud Ke... | 0.0174 | 1.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.0220 | 0.7071 |
| In general, thinking about job opportunities where you live,... | 0.0230 | 1.0000 |
| In the last 12 months, have you had someone attempt to open ... | 0.0320 | 0.8165 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How much health risk, if any, does eating food and drinks wi... | 0.5441 | 0.3162 |
| Do you think it is very likely, somewhat likely, not very li... | 0.6025 | 0.3586 |
| Do you personally know anyone who has lost a job, or had the... | 0.6144 | 0.0000 |
| How much health risk, if any, does eating fruits and vegetab... | 0.6579 | 0.0000 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
