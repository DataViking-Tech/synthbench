# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85
**Dataset:** subpop (100 questions)
**Samples per question:** 15
**Elapsed:** 77.7s

## SynthBench Parity Score (SPS)

**SPS: 0.7989 [0.6950, 0.7488]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7018 [0.6728, 0.7320] | ███████░░░ |
| P_rank  Rank-Order | 0.7410 [0.7074, 0.7696] | ███████░░░ |
| P_refuse Refusal Cal. | 0.9540 [0.9063, 0.9735] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2982 |
| Median JSD | 0.2682 |
| Mean Kendall's tau | 0.4820 |
| Composite Parity (legacy) | 0.7214 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1594 | +28% |
| random-baseline | 0.6495 | +0.0719 | +11% |

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
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| If you were looking for work, would you want to apply for a ... | 0.0339 | 1.0000 |
| Do you think gender should be a major factor, minor factor, ... | 0.0446 | 0.9129 |
| Have there been times in the past 12 months when you did not... | 0.0606 | 0.9129 |
| Would you favor or oppose employers’ use of artificial intel... | 0.0827 | 0.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Regardless of whether you think abortion should be legal or ... | 0.5807 | 0.0861 |
| How acceptable do you think it is for a smart speaker to ana... | 0.6048 | 0.1155 |
| Do you think race or ethnicity should be a major factor, min... | 0.6062 | 0.2357 |
| How important is your religion in shaping your views about a... | 0.6084 | -0.4606 |
| Thinking about the use of artificial intelligence (AI) in th... | 0.6221 | 0.0000 |
