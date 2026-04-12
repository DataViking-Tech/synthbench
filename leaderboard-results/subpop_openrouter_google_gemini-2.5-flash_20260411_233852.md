# SynthBench Score Card

**Provider:** openrouter/google/gemini-2.5-flash
**Dataset:** subpop (100 questions)
**Samples per question:** 15
**Elapsed:** 154.5s

## SynthBench Parity Score (SPS)

**SPS: 0.7826 [0.6430, 0.7179]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6694 [0.6236, 0.7057] | ███████░░░ |
| P_rank  Rank-Order | 0.6984 [0.6541, 0.7358] | ███████░░░ |
| P_refuse Refusal Cal. | 0.9799 [0.9394, 0.9903] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3306 |
| Median JSD | 0.2675 |
| Mean Kendall's tau | 0.3967 |
| Composite Parity (legacy) | 0.6839 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1219 | +22% |
| random-baseline | 0.6495 | +0.0344 | +5% |

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
| Please indicate if you have traveled more than 100 miles fro... | 0.0025 | 1.0000 |
| In the news you are receiving about the Biden administration... | 0.0676 | 1.0000 |
| Have there been times in the past 12 months when you did not... | 0.0759 | 0.5477 |
| Do you personally know someone (such as a close friend, fami... | 0.0847 | 1.0000 |
| Do you think that you have ever been at an advantage in your... | 0.0875 | 0.9129 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think abortion should be...... | 0.8173 | -0.3586 |
| Do you think abortion should be...... | 0.8231 | -0.3586 |
| Do you think abortion should be...... | 0.9401 | -0.6325 |
| How confident, if at all, are you that the government is con... | 0.9474 | -0.6325 |
| Do you think abortion should be…... | 0.9526 | -0.6325 |
