# SynthBench Score Card

**Provider:** synthpanel/openrouter/google/gemini-2.5-flash-lite t=1.5
**Dataset:** opinionsqa (100 questions)
**Samples per question:** 30
**Elapsed:** 133.6s

## SynthBench Parity Score (SPS)

**SPS: 0.8585 [0.7648, 0.8144]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7713 [0.7451, 0.7966] | ████████░░ |
| P_rank  Rank-Order | 0.8100 [0.7820, 0.8363] | ████████░░ |
| P_refuse Refusal Cal. | 0.9943 [0.9934, 0.9949] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2287 |
| Median JSD | 0.2237 |
| Mean Kendall's tau | 0.6199 |
| Composite Parity (legacy) | 0.7906 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2286 | +41% |
| random-baseline | 0.6495 | +0.1411 | +22% |

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
| 2017 | 0.7722 | 0.8099 | 0.2278 | 99 |
| 2018 | 0.6876 | 0.8162 | 0.3124 | 1 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Has anyone ever used a gun to threaten or intimidate you or ... | 0.0020 | 1.0000 |
| Do you think men and women are basically similar or basicall... | 0.0042 | 1.0000 |
| If driverless vehicles become widespread, which of the follo... | 0.0135 | 1.0000 |
| Do you think men and women are basically similar or basicall... | 0.0155 | 1.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.0220 | 0.7071 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| The next question is about local elections, such as for mayo... | 0.5062 | 0.3162 |
| Do you personally know anyone who has lost a job, or had the... | 0.5178 | 0.3333 |
| Compared to 50 years ago, do you think... | 0.5189 | 0.5477 |
| How well, if at all, do the following words or phrases descr... | 0.5362 | 0.3162 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
