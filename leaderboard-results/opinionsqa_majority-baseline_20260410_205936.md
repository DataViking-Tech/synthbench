# SynthBench Score Card

**Provider:** majority-baseline
**Dataset:** opinionsqa (175 questions)
**Samples per question:** 30
**Elapsed:** 0.1s

## SynthBench Parity Score (SPS)

**SPS: 0.6872 [0.5076, 0.5669]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.4863 [0.4542, 0.5196] | █████░░░░░ |
| P_rank  Rank-Order | 0.5873 [0.5595, 0.6156] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.9880 [0.9850, 0.9903] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.5137 |
| Median JSD | 0.5261 |
| Mean Kendall's tau | 0.1747 |
| Composite Parity (legacy) | 0.5368 |

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
| How important, if at all, do you think a good work ethic is ... | 0.0388 | 0.7071 |
| Do you think science has had a mostly positive or mostly neg... | 0.0423 | 0.8165 |
| Overall, do you think science has made life easier or more d... | 0.0452 | 0.8165 |
| Do you have a smartphone?... | 0.0664 | 0.8165 |
| How much power and influence do you think politicians have o... | 0.0863 | 0.7071 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think foods with genetically modified ingredients are... | 0.8904 | -0.3162 |
| How much do you trust the accuracy of the news and informati... | 0.8946 | -0.3162 |
| Do you think it is very likely, somewhat likely, not very li... | 0.9135 | -0.3162 |
| Have you yourself ever lost a job because your employer repl... | 0.9288 | -0.2357 |
| Would you say China is doing a good or bad job dealing with ... | 0.9422 | -0.6325 |
