# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-sonnet-4
**Dataset:** opinionsqa (684 questions)
**Samples per question:** 30
**Elapsed:** 572.6s

## SynthBench Parity Score (SPS)

**SPS: 0.8262 [0.7471, 0.7672]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7251 [0.7145, 0.7353] | ███████░░░ |
| P_rank  Rank-Order | 0.7891 [0.7768, 0.7995] | ████████░░ |
| P_refuse Refusal Cal. | 0.9644 [0.9562, 0.9705] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2749 |
| Median JSD | 0.2715 |
| Mean Kendall's tau | 0.5781 |
| Composite Parity (legacy) | 0.7571 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1951 | +35% |
| random-baseline | 0.6495 | +0.1076 | +17% |

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
| 2017 | 0.7418 | 0.7872 | 0.2582 | 99 |
| 2018 | 0.7256 | 0.7924 | 0.2744 | 124 |
| 2019 | 0.7143 | 0.7866 | 0.2858 | 218 |
| 2020 | 0.7514 | 0.8126 | 0.2485 | 101 |
| 2022 | 0.7110 | 0.7745 | 0.2890 | 142 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you regularly wear a smart watch or a wearable fitness tr... | 0.0016 | 1.0000 |
| Do you think the following are likely to happen as a result ... | 0.0029 | 1.0000 |
| Do you approve or disapprove of the way Joe Biden is handlin... | 0.0062 | 0.8165 |
| Have you participated in any of these groups during the last... | 0.0065 | 1.0000 |
| Please choose the statement that comes closer to your own vi... | 0.0095 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Thinking about the adults in your life, who is the person yo... | 0.6401 | 0.4700 |
| Please indicate how much of a problem, if at all, the follow... | 0.6625 | 0.0000 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
| By 2050, do you expect that people who are married will be... | 0.7382 | -0.2357 |
| Now thinking about your own experiences have you ever person... | 0.8259 | -0.3333 |
