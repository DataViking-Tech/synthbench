# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85
**Dataset:** subpop (100 questions)
**Samples per question:** 15
**Elapsed:** 4111.6s

## SynthBench Parity Score (SPS)

**SPS: 0.6619 [0.6943, 0.7529]** (from 5 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7025 [0.6718, 0.7333] | ███████░░░ |
| P_rank  Rank-Order | 0.7417 [0.7047, 0.7717] | ███████░░░ |
| P_cond  Conditioning | 0.0227 | ░░░░░░░░░░ |
| P_sub   Subgroup | 0.8768 | █████████░ |
| P_refuse Refusal Cal. | 0.9658 [0.9154, 0.9842] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2975 |
| Median JSD | 0.2798 |
| Mean Kendall's tau | 0.4834 |
| Composite Parity (legacy) | 0.7221 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1601 | +28% |
| random-baseline | 0.6495 | +0.0726 | +11% |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Demographic Breakdown

### RACE

Best: White (P_dist=0.7924) / Worst: Black (P_dist=0.5839)

| Group | P_dist | P_cond | Questions |
|-------|--------|--------|-----------|
| White | 0.7924 | 0.1415 | 100 |
| Asian | 0.6422 | 0.0290 | 100 |
| Hispanic | 0.6090 | 0.0392 | 100 |
| Black | 0.5839 | 0.0276 | 100 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please indicate if you have attended a concert over the past... | 0.0023 | 1.0000 |
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| Do you think people have ever assumed that you benefited unf... | 0.0155 | 1.0000 |
| Do you think gender should be a major factor, minor factor, ... | 0.0278 | 0.9129 |
| Do you think the United States’ decision to withdraw all tro... | 0.0508 | 0.3333 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How acceptable do you think it is for a smart speaker to ana... | 0.6048 | 0.1155 |
| Do you think race or ethnicity should be a major factor, min... | 0.6062 | 0.2357 |
| Thinking about the use of artificial intelligence (AI) in th... | 0.6221 | 0.0000 |
| How important is your religion in shaping your views about a... | 0.6310 | -0.4606 |
| Regardless of whether you think abortion should be legal or ... | 0.6906 | -0.3464 |
