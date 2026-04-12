# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** globalopinionqa (100 questions)
**Samples per question:** 30
**Elapsed:** 149.4s

## SynthBench Parity Score (SPS)

**SPS: 0.7207 [0.5902, 0.6887]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6589 [0.6106, 0.7022] | ███████░░░ |
| P_rank  Rank-Order | 0.6278 [0.5628, 0.6906] | ██████░░░░ |
| P_refuse Refusal Cal. | 0.8755 [0.8129, 0.9154] | █████████░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3411 |
| Median JSD | 0.2861 |
| Mean Kendall's tau | 0.2557 |
| Composite Parity (legacy) | 0.6434 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.0814 | +14% |
| random-baseline | 0.6495 | -0.0062 | -1% |

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
| Thinking about possible war with Iraq, would you favor or op... | 0.0036 | 1.0000 |
| Please tell me if you approve or disapprove of the way Presi... | 0.0097 | 0.0000 |
| On another topic, had you heard that President Barack Obama'... | 0.0203 | 1.0000 |
| (Now/And thinking about the American people...) Which of the... | 0.0524 | 1.0000 |
| Do you personally believe that drinking alcohol is morally a... | 0.0600 | 0.1826 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Please tell me if you have a very favorable, somewhat favora... | 0.9022 | -0.6325 |
| Please tell me if you have a very favorable, somewhat favora... | 0.9022 | -0.3162 |
| Please tell me if you have a very favorable, somewhat favora... | 0.9290 | -0.6325 |
| And thinking about some political leaders and organizations ... | 1.0000 | 0.0000 |
| As I read a list of groups and organizations, for each, plea... | 1.0000 | 0.0000 |
