# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** subpop (200 questions)
**Samples per question:** 30
**Elapsed:** 161.2s

## SynthBench Parity Score (SPS)

**SPS: 0.8091 [0.7149, 0.7548]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7121 [0.6886, 0.7341] | ███████░░░ |
| P_rank  Rank-Order | 0.7572 [0.7325, 0.7785] | ████████░░ |
| P_refuse Refusal Cal. | 0.9580 [0.9301, 0.9745] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2879 |
| Median JSD | 0.2725 |
| Mean Kendall's tau | 0.5145 |
| Composite Parity (legacy) | 0.7346 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1726 | +31% |
| random-baseline | 0.6495 | +0.0851 | +13% |

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
| In recent years, several social media sites have emerged as ... | 0.0067 | 1.0000 |
| Please indicate if you have attended a concert over the past... | 0.0067 | 1.0000 |
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| And would you say that the news coverage you have seen of th... | 0.0205 | 1.0000 |
| When you see or hear news about terrible things happening to... | 0.0326 | 0.8367 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Have you heard of the social media site or app Rumble?... | 0.6286 | 0.0000 |
| Would you say that the news coverage you have seen of the Bi... | 0.6350 | 0.0000 |
| How much have you heard about the boycott, divestment, and s... | 0.6460 | -0.1195 |
| Thinking now about what you see and hear in the news about t... | 0.7315 | -0.2357 |
| Have you heard of the social media site or app Gab?... | 0.7439 | 0.0000 |
