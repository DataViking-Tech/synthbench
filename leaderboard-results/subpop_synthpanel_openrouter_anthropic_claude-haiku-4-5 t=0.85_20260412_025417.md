# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85
**Dataset:** subpop (100 questions)
**Samples per question:** 15
**Elapsed:** 4415.1s

## SynthBench Parity Score (SPS)

**SPS: 0.6605 [0.6902, 0.7448]** (from 5 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7024 [0.6733, 0.7315] | ███████░░░ |
| P_rank  Rank-Order | 0.7324 [0.6955, 0.7623] | ███████░░░ |
| P_cond  Conditioning | 0.0092 | ░░░░░░░░░░ |
| P_sub   Subgroup | 0.9070 | █████████░ |
| P_refuse Refusal Cal. | 0.9516 [0.9050, 0.9721] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2976 |
| Median JSD | 0.2630 |
| Mean Kendall's tau | 0.4648 |
| Composite Parity (legacy) | 0.7174 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1554 | +28% |
| random-baseline | 0.6495 | +0.0679 | +10% |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Demographic Breakdown

### RACE

Best: White (P_dist=0.7370) / Worst: Black (P_dist=0.5829)

| Group | P_dist | P_cond | Questions |
|-------|--------|--------|-----------|
| White | 0.7370 | 0.1101 | 100 |
| Asian | 0.6287 | 0.0196 | 100 |
| Hispanic | 0.6040 | 0.0299 | 100 |
| Black | 0.5829 | 0.0238 | 100 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| If you were looking for work, would you want to apply for a ... | 0.0569 | 1.0000 |
| Have there been times in the past 12 months when you did not... | 0.0630 | 0.9129 |
| Over the next 20 years, how much impact do you think the use... | 0.0648 | 0.4000 |
| Have there been times in the past 12 months when you did not... | 0.0690 | 0.9129 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think artificial intelligence (AI) would do better, w... | 0.5772 | -0.3162 |
| How important is your religion in shaping your views about a... | 0.5819 | -0.4606 |
| Do you think race or ethnicity should be a major factor, min... | 0.6062 | 0.2357 |
| Thinking about the use of artificial intelligence (AI) in th... | 0.6221 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 0.6906 | -0.3464 |
