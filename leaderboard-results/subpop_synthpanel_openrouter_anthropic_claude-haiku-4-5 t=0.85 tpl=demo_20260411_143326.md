# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85 tpl=demo
**Dataset:** subpop (100 questions)
**Samples per question:** 30
**Elapsed:** 186.9s

## SynthBench Parity Score (SPS)

**SPS: 0.5687 [0.5935, 0.6860]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6464 [0.5948, 0.6912] | ██████░░░░ |
| P_rank  Rank-Order | 0.6396 [0.5920, 0.6830] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.4202 [0.3651, 0.4740] | ████░░░░░░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3536 |
| Median JSD | 0.2926 |
| Mean Kendall's tau | 0.2791 |
| Composite Parity (legacy) | 0.6430 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.0810 | +14% |
| random-baseline | 0.6495 | -0.0065 | -1% |

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
| Did you refuse to answer the previous question?... | 0.0139 | 1.0000 |
| Do you think there are situations when abortion should be le... | 0.0166 | 1.0000 |
| Do you think whether a relative attended the school should b... | 0.0300 | 0.9129 |
| Have there been times in the past 12 months when you did not... | 0.0347 | 0.9129 |
| Do you think the United States’ decision to withdraw all tro... | 0.0459 | 0.3333 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Regardless of whether you think abortion should be legal or ... | 0.9490 | -0.5774 |
| Do you think abortion should be…... | 0.9526 | -0.6325 |
| Which statement comes closer to your view, even if neither i... | 0.9648 | -0.8165 |
| Please indicate if you have traveled more than 100 miles fro... | 0.9774 | -0.8165 |
| As you may know, the Supreme Court’s decision found that the... | 1.0000 | 0.0000 |
