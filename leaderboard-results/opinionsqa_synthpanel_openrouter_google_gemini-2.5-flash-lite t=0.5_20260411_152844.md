# SynthBench Score Card

**Provider:** synthpanel/openrouter/google/gemini-2.5-flash-lite t=0.5
**Dataset:** opinionsqa (100 questions)
**Samples per question:** 30
**Elapsed:** 156.7s

## SynthBench Parity Score (SPS)

**SPS: 0.8260 [0.7147, 0.7687]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7089 [0.6806, 0.7410] | ███████░░░ |
| P_rank  Rank-Order | 0.7747 [0.7455, 0.8034] | ████████░░ |
| P_refuse Refusal Cal. | 0.9943 [0.9934, 0.9949] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2911 |
| Median JSD | 0.3030 |
| Mean Kendall's tau | 0.5494 |
| Composite Parity (legacy) | 0.7418 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1798 | +32% |
| random-baseline | 0.6495 | +0.0923 | +14% |

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
| 2017 | 0.7092 | 0.7743 | 0.2908 | 99 |
| 2018 | 0.6876 | 0.8162 | 0.3124 | 1 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think men and women are basically similar or basicall... | 0.0032 | 1.0000 |
| If driverless vehicles become widespread, which of the follo... | 0.0051 | 1.0000 |
| Has anyone ever used a gun to threaten or intimidate you or ... | 0.0109 | 1.0000 |
| Do you think men and women are basically similar or basicall... | 0.0156 | 1.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.0220 | 0.7071 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How well, if at all, do the following words or phrases descr... | 0.5362 | 0.3162 |
| How much of a problem was gun violence in the community wher... | 0.5552 | 0.3162 |
| Regardless of whether or not you own a gun, have you ever fi... | 0.5721 | 0.0000 |
| Do you personally know anyone who has lost a job, or had the... | 0.6144 | 0.0000 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
