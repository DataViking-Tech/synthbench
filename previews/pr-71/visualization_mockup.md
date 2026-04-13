# SynthBench Leaderboard — Visualization & Interpretability Mockup

This mockup translates the recommendations into a concrete, implementation-ready layout.

> Rendered version: `docs/mockup.html` (open directly in a browser).

---

## 1) Page Structure (desktop)

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ SynthBench                                                                    │
│ Open benchmark for synthetic survey respondent quality                        │
│ [GitHub] [Methodology] [Submit Results]                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ HERO SUMMARY                                                                  │
│ "Best model is +23 points vs random baseline"                                │
│                                                                              │
│ [Dataset: All ▾] [Metric: SPS* ▾] [Show: Top 10 ▾] [Include baselines ☑]    │
│                                                                              │
│  Top-10 Dot Plot with uncertainty bars                                        │
│  (x-axis = SPS*, vertical baseline lines at Random and Majority)              │
│                                                                              │
│  Legend: ● raw LLM   ■ product   ◆ ensemble                                   │
│  Reliability cue: opaque = high reliability, faded = low reliability          │
├──────────────────────────────────────────────────────────────────────────────┤
│ COMPARISON TABS                                                               │
│ [Overview] [GlobalOpinionQA] [OpinionsQA] [SubPOP] [Trends]                  │
├──────────────────────────────────────────────────────────────────────────────┤
│ OVERVIEW PANEL                                                                │
│                                                                              │
│ Rank | Model | GQA | OQA | SubPOP | Aggregate SPS* | Reliability | Coverage  │
│------------------------------------------------------------------------------│
│ 1    | ...   | ... | ... | ...    | 0.8565         | High        | 3/3      │
│ 2    | ...   |  —  | ... |  —     | 0.7499         | Medium      | 1/3      │
│                                                                              │
│ Right-side explainer card:                                                    │
│  - What SPS* means                                                            │
│  - Why reliability can change interpretation                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│ MODEL DETAIL DRAWER (on row click)                                            │
│                                                                              │
│ [Model name]                                                                  │
│  Score decomposition: [P_dist][P_rank][P_refuse][P_cond][P_sub]              │
│  Run stability: sparkline + CI + # runs                                       │
│  Topic performance: Consumer / Neutral / Political                             │
│  Notes: warnings/anomalies (e.g., Tau ≈ 0)                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ METHODOLOGY SNAPSHOT + FOOTNOTES                                              │
│ - SPS vs SPS*                                                                  │
│ - Baseline definitions                                                         │
│ - Data freshness and update timestamp                                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2) Mobile-first mockup

```text
[Header]
[Top controls: Dataset | Metric]
[Hero top-5 chart]
[Toggle: Show table]

Card list:
┌────────────────────────────┐
│ #1 Model Name              │
│ SPS* 0.8565  (+0.23 vs rnd)│
│ Reliability: High          │
│ Coverage: 3/3              │
│ [Expand details]           │
└────────────────────────────┘
```

Behavior:
- Keep only top controls sticky.
- Collapse dense numeric columns into chips.
- Details drawer opens full-width under each card.

---

## 3) Visual encodings

### Reliability encoding
- **High**: `N >= 200`, `runs >= 3`, `coverage >= 2/3`
- **Medium**: `N >= 100`, `runs >= 2`
- **Low**: otherwise

Use both:
1. Badge (`High / Medium / Low`)
2. Opacity on marks (1.0 / 0.8 / 0.55)

### Baselines
- Random and majority shown as **persistent vertical rules** on every score plot.
- Add short inline interpretation label:
  - `Above random by +0.09`
  - `Near random (within 0.01)`

### Uncertainty
- For each model mark, show whisker from p10 to p90 (or CI from bootstraps if available).
- Tooltip includes:
  - SPS* mean
  - interval bounds
  - N
  - run count

---

## 4) Interaction spec (concise)

- **Sort options**: SPS*, vs random, reliability, recency.
- **Filter chips**: raw/product/ensemble, dataset coverage, min N.
- **Explain mode toggle**: overlays plain-language helper text on column headers.
- **Anomaly badges**:
  - `Low tau`
  - `High variance`
  - `Partial coverage`
- **Compare mode**: pick 2–3 models and open side-by-side decomposition.

---

## 5) Accessibility checklist (must-have)

- Sort headers are `<button>` elements with `aria-sort` updates.
- Expanders are `<button>` with `aria-expanded` and `aria-controls`.
- Color is never the only signal (also use icon/shape/text).
- Ensure contrast for gold/yellow states in both dark/light themes.
- Keyboard path for all interactions (tab, enter, space, esc).

---

## 6) Suggested implementation phases

1. **Phase 1 (1–2 days)**
   - Hero chart reduction (Top 10 + controls)
   - Reliability badge + coverage emphasis in table
   - SPS* inline explainer near headers

2. **Phase 2 (2–4 days)**
   - Model detail drawer with decomposition + uncertainty
   - Anomaly badges and compare mode

3. **Phase 3 (later)**
   - Trends tab (time-series per model)
   - Saved views / sharable URLs

---

## 7) Wireframe snippets for key components

### Hero row template

```text
Model Name                  ●────────┄┄┄┄┄┄┄┄┄┄┄┄│
                             ^mean      whisker      random baseline
```

### Reliability badge

```text
[High reliability]  N=684 · runs=5 · coverage=3/3
```

### Decomposition strip

```text
P_dist 0.74 | P_rank 0.53 | P_refuse 0.99 | P_cond — | P_sub —
```

