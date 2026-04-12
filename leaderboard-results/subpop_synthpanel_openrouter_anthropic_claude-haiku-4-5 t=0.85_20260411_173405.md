# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85
**Dataset:** subpop (100 questions)
**Samples per question:** 30
**Elapsed:** 3142.7s

## SynthBench Parity Score (SPS)

**SPS: 0.6805 [0.6995, 0.7530]** (from 5 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7108 [0.6843, 0.7389] | ███████░░░ |
| P_rank  Rank-Order | 0.7413 [0.7031, 0.7700] | ███████░░░ |
| P_cond  Conditioning | 0.0000 | ░░░░░░░░░░ |
| P_sub   Subgroup | 0.9881 | ██████████ |
| P_refuse Refusal Cal. | 0.9624 [0.9166, 0.9812] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2892 |
| Median JSD | 0.2747 |
| Mean Kendall's tau | 0.4827 |
| Composite Parity (legacy) | 0.7261 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1641 | +29% |
| random-baseline | 0.6495 | +0.0765 | +12% |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Demographic Breakdown

### POLPARTY

Best: Republican (P_dist=0.6608) / Worst: Democrat (P_dist=0.6453)

| Group | P_dist | P_cond | Questions |
|-------|--------|--------|-----------|
| Republican | 0.6608 | 0.0719 | 100 |
| Democrat | 0.6453 | 0.0334 | 100 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please indicate if you have attended a concert over the past... | 0.0121 | 1.0000 |
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| Have there been times in the past 12 months when you did not... | 0.0656 | 0.9129 |
| Have there been times in the past 12 months when you did not... | 0.0941 | 0.5477 |
| If you were looking for work, would you want to apply for a ... | 0.0992 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Regardless of whether you think abortion should be legal or ... | 0.5807 | 0.0861 |
| How acceptable do you think it is for a smart speaker to ana... | 0.6048 | 0.1155 |
| How important is your religion in shaping your views about a... | 0.6084 | -0.4606 |
| Regardless of whether you think abortion should be legal or ... | 0.6171 | 0.1155 |
| Thinking about the use of artificial intelligence (AI) in th... | 0.6221 | 0.0000 |
