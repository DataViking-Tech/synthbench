# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85
**Dataset:** subpop (100 questions)
**Samples per question:** 15
**Elapsed:** 2446.0s

## SynthBench Parity Score (SPS)

**SPS: 0.6692 [0.6772, 0.7356]** (from 5 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6857 [0.6525, 0.7161] | ███████░░░ |
| P_rank  Rank-Order | 0.7300 [0.6919, 0.7618] | ███████░░░ |
| P_cond  Conditioning | 0.0000 | ░░░░░░░░░░ |
| P_sub   Subgroup | 0.9764 | ██████████ |
| P_refuse Refusal Cal. | 0.9537 [0.9066, 0.9758] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3143 |
| Median JSD | 0.2892 |
| Mean Kendall's tau | 0.4600 |
| Composite Parity (legacy) | 0.7079 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1459 | +26% |
| random-baseline | 0.6495 | +0.0583 | +9% |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Demographic Breakdown

### SEX

Best: Male (P_dist=0.6473) / Worst: Female (P_dist=0.6175)

| Group | P_dist | P_cond | Questions |
|-------|--------|--------|-----------|
| Male | 0.6473 | 0.0546 | 100 |
| Female | 0.6175 | 0.0265 | 100 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| Do you think people have ever assumed that you benefited unf... | 0.0246 | 1.0000 |
| Do you think gender should be a major factor, minor factor, ... | 0.0446 | 0.9129 |
| Have there been times in the past 12 months when you did not... | 0.0606 | 0.9129 |
| How would you rate the job the Biden administration has done... | 0.0804 | 0.9487 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How important is your religion in shaping your views about a... | 0.6084 | -0.4606 |
| Regardless of whether you think abortion should be legal or ... | 0.6116 | 0.1155 |
| Thinking about the use of artificial intelligence (AI) in th... | 0.6221 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 0.6906 | -0.3464 |
| In the news you are receiving about the Biden administration... | 1.0000 | 0.0000 |
