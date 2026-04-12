# SynthBench Score Card

**Provider:** synthpanel/openrouter/google/gemini-2.5-flash-lite t=1.0
**Dataset:** opinionsqa (100 questions)
**Samples per question:** 30
**Elapsed:** 197.7s

## SynthBench Parity Score (SPS)

**SPS: 0.8540 [0.7550, 0.8083]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7663 [0.7386, 0.7942] | ████████░░ |
| P_rank  Rank-Order | 0.8019 [0.7730, 0.8293] | ████████░░ |
| P_refuse Refusal Cal. | 0.9940 [0.9929, 0.9947] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2337 |
| Median JSD | 0.2309 |
| Mean Kendall's tau | 0.6037 |
| Composite Parity (legacy) | 0.7841 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2221 | +40% |
| random-baseline | 0.6495 | +0.1345 | +21% |

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
| 2017 | 0.7670 | 0.8017 | 0.2330 | 99 |
| 2018 | 0.6876 | 0.8162 | 0.3124 | 1 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| If driverless vehicles become widespread, which of the follo... | 0.0044 | 1.0000 |
| Do you think men and women are basically similar or basicall... | 0.0067 | 1.0000 |
| Do you think men and women are basically similar or basicall... | 0.0114 | 1.0000 |
| Do you think men and women are basically similar or basicall... | 0.0203 | 1.0000 |
| Has anyone ever used a gun to threaten or intimidate you or ... | 0.0211 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you personally know anyone who has lost a job, or had the... | 0.5178 | 0.3333 |
| How well, if at all, do the following words or phrases descr... | 0.5362 | 0.3162 |
| Compared to 50 years ago, do you think... | 0.5634 | 0.1826 |
| Regardless of whether or not you own a gun, have you ever fi... | 0.5721 | 0.0000 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
