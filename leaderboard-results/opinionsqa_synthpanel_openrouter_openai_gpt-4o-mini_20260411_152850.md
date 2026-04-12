# SynthBench Score Card

**Provider:** synthpanel/openrouter/openai/gpt-4o-mini
**Dataset:** opinionsqa (175 questions)
**Samples per question:** 50
**Elapsed:** 179.7s

## SynthBench Parity Score (SPS)

**SPS: 0.8200 [0.7149, 0.7558]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6965 [0.6730, 0.7192] | ███████░░░ |
| P_rank  Rank-Order | 0.7759 [0.7528, 0.7957] | ████████░░ |
| P_refuse Refusal Cal. | 0.9876 [0.9848, 0.9899] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3035 |
| Median JSD | 0.3193 |
| Mean Kendall's tau | 0.5517 |
| Composite Parity (legacy) | 0.7362 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1742 | +31% |
| random-baseline | 0.6495 | +0.0867 | +13% |

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
| 2017 | 0.6974 | 0.7745 | 0.3026 | 37 |
| 2018 | 0.7208 | 0.7905 | 0.2792 | 39 |
| 2019 | 0.7262 | 0.7875 | 0.2738 | 50 |
| 2020 | 0.6600 | 0.7749 | 0.3400 | 31 |
| 2022 | 0.6224 | 0.7162 | 0.3776 | 18 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please indicate whether or not each has happened to you beca... | 0.0149 | 1.0000 |
| If driverless vehicles become widespread, which of the follo... | 0.0167 | 1.0000 |
| Do you think changing a baby's genetic characteristics to re... | 0.0199 | 0.3333 |
| Have you yourself ever lost a job because your employer repl... | 0.0220 | 0.7071 |
| In the last 12 months, have you had someone attempt to open ... | 0.0320 | 0.8165 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you use a password manager, such as LastPass or iCloud Ke... | 0.6109 | 0.0000 |
| Do you personally know anyone who has lost a job, or had the... | 0.6144 | 0.0000 |
| Overall, how much has your family's financial situation when... | 0.6696 | -0.3464 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
| Would you say the European Union is doing a good or bad job ... | 0.8189 | -0.3162 |
