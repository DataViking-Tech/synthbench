# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85 tpl=values
**Dataset:** subpop (100 questions)
**Samples per question:** 30
**Elapsed:** 188.5s

## SynthBench Parity Score (SPS)

**SPS: 0.5318 [0.5415, 0.6435]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.5796 [0.5171, 0.6352] | ██████░░░░ |
| P_rank  Rank-Order | 0.6154 [0.5630, 0.6603] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.4003 [0.3459, 0.4565] | ████░░░░░░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.4204 |
| Median JSD | 0.3222 |
| Mean Kendall's tau | 0.2308 |
| Composite Parity (legacy) | 0.5975 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.0355 | +6% |
| random-baseline | 0.6495 | -0.0520 | -8% |

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
| Do you think there are situations when abortion should be le... | 0.0068 | 1.0000 |
| Have there been times in the past 12 months when you did not... | 0.0213 | 0.9129 |
| Over the next 20 years, how much impact do you think the use... | 0.0241 | 0.8000 |
| Do you think high school grades should be a major factor, mi... | 0.0535 | 0.9129 |
| Do you personally know someone (such as a close friend, fami... | 0.0660 | 0.3333 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| If a doctor or provider performed an abortion in a situation... | 1.0000 | 0.0000 |
| Thinking about policies around abortion in this country, in ... | 1.0000 | 0.0000 |
| As you may know, the Supreme Court’s decision found that the... | 1.0000 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 1.0000 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 1.0000 | 0.0000 |
