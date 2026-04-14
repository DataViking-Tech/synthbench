# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85
**Dataset:** subpop (100 questions)
**Samples per question:** 15
**Elapsed:** 60.3s

## SynthBench Parity Score (SPS)

**SPS: 0.7980 [0.6870, 0.7432]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6928 [0.6604, 0.7256] | ███████░░░ |
| P_rank  Rank-Order | 0.7391 [0.6998, 0.7688] | ███████░░░ |
| P_refuse Refusal Cal. | 0.9622 [0.9149, 0.9817] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3072 |
| Median JSD | 0.2959 |
| Mean Kendall's tau | 0.4781 |
| Composite Parity (legacy) | 0.7159 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1539 | +27% |
| random-baseline | 0.6495 | +0.0664 | +10% |

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
| Please indicate if you have attended a concert over the past... | 0.0200 | 1.0000 |
| Do you think gender should be a major factor, minor factor, ... | 0.0270 | 0.9129 |
| Do you think the United States’ decision to withdraw all tro... | 0.0508 | 0.3333 |
| Have there been times in the past 12 months when you did not... | 0.0606 | 0.9129 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think race or ethnicity should be a major factor, min... | 0.6062 | 0.2357 |
| Thinking about the use of artificial intelligence (AI) in th... | 0.6221 | 0.0000 |
| How important is your religion in shaping your views about a... | 0.6310 | -0.4606 |
| Regardless of whether you think abortion should be legal or ... | 0.6906 | -0.3464 |
| In the news you are receiving about the Biden administration... | 1.0000 | 0.0000 |
