# SynthBench Score Card

**Provider:** synthpanel/gemini-2.5-flash-lite
**Dataset:** globalopinionqa (100 questions)
**Samples per question:** 30
**Elapsed:** 71.1s

## SynthBench Parity Score (SPS)

**SPS: 0.7616 [0.6050, 0.7012]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6870 [0.6374, 0.7260] | ███████░░░ |
| P_rank  Rank-Order | 0.6241 [0.5606, 0.6864] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.9737 [0.9560, 0.9829] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3130 |
| Median JSD | 0.2777 |
| Mean Kendall's tau | 0.2481 |
| Composite Parity (legacy) | 0.6555 |

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
| As I read some specific policies of [American] President Geo... | 0.0003 | 1.0000 |
| Which of these characteristics do you associate with people ... | 0.0020 | 1.0000 |
| Do you think that the rise of nontraditional political parti... | 0.0038 | 1.0000 |
| In general, when European companies build factories in our c... | 0.0080 | 1.0000 |
| On another topic, had you heard that President Barack Obama'... | 0.0203 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| (Now I'd like to ask you about some political parties.) Plea... | 0.7583 | -0.3162 |
| Now I am going to read you a list of things that may be prob... | 0.7741 | -0.5477 |
| Now I am going to read you a list of things that may be prob... | 0.7828 | -0.7071 |
| Please tell me if you have a very favorable, somewhat favora... | 0.9022 | -0.6325 |
| Please tell me if you have a very favorable, somewhat favora... | 0.9022 | -0.3162 |
