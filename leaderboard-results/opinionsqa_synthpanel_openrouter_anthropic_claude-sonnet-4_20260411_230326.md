# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-sonnet-4
**Dataset:** opinionsqa (684 questions)
**Samples per question:** 30
**Elapsed:** 334.7s

## SynthBench Parity Score (SPS)

**SPS: 0.7911 [0.6948, 0.7106]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7867 [0.7775, 0.7948] | ████████░░ |
| P_rank  Rank-Order | 0.6188 [0.6061, 0.6326] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.9679 [0.9576, 0.9753] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2133 |
| Median JSD | 0.1817 |
| Mean Kendall's tau | 0.2375 |
| Composite Parity (legacy) | 0.7027 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1407 | +25% |
| random-baseline | 0.6495 | +0.0532 | +8% |

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
| 2017 | 0.7409 | 0.7844 | 0.2591 | 99 |
| 2018 | 0.7257 | 0.7874 | 0.2743 | 124 |
| 2019 | 0.7990 | 0.5800 | 0.2010 | 218 |
| 2020 | 0.8079 | 0.5000 | 0.1921 | 101 |
| 2022 | 0.8379 | 0.5000 | 0.1621 | 142 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Have you ever had your pay or hours reduced because your emp... | 0.0034 | 0.9129 |
| Have you participated in any of these groups during the last... | 0.0060 | 1.0000 |
| Do you think the following are likely to happen as a result ... | 0.0060 | 1.0000 |
| If robots and computers perform most of the jobs currently b... | 0.0100 | 1.0000 |
| Have you ever been a victim of a violent crime, whether a gu... | 0.0120 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you personally know anyone who has lost a job, or had the... | 0.6144 | 0.0000 |
| How likely is the following if gene editing to change a baby... | 0.6218 | 0.0000 |
| How well, if at all, do the following words or phrases descr... | 0.6276 | 0.0000 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
| Now thinking about your own experiences have you ever person... | 0.6902 | -0.3333 |
