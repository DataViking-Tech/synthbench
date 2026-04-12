# SynthBench Score Card

**Provider:** openrouter/google/gemini-2.5-flash
**Dataset:** globalopinionqa (100 questions)
**Samples per question:** 15
**Elapsed:** 150.8s

## SynthBench Parity Score (SPS)

**SPS: 0.7704 [0.6141, 0.7077]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6870 [0.6415, 0.7244] | ███████░░░ |
| P_rank  Rank-Order | 0.6445 [0.5746, 0.7015] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.9797 [0.9684, 0.9862] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3130 |
| Median JSD | 0.2583 |
| Mean Kendall's tau | 0.2890 |
| Composite Parity (legacy) | 0.6658 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1038 | +18% |
| random-baseline | 0.6495 | +0.0163 | +3% |

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
| Thinking about possible war with Iraq, would you favor or op... | 0.0012 | 1.0000 |
| In general, do you think our country is covered fairly or un... | 0.0014 | -1.0000 |
| On the subject of Iraq, did your country make the right deci... | 0.0045 | -1.0000 |
| Do you think this change in the working conditions for ordin... | 0.0083 | 1.0000 |
| Which of these characteristics do you associate with (the Ch... | 0.0131 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please tell me if you have a very favorable, somewhat favora... | 0.7481 | 0.1195 |
| Which statement comes closer to your own views, even if neit... | 0.7544 | -0.1179 |
| Do you personally believe that getting a divorce is morally ... | 0.7605 | -0.7071 |
| Please tell me if you have a very favorable, somewhat favora... | 0.9235 | -0.6325 |
| Please tell me if you have a very favorable, somewhat favora... | 0.9290 | -0.6325 |
