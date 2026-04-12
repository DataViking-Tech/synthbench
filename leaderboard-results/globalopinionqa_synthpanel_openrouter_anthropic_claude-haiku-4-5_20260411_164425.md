# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** globalopinionqa (100 questions)
**Samples per question:** 30
**Elapsed:** 69.4s

## SynthBench Parity Score (SPS)

**SPS: 0.7249 [0.5937, 0.6918]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6655 [0.6147, 0.7071] | ███████░░░ |
| P_rank  Rank-Order | 0.6282 [0.5593, 0.6893] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.8808 [0.8219, 0.9192] | █████████░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3345 |
| Median JSD | 0.2725 |
| Mean Kendall's tau | 0.2564 |
| Composite Parity (legacy) | 0.6469 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.0849 | +15% |
| random-baseline | 0.6495 | -0.0026 | -0% |

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
| Please tell me if you approve or disapprove of the way Presi... | 0.0115 | 1.0000 |
| Thinking about possible war with Iraq, would you favor or op... | 0.0170 | 1.0000 |
| On another topic, had you heard that President Barack Obama'... | 0.0203 | 1.0000 |
| Which of these characteristics do you associate with (the Ch... | 0.0346 | 1.0000 |
| Now I am going to read you a list of things that may be prob... | 0.0449 | 0.9129 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please tell me if you have a very favorable, somewhat favora... | 0.9022 | -0.6325 |
| Please tell me if you have a very favorable, somewhat favora... | 0.9022 | -0.3162 |
| Please tell me if you have a very favorable, somewhat favora... | 0.9290 | -0.6325 |
| And thinking about some political leaders and organizations ... | 1.0000 | 0.0000 |
| And thinking about some political leaders and organizations ... | 1.0000 | 0.0000 |
