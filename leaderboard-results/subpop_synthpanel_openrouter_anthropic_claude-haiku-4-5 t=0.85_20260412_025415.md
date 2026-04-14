# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85
**Dataset:** subpop (100 questions)
**Samples per question:** 15
**Elapsed:** 3982.8s

## SynthBench Parity Score (SPS)

**SPS: 0.6545 [0.6838, 0.7420]** (from 5 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6934 [0.6589, 0.7285] | ███████░░░ |
| P_rank  Rank-Order | 0.7324 [0.6951, 0.7619] | ███████░░░ |
| P_cond  Conditioning | 0.0332 | ░░░░░░░░░░ |
| P_sub   Subgroup | 0.8561 | █████████░ |
| P_refuse Refusal Cal. | 0.9577 [0.9100, 0.9778] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3066 |
| Median JSD | 0.2661 |
| Mean Kendall's tau | 0.4648 |
| Composite Parity (legacy) | 0.7129 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1509 | +27% |
| random-baseline | 0.6495 | +0.0634 | +10% |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Demographic Breakdown

### RACE

Best: White (P_dist=0.8258) / Worst: Black (P_dist=0.5869)

| Group | P_dist | P_cond | Questions |
|-------|--------|--------|-----------|
| White | 0.8258 | 0.1707 | 100 |
| Asian | 0.6388 | 0.0276 | 100 |
| Hispanic | 0.6029 | 0.0327 | 100 |
| Black | 0.5869 | 0.0223 | 100 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| Please indicate if you have attended a concert over the past... | 0.0200 | 1.0000 |
| Please indicate if you have attended a sporting event over t... | 0.0220 | 0.3333 |
| Do you think the United States’ decision to withdraw all tro... | 0.0314 | 0.3333 |
| Do you think gender should be a major factor, minor factor, ... | 0.0446 | 0.9129 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How acceptable do you think it is for a smart speaker to ana... | 0.6048 | 0.1155 |
| Do you think race or ethnicity should be a major factor, min... | 0.6062 | 0.2357 |
| Thinking about the use of artificial intelligence (AI) in th... | 0.6221 | 0.0000 |
| If an abortion was carried out in a situation where it was i... | 0.6746 | -0.3333 |
| In the news you are receiving about the Biden administration... | 1.0000 | 0.0000 |
