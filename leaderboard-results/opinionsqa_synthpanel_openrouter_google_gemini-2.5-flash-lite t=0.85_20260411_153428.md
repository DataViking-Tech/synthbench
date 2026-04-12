# SynthBench Score Card

**Provider:** synthpanel/openrouter/google/gemini-2.5-flash-lite t=0.85
**Dataset:** opinionsqa (100 questions)
**Samples per question:** 30
**Elapsed:** 152.6s

## SynthBench Parity Score (SPS)

**SPS: 0.8468 [0.7465, 0.7971]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7480 [0.7196, 0.7756] | ███████░░░ |
| P_rank  Rank-Order | 0.7981 [0.7696, 0.8233] | ████████░░ |
| P_refuse Refusal Cal. | 0.9943 [0.9934, 0.9949] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2520 |
| Median JSD | 0.2490 |
| Mean Kendall's tau | 0.5961 |
| Composite Parity (legacy) | 0.7730 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2110 | +38% |
| random-baseline | 0.6495 | +0.1235 | +19% |

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
| 2017 | 0.7486 | 0.7979 | 0.2514 | 99 |
| 2018 | 0.6876 | 0.8162 | 0.3124 | 1 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| If driverless vehicles become widespread, which of the follo... | 0.0026 | 1.0000 |
| Do you think men and women are basically similar or basicall... | 0.0032 | 1.0000 |
| Do you think men and women are basically similar or basicall... | 0.0041 | 1.0000 |
| Has anyone ever used a gun to threaten or intimidate you or ... | 0.0211 | 1.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.0220 | 0.7071 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| In the last 12 months, how often did you talk with any of yo... | 0.5124 | 0.3563 |
| Compared to 50 years ago, do you think... | 0.5189 | 0.5477 |
| How well, if at all, do the following words or phrases descr... | 0.5362 | 0.3162 |
| Regardless of whether or not you own a gun, have you ever fi... | 0.5721 | 0.0000 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
