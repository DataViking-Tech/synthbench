# SynthBench Score Card

**Provider:** synthpanel/openrouter/anthropic/claude-haiku-4-5
**Dataset:** opinionsqa (175 questions)
**Samples per question:** 50
**Elapsed:** 196.9s

## SynthBench Parity Score (SPS)

**SPS: 0.8512 [0.7633, 0.8033]** (from 3 metrics)

| Metric | Score | |
|--------|------:|---|
| P_dist  Distributional | 0.7534 [0.7317, 0.7743] | ████████░░ |
| P_rank  Rank-Order | 0.8149 [0.7944, 0.8348] | ████████░░ |
| P_refuse Refusal Cal. | 0.9853 [0.9734, 0.9885] | ██████████ |

## Raw Metrics

| Metric | Value |
|--------|-------|
| Mean JSD | 0.2466 |
| Median JSD | 0.2458 |
| Mean Kendall's tau | 0.6299 |
| Composite Parity (legacy) | 0.7842 |

## vs Baselines

| Baseline | Score | Delta | % |
|----------|------:|------:|--:|
| majority-baseline | 0.5620 | +0.2222 | +40% |
| random-baseline | 0.6495 | +0.1347 | +21% |

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
| 2017 | 0.7528 | 0.8028 | 0.2472 | 37 |
| 2018 | 0.7444 | 0.7962 | 0.2556 | 39 |
| 2019 | 0.7596 | 0.8525 | 0.2404 | 50 |
| 2020 | 0.7783 | 0.8385 | 0.2217 | 31 |
| 2022 | 0.7140 | 0.7356 | 0.2860 | 18 |

## Best Matches (lowest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you use a password manager, such as LastPass or iCloud Ke... | 0.0034 | 1.0000 |
| When it comes to sexual harassment in the workplace today, h... | 0.0106 | 1.0000 |
| Still thinking ahead 30 years, which do you think is more li... | 0.0210 | 1.0000 |
| Have you yourself ever lost a job because your employer repl... | 0.0220 | 0.7071 |
| Do you use any other social media sites?... | 0.0234 | 1.0000 |

## Worst Matches (highest JSD)

| Question | JSD | tau |
|----------|-----|-----|
| Do you think foods with genetically modified ingredients are... | 0.5423 | 0.0000 |
| Do you think it is very likely, somewhat likely, not very li... | 0.6025 | 0.3586 |
| Do you personally know anyone who has lost a job, or had the... | 0.6144 | 0.0000 |
| How much health risk, if any, does eating fruits and vegetab... | 0.6579 | 0.0000 |
| On a different subject, would you say that society generally... | 0.6715 | -0.2357 |
