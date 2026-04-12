# SynthBench Score Card

**Provider:** synthpanel/openrouter/openai/gpt-4o-mini t=1.0
**Dataset:** opinionsqa (100 questions)
**Samples per question:** 30
**Elapsed:** 476.5s

## SynthBench Parity Score (SPS)

**SPS: 0.8276 [0.7167, 0.7713]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7180 [0.6898, 0.7490] | ███████░░░ |
| P_rank  Rank-Order | 0.7706 [0.7400, 0.7984] | ████████░░ |
| P_refuse Refusal Cal. | 0.9943 [0.9934, 0.9949] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2820 |
| Median JSD | 0.2771 |
| Mean Kendall's tau | 0.5413 |
| Composite Parity (legacy) | 0.7443 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1823 | +32% |
| random-baseline | 0.6495 | +0.0948 | +15% |

## What These Scores Mean

- **SPS** (SynthBench Parity Score): The overall score — average of all metrics. 0 = random noise, 1 = indistinguishable from real humans.
- **P_dist** (Distributional Parity): How closely does the AI's answer distribution match real humans? If 60% of humans say 'yes' and the AI says 'yes' 60% of the time, that's a perfect match. 0 = completely different, 1 = identical distributions.
- **P_rank** (Rank-Order Parity): Does the AI get the preference ordering right? If humans prefer A > B > C, does the AI agree — even if the exact percentages differ? 0 = reversed ordering, 1 = perfect agreement.
- **P_refuse** (Refusal Calibration): Does the AI refuse to answer at appropriate rates? Humans sometimes decline sensitive questions. An AI that never refuses, or refuses too often, is miscalibrated. 0 = rates completely off, 1 = perfect match.
- **P_cond** (Conditioning Fidelity): When told 'respond as a 65-year-old conservative,' does the AI actually shift its answers? Higher = better demographic role-playing. (When available.)
- **P_sub** (Subgroup Consistency): Is the AI equally accurate across all demographics, or does it nail some groups and miss others? (When available.)

## Temporal Breakdown (by Survey Year)

Scores stratified by Pew ATP survey wave year. Rising P_dist in recent years may indicate training-data contamination.

| Year | P_dist | P_rank | Mean JSD | Questions |
|------|--------|--------|----------|-----------|
| 2017 | 0.7160 | 0.7691 | 0.2840 | 99 |
| 2018 | 0.9153 | 0.9183 | 0.0847 | 1 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Have you ever personally experienced discrimination or been ... | 0.0118 | 1.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.0220 | 0.7071 |
| Have you ever had your pay or hours reduced because your emp... | 0.0333 | 0.7071 |
| Not including in military combat or as part of your job, hav... | 0.0368 | 0.8165 |
| Have you ever been a victim of a violent crime, whether a gu... | 0.0468 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How well, if at all, do the following words or phrases descr... | 0.5362 | 0.3162 |
| How much, if at all, do you worry about the following happen... | 0.5762 | 0.2357 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
| How often, if ever, do you participate in online discussion ... | 0.6910 | 0.3586 |
| How much of a problem was gun violence in the community wher... | 0.7081 | 0.1195 |
