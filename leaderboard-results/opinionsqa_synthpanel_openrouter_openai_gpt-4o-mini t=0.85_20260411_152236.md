# SynthBench Score Card

**Provider:** synthpanel/openrouter/openai/gpt-4o-mini t=0.85
**Dataset:** opinionsqa (100 questions)
**Samples per question:** 30
**Elapsed:** 136.4s

## SynthBench Parity Score (SPS)

**SPS: 0.8225 [0.7078, 0.7633]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7110 [0.6796, 0.7419] | ███████░░░ |
| P_rank  Rank-Order | 0.7624 [0.7311, 0.7913] | ████████░░ |
| P_refuse Refusal Cal. | 0.9943 [0.9934, 0.9949] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2890 |
| Median JSD | 0.2807 |
| Mean Kendall's tau | 0.5247 |
| Composite Parity (legacy) | 0.7367 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.1747 | +31% |
| random-baseline | 0.6495 | +0.0872 | +13% |

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
| 2017 | 0.7091 | 0.7608 | 0.2909 | 99 |
| 2018 | 0.8991 | 0.9183 | 0.1009 | 1 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Have you yourself ever lost a job because your employer repl... | 0.0220 | 0.7071 |
| Have you ever had your pay or hours reduced because your emp... | 0.0333 | 0.7071 |
| Not including in military combat or as part of your job, hav... | 0.0368 | 0.8165 |
| Have you ever personally experienced discrimination or been ... | 0.0476 | 1.0000 |
| Do you think men and women are basically similar or basicall... | 0.0582 | 0.8165 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you personally know anyone who has lost a job, or had the... | 0.6144 | 0.0000 |
| Would you favor or oppose the following? If people had the o... | 0.6201 | 0.0000 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
| How often, if ever, do you participate in online discussion ... | 0.7219 | 0.3162 |
| How much of a problem was gun violence in the community wher... | 0.8215 | 0.0000 |
