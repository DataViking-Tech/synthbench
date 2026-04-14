# SynthBench Methodology Design

**Author**: datascientist | **Date**: 2026-04-10 | **Status**: PROPOSAL

---

## Quick Guide: What SynthBench Measures

SynthBench answers one question: **how well does an AI reproduce real human survey responses?**

We compare the AI's answers against ground-truth data from thousands of real human survey respondents, then score it across six dimensions:

| Metric | Plain English | 0 means... | 1 means... |
|--------|--------------|------------|------------|
| **SPS** | Overall score (average of all metrics below) | Random noise | Indistinguishable from humans |
| **P_dist** | Do the AI's answer percentages match humans? | Completely different distributions | Identical distributions |
| **P_rank** | Does the AI rank options in the same order as humans? | Reversed or random ordering | Perfect rank agreement |
| **P_refuse** | Does the AI decline to answer at the right rate? | Refusal rates completely off | Matches human refusal patterns |
| **P_cond** | When told "respond as a 65-year-old conservative," does the AI shift its answers? | Personas have no effect | Perfect demographic role-playing |
| **P_sub** | Is the AI equally accurate for all demographics? | Wildly uneven across groups | Equally accurate everywhere |

**Concrete example**: On "Do you support renewable energy?" real humans split 70/30. If the AI also splits 70/30, P_dist is near 1. If the AI splits 50/50, P_dist drops. P_rank checks whether the AI at least got the *ordering* right (more "yes" than "no"), even if the exact percentages are off.

**Baselines** give meaning to scores:
- **Random**: Picks answers uniformly. The absolute floor — scoring at or below this means the AI adds negative value.
- **Majority-Class**: Always picks the most popular answer. Scores well on consensus questions, poorly on divisive ones.

For the full technical details, read on.

---

## 1. Metric Framework: Recommended Hybrid Approach

### 1.1 Analysis of the Two Frameworks

**Proposed (synthpanel datascientist) — 4 sub-scores:**
| Metric | Measures | Method |
|--------|----------|--------|
| P_dist | Distributional parity | Jensen-Shannon divergence |
| P_rank | Rank-order parity | Kendall's tau-b |
| P_theme | Qualitative theme overlap | LLM-as-judge |
| P_subgroup | Demographic sub-group consistency | Per-group scoring |

**OpinionsQA (Santurkar et al.) — 4 axes:**
| Axis | Measures | Method |
|------|----------|--------|
| Representativeness | Distribution alignment | 1-Wasserstein distance |
| Steerability | Persona conditioning effectiveness | Max alignment across 3 conditioning styles |
| Consistency | Cross-topic stability | Best-group agreement rate across topics |
| Refusals | Refusal rate calibration | Refusal probability comparison |

### 1.2 Compatibility Assessment

**Compatible (map cleanly):**
- P_dist ≈ Representativeness. Both measure distributional similarity. Different
  distance metrics (JSD vs Wasserstein) but same intent.
- P_subgroup ≈ Representativeness (group-level) + Consistency. OpinionsQA
  computes representativeness per-group; P_subgroup captures the same concern.

**Complementary (no overlap, both needed):**
- P_rank has no OpinionsQA equivalent. Captures rank-order fidelity even when
  exact proportions differ — valuable signal.
- P_theme has no OpinionsQA equivalent. Needed for open-ended responses
  (Phase 2+). Not applicable to OpinionsQA's multiple-choice format.
- Steerability has no proposed equivalent. This is *the central question* for
  synthetic respondent providers: how well does persona conditioning work?
  Critical omission from the proposed framework.
- Refusals has no proposed equivalent. A provider that never refuses lacks human
  authenticity; one that refuses too much is useless.

### 1.3 Recommendation: 6-Metric Parity Framework

Adopt a hybrid that preserves what's strong in both and fills the gaps.

```
SYNTHBENCH PARITY SCORE (SPS)
├── P_dist   Distributional Parity     [Phase 1]
├── P_rank   Rank-Order Parity         [Phase 1]
├── P_cond   Conditioning Fidelity     [Phase 1]
├── P_sub    Subgroup Consistency       [Phase 1]
├── P_refuse Refusal Calibration        [Phase 1]
└── P_theme  Thematic Parity           [Phase 2+]
```

#### P_dist — Distributional Parity

**What it measures**: How closely a provider's response distribution matches the
human distribution for a given question-demographic pair.

**Primary metric**: Jensen-Shannon divergence (JSD).
- Bounded [0, 1], symmetric, well-defined even when distributions have zero
  entries.
- Consistent with GlobalOpinionQA (Phase 2 ground truth), which uses JSD.

**Supplementary metric**: 1-Wasserstein distance (WD) for ordinal questions.
- WD respects ordinal structure: "Strongly Agree" is closer to "Agree" than to
  "Strongly Disagree."
- Only applicable when response options have meaningful order (Likert scales).
- Not all OpinionsQA questions are ordinal, so WD cannot be the primary.

**Score**: `P_dist = 1 - mean(JSD)` across all question-demographic pairs.

**Why JSD over WD as primary**: OpinionsQA uses WD, but WD requires ordinal
assumptions that don't hold for all questions (e.g., "Which party do you
identify with?" has no ordinal order). JSD works universally. We report both
where applicable to maintain comparability with OpinionsQA results.

#### P_rank — Rank-Order Parity

**What it measures**: Whether the provider gets the *ordering* of options right,
even if exact proportions differ.

**Metric**: Kendall's tau-b on the probability rankings.
- Range [-1, 1], where 1 = perfect agreement, 0 = no correlation, -1 = reversed.
- tau-b handles tied ranks (common when options have similar probabilities).

**Score**: `P_rank = (1 + mean(tau_b)) / 2` (normalized to [0, 1]).

**Why this matters**: A provider that ranks options A > B > C when humans rank
A > B > C has captured the population's preference structure — even if the
exact split is 45/35/20 vs 40/38/22. Rank fidelity is independently valuable.

#### P_cond — Conditioning Fidelity

**What it measures**: How much persona conditioning improves alignment with the
target demographic. This is OpinionsQA's "steerability" reframed for the
synthetic respondent use case.

**Computation**:
1. For each demographic group G, compute P_dist with no persona conditioning
   (default prompt) → `align_default(G)`.
2. Compute P_dist with full persona conditioning → `align_conditioned(G)`.
3. `P_cond(G) = align_conditioned(G) - align_default(G)` (improvement from
   conditioning).
4. `P_cond = mean(max(0, P_cond(G)))` across all groups.

Floor at 0: if conditioning makes alignment *worse*, the provider gets no credit
(but we report the raw values for diagnostics).

**Why this is critical**: The entire value proposition of a synthetic respondent
provider is that persona conditioning produces responses that reflect the target
demographic. A provider with high P_dist but low P_cond might just have a lucky
default distribution. P_cond isolates the *conditioning mechanism itself*.

**Conditioning protocol**: Each provider is tested with the persona spec it
supports. For raw LLMs, we test all three OpinionsQA styles (QA, BIO, PORTRAY)
and take the max. For dedicated providers (synth-panel, Ditto), we use their
native persona interface.

#### P_sub — Subgroup Consistency

**What it measures**: Whether parity holds across all 60 demographic groups, or
whether some groups are systematically underserved.

**Computation**:
1. Compute P_dist for each of the 60 demographic groups independently.
2. `P_sub = 1 - CV(group_scores)` where CV = coefficient of variation
   (std / mean).

A provider with equal accuracy across all groups gets P_sub ≈ 1.
A provider that's accurate for some groups but terrible for others gets P_sub < 1.

**Why coefficient of variation**: We care about *relative* dispersion. A provider
that scores 0.90 ± 0.02 across groups is more consistent than one scoring
0.70 ± 0.10, even though both have small absolute standard deviations.

**Diagnostic output**: Per-group scores are always reported. P_sub is the
summary; the per-group breakdown is the actionable detail.

#### P_refuse — Refusal Calibration

**What it measures**: Whether the provider's refusal rate matches human refusal
patterns.

**Computation**:
1. For each question-demographic pair, compute the absolute difference between
   provider refusal rate and human refusal rate.
2. `P_refuse = 1 - mean(|R_provider - R_human|)`.

**Why this matters**: Human refusal patterns carry signal. Questions about
religion see higher refusals from non-religious respondents; income questions
see higher refusals from high earners. A good synthetic respondent reproduces
these patterns. A provider that answers everything with zero refusals is
over-confident; one that refuses everything is useless.

#### P_theme — Thematic Parity [Phase 2+]

**What it measures**: For open-ended responses, whether the provider's themes
and reasoning align with human qualitative patterns.

**Method**: LLM-as-judge evaluation.
1. Human open-ended responses are clustered into themes (via embedding + clustering).
2. Provider responses are evaluated for theme overlap and theme proportion.
3. A judge LLM scores each provider response on a rubric: theme relevance,
   theme distribution accuracy, and reasoning quality.

**Why Phase 2+**: OpinionsQA is entirely multiple-choice. P_theme requires
open-ended ground truth data, which we don't have in Phase 1. Phase 2 can
incorporate open-ended questions from World Values Survey qualitative supplements
or purpose-built question sets.

### 1.4 Composite Score

```
SPS = w1*P_dist + w2*P_rank + w3*P_cond + w4*P_sub + w5*P_refuse
```

**Phase 1 default weights**: Equal (0.20 each).

Weights are a policy choice, not a statistical one. Different use cases may
weight differently:
- **Market research**: Heavier on P_dist and P_sub (accuracy across segments).
- **UX research**: Heavier on P_cond and P_rank (persona fidelity, preference
  ordering).
- **Academic**: Heavier on P_refuse and P_sub (methodological rigor, equity).

The score card always reports component scores. The composite is a convenience,
not a replacement.

---

## 2. Provider Adapter Specification

### 2.1 Interface Contract

Every synthetic respondent provider implements the `SynthRespondent` protocol.
The benchmark harness calls providers through this interface only.

```python
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class PersonaSpec:
    """Demographic persona for survey conditioning."""
    demographics: dict[str, str]
    # e.g. {"age": "18-29", "gender": "Female", "ideology": "Liberal"}

    biography: str | None = None
    # Optional free-text bio (used for BIO-style conditioning)

    conditioning_style: str = "default"
    # "default" = use provider's native method
    # "qa"      = OpinionsQA question-answer format
    # "bio"     = biographical context
    # "portray" = direct role instruction


@dataclass
class Response:
    """A single synthetic response."""
    selected_option: int           # 0-indexed into options list
    confidence: float | None       # [0, 1] or None if unavailable
    reasoning: str | None = None   # Free-text reasoning (if supported)
    refusal: bool = False          # True if respondent refused to answer
    metadata: dict = field(default_factory=dict)


@dataclass
class Distribution:
    """Probability distribution over response options."""
    probabilities: list[float]     # P(option_i), sums to ~1.0
    refusal_probability: float = 0.0
    method: str = "logprobs"       # "logprobs" | "sampling" | "reported"
    n_samples: int | None = None   # If method="sampling", sample count


@dataclass
class ProviderMetadata:
    """Provider identification and capabilities."""
    name: str                      # e.g. "synth-panel", "openai-gpt4o"
    version: str                   # Semantic version or model identifier
    supports_logprobs: bool        # Can return token log-probabilities
    supports_distribution: bool    # Can return Distribution directly
    supports_reasoning: bool       # Can return reasoning text
    max_concurrent: int = 10       # Concurrency limit for rate limiting
    cost_per_query: float | None = None  # USD per query, for reporting


class SynthRespondent(Protocol):
    """Interface every provider adapter must implement."""

    @property
    def metadata(self) -> ProviderMetadata:
        """Return provider identification and capabilities."""
        ...

    def respond(
        self,
        question: str,
        options: list[str],
        persona: PersonaSpec,
        *,
        n_samples: int = 1,
    ) -> list[Response]:
        """Generate synthetic response(s) to a survey question.

        Args:
            question:  Survey question text.
            options:   Response options (e.g. ["Strongly agree", ..., "Refused"]).
            persona:   Demographic persona specification.
            n_samples: Independent samples to generate.

        Returns:
            List of Response objects (length = n_samples).
        """
        ...

    def get_distribution(
        self,
        question: str,
        options: list[str],
        persona: PersonaSpec,
    ) -> Distribution:
        """Get probability distribution over response options.

        Providers with logprob access return distributions directly from a
        single query. Sampling-based providers call respond() internally
        and aggregate.

        Returns:
            Distribution over the given options.
        """
        ...
```

### 2.2 Provider Adapters

| Provider | Adapter | Distribution Method | Notes |
|----------|---------|-------------------|-------|
| **synth-panel** | `SynthPanelAdapter` | Reported (native API returns distribution) | Our reference provider |
| **OpenAI (GPT-4o, etc.)** | `OpenAIAdapter` | Logprobs (top-k token logprobs) | `conditioning_style` mapped to system/user prompt |
| **Anthropic (Claude)** | `AnthropicAdapter` | Sampling (no logprobs available) | Requires n_samples >= 30 for stable distributions |
| **Ditto** | `DittoAdapter` | Reported (if API returns distribution) or Sampling | Pending API access to confirm capabilities |
| **Generic HTTP** | `GenericHTTPAdapter` | Sampling | Config-driven: URL, auth, request/response mapping |

### 2.3 Sampling Protocol for Non-Logprob Providers

When a provider cannot return logprobs, distributions are estimated via
repeated sampling:

- **Minimum samples**: 30 per question-persona pair.
- **Recommended**: 100 for publication-grade results.
- **Distribution estimation**: `P(option_i) = count(option_i) / n_samples`.
- **Confidence interval**: Wilson score interval reported alongside point
  estimate.
- **Temperature**: Fixed at provider default (documented in metadata). The
  benchmark measures the provider as-shipped, not temperature-optimized.

### 2.4 Adapter Registration

Providers register via entry points or a simple registry:

```python
# synthbench.providers.registry
PROVIDERS: dict[str, type[SynthRespondent]] = {}

def register(name: str):
    """Decorator to register a provider adapter."""
    def wrapper(cls):
        PROVIDERS[name] = cls
        return cls
    return wrapper

# Usage:
@register("openai")
class OpenAIAdapter:
    ...
```

CLI invocation:
```bash
synthbench run --provider openai --model gpt-4o --suite core
synthbench run --provider synth-panel --suite full
synthbench run --provider generic-http --config ./my-provider.yaml --suite core
```

---

## 3. Benchmark Suite Design

### 3.1 Question Corpus

**Primary source**: OpinionsQA — 1,498 multiple-choice questions from 15 Pew
American Trends Panel waves.

**Two tiers**:

| Suite | Questions | Purpose | Runtime estimate |
|-------|-----------|---------|-----------------|
| **SynthBench-Full** | 1,498 | Complete evaluation, publication-grade | ~6h (logprob), ~24h (sampling@100) |
| **SynthBench-Core** | 300 | Quick evaluation, development iteration | ~1h (logprob), ~5h (sampling@100) |

**Alternative datasets** (selectable via `--dataset`):

| Key | Dataset | Scope | Ground truth | Setup |
|-----|---------|-------|--------------|-------|
| `opinionsqa` | OpinionsQA (Santurkar et al.) | 1,498 US questions, 60 demographic groups | Pew ATP | Bundled |
| `globalopinionqa` | GlobalOpinionQA (Durmus et al.) | 2,556 questions, 138 countries | Pew Global + WVS subset | Auto-download (HuggingFace) |
| `subpop` | SubPOP (Suh et al., ACL 2025) | 3,362 questions, 22 US subpopulations | ATP aggregates | Auto-download (HuggingFace, gated) |
| `pewtech` | Pew Internet & Technology | Tech adoption, privacy, AI attitudes | Pew ATP (tech waves) | Manual (free Pew account) |
| `wvs` | World Values Survey Wave 7 | 290+ questions, 64 countries, social/political/religious values | WVS7 microdata (2017-2022) | Manual (registration at worldvaluessurvey.org) |
| `gss` | General Social Survey (NORC) | 50+ years of US attitudes on work, gender, race, institutions | GSS cumulative file | Manual (public download from gss.norc.org) |

**Suitability guidance**:

- **Cross-cultural conditioning** — use `globalopinionqa` (138 countries, ready
  out of the box) or `wvs` (64 countries, deeper political/religious coverage
  but manual setup).
- **US demographic parity** — use `opinionsqa` (richest group coverage) or
  `subpop` (pre-aggregated subgroup distributions).
- **Temporal drift** — use `gss` with a `year` filter to evaluate against
  distributions from a specific survey year (1972-present).
- **Tech-domain attitudes** — use `pewtech`.

Both `wvs` and `gss` expect a pre-aggregated CSV in the adapter's data
directory (`~/.synthbench/data/{wvs,gss}/raw/`) with columns
`question_id, question_text, {country|year}, option, count`. One row per
(question, stratum, option) tuple; the adapter sums counts to build the
ground-truth distribution (population-weighted when no filter is active).
The adapters raise `DatasetDownloadError` with setup instructions when the
expected file is missing.

### 3.2 Core Subset Selection (SynthBench-Core)

The 300-question Core subset is stratified across three dimensions:

**A. Topic coverage** (proportional):
- 13 questions per coarse-grained topic (23 topics × 13 ≈ 300).
- Within each topic, select questions that maximize variance in human response
  entropy (mix of consensus questions and divisive questions).

**B. Response entropy** (balanced):
- **Low entropy** (< 1.0 bits): Strong consensus questions. Easy for providers
  to match.
- **Medium entropy** (1.0 - 1.5 bits): Moderate disagreement. The diagnostic
  sweet spot.
- **High entropy** (> 1.5 bits): High disagreement. Hardest to match. Most
  sensitive to distributional accuracy.
- Target: ~100 questions in each entropy band.

**C. Demographic sensitivity** (flagged):
- Questions where inter-group variance is high (e.g., abortion, gun control)
  are tagged as "demographically sensitive."
- Core must include at least 30% sensitive questions — these are where
  conditioning fidelity matters most.

**Selection algorithm**:
1. Compute response entropy H(q) and inter-group variance V(q) for each question.
2. Stratified sample: 13 per topic, balanced across entropy bands, ensuring ≥30%
   sensitive.
3. Publish the exact question IDs for reproducibility. Locked per SynthBench
   version.

### 3.3 Demographic Groups

All 60 OpinionsQA demographic groups across 11 attributes:

| Attribute | Groups | Count |
|-----------|--------|-------|
| Age | 18-29, 30-49, 50-64, 65+ | 4 |
| Education | < HS, HS grad, Some college, Associate's, College grad, Postgrad | 6 |
| Gender | Male, Female | 2 |
| Political ideology | Very conservative, Conservative, Moderate, Liberal, Very liberal | 5 |
| Political party | Republican, Democrat, Independent, Other | 4 |
| Income | <$30K, $30-50K, $50-75K, $75-100K, $100K+ | 5 |
| Religion | Protestant, Catholic, Mormon, Orthodox, Jewish, Muslim, Buddhist, Hindu, Atheist, Agnostic, Other, Nothing in particular | 12 |
| Religious attendance | >Weekly, Weekly, 1-2x/month, Few times/year, Seldom, Never | 6 |
| Census region | Northeast, Midwest, South, West | 4 |
| Marital status | Married, Partnered, Divorced, Separated, Widowed, Never married | 6 |
| Citizenship | Yes, No | 2 |
| | | **56** |

Note: The canonical count is 56 unique group labels across 11 attributes (some
sources cite 60 due to counting methodology; we use the actual unique labels
from OpinionsQA data files). Each question is evaluated against every
demographic group within each attribute.

### 3.4 Evaluation Matrix

Per question q, per attribute a, per group g within a:

| Component | Queries required (logprob provider) | Queries required (sampling@100) |
|-----------|------------------------------------|---------------------------------|
| Default (no persona) | 1 | 100 |
| Conditioned (per group) | 1 per group | 100 per group |

**Full suite scale** (logprob provider):
- 1,498 questions × (1 default + ~5 groups avg per attribute × 11 attributes)
  ≈ 1,498 × 56 = ~84K conditioned queries + 1,498 default = **~85K total queries**

**Core suite scale** (logprob provider):
- 300 × 56 + 300 = **~17K total queries**

For sampling-based providers, multiply by n_samples.

---

## 4. Baseline Definitions

Every baseline uses the same evaluation pipeline as real providers. Baselines
give meaning to scores — a P_dist of 0.72 is meaningless without knowing the
floor and ceiling.

### 4.1 Random Baseline (Lower Bound)

**Definition**: Uniform distribution over all non-refusal options.

**Construction**: For a question with k options, P(option_i) = 1/k,
P(refusal) = 0.

**Expected P_dist**: Depends on question entropy. For low-entropy questions
(strong consensus), random will score poorly. For maximum-entropy questions,
random will score well by accident.

**Purpose**: Absolute floor. Any provider scoring at or below random is adding
negative value.

### 4.2 Majority-Class Baseline

**Definition**: Always select the mode of the overall population distribution.

**Construction**: For each question, find the option with highest probability
in the aggregate human distribution. Assign P = 1.0 to that option, 0.0 to
all others.

**Expected behavior**: Scores well on consensus questions, poorly on divisive
ones. P_cond = 0 by definition (no conditioning mechanism). P_sub will be poor
(ignores subgroup variation).

**Purpose**: Shows the value of distributional modeling. If a provider can't
beat majority-class on P_dist, it's not learning the shape of opinions — just
the center.

### 4.3 Population-Average Baseline

**Definition**: Use the overall population distribution (ignoring demographics)
for every group.

**Construction**: For each question, use the weighted aggregate distribution
D_O(q) from OpinionsQA (weighted by survey sampling weights) as the response
for every demographic group.

**Expected behavior**: Decent P_dist on aggregate, poor P_cond (conditioning
adds nothing since the same distribution is used for all groups), moderate
P_sub (will do well for groups near the population center, poorly for outlier
groups).

**Purpose**: Isolates the value of demographic conditioning. The gap between
Population-Average and a conditioned provider is the *conditioning premium* —
the whole reason synthetic respondent products exist.

### 4.4 Unconditioned LLM Baseline (GPT-4o, No Persona)

**Definition**: Raw GPT-4o prompted with the survey question and options, no
persona description, standard completion parameters.

**Construction**: Use the OpenAI adapter with an empty PersonaSpec. This is the
"just prompt ChatGPT" approach that many researchers currently use.

**Expected behavior**: Based on OpinionsQA findings, this will show moderate
representativeness with systematic biases (skews young, liberal, educated).
P_cond = 0 (no conditioning applied). P_sub will reveal which demographic
groups the base model naturally aligns with.

**Purpose**: The competitive baseline. This is what people do today when they
"use AI for surveys." Every dedicated synthetic respondent product must
demonstrate clear improvement over this to justify its existence.

### 4.5 Human Ceiling (Split-Half Reliability)

**Definition**: The theoretical maximum score, determined by human response
variability.

**Construction**: Split each demographic group's respondents randomly into two
halves. Compute all parity metrics between the two halves. This measures the
inherent noise in human survey data.

**Expected behavior**: P_dist will not be 1.0 — human responses have sampling
variance. This ceiling tells us the maximum achievable score.

**Purpose**: A provider scoring *above* the human ceiling is overfitting or
exploiting artifacts. The meaningful range for evaluation is
[Unconditioned LLM, Human Ceiling].

**Computation note**: Requires access to individual-level OpinionsQA response
data (not just aggregated distributions). If individual responses are not
available in the public dataset, we estimate the ceiling via bootstrap
resampling of the aggregate distributions.

### 4.6 Baseline Summary

```
Score axis:  0.0                                              1.0
             |----|----|----|----|----|----|----|----|----|----|
             ^         ^              ^                   ^
           Random   Majority    Unconditioned LLM    Human Ceiling
                       ^
                  Pop-Average

Meaningful evaluation range: [Unconditioned LLM ... Human Ceiling]
```

---

## 5. Model Card Format (SynthBench Score Card)

### 5.1 Machine-Readable Output (JSON)

Every SynthBench run produces a JSON artifact:

```json
{
  "synthbench_version": "1.0.0",
  "run_id": "sb-20260410-a1b2c3",
  "timestamp": "2026-04-10T12:00:00Z",
  "suite": "core",
  "provider": {
    "name": "synth-panel",
    "version": "2.1.0",
    "adapter": "SynthPanelAdapter",
    "config_hash": "sha256:..."
  },
  "scores": {
    "composite": 0.74,
    "P_dist": 0.81,
    "P_rank": 0.77,
    "P_cond": 0.68,
    "P_sub": 0.72,
    "P_refuse": 0.71,
    "weights": [0.2, 0.2, 0.2, 0.2, 0.2]
  },
  "baselines": {
    "random":        {"composite": 0.31, "P_dist": 0.42, "...": "..."},
    "majority":      {"composite": 0.45, "P_dist": 0.55, "...": "..."},
    "pop_average":   {"composite": 0.52, "P_dist": 0.65, "...": "..."},
    "unconditioned": {"composite": 0.58, "P_dist": 0.67, "...": "..."},
    "human_ceiling": {"composite": 0.89, "P_dist": 0.92, "...": "..."}
  },
  "demographic_breakdown": {
    "by_attribute": {
      "age": {"18-29": 0.83, "30-49": 0.79, "50-64": 0.74, "65+": 0.62},
      "...": "..."
    },
    "best_group":  {"group": "Liberal", "P_dist": 0.91},
    "worst_group": {"group": "65+",     "P_dist": 0.62}
  },
  "topic_breakdown": {
    "by_topic": {"abortion": 0.65, "climate": 0.78, "...": "..."},
    "best_topic":  {"topic": "technology", "P_dist": 0.88},
    "worst_topic": {"topic": "abortion",   "P_dist": 0.65}
  },
  "run_metadata": {
    "questions_evaluated": 300,
    "demographic_groups": 56,
    "total_queries": 17100,
    "total_cost_usd": 42.50,
    "duration_seconds": 3840,
    "distribution_method": "logprobs",
    "n_samples": null
  }
}
```

### 5.2 Human-Readable Score Card

```
================================================================
  SYNTHBENCH v1.0 SCORE CARD
================================================================
  Provider:  synth-panel v2.1.0
  Suite:     SynthBench-Core (300 questions)
  Date:      2026-04-10
  Run ID:    sb-20260410-a1b2c3
================================================================

  COMPOSITE PARITY SCORE:  0.74 / 1.00
  ────────────────────────────────────────────────
  P_dist   Distributional   0.81  ████████░░  
  P_rank   Rank-Order       0.77  ████████░░  
  P_cond   Conditioning     0.68  ███████░░░  
  P_sub    Subgroup         0.72  ███████░░░  
  P_refuse Refusal Cal.     0.71  ███████░░░  

  VERSUS BASELINES
  ────────────────────────────────────────────────
  vs Random:            +0.43  (+138%)
  vs Majority-Class:    +0.29  (+64%)
  vs Population-Avg:    +0.22  (+42%)
  vs Unconditioned LLM: +0.16  (+28%)
  vs Human Ceiling:     -0.15  (-17%)

  DEMOGRAPHIC HIGHLIGHTS
  ────────────────────────────────────────────────
  Best aligned:   Liberal          (P_dist = 0.91)
  Worst aligned:  65+              (P_dist = 0.62)
  Spread (CV):    0.12

  TOPIC HIGHLIGHTS
  ────────────────────────────────────────────────
  Best topic:     Technology       (P_dist = 0.88)
  Worst topic:    Abortion         (P_dist = 0.65)

  RUN INFO
  ────────────────────────────────────────────────
  Questions:      300
  Groups:         56
  Total queries:  17,100
  Cost:           $42.50
  Duration:       1h 4m
  Method:         logprobs
================================================================
```

### 5.3 Comparative Leaderboard Row

For multi-provider comparisons:

```
| Provider        | Version | SPS  | P_dist | P_rank | P_cond | P_sub | P_refuse | Suite |
|-----------------|---------|------|--------|--------|--------|-------|----------|-------|
| synth-panel     | 2.1.0   | 0.74 | 0.81   | 0.77   | 0.68   | 0.72  | 0.71     | core  |
| GPT-4o (portray)| 2026-03 | 0.61 | 0.67   | 0.63   | 0.55   | 0.58  | 0.62     | core  |
| Claude (portray)| sonnet  | 0.59 | 0.65   | 0.61   | 0.52   | 0.60  | 0.58     | core  |
| GPT-4o (raw)    | 2026-03 | 0.48 | 0.55   | 0.52   | 0.00   | 0.45  | 0.40     | core  |
| Pop-Average     | —       | 0.52 | 0.65   | 0.58   | 0.00   | 0.39  | 0.48     | core  |
| Random          | —       | 0.31 | 0.42   | 0.30   | 0.00   | 0.25  | 0.20     | core  |
```

---

## 6. Phase Roadmap

| Phase | Ground Truth | Metrics | Scope |
|-------|-------------|---------|-------|
| **1** (now) | OpinionsQA (1,498 Qs, 60 US groups) | P_dist, P_rank, P_cond, P_sub, P_refuse | US demographic parity |
| **2** | GlobalOpinionQA (2,556 Qs, 40+ countries) | + cross-cultural P_dist, P_sub by nation | Global cultural parity |
| **3** | Custom open-ended questions | + P_theme (LLM-as-judge) | Qualitative fidelity |
| **4** | Longitudinal (opinion drift tracking) | + temporal stability metrics | Temporal parity |

---

## 7. Key Design Decisions & Rationale

**JSD over Wasserstein as primary distance**: Universality (works for non-ordinal
questions), boundedness, and Phase 2 consistency with GlobalOpinionQA. WD
retained as supplementary for ordinal questions.

**Equal default weights**: The composite score is a convenience aggregation.
Premature weighting would embed research-community preferences before we have
empirical data on metric correlations. Equal weights until evidence suggests
otherwise.

**56 demographic groups, not aggregated**: SynthBench evaluates per-group, not
just aggregate. A provider that's excellent on average but terrible for specific
populations (e.g., 65+, widowed — the groups OpinionsQA found most underserved)
should be exposed by P_sub.

**Both Core and Full suites**: Vendors need fast iteration (Core, ~1h). Published
results need rigor (Full, ~6h). Core is a stratified subset, not a random sample
— it's designed to correlate strongly with Full results.

**Human ceiling baseline**: Without this, we can't distinguish "provider is
imperfect" from "the task is inherently noisy." Split-half reliability grounds
expectations.

**Sampling protocol for non-logprob providers**: 30 minimum, 100 recommended.
Wilson score intervals quantify uncertainty. This ensures fair comparison between
logprob providers (exact distributions) and sampling providers (estimated
distributions).
