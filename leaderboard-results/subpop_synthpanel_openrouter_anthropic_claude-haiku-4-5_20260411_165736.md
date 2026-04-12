# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** subpop (200 questions)
**Samples per question:** 30
**Elapsed:** 156.2s

## SynthBench Parity Score (SPS)

**SPS: 0.8043 [0.7068, 0.7493]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7024 [0.6770, 0.7263] | ███████░░░ |
| P_rank  Rank-Order | 0.7552 [0.7305, 0.7781] | ████████░░ |
| P_refuse Refusal Cal. | 0.9554 [0.9281, 0.9713] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2976 |
| Median JSD | 0.2701 |
| Mean Kendall's tau | 0.5104 |
| Composite Parity (legacy) | 0.7288 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1668 | +30% |
| random-baseline | 0.6495 | +0.0793 | +12% |

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
| Have you heard of the social media site or app BitChute?... | 0.0038 | 1.0000 |
| Please indicate if you have attended a concert over the past... | 0.0067 | 1.0000 |
| In the last month, did you attend religious services in pers... | 0.0124 | 1.0000 |
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| In recent years, several social media sites have emerged as ... | 0.0177 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Would you say that the news coverage you have seen of the Bi... | 0.6350 | 0.0000 |
| How much have you heard about the boycott, divestment, and s... | 0.6460 | -0.1195 |
| Thinking now about what you see and hear in the news about t... | 0.7315 | -0.2357 |
| Have you heard of the social media site or app Gab?... | 0.7439 | 0.0000 |
| In the news you are receiving about the Biden administration... | 1.0000 | 0.0000 |
