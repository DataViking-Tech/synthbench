# SynthBench Score Card

**Provider:** synthpanel/openrouter/openai/gpt-4o-mini
**Dataset:** opinionsqa (200 questions)
**Samples per question:** 50
**Elapsed:** 282.1s

## SynthBench Parity Score (SPS)

**SPS: 0.7945 [0.6949, 0.7248]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7801 [0.7618, 0.7976] | ████████░░ |
| P_rank  Rank-Order | 0.6370 [0.6133, 0.6615] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.9663 [0.9611, 0.9710] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2199 |
| Median JSD | 0.1771 |
| Mean Kendall's tau | 0.2739 |
| Composite Parity (legacy) | 0.7085 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1465 | +26% |
| random-baseline | 0.6495 | +0.0590 | +9% |

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
| 2017 | 0.7226 | 0.7725 | 0.2774 | 99 |
| 2018 | 0.8365 | 0.5041 | 0.1635 | 101 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Which of the following, if any, do you restrict or limit eat... | 0.0005 | 0.0000 |
| Which of the following, if any, do you restrict or limit eat... | 0.0040 | 0.0000 |
| Have you ever personally experienced discrimination or been ... | 0.0075 | 1.0000 |
| Which of the following, if any, do you restrict or limit eat... | 0.0129 | 0.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.0220 | 0.7071 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you personally know anyone who has lost a job, or had the... | 0.5448 | 0.3333 |
| How much, if at all, do you worry about the following happen... | 0.5762 | 0.2357 |
| How much of a problem was gun violence in the community wher... | 0.6466 | 0.1195 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
| How often, if ever, do you participate in online discussion ... | 0.6735 | 0.3586 |
