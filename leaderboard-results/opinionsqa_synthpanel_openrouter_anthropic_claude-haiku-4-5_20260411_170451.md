# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** opinionsqa (200 questions)
**Samples per question:** 30
**Elapsed:** 195.2s

## SynthBench Parity Score (SPS)

**SPS: 0.8313 [0.7375, 0.7826]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7368 [0.7110, 0.7606] | ███████░░░ |
| P_rank  Rank-Order | 0.7861 [0.7606, 0.8088] | ████████░░ |
| P_refuse Refusal Cal. | 0.9710 [0.9470, 0.9837] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2632 |
| Median JSD | 0.2504 |
| Mean Kendall's tau | 0.5722 |
| Composite Parity (legacy) | 0.7614 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1995 | +35% |
| random-baseline | 0.6495 | +0.1119 | +17% |

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
| 2017 | 0.7573 | 0.7956 | 0.2427 | 99 |
| 2018 | 0.7167 | 0.7769 | 0.2833 | 101 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Regardless of whether or not you own a gun, have you ever fi... | 0.0025 | 1.0000 |
| Have you participated in any of these groups during the last... | 0.0045 | 1.0000 |
| Do you think the following are likely to happen as a result ... | 0.0052 | 1.0000 |
| When it comes to sexual harassment in the workplace today, h... | 0.0105 | 1.0000 |
| How important, if at all, do you think work skills learned o... | 0.0115 | 0.9129 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How much health risk, if any, does eating fruits and vegetab... | 0.6579 | 0.0000 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
| Compared to 50 years ago, do you think... | 0.7640 | -0.2357 |
| Do you think it is very likely, somewhat likely, not very li... | 0.8241 | 0.1195 |
| Which statement comes closer to your view, even if neither i... | 1.0000 | 0.0000 |
