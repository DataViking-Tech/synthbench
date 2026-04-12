# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85 tpl=minimal
**Dataset:** subpop (100 questions)
**Samples per question:** 30
**Elapsed:** 182.4s

## SynthBench Parity Score (SPS)

**SPS: 0.5771 [0.5562, 0.6562]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6086 [0.5518, 0.6598] | ██████░░░░ |
| P_rank  Rank-Order | 0.6123 [0.5630, 0.6588] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.5105 [0.4469, 0.5755] | █████░░░░░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3914 |
| Median JSD | 0.2945 |
| Mean Kendall's tau | 0.2245 |
| Composite Parity (legacy) | 0.6104 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.0485 | +9% |
| random-baseline | 0.6495 | -0.0391 | -6% |

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
| Do you think there are situations when abortion should be le... | 0.0069 | 1.0000 |
| If an abortion was carried out in a situation where it was i... | 0.0161 | 1.0000 |
| Over the next 20 years, how much impact do you think the use... | 0.0212 | 0.6000 |
| Thinking about the use of artificial intelligence (AI) in th... | 0.0355 | 0.8000 |
| Have there been times in the past 12 months when you did not... | 0.0713 | 0.9129 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Which statement comes closer to your view, even if neither i... | 0.9648 | -0.8165 |
| Please indicate if you have attended a concert over the past... | 0.9792 | -0.8165 |
| As you may know, the Supreme Court’s decision found that the... | 1.0000 | 0.0000 |
| Do you think race or ethnicity should be a major factor, min... | 1.0000 | 0.0000 |
| Do you think gender should be a major factor, minor factor, ... | 1.0000 | 0.0000 |
