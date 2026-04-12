# SynthBench Score Card

**Provider:** synthpanel/openrouter/openai/gpt-4o-mini
**Dataset:** globalopinionqa (100 questions)
**Samples per question:** 30
**Elapsed:** 142.9s

## SynthBench Parity Score (SPS)

**SPS: 0.7846 [0.6483, 0.7313]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6950 [0.6615, 0.7283] | ███████░░░ |
| P_rank  Rank-Order | 0.6911 [0.6269, 0.7455] | ███████░░░ |
| P_refuse Refusal Cal. | 0.9678 [0.9524, 0.9781] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3050 |
| Median JSD | 0.2781 |
| Mean Kendall's tau | 0.3822 |
| Composite Parity (legacy) | 0.6931 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1311 | +23% |
| random-baseline | 0.6495 | +0.0435 | +7% |

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
| Do you think the U.S. should keep military troops in Iraq un... | 0.0002 | 1.0000 |
| Do you think the government of Ukraine respects the personal... | 0.0005 | 1.0000 |
| On another topic, had you heard that President Barack Obama'... | 0.0203 | 1.0000 |
| As I read some specific policies of [American] President Geo... | 0.0479 | 1.0000 |
| (Now/And thinking about the American people...) Which of the... | 0.0524 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| After the dissolution of the Soviet Union, we changed from a... | 0.6261 | 0.0000 |
| Here is the 'ladder of life.'  Let's suppose the top of the ... | 0.6604 | -0.1547 |
| Which of these characteristics do you associate with (the Ch... | 0.6684 | -1.0000 |
| Do you approve or disapprove of the U.S. military operation ... | 0.6983 | -1.0000 |
| Please tell me if you have a very favorable, somewhat favora... | 0.8135 | 0.0000 |
