# SynthBench Score Card

**Provider:** synthpanel/openrouter/google/gemini-2.5-flash-lite t=0.85
**Dataset:** opinionsqa (100 questions)
**Samples per question:** 30
**Elapsed:** 486.1s

## SynthBench Parity Score (SPS)

**SPS: 0.8504 [0.7514, 0.8028]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7584 [0.7329, 0.7861] | ████████░░ |
| P_rank  Rank-Order | 0.7986 [0.7687, 0.8247] | ████████░░ |
| P_refuse Refusal Cal. | 0.9943 [0.9934, 0.9949] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2416 |
| Median JSD | 0.2463 |
| Mean Kendall's tau | 0.5973 |
| Composite Parity (legacy) | 0.7785 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2165 | +39% |
| random-baseline | 0.6495 | +0.1290 | +20% |

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
| 2017 | 0.7591 | 0.7985 | 0.2409 | 99 |
| 2018 | 0.6876 | 0.8162 | 0.3124 | 1 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Has anyone ever used a gun to threaten or intimidate you or ... | 0.0049 | 1.0000 |
| If driverless vehicles become widespread, which of the follo... | 0.0102 | 1.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.0220 | 0.7071 |
| Do you think men and women are basically similar or basicall... | 0.0242 | 1.0000 |
| Have you ever had your pay or hours reduced because your emp... | 0.0333 | 0.7071 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How much of a problem was gun violence in the community wher... | 0.4642 | 0.5976 |
| Do you think it is very likely, somewhat likely, not very li... | 0.4844 | 0.3162 |
| Compared to 50 years ago, do you think... | 0.5189 | 0.5477 |
| Regardless of whether or not you own a gun, have you ever fi... | 0.5721 | 0.0000 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
