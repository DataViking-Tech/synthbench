# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85
**Dataset:** subpop (100 questions)
**Samples per question:** 30
**Elapsed:** 2984.2s

## SynthBench Parity Score (SPS)

**SPS: 0.6664 [0.6970, 0.7510]** (from 5 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7114 [0.6777, 0.7409] | ███████░░░ |
| P_rank  Rank-Order | 0.7378 [0.7044, 0.7691] | ███████░░░ |
| P_cond  Conditioning | 0.0000 | ░░░░░░░░░░ |
| P_sub   Subgroup | 0.9247 | █████████░ |
| P_refuse Refusal Cal. | 0.9581 [0.9116, 0.9784] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2886 |
| Median JSD | 0.2676 |
| Mean Kendall's tau | 0.4756 |
| Composite Parity (legacy) | 0.7246 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1626 | +29% |
| random-baseline | 0.6495 | +0.0751 | +12% |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Demographic Breakdown

### INCOME

Best: $100,000 or more (P_dist=0.6748) / Worst: Less than $30,000 (P_dist=0.5803)

| Group | P_dist | P_cond | Questions |
|-------|--------|--------|-----------|
| $100,000 or more | 0.6748 | 0.0279 | 100 |
| Less than $30,000 | 0.5803 | 0.0176 | 100 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| Please indicate if you have attended a concert over the past... | 0.0309 | 1.0000 |
| Do you think people have ever assumed that you benefited unf... | 0.0400 | 0.6667 |
| Do you think gender should be a major factor, minor factor, ... | 0.0446 | 0.9129 |
| How would you rate the job the Biden administration has done... | 0.0510 | 0.9487 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How acceptable do you think it is for a smart speaker to ana... | 0.6048 | 0.1155 |
| Do you think race or ethnicity should be a major factor, min... | 0.6062 | 0.2357 |
| Regardless of whether you think abortion should be legal or ... | 0.6204 | 0.0861 |
| Thinking about the use of artificial intelligence (AI) in th... | 0.6221 | 0.0000 |
| In the news you are receiving about the Biden administration... | 1.0000 | 0.0000 |
