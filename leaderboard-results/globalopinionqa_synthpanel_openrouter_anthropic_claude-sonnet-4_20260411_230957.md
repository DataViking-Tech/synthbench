# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-sonnet-4
**Dataset:** globalopinionqa (100 questions)
**Samples per question:** 30
**Elapsed:** 124.0s

## SynthBench Parity Score (SPS)

**SPS: 0.7966 [0.6971, 0.7122]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.9101 [0.8944, 0.9243] | █████████░ |
| P_rank  Rank-Order | 0.5000 [0.5000, 0.5000] | █████░░░░░ |
| P_refuse Refusal Cal. | 0.9797 [0.9684, 0.9862] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.0899 |
| Median JSD | 0.0729 |
| Mean Kendall's tau | 0.0000 |
| Composite Parity (legacy) | 0.7051 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1431 | +25% |
| random-baseline | 0.6495 | +0.0556 | +9% |

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
| Overall, was the break-up of Czechoslovakia into two indepen... | 0.0000 | 0.0000 |
| In general, do you think our country is covered fairly or un... | 0.0001 | 0.0000 |
| Do you know someone who went to the U.S., but returned to yo... | 0.0003 | 0.0000 |
| On the subject of Iraq, did your country make the right deci... | 0.0015 | 0.0000 |
| How much of a threat, if any, does Islamic extremism pose to... | 0.0015 | 0.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| I am going to read you a list of things that the government ... | 0.2274 | 0.0000 |
| Please tell me if you have a very favorable, somewhat favora... | 0.2301 | 0.0000 |
| I'm going to read you a list of issues that human rights org... | 0.2408 | 0.0000 |
| How important is it to have the following things in our coun... | 0.3187 | 0.0000 |
| (Now I am going to read you a list of things that may be pro... | 0.3432 | 0.0000 |
