# SynthBench Score Card

**Provider:** synthpanel/openrouter/openai/gpt-4o-mini
**Dataset:** opinionsqa (175 questions)
**Samples per question:** 50
**Elapsed:** 164.5s

## SynthBench Parity Score (SPS)

**SPS: 0.8139 [0.7152, 0.7558]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6991 [0.6745, 0.7209] | ███████░░░ |
| P_rank  Rank-Order | 0.7746 [0.7524, 0.7944] | ████████░░ |
| P_refuse Refusal Cal. | 0.9679 [0.9603, 0.9732] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3009 |
| Median JSD | 0.3033 |
| Mean Kendall's tau | 0.5491 |
| Composite Parity (legacy) | 0.7368 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1748 | +31% |
| random-baseline | 0.6495 | +0.0873 | +13% |

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
| 2017 | 0.7043 | 0.7738 | 0.2957 | 37 |
| 2018 | 0.7166 | 0.7852 | 0.2834 | 39 |
| 2019 | 0.7364 | 0.7839 | 0.2636 | 50 |
| 2020 | 0.6590 | 0.7716 | 0.3410 | 31 |
| 2022 | 0.6160 | 0.7321 | 0.3840 | 18 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think genetic engineering of aquarium fish to change ... | 0.0137 | 1.0000 |
| If driverless vehicles become widespread, which of the follo... | 0.0167 | 1.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.0220 | 0.7071 |
| Do you think changing a baby's genetic characteristics to re... | 0.0289 | 0.3333 |
| In the last 12 months, have you had someone attempt to open ... | 0.0320 | 0.8165 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you use a password manager, such as LastPass or iCloud Ke... | 0.6109 | 0.0000 |
| Do you personally know anyone who has lost a job, or had the... | 0.6144 | 0.0000 |
| Overall, how much has your family's financial situation when... | 0.6696 | -0.3464 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
| Would you say the European Union is doing a good or bad job ... | 0.8189 | -0.3162 |
