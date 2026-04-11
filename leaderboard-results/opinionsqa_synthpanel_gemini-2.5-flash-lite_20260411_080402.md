# SynthBench Score Card

**Provider:** synthpanel/gemini-2.5-flash-lite
**Dataset:** opinionsqa (200 questions)
**Samples per question:** 50
**Elapsed:** 185.5s

## SynthBench Parity Score (SPS)

**SPS: 0.7940 [0.7405, 0.7852]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7448 [0.7139, 0.7670] | ███████░░░ |
| P_rank  Rank-Order | 0.7831 [0.7564, 0.8049] | ████████░░ |
| P_refuse Refusal Cal. | 0.8540 [0.8099, 0.8911] | █████████░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2552 |
| Median JSD | 0.2252 |
| Mean Kendall's tau | 0.5663 |
| Composite Parity (legacy) | 0.7640 |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Temporal Breakdown (by Survey Year)

Scores stratified by Pew ATP survey wave year. Rising P_dist in recent years may indicate training-data contamination.

| Year | P_dist | P_rank | Mean JSD | Questions |
|------|--------|--------|----------|-----------|
| 2017 | 0.7335 | 0.7878 | 0.2665 | 99 |
| 2018 | 0.7559 | 0.7786 | 0.2441 | 101 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Has anyone ever used a gun to threaten or intimidate you or ... | 0.0023 | 1.0000 |
| If driverless vehicles become widespread, which of the follo... | 0.0030 | 1.0000 |
| Do you think men and women are basically similar or basicall... | 0.0042 | 1.0000 |
| Which statement comes closer to your own views?... | 0.0112 | 1.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.0220 | 0.7071 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Have you participated in any of these groups during the last... | 1.0000 | 0.0000 |
| Have you participated in any of these groups during the last... | 1.0000 | 0.0000 |
| How important is it to you, personally, to live in a communi... | 1.0000 | 0.0000 |
| Genetically modified foods come from a technique that adds g... | 1.0000 | 0.0000 |
| Do you think foods with genetically modified ingredients are... | 1.0000 | 0.0000 |
