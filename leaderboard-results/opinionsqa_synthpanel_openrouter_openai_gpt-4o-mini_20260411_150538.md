# SynthBench Score Card

**Provider:** synthpanel/openrouter/openai/gpt-4o-mini
**Dataset:** opinionsqa (684 questions)
**Samples per question:** 50
**Elapsed:** 339.5s

## SynthBench Parity Score (SPS)

**SPS: 0.8230 [0.7326, 0.7541]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7085 [0.6974, 0.7201] | ███████░░░ |
| P_rank  Rank-Order | 0.7788 [0.7657, 0.7901] | ████████░░ |
| P_refuse Refusal Cal. | 0.9816 [0.9744, 0.9857] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2915 |
| Median JSD | 0.2854 |
| Mean Kendall's tau | 0.5577 |
| Composite Parity (legacy) | 0.7437 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1817 | +32% |
| random-baseline | 0.6495 | +0.0941 | +14% |

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
| 2017 | 0.7249 | 0.7697 | 0.2751 | 99 |
| 2018 | 0.7047 | 0.7477 | 0.2953 | 124 |
| 2019 | 0.7119 | 0.7880 | 0.2881 | 218 |
| 2020 | 0.7361 | 0.8135 | 0.2639 | 101 |
| 2022 | 0.6754 | 0.7736 | 0.3246 | 142 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you have a voice-controlled smart speaker in your home, s... | 0.0014 | 1.0000 |
| Do you think bringing back an animal that is currently extin... | 0.0054 | 1.0000 |
| Do you think changing a baby's genetic characteristics to re... | 0.0067 | 1.0000 |
| Now thinking again about the community where you live do you... | 0.0073 | 1.0000 |
| Have you ever personally experienced discrimination or been ... | 0.0077 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How much, if at all, is racism a problem in your local commu... | 0.6872 | -0.2357 |
| How often, if ever, do you participate in online discussion ... | 0.6884 | 0.3586 |
| How much of a problem was gun violence in the community wher... | 0.7400 | 0.1195 |
| Please choose the statement that comes closer to your own vi... | 1.0000 | 0.0000 |
| Would you prefer to live in a community where the houses are... | 1.0000 | 0.0000 |
