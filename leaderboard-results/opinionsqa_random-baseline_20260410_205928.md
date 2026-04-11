# SynthBench Score Card

**Provider:** random-baseline
**Dataset:** opinionsqa (175 questions)
**Samples per question:** 5
**Elapsed:** 0.0s

## SynthBench Parity Score (SPS)

**SPS: 0.7282 [0.5667, 0.6311]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6903 [0.6599, 0.7184] | ███████░░░ |
| P_rank  Rank-Order | 0.5064 [0.4626, 0.5433] | █████░░░░░ |
| P_refuse Refusal Cal. | 0.9880 [0.9850, 0.9903] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3097 |
| Median JSD | 0.2661 |
| Mean Kendall's tau | 0.0129 |
| Composite Parity (legacy) | 0.5984 |

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
| Do you think changing a baby's genetic characteristics to tr... | 0.0084 | 1.0000 |
| Still thinking ahead 30 years, which do you think is more li... | 0.0207 | 0.8165 |
| By the year 2050, do you think the overall condition of the ... | 0.0256 | 0.9129 |
| Please indicate whether or not each has happened to you beca... | 0.0309 | 0.3333 |
| Overall, has the automation of jobs through new technology i... | 0.0337 | 0.5477 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please indicate how much of a problem, if at all, the follow... | 0.7632 | -0.8944 |
| Overall, do you think science has made life easier or more d... | 0.7844 | -0.3333 |
| How satisfied are you with the way democracy is working in t... | 0.8655 | -0.8367 |
| Would you favor or oppose the following? If robots and compu... | 0.8857 | -0.5976 |
| Do you think the following will or will not happen in the ne... | 0.9426 | -0.8367 |
