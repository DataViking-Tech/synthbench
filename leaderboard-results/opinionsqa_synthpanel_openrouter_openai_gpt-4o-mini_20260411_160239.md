# SynthBench Score Card

**Provider:** synthpanel/openrouter/openai/gpt-4o-mini
**Dataset:** opinionsqa (200 questions)
**Samples per question:** 50
**Elapsed:** 142.8s

## SynthBench Parity Score (SPS)

**SPS: 0.8115 [0.6993, 0.7426]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7003 [0.6767, 0.7217] | ███████░░░ |
| P_rank  Rank-Order | 0.7435 [0.7136, 0.7686] | ███████░░░ |
| P_refuse Refusal Cal. | 0.9908 [0.9867, 0.9928] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2997 |
| Median JSD | 0.3005 |
| Mean Kendall's tau | 0.4870 |
| Composite Parity (legacy) | 0.7219 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1599 | +28% |
| random-baseline | 0.6495 | +0.0724 | +11% |

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
| 2017 | 0.7183 | 0.7693 | 0.2817 | 99 |
| 2018 | 0.6827 | 0.7182 | 0.3173 | 101 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Have you ever personally experienced discrimination or been ... | 0.0077 | 1.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.0220 | 0.7071 |
| Now thinking again about the community where you live do you... | 0.0224 | 0.3333 |
| Have you ever had your pay or hours reduced because your emp... | 0.0333 | 0.7071 |
| Not including in military combat or as part of your job, hav... | 0.0368 | 0.8165 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| How much, if at all, is access to high-speed internet a prob... | 0.6499 | -0.1826 |
| How much of a problem was gun violence in the community wher... | 0.6608 | 0.1195 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
| How much, if at all, is racism a problem in your local commu... | 0.6872 | -0.2357 |
| How often, if ever, do you participate in online discussion ... | 0.6884 | 0.3586 |
