# SynthBench Score Card

**Provider:** random-baseline
**Dataset:** globalopinionqa (10 questions)
**Samples per question:** 5
**Elapsed:** 0.1s

## SynthBench Parity Score (SPS)

**SPS: 0.7097 [0.4807, 0.6798]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7468 [0.6426, 0.8225] | ███████░░░ |
| P_rank  Rank-Order | 0.3991 [0.2403, 0.5407] | ████░░░░░░ |
| P_refuse Refusal Cal. | 0.9832 [0.9639, 0.9948] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2532 |
| Median JSD | 0.1760 |
| Mean Kendall's tau | -0.2019 |
| Composite Parity (legacy) | 0.5729 |

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
| Please tell me how worried you are about each of the followi... | 0.1177 | 0.5477 |
| Please tell me if you approve or disapprove of the way Prime... | 0.1277 | 0.3333 |
| Please tell me which of the following is closest to your own... | 0.1297 | -1.0000 |
| When it comes to Germany’s decision-making in the European U... | 0.1462 | 0.1826 |
| In your opinion, how strong a sense of Islamic identity do M... | 0.1593 | -0.7071 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think China will replace the U.S. as the world's lead... | 0.1926 | 0.1826 |
| And thinking about some political leaders and organizations ... | 0.3202 | -0.5477 |
| Which statement comes closer to your own views, even if neit... | 0.3759 | 0.0348 |
| Now I am going to read you a list of things that may be prob... | 0.4450 | -0.5976 |
| Please tell me if you have a very favorable, somewhat favora... | 0.5175 | -0.4472 |
