# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85 tpl=demo
**Dataset:** subpop (100 questions)
**Samples per question:** 30
**Elapsed:** 283.3s

## SynthBench Parity Score (SPS)

**SPS: 0.5700 [0.5600, 0.6584]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6041 [0.5441, 0.6571] | ██████░░░░ |
| P_rank  Rank-Order | 0.6211 [0.5742, 0.6673] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.4848 [0.4223, 0.5481] | █████░░░░░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3959 |
| Median JSD | 0.3037 |
| Mean Kendall's tau | 0.2422 |
| Composite Parity (legacy) | 0.6126 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.0506 | +9% |
| random-baseline | 0.6495 | -0.0369 | -6% |

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
| Do you think there are situations when abortion should be le... | 0.0071 | 1.0000 |
| Do you think the United States’ decision to withdraw all tro... | 0.0242 | 0.8165 |
| Have there been times in the past 12 months when you did not... | 0.0295 | 0.9129 |
| Do you think whether a relative attended the school should b... | 0.0347 | 0.9129 |
| Did you refuse to answer the previous question?... | 0.0502 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Regardless of whether you think abortion should be legal or ... | 1.0000 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 1.0000 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 1.0000 | 0.0000 |
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
| Do you think race or ethnicity should be a major factor, min... | 1.0000 | 0.0000 |
