# SynthBench Score Card

**Provider:** random-baseline
**Dataset:** opinionsqa (175 questions)
**Samples per question:** 30
**Elapsed:** 0.1s

## SynthBench Parity Score (SPS)

**SPS: 0.7441 [0.5974, 0.6486]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.8005 [0.7870, 0.8129] | ████████░░ |
| P_rank  Rank-Order | 0.4439 [0.4050, 0.4866] | ████░░░░░░ |
| P_refuse Refusal Cal. | 0.9880 [0.9850, 0.9903] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.1995 |
| Median JSD | 0.1965 |
| Mean Kendall's tau | -0.1123 |
| Composite Parity (legacy) | 0.6222 |

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
| Thinking about news (by news we mean information about event... | 0.0171 | 0.7379 |
| How much, if at all, do you think what happens to white peop... | 0.0336 | 0.5270 |
| Overall, how much has your family's financial situation when... | 0.0428 | 0.3333 |
| Would you say the US is doing a good or bad job dealing with... | 0.0446 | 0.7746 |
| How much, if at all, do you think what happens to black peop... | 0.0483 | 0.3162 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How much power and influence do you think politicians have o... | 0.4070 | -0.6667 |
| In the last 12 months, have you had someone attempt to open ... | 0.4088 | -1.0000 |
| Have you ever had your pay or hours reduced because your emp... | 0.4228 | 0.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.4313 | 0.0000 |
| How important, if at all, do you think a good work ethic is ... | 0.4464 | 0.1826 |
