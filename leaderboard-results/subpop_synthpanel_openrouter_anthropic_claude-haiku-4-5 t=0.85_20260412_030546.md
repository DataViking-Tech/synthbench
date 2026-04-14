# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85
**Dataset:** subpop (100 questions)
**Samples per question:** 15
**Elapsed:** 681.4s

## SynthBench Parity Score (SPS)

**SPS: 0.6502 [0.6651, 0.6762]** (from 5 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.8421 [0.8298, 0.8535] | ████████░░ |
| P_rank  Rank-Order | 0.5000 [0.5000, 0.5000] | █████░░░░░ |
| P_cond  Conditioning | 0.0000 | ░░░░░░░░░░ |
| P_sub   Subgroup | 0.9291 | █████████░ |
| P_refuse Refusal Cal. | 0.9799 [0.9394, 0.9903] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.1579 |
| Median JSD | 0.1494 |
| Mean Kendall's tau | 0.0000 |
| Composite Parity (legacy) | 0.6711 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1091 | +19% |
| random-baseline | 0.6495 | +0.0216 | +3% |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Demographic Breakdown

### CREGION

Best: Northeast (P_dist=0.8393) / Worst: South (P_dist=0.7281)

| Group | P_dist | P_cond | Questions |
|-------|--------|--------|-----------|
| Northeast | 0.8393 | 0.0000 | 100 |
| South | 0.7281 | 0.0065 | 100 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Regardless of whether you think abortion should be legal or ... | 0.0549 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 0.0584 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 0.0649 | 0.0000 |
| How important is your religion in shaping your views about a... | 0.0671 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 0.0702 | 0.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think abortion should be legal or illegal in the situ... | 0.2705 | 0.0000 |
| Do you think gender should be a major factor, minor factor, ... | 0.2776 | 0.0000 |
| Thinking about health products, which of the following uses ... | 0.2786 | 0.0000 |
| Have there been times in the past 12 months when you did not... | 0.2811 | 0.0000 |
| Did you refuse to answer the previous question?... | 0.3915 | 0.0000 |
