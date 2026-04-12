# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85 tpl=minimal
**Dataset:** subpop (100 questions)
**Samples per question:** 30
**Elapsed:** 279.0s

## SynthBench Parity Score (SPS)

**SPS: 0.5846 [0.5444, 0.6447]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.5789 [0.5183, 0.6350] | ██████░░░░ |
| P_rank  Rank-Order | 0.6144 [0.5633, 0.6601] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.5604 [0.4890, 0.6355] | ██████░░░░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.4211 |
| Median JSD | 0.3210 |
| Mean Kendall's tau | 0.2289 |
| Composite Parity (legacy) | 0.5967 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.0347 | +6% |
| random-baseline | 0.6495 | -0.0529 | -8% |

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
| Did you refuse to answer the previous question?... | 0.0075 | 1.0000 |
| Over the next 20 years, how much impact do you think the use... | 0.0075 | 1.0000 |
| Do you think there are situations when abortion should be le... | 0.0094 | 1.0000 |
| Thinking about the use of artificial intelligence (AI) in th... | 0.0356 | 0.8000 |
| Do you think people have ever assumed that you benefited unf... | 0.0598 | 0.6667 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Thinking about policies around abortion in this country, in ... | 1.0000 | 0.0000 |
| As you may know, the Supreme Court’s decision found that the... | 1.0000 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 1.0000 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 1.0000 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 1.0000 | 0.0000 |
