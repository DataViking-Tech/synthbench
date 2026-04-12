# SynthBench Score Card

**Provider:** synthpanel/openrouter/google/gemini-2.5-flash-lite
**Dataset:** globalopinionqa (100 questions)
**Samples per question:** 15
**Elapsed:** 16.2s

## SynthBench Parity Score (SPS)

**SPS: 0.7646 [0.6089, 0.7061]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6948 [0.6520, 0.7337] | ███████░░░ |
| P_rank  Rank-Order | 0.6253 [0.5588, 0.6865] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.9737 [0.9590, 0.9817] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3052 |
| Median JSD | 0.2649 |
| Mean Kendall's tau | 0.2507 |
| Composite Parity (legacy) | 0.6601 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.0981 | +17% |
| random-baseline | 0.6495 | +0.0105 | +2% |

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
| Which of these characteristics do you associate with people ... | 0.0047 | -1.0000 |
| Do you think this change in the availability of modern medic... | 0.0099 | 0.0000 |
| Do you approve or disapprove of the way President Nicolas Ma... | 0.0102 | 1.0000 |
| Which of these characteristics do you associate with (the Ch... | 0.0152 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Thinking about our relations with China, in your view, which... | 0.7398 | -0.3586 |
| How serious of a threat is the Taliban to our country? Is it... | 0.7417 | -0.5976 |
| Which statement comes closer to your own views, even if neit... | 0.7544 | -0.1179 |
| (Now I'd like to ask you about some political parties.) Plea... | 0.7583 | -0.3162 |
| Please tell me if you have a very favorable, somewhat favora... | 0.9022 | -0.6325 |
