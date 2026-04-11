# SynthBench Score Card

**Provider:** random-baseline
**Dataset:** opinionsqa (429 questions)
**Samples per question:** 30
**Elapsed:** 0.1s

## SynthBench Parity Score (SPS)

**SPS: 0.7568 [0.6259, 0.6542]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.8040 [0.7958, 0.8117] | ████████░░ |
| P_rank  Rank-Order | 0.4764 [0.4534, 0.5017] | █████░░░░░ |
| P_refuse Refusal Cal. | 0.9899 [0.9890, 0.9907] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.1960 |
| Median JSD | 0.1826 |
| Mean Kendall's tau | -0.0471 |
| Composite Parity (legacy) | 0.6402 |

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
| Which of the following, if any, do you restrict or limit eat... | 0.0005 | 0.0000 |
| Which of the following, if any, do you restrict or limit eat... | 0.0012 | 1.0000 |
| Which of the following, if any, do you restrict or limit eat... | 0.0289 | -1.0000 |
| Overall, would you say people who are convicted of crimes in... | 0.0343 | 1.0000 |
| How much, if at all, do you think the legacy of slavery affe... | 0.0415 | 0.5270 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| What do you think is the ideal situation for men with young ... | 0.4346 | -0.5477 |
| Do you think it's good or bad for US colleges and universiti... | 0.4584 | -0.3333 |
| In general, would you say scientific experts are... | 0.4682 | -0.1054 |
| How much do you think the following type of news and informa... | 0.4803 | -0.4000 |
| Do you think of yourself as... | 0.5523 | -0.2965 |
