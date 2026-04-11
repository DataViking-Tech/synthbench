# SynthBench Score Card

**Provider:** random-baseline
**Dataset:** opinionsqa (80 questions)
**Samples per question:** 5
**Elapsed:** 0.0s

## SynthBench Parity Score (SPS)

**SPS: 0.7041 [0.5120, 0.6050]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6329 [0.5848, 0.6728] | ██████░░░░ |
| P_rank  Rank-Order | 0.4887 [0.4340, 0.5377] | █████░░░░░ |
| P_refuse Refusal Cal. | 0.9909 [0.9889, 0.9922] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3671 |
| Median JSD | 0.3423 |
| Mean Kendall's tau | -0.0226 |
| Composite Parity (legacy) | 0.5608 |

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
| Thinking about how the federal government spends money, do y... | 0.0201 | 0.9129 |
| Have you ever taken any gun safety courses such as weapons t... | 0.0370 | 0.3333 |
| Do you feel that people in your local community tend to look... | 0.0770 | 0.8165 |
| Do you think adequate housing is something the federal gover... | 0.0851 | 0.3333 |
| Thinking about the US, how much would you say the political ... | 0.0998 | 0.4472 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| In order to address economic inequality in this country, do ... | 0.7199 | -1.0000 |
| How much do you trust the accuracy of the news and informati... | 0.7614 | -0.6708 |
| How much of a challenge do you think political divides are i... | 0.8150 | -0.8944 |
| Have you or anyone in your household received unemployment b... | 0.8865 | -1.0000 |
| Thinking about elections in the country, how important, if a... | 0.9217 | -0.5976 |
