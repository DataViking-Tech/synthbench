# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-sonnet-4
**Dataset:** opinionsqa (684 questions)
**Samples per question:** 30
**Elapsed:** 565.7s

## SynthBench Parity Score (SPS)

**SPS: 0.8290 [0.7493, 0.7699]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7263 [0.7156, 0.7371] | ███████░░░ |
| P_rank  Rank-Order | 0.7929 [0.7812, 0.8035] | ████████░░ |
| P_refuse Refusal Cal. | 0.9677 [0.9594, 0.9731] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2737 |
| Median JSD | 0.2674 |
| Mean Kendall's tau | 0.5859 |
| Composite Parity (legacy) | 0.7596 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1977 | +35% |
| random-baseline | 0.6495 | +0.1101 | +17% |

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
| 2017 | 0.7381 | 0.7842 | 0.2619 | 99 |
| 2018 | 0.7254 | 0.7973 | 0.2746 | 124 |
| 2019 | 0.7198 | 0.7846 | 0.2802 | 218 |
| 2020 | 0.7613 | 0.8259 | 0.2387 | 101 |
| 2022 | 0.7041 | 0.7845 | 0.2959 | 142 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think the following are likely to happen as a result ... | 0.0023 | 1.0000 |
| Do you regularly wear a smart watch or a wearable fitness tr... | 0.0052 | 1.0000 |
| Has the issue of made-up news and information led you to rep... | 0.0058 | 1.0000 |
| Have you ever shared news and information that you knew at t... | 0.0058 | 1.0000 |
| Please choose the statement that comes closer to your own vi... | 0.0067 | 0.8165 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
| By 2050, do you expect that people who are married will be... | 0.7382 | -0.2357 |
| Thinking about the adults in your life, who is the person yo... | 0.7799 | 0.2485 |
| Now thinking about your own experiences have you ever person... | 0.7974 | -0.8165 |
| Would you prefer to live in a community where the houses are... | 1.0000 | 0.0000 |
