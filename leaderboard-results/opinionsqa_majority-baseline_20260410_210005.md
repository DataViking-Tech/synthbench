# SynthBench Score Card

**Provider:** majority-baseline
**Dataset:** opinionsqa (429 questions)
**Samples per question:** 30
**Elapsed:** 0.2s

## SynthBench Parity Score (SPS)

**SPS: 0.7097 [0.5513, 0.5904]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.5163 [0.4949, 0.5381] | █████░░░░░ |
| P_rank  Rank-Order | 0.6228 [0.6035, 0.6427] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.9899 [0.9890, 0.9907] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.4837 |
| Median JSD | 0.4749 |
| Mean Kendall's tau | 0.2457 |
| Composite Parity (legacy) | 0.5696 |

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
| Thinking again about colleges and universities which of the ... | 0.0444 | 0.8165 |
| In general, would you say the following statements describes... | 0.0498 | 0.8165 |
| How much do you think to push an agenda or viewpoint is a re... | 0.0534 | 0.7071 |
| How important, if at all, do you think knowing how to get al... | 0.0569 | 0.7071 |
| Overall, do you think having people of many different backgr... | 0.0608 | 0.8165 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| If you were asked to use one of these commonly used names fo... | 0.9406 | -0.3464 |
| How much confidence do you have in russian President Vladimi... | 0.9458 | -0.6325 |
| How much confidence do you have in chinese President Xi Jinp... | 0.9555 | -0.6325 |
| Overall, do you think current economic relations between the... | 0.9594 | -0.6325 |
| How often, if ever, do you participate in online discussion ... | 0.9718 | -0.3162 |
