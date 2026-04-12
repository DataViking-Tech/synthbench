# SynthBench Score Card

**Provider:** synthpanel/openrouter/openai/gpt-4o-mini
**Dataset:** globalopinionqa (100 questions)
**Samples per question:** 30
**Elapsed:** 153.4s

## SynthBench Parity Score (SPS)

**SPS: 0.7854 [0.6473, 0.7315]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6847 [0.6499, 0.7182] | ███████░░░ |
| P_rank  Rank-Order | 0.7002 [0.6365, 0.7541] | ███████░░░ |
| P_refuse Refusal Cal. | 0.9714 [0.9567, 0.9807] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3153 |
| Median JSD | 0.2919 |
| Mean Kendall's tau | 0.4004 |
| Composite Parity (legacy) | 0.6924 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1304 | +23% |
| random-baseline | 0.6495 | +0.0429 | +7% |

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
| Do you think the U.S. should keep military troops in Iraq un... | 0.0019 | 1.0000 |
| Do you think the government of Ukraine respects the personal... | 0.0032 | 1.0000 |
| On another topic, had you heard that President Barack Obama'... | 0.0203 | 1.0000 |
| (Now/And thinking about the American people...) Which of the... | 0.0524 | 1.0000 |
| Now I am going to read you a list of things that may be prob... | 0.0553 | 0.9129 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| After the dissolution of the Soviet Union, we changed from a... | 0.6261 | 0.0000 |
| Which of these characteristics do you associate with (the Ch... | 0.6684 | -1.0000 |
| Do you approve or disapprove of the U.S. military operation ... | 0.6983 | -1.0000 |
| Which statement comes closer to your own views, even if neit... | 0.7544 | -0.1179 |
| Please tell me if you have a very favorable, somewhat favora... | 0.8135 | 0.0000 |
