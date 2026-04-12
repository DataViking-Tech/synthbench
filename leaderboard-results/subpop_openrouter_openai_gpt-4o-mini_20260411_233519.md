# SynthBench Score Card

**Provider:** openrouter/openai/gpt-4o-mini
**Dataset:** subpop (100 questions)
**Samples per question:** 15
**Elapsed:** 115.0s

## SynthBench Parity Score (SPS)

**SPS: 0.7701 [0.6277, 0.6967]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6284 [0.5879, 0.6639] | ██████░░░░ |
| P_rank  Rank-Order | 0.7021 [0.6638, 0.7383] | ███████░░░ |
| P_refuse Refusal Cal. | 0.9799 [0.9394, 0.9903] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3716 |
| Median JSD | 0.3778 |
| Mean Kendall's tau | 0.4042 |
| Composite Parity (legacy) | 0.6652 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1032 | +18% |
| random-baseline | 0.6495 | +0.0157 | +2% |

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
| Have there been times in the past 12 months when you did not... | 0.0063 | 1.0000 |
| If an abortion was carried out in a situation where it was i... | 0.0080 | 1.0000 |
| If an abortion was carried out in a situation where it was i... | 0.0304 | 0.3333 |
| Do you think whether a relative attended the school should b... | 0.0319 | 0.9129 |
| Have there been times in the past 12 months when you did not... | 0.0607 | 0.9129 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Thinking about the use of artificial intelligence (AI) in th... | 0.6822 | -0.3162 |
| How acceptable do you think it is for social media companies... | 0.7074 | 0.0861 |
| How acceptable do you think it is for a smart speaker to ana... | 0.7683 | -0.3464 |
| Thinking now about how AI can be used in hiring, how much ha... | 0.7811 | -0.2357 |
| Did you refuse to answer the previous question?... | 1.0000 | -0.8165 |
