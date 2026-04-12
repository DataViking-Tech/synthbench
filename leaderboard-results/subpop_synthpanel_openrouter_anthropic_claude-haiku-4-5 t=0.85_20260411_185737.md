# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5 t=0.85
**Dataset:** subpop (100 questions)
**Samples per question:** 30
**Elapsed:** 2841.5s

## SynthBench Parity Score (SPS)

**SPS: 0.6790 [0.7011, 0.7528]** (from 5 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7110 [0.6835, 0.7390] | ███████░░░ |
| P_rank  Rank-Order | 0.7426 [0.7089, 0.7705] | ███████░░░ |
| P_cond  Conditioning | 0.0000 | ░░░░░░░░░░ |
| P_sub   Subgroup | 0.9790 | ██████████ |
| P_refuse Refusal Cal. | 0.9626 [0.9134, 0.9817] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2890 |
| Median JSD | 0.2717 |
| Mean Kendall's tau | 0.4852 |
| Composite Parity (legacy) | 0.7268 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1648 | +29% |
| random-baseline | 0.6495 | +0.0773 | +12% |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Demographic Breakdown

### POLPARTY

Best: Republican (P_dist=0.6695) / Worst: Democrat (P_dist=0.6420)

| Group | P_dist | P_cond | Questions |
|-------|--------|--------|-----------|
| Republican | 0.6695 | 0.0742 | 100 |
| Democrat | 0.6420 | 0.0303 | 100 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Did you refuse to answer the previous question?... | 0.0149 | 0.8165 |
| Please indicate if you have attended a concert over the past... | 0.0200 | 1.0000 |
| Do you think gender should be a major factor, minor factor, ... | 0.0446 | 0.9129 |
| Do you think people have ever assumed that you benefited unf... | 0.0510 | 0.9129 |
| Do you think the United States’ decision to withdraw all tro... | 0.0770 | 0.3333 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think artificial intelligence (AI) would do better, w... | 0.5772 | -0.3162 |
| How important is your religion in shaping your views about a... | 0.6000 | -0.4606 |
| How acceptable do you think it is for a smart speaker to ana... | 0.6048 | 0.1155 |
| Thinking about the use of artificial intelligence (AI) in th... | 0.6221 | 0.0000 |
| Regardless of whether you think abortion should be legal or ... | 0.6303 | -0.4303 |
