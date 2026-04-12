# SynthBench Score Card

**Provider:** synthpanel/openrouter/google/gemini-2.5-flash-lite
**Dataset:** subpop (100 questions)
**Samples per question:** 15
**Elapsed:** 54.8s

## SynthBench Parity Score (SPS)

**SPS: 0.8339 [0.7359, 0.7850]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7329 [0.7069, 0.7617] | ███████░░░ |
| P_rank  Rank-Order | 0.7889 [0.7591, 0.8144] | ████████░░ |
| P_refuse Refusal Cal. | 0.9799 [0.9394, 0.9903] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2671 |
| Median JSD | 0.2696 |
| Mean Kendall's tau | 0.5778 |
| Composite Parity (legacy) | 0.7609 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1989 | +35% |
| random-baseline | 0.6495 | +0.1114 | +17% |

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
| Please indicate if you have attended a sporting event over t... | 0.0026 | 1.0000 |
| Please indicate if you have attended a concert over the past... | 0.0051 | 1.0000 |
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| Would you favor or oppose employers’ use of artificial intel... | 0.0246 | 0.6667 |
| Do you think gender should be a major factor, minor factor, ... | 0.0278 | 0.9129 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Which country in Africa is known for having the largest popu... | 0.5123 | 0.3464 |
| How confident, if at all, are you that the government is con... | 0.5388 | 0.3162 |
| Just to confirm, do you think there are any exceptions when ... | 0.5494 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 0.5557 | 0.5774 |
| How important is your religion in shaping your views about a... | 0.6096 | -0.1974 |
