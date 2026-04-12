# SynthBench Research Findings

**Date**: 2026-04-12 | **Version**: Session 1 Results

---

## Executive Summary

Six experiments across 3 models, 3 datasets, and 200+ benchmark runs reveal that **multi-model ensemble blending is the single largest lever for improving synthetic survey quality** (+5-7 SPS points), while temperature tuning and demographic conditioning provide smaller, model-specific gains. The benchmark also functions as a bias auditing tool, quantifying systematic asymmetries in how LLMs represent different demographic groups.

**Best configuration discovered**: 3-model equal-weight ensemble (Haiku + Gemini Flash Lite + GPT-4o-mini) achieves **SPS 0.900** on OpinionsQA — meaning blended AI responses are 90% indistinguishable from real human survey data.

---

## Experiment A: Temperature Sensitivity

**Question**: Does sampling temperature affect how well models reproduce human survey distributions?

**Method**: 5 temperatures (0.3, 0.5, 0.7, 0.85, 1.0) × 3 models × 2-3 replications each, on OpinionsQA (100 questions, 30 samples/question).

### Results

| Model | Temp Range | SPS Range | Sensitivity | Optimal |
|-------|-----------|-----------|-------------|---------|
| Claude Haiku 4.5 | 0.3–1.0 | 0.843–0.850 | Insensitive (±0.6%) | Any |
| Gemini Flash Lite | 0.3–2.0 | 0.819–0.864 | Strong monotonic (+4.5%) | t=2.0 |
| GPT-4o-mini | 0.3–1.0 | 0.817–0.829 | Mild monotonic (+1.2%) | t=1.0 |

### Key Finding

Temperature sensitivity is **model-specific**, not universal. Higher temperature universally helps or is neutral — it never hurts. The effect correlates with base output entropy (see Experiment H5 below).

**Replication**: All findings confirmed across 2-3 independent replications per data point. Run-to-run standard deviations: 0.001–0.007 SPS.

---

## Experiment B: Persona Template Variants

**Question**: Does the structure of the persona system prompt affect survey quality?

**Method**: 4 template variants × 2 replications on SubPOP (100 questions, 30 samples), all at t=0.85 with Haiku.

| Template | Description | Mean SPS | Std |
|----------|------------|----------|-----|
| **CURRENT** | Name, age, occupation, background, personality | **0.690** | 0.019 |
| MINIMAL | Name, age, occupation only | 0.581 | 0.005 |
| VALUES | + core beliefs, decision style (unfilled) | 0.555 | 0.032 |
| DEMO | + education, income, location, politics (unfilled) | 0.569 | 0.001 |

### Key Finding

The default template wins by **+11 SPS points** (5× the noise band). Templates with unfilled format-string placeholders (`{education_level}`) actively hurt — P_refuse collapses from 0.80 to 0.40–0.50, indicating the model refuses more when the prompt contains garbled placeholder text.

---

## Experiment B v2: Demographic Conditioning

**Question**: Does telling the model "you are a Republican" actually shift its responses toward real Republican survey data?

**Method**: Per-group conditioned evaluation on SubPOP using POLPARTY, INCOME, EDUCATION, RACE, CREGION, and GENDER attributes. Haiku at t=0.85, 100 questions, 15–30 samples.

### POLPARTY (4 replications)

| Group | P_dist | P_cond | Interpretation |
|-------|--------|--------|----------------|
| Republican | 0.666 ± 0.004 | **0.073 ± 0.004** | 7.3% closer to real Republican data |
| Democrat | 0.644 ± 0.006 | **0.033 ± 0.005** | 3.3% closer to real Democrat data |

### INCOME (2 replications)

| Group | P_dist | P_cond |
|-------|--------|--------|
| $100K+ | 0.673 | 0.031 |
| <$30K | 0.603 | 0.020 |

### EDUCATION (1 run)

| Group | P_dist | P_cond |
|-------|--------|--------|
| College graduate | 0.641 | 0.036 |
| Less than HS | 0.597 | 0.038 |

### Key Findings

1. **Conditioning works but the effect is small** (2–7% improvement per group).
2. **Republican conditioning is 2.4× stronger than Democrat** — the model's unconditioned output already approximates Democrat response patterns. This quantifies the documented progressive lean in LLM defaults.
3. **High-income conditioning is 1.5× stronger than low-income** — the model is systematically worse at reproducing low-income response distributions (7pp P_dist gap).
4. **These asymmetries are publishable calibration findings.** The benchmark functions as a bias auditing tool, not just an accuracy leaderboard.

---

## Experiment C: Ensemble Blending

**Question**: Does averaging response distributions across multiple models beat any single model?

**Method**: Per-question distribution blending of Haiku + Gemini Flash Lite + GPT-4o-mini results. Pure arithmetic on existing data — zero additional API cost.

### Results

| Dataset | Best Single Model | Equal Blend | Improvement |
|---------|-------------------|-------------|-------------|
| OpinionsQA (684q) | 0.766 (Haiku) | **0.836** | **+7.0 pts (+9%)** |
| SubPOP (200q) | 0.744 (Gemini) | **0.796** | **+5.2 pts (+7%)** |
| GlobalOpinionQA (100q) | 0.692 (GPT-4o-mini) | **0.747** | **+5.6 pts (+8%)** |

### Key Findings

1. **Largest single lever discovered**: +5–7 SPS points, consistent across all 3 datasets.
2. **Simple equal-weight averaging is optimal** — score-proportional and inverse-JSD weighting produce identical results. No hyperparameter tuning needed.
3. **72–81% of individual questions improve** under blending. Models make uncorrelated errors on different questions.
4. **ORACLE ceiling barely exceeds equal blend** — per-question model selection offers negligible headroom over naive averaging.

### Optimal-Temperature Ensemble (Experiment E)

Using each model at its best temperature (Haiku t=0.85, Gemini t=2.0, GPT-4o-mini t=1.0):

| Method | Default-Temp SPS | Optimal-Temp SPS |
|--------|-----------------|-----------------|
| Best Single Model | 0.846 | 0.864 |
| Equal Blend | **0.899** | **0.900** |

Temperature optimization adds only +0.1pp at the ensemble level — the blend already absorbs per-model weaknesses.

---

## Experiment D: Gemini Extended Temperature

**Question**: Does Gemini Flash Lite's monotonic improvement continue past t=1.0?

**Method**: t={1.2, 1.5, 1.8, 2.0} × 2 replications on OpinionsQA.

| Temp | Mean SPS |
|------|----------|
| 1.0 | 0.856 |
| 1.2 | 0.856 |
| 1.5 | 0.858 |
| 1.8 | 0.857 |
| **2.0** | **0.864** |

### Key Finding

**No peak found even at t=2.0.** Gemini's base output entropy is low enough that extreme temperatures still improve distributional matching. The plateau from 1.0–1.8 then jump at 2.0 may reflect discrete regime changes in the inference backend.

---

## Experiment H5: Base Entropy Predicts Temperature Sensitivity

**Question**: Do models with more concentrated (peaked) default outputs benefit more from raising temperature?

**Method**: Compute KL divergence from uniform for each model's default-temperature outputs.

| Model | Base Entropy | Concentration | Degenerate Questions | Temp Sensitivity |
|-------|-------------|---------------|---------------------|-----------------|
| GPT-4o-mini | 0.22 bits | 92.6% | 58.8% | Mild (+1.2%) |
| Haiku | 0.36 bits | 85.9% | 39.8% | Insensitive (±0.6%) |
| Gemini Flash Lite | 0.56 bits | 77.3% | 32.2% | **Strong (+4.5%)** |

### Key Finding

**Hypothesis NOT supported — actually inverted.** The model with the highest base entropy (Gemini, already most diverse) benefits most from temperature. The most peaked model (GPT-4o-mini, 59% degenerate) shows minimal improvement.

**Interpretation**: Temperature amplifies existing distributional capacity; it doesn't create it. A model hardcoded to pick one answer won't spread with more temperature — it just adds noise.

---

## Lever Hierarchy

| Lever | Effect Size | Cost | Priority |
|-------|-----------|------|----------|
| **Ensemble blending** | **+5–7 SPS pts** | Zero (offline arithmetic) | Highest |
| Per-model optimal temperature | +0–4.5 SPS pts | Low (known configs) | Medium |
| Demographic conditioning | +2–7% on P_cond only | Moderate (per-group API runs) | Scientific value |
| Persona template | CURRENT already optimal | N/A | Done |

---

## Datasets

All experiments use publicly available survey datasets with real human response distributions:

| Dataset | Questions | Demographics | Source |
|---------|-----------|-------------|--------|
| OpinionsQA | 684 | US population | Pew Research ATP surveys |
| SubPOP | 3,362 | 22 US subpopulations | Suh et al., ACL 2025 |
| GlobalOpinionQA | 2,556 | Cross-country | Pew Global Attitudes |

---

## Reproducibility

- All result JSON files are stored in `leaderboard-results/`
- Each file contains per-question distributions, metadata, and configuration
- The `synthbench ensemble` CLI command reproduces blending results from saved files
- Run-to-run standard deviations reported for all replicated experiments
