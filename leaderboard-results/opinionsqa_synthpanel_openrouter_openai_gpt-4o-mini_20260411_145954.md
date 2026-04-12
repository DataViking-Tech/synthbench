# SynthBench Score Card

**Provider:** synthpanel/openrouter/openai/gpt-4o-mini
**Dataset:** opinionsqa (684 questions)
**Samples per question:** 50
**Elapsed:** 353.3s

## SynthBench Parity Score (SPS)

**SPS: 0.8225 [0.7320, 0.7535]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7077 [0.6967, 0.7191] | ███████░░░ |
| P_rank  Rank-Order | 0.7780 [0.7644, 0.7894] | ████████░░ |
| P_refuse Refusal Cal. | 0.9818 [0.9747, 0.9860] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2923 |
| Median JSD | 0.2876 |
| Mean Kendall's tau | 0.5560 |
| Composite Parity (legacy) | 0.7429 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1809 | +32% |
| random-baseline | 0.6495 | +0.0934 | +14% |

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
| 2017 | 0.7226 | 0.7742 | 0.2774 | 99 |
| 2018 | 0.7025 | 0.7430 | 0.2975 | 124 |
| 2019 | 0.7118 | 0.7895 | 0.2882 | 218 |
| 2020 | 0.7345 | 0.8184 | 0.2655 | 101 |
| 2022 | 0.6767 | 0.7649 | 0.3233 | 142 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Have you ever personally experienced discrimination or been ... | 0.0017 | 1.0000 |
| How do you feel about your own ability to recognize the foll... | 0.0042 | 1.0000 |
| Do you have the following type of loans or debt: Student loa... | 0.0055 | 1.0000 |
| Do you think changing a baby's genetic characteristics to re... | 0.0066 | 1.0000 |
| Do you have a voice-controlled smart speaker in your home, s... | 0.0066 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| When it comes to people who have immigrated to the U.S illeg... | 0.6771 | 0.1195 |
| How much, if at all, is racism a problem in your local commu... | 0.6872 | -0.2357 |
| How often, if ever, do you participate in online discussion ... | 0.7219 | 0.3162 |
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
| Would you prefer to live in a community where the houses are... | 1.0000 | 0.0000 |
