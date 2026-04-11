# SynthBench Score Card

**Provider:** majority-baseline
**Dataset:** opinionsqa (80 questions)
**Samples per question:** 5
**Elapsed:** 0.0s

## SynthBench Parity Score (SPS)

**SPS: 0.7145 [0.5309, 0.6208]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.5119 [0.4573, 0.5635] | █████░░░░░ |
| P_rank  Rank-Order | 0.6407 [0.5929, 0.6833] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.9909 [0.9889, 0.9922] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.4881 |
| Median JSD | 0.4633 |
| Mean Kendall's tau | 0.2814 |
| Composite Parity (legacy) | 0.5763 |

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
| Thinking about elections in the country, how important, if a... | 0.0553 | 0.6325 |
| Do you think high quality K-12 education is something the fe... | 0.1084 | 0.8165 |
| In your opinion, do you think government investments in basi... | 0.1087 | 0.8165 |
| Regardless of whether or not you own a gun, have you ever fi... | 0.1277 | 0.8165 |
| Overall, how much of an impact do you think made-up news and... | 0.1641 | 0.6325 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| In general, would you say the quality of the candidates runn... | 0.9243 | -0.3162 |
| How often, if ever, do you visit websites about guns, huntin... | 0.9259 | -0.3162 |
| As far as you know, how many of your neighbors have the same... | 0.9440 | -0.5774 |
| How often, if ever, do you attend gun shows... | 0.9625 | -0.3162 |
| How often, if ever, do you listen to gun-oriented podcasts o... | 0.9692 | -0.3162 |
