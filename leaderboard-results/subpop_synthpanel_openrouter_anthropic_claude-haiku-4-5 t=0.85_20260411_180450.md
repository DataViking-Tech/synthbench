# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85
**Dataset:** subpop (100 questions)
**Samples per question:** 30
**Elapsed:** 2983.3s

## SynthBench Parity Score (SPS)

**SPS: 0.6795 [0.7021, 0.7572]** (from 5 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7204 [0.6907, 0.7509] | ███████░░░ |
| P_rank  Rank-Order | 0.7389 [0.6979, 0.7684] | ███████░░░ |
| P_cond  Conditioning | 0.0000 | ░░░░░░░░░░ |
| P_sub   Subgroup | 0.9792 | ██████████ |
| P_refuse Refusal Cal. | 0.9590 [0.9130, 0.9781] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2796 |
| Median JSD | 0.2592 |
| Mean Kendall's tau | 0.4778 |
| Composite Parity (legacy) | 0.7296 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1677 | +30% |
| random-baseline | 0.6495 | +0.0801 | +12% |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Demographic Breakdown

### POLPARTY

Best: Republican (P_dist=0.6648) / Worst: Democrat (P_dist=0.6377)

| Group | P_dist | P_cond | Questions |
|-------|--------|--------|-----------|
| Republican | 0.6648 | 0.0680 | 100 |
| Democrat | 0.6377 | 0.0276 | 100 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please indicate if you have attended a concert over the past... | 0.0035 | 1.0000 |
| Do you think gender should be a major factor, minor factor, ... | 0.0100 | 1.0000 |
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| Do you think the United States’ decision to withdraw all tro... | 0.0403 | 0.3333 |
| Over the next 20 years, how much impact do you think the use... | 0.0527 | 0.7379 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How much, if at all, do you think more support for parents, ... | 0.5598 | 0.1155 |
| Do you think artificial intelligence (AI) would do better, w... | 0.5772 | -0.3162 |
| How important is your religion in shaping your views about a... | 0.5869 | -0.4606 |
| Thinking about the use of artificial intelligence (AI) in th... | 0.6221 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 0.6906 | -0.3464 |
