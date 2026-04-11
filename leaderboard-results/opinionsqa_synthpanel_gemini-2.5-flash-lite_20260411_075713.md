# SynthBench Score Card

**Provider:** synthpanel/gemini-2.5-flash-lite
**Dataset:** opinionsqa (429 questions)
**Samples per question:** 50
**Elapsed:** 332.2s

## SynthBench Parity Score (SPS)

**SPS: 0.8148 [0.7439, 0.7704]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7419 [0.7254, 0.7558] | ███████░░░ |
| P_rank  Rank-Order | 0.7725 [0.7569, 0.7879] | ████████░░ |
| P_refuse Refusal Cal. | 0.9300 [0.9098, 0.9451] | █████████░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2581 |
| Median JSD | 0.2328 |
| Mean Kendall's tau | 0.5449 |
| Composite Parity (legacy) | 0.7572 |

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
| 2017 | 0.7392 | 0.7685 | 0.2608 | 44 |
| 2018 | 0.7768 | 0.7691 | 0.2232 | 78 |
| 2019 | 0.7116 | 0.7533 | 0.2884 | 153 |
| 2020 | 0.7603 | 0.8018 | 0.2397 | 56 |
| 2022 | 0.7519 | 0.7901 | 0.2481 | 98 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Are colleges and universities having a positive or negative ... | 0.0105 | 1.0000 |
| Do you think bringing back an animal that is currently extin... | 0.0235 | 1.0000 |
| On a different topic, compared with five years ago, do you f... | 0.0254 | 0.9129 |
| Would you prefer to live in a community where the houses are... | 0.0271 | 0.3333 |
| Different organizations and news outlets have taken on fact-... | 0.0284 | 0.3333 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| In 2050, do you think population growth in the U.S. will be ... | 1.0000 | 0.0000 |
| How comfortable are you, if at all, with companies using you... | 1.0000 | 0.0000 |
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
| How much, if at all, do you think the legacy of slavery affe... | 1.0000 | 0.0000 |
| Thinking about your own experience, have you ever personally... | 1.0000 | 0.0000 |
