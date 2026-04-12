# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85 tpl=current
**Dataset:** subpop (100 questions)
**Samples per question:** 30
**Elapsed:** 208.3s

## SynthBench Parity Score (SPS)

**SPS: 0.6769 [0.6409, 0.7199]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6889 [0.6444, 0.7241] | ███████░░░ |
| P_rank  Rank-Order | 0.6778 [0.6334, 0.7188] | ███████░░░ |
| P_refuse Refusal Cal. | 0.6640 [0.6087, 0.7176] | ███████░░░ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3111 |
| Median JSD | 0.2686 |
| Mean Kendall's tau | 0.3556 |
| Composite Parity (legacy) | 0.6833 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1213 | +22% |
| random-baseline | 0.6495 | +0.0338 | +5% |

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
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| Have there been times in the past 12 months when you did not... | 0.0241 | 0.9129 |
| Do you think whether a relative attended the school should b... | 0.0309 | 1.0000 |
| Do you think there are situations when abortion should be le... | 0.0496 | 1.0000 |
| Do you think gender should be a major factor, minor factor, ... | 0.0509 | 0.9129 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| In the news you are receiving about the Biden administration... | 0.9102 | -0.8165 |
| Thinking about policies around abortion in this country, in ... | 0.9509 | -0.5774 |
| Which statement comes closer to your view, even if neither i... | 0.9648 | -0.8165 |
| If a woman had an abortion in a situation where it was illeg... | 1.0000 | 0.0000 |
| As you may know, the Supreme Court’s decision found that the... | 1.0000 | 0.0000 |
