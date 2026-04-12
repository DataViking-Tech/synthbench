# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85
**Dataset:** subpop (100 questions)
**Samples per question:** 30
**Elapsed:** 2953.0s

## SynthBench Parity Score (SPS)

**SPS: 0.6773 [0.6887, 0.7438]** (from 5 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.6989 [0.6668, 0.7318] | ███████░░░ |
| P_rank  Rank-Order | 0.7356 [0.7003, 0.7646] | ███████░░░ |
| P_cond  Conditioning | 0.0035 | ░░░░░░░░░░ |
| P_sub   Subgroup | 0.9862 | ██████████ |
| P_refuse Refusal Cal. | 0.9622 [0.9141, 0.9812] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.3011 |
| Median JSD | 0.2907 |
| Mean Kendall's tau | 0.4712 |
| Composite Parity (legacy) | 0.7173 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1553 | +28% |
| random-baseline | 0.6495 | +0.0678 | +10% |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Demographic Breakdown

### POLPARTY

Best: Republican (P_dist=0.6691) / Worst: Democrat (P_dist=0.6509)

| Group | P_dist | P_cond | Questions |
|-------|--------|--------|-----------|
| Republican | 0.6691 | 0.0770 | 100 |
| Democrat | 0.6509 | 0.0400 | 100 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| Do you think gender should be a major factor, minor factor, ... | 0.0270 | 0.9129 |
| Please indicate if you have attended a concert over the past... | 0.0455 | 1.0000 |
| Do you think people have ever assumed that you benefited unf... | 0.0657 | 0.6667 |
| Have there been times in the past 12 months when you did not... | 0.0738 | 0.9129 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think artificial intelligence (AI) would do better, w... | 0.5772 | -0.3162 |
| How important is your religion in shaping your views about a... | 0.6084 | -0.4606 |
| Thinking about the use of artificial intelligence (AI) in th... | 0.6221 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 0.6303 | -0.4303 |
| In the news you are receiving about the Biden administration... | 1.0000 | 0.0000 |
