# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85 tpl=current
**Dataset:** subpop (100 questions)
**Samples per question:** 30
**Elapsed:** 266.5s

## SynthBench Parity Score (SPS)

**SPS: 0.7038 [0.6118, 0.6951]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6561 [0.6082, 0.6978] | ███████░░░ |
| P_rank  Rank-Order | 0.6552 [0.6038, 0.7000] | ███████░░░ |
| P_refuse Refusal Cal. | 0.8000 [0.7319, 0.8563] | ████████░░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3439 |
| Median JSD | 0.2882 |
| Mean Kendall's tau | 0.3104 |
| Composite Parity (legacy) | 0.6557 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.0937 | +17% |
| random-baseline | 0.6495 | +0.0061 | +1% |

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
| Do you think whether a relative attended the school should b... | 0.0112 | 1.0000 |
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| Have there been times in the past 12 months when you did not... | 0.0420 | 0.9129 |
| Do you think there are situations when abortion should be le... | 0.0546 | 1.0000 |
| Do you think gender should be a major factor, minor factor, ... | 0.0728 | 0.9129 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| If a doctor or provider performed an abortion in a situation... | 1.0000 | 0.0000 |
| If a doctor or provider performed an abortion in a situation... | 1.0000 | 0.0000 |
| Thinking about policies around abortion in this country, in ... | 1.0000 | 0.0000 |
| As you may know, the Supreme Court’s decision found that the... | 1.0000 | 0.0000 |
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
