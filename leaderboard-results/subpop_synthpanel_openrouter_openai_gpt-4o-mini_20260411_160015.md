# SynthBench Score Card

**Provider:** synthpanel/openrouter/openai/gpt-4o-mini
**Dataset:** subpop (200 questions)
**Samples per question:** 30
**Elapsed:** 139.6s

## SynthBench Parity Score (SPS)

**SPS: 0.7910 [0.6777, 0.7193]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6557 [0.6325, 0.6782] | ███████░░░ |
| P_rank  Rank-Order | 0.7419 [0.7188, 0.7634] | ███████░░░ |
| P_refuse Refusal Cal. | 0.9755 [0.9539, 0.9862] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3443 |
| Median JSD | 0.3506 |
| Mean Kendall's tau | 0.4837 |
| Composite Parity (legacy) | 0.6988 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1368 | +24% |
| random-baseline | 0.6495 | +0.0493 | +8% |

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
| In the last month, did you attend religious services in pers... | 0.0110 | 1.0000 |
| In the last month, did you attend religious services in pers... | 0.0153 | 1.0000 |
| In the last month, did you attend religious services in pers... | 0.0225 | 1.0000 |
| Do you think it is possible to go about daily life today wit... | 0.0239 | 1.0000 |
| Do you believe that some things happen in life that can’t re... | 0.0281 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think that you have ever been at an advantage in your... | 0.7174 | -0.2357 |
| Have you heard of the social media site or app Gab?... | 0.7439 | 0.0000 |
| In recent years, several social media sites have emerged as ... | 0.7570 | 0.0000 |
| Thinking about another way employers may use artificial inte... | 0.7967 | -0.2357 |
| Have you heard of the social media site or app BitChute?... | 0.8196 | 0.0000 |
