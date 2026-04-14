# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85
**Dataset:** subpop (20 questions)
**Samples per question:** 15
**Elapsed:** 117.2s

## SynthBench Parity Score (SPS)

**SPS: 0.6968 [0.6845, 0.8080]** (from 5 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7244 [0.6525, 0.7862] | ███████░░░ |
| P_rank  Rank-Order | 0.7849 [0.6878, 0.8325] | ████████░░ |
| P_cond  Conditioning | 0.0822 | █░░░░░░░░░ |
| P_sub   Subgroup | 0.9555 | ██████████ |
| P_refuse Refusal Cal. | 0.9368 [0.7363, 0.9874] | █████████░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2756 |
| Median JSD | 0.2315 |
| Mean Kendall's tau | 0.5698 |
| Composite Parity (legacy) | 0.7546 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1927 | +34% |
| random-baseline | 0.6495 | +0.1051 | +16% |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Demographic Breakdown

### RELIG

Best: Protestant (P_dist=0.8380) / Worst: Atheist (P_dist=0.7384)

| Group | P_dist | P_cond | Questions |
|-------|--------|--------|-----------|
| Protestant | 0.8380 | 0.1781 | 20 |
| Muslim | 0.8198 | 0.1612 | 20 |
| Hindu | 0.8063 | 0.1292 | 20 |
| Jewish | 0.7737 | 0.1270 | 20 |
| Atheist | 0.7384 | 0.0953 | 20 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| Do you think people have ever assumed that you benefited unf... | 0.1206 | 0.9129 |
| Have your personal views about abortion changed in any way o... | 0.1270 | 0.7071 |
| Do you think abortion should be legal or illegal in the situ... | 0.1278 | 0.7071 |
| Do you think there are situations when abortion should be le... | 0.1442 | 0.8165 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think abortion should be…... | 0.4337 | 0.6325 |
| Do you think abortion should be...... | 0.4462 | 0.6325 |
| Do you think abortion should be...... | 0.4544 | 0.6325 |
| Just to confirm, do you think there are any exceptions when ... | 0.5494 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 0.5539 | 0.3464 |
