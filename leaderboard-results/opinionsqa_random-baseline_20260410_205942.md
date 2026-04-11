# SynthBench Score Card

**Provider:** random-baseline
**Dataset:** opinionsqa (80 questions)
**Samples per question:** 30
**Elapsed:** 0.0s

## SynthBench Parity Score (SPS)

**SPS: 0.7554 [0.6045, 0.6701]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7906 [0.7684, 0.8118] | ████████░░ |
| P_rank  Rank-Order | 0.4846 [0.4346, 0.5374] | █████░░░░░ |
| P_refuse Refusal Cal. | 0.9909 [0.9889, 0.9922] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2094 |
| Median JSD | 0.1916 |
| Mean Kendall's tau | -0.0308 |
| Composite Parity (legacy) | 0.6376 |

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
| Thinking about how the federal government spends money, do y... | 0.0320 | 0.6667 |
| Now that Joe Biden is president, do you think other countrie... | 0.0361 | 0.7379 |
| Still thinking about elections in the country, how confident... | 0.0623 | 0.2236 |
| How much confidence do you have in us President Joe Biden to... | 0.0762 | 0.3162 |
| Thinking about how the federal government spends money, do y... | 0.0839 | 0.5477 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Still thinking about the future of our country, how worried ... | 0.3839 | -0.8944 |
| How much of a priority should the following be for the feder... | 0.3879 | -0.6000 |
| In the US, how strong, if at all, are conflicts between peop... | 0.3925 | -0.4000 |
| How much of a priority should the following be for the feder... | 0.4122 | -0.6000 |
| Thinking about elections in the country, how important, if a... | 0.4276 | 0.0000 |
