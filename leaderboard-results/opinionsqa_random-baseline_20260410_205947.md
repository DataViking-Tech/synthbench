# SynthBench Score Card

**Provider:** random-baseline
**Dataset:** opinionsqa (429 questions)
**Samples per question:** 5
**Elapsed:** 0.2s

## SynthBench Parity Score (SPS)

**SPS: 0.7215 [0.5659, 0.6074]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6823 [0.6643, 0.7011] | ███████░░░ |
| P_rank  Rank-Order | 0.4922 [0.4678, 0.5177] | █████░░░░░ |
| P_refuse Refusal Cal. | 0.9899 [0.9890, 0.9907] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3177 |
| Median JSD | 0.2892 |
| Mean Kendall's tau | -0.0156 |
| Composite Parity (legacy) | 0.5872 |

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
| Which of the following, if any, do you restrict or limit eat... | 0.0005 | 1.0000 |
| Which of the following, if any, do you restrict or limit eat... | 0.0008 | 1.0000 |
| Which of the following, if any, do you restrict or limit eat... | 0.0040 | 1.0000 |
| Which of these statements best describes your opinion about ... | 0.0071 | 0.9129 |
| Please choose the statement that comes closer to your own vi... | 0.0071 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How much do you think the following type of news and informa... | 0.8105 | -0.6708 |
| How likely is the following if gene editing to change a baby... | 0.8214 | -0.5976 |
| Not including in military combat or as part of your job, hav... | 0.8241 | -0.3333 |
| In the US, how strong, if at all, are conflicts between peop... | 0.9381 | -0.5976 |
| Which of the following best describes what you think about t... | 0.9484 | -0.8165 |
