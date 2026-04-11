# SynthBench Score Card

**Provider:** synthpanel/gemini-2.5-flash-lite
**Dataset:** subpop (200 questions)
**Samples per question:** 30
**Elapsed:** 146.6s

## SynthBench Parity Score (SPS)

**SPS: 0.8210 [0.7244, 0.7634]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7071 [0.6835, 0.7295] | ███████░░░ |
| P_rank  Rank-Order | 0.7804 [0.7619, 0.7993] | ████████░░ |
| P_refuse Refusal Cal. | 0.9755 [0.9539, 0.9862] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2929 |
| Median JSD | 0.2712 |
| Mean Kendall's tau | 0.5608 |
| Composite Parity (legacy) | 0.7437 |

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
| Do you believe in hell?... | 0.0101 | 1.0000 |
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| Please choose the statement that comes closer to your own vi... | 0.0157 | 1.0000 |
| Do you believe in fate, the idea that the course of your lif... | 0.0198 | 1.0000 |
| Please indicate if you have attended a concert over the past... | 0.0200 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Have you heard of the social media site or app Rumble?... | 0.6286 | 0.0000 |
| How much have you heard about the boycott, divestment, and s... | 0.7013 | 0.0000 |
| Have you heard of the social media site or app Gab?... | 0.7439 | 0.0000 |
| In recent years, several social media sites have emerged as ... | 0.7570 | 0.0000 |
| Have you heard of the social media site or app BitChute?... | 0.8196 | 0.0000 |
