# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85 tpl=values
**Dataset:** subpop (100 questions)
**Samples per question:** 30
**Elapsed:** 286.6s

## SynthBench Parity Score (SPS)

**SPS: 0.5776 [0.5658, 0.6591]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6104 [0.5526, 0.6598] | ██████░░░░ |
| P_rank  Rank-Order | 0.6210 [0.5751, 0.6636] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.5015 [0.4358, 0.5700] | █████░░░░░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3896 |
| Median JSD | 0.3203 |
| Mean Kendall's tau | 0.2419 |
| Composite Parity (legacy) | 0.6157 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.0537 | +10% |
| random-baseline | 0.6495 | -0.0338 | -5% |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Did you refuse to answer the previous question?... | 0.0001 | 1.0000 |
| Over the next 20 years, how much impact do you think the use... | 0.0126 | 0.8000 |
| Have there been times in the past 12 months when you did not... | 0.0213 | 0.9129 |
| Do you think there are situations when abortion should be le... | 0.0355 | 1.0000 |
| If an abortion was carried out in a situation where it was i... | 0.0568 | 0.3333 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Which statement comes closer to your view, even if neither i... | 0.9648 | -0.8165 |
| Just to confirm, do you think there are any exceptions when ... | 0.9809 | -0.8165 |
| Thinking about abortion policies around the country, which i... | 1.0000 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 1.0000 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 1.0000 | 0.0000 |
