# SynthBench Hardening Analysis

**Author:** datascientist (crew)
**Date:** 2026-04-18
**Prompted by:** mayor research brief (hq-wisp-bj6je1)
**Reference:** Wang, Mang, Cheung, Sen & Song, "How We Broke Top AI Agent Benchmarks," UC Berkeley RDI, April 2026 — <https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/>

---

## 1. Executive summary

The Berkeley paper shows that 8 major agent benchmarks can be driven to near-perfect scores without actually solving tasks, via attacks on the evaluator (binary-wrapper trojans, pytest-hook injection, public gold file downloads, `eval()` on untrusted input, LLM-judge prompt injection, normalization collisions, filesystem answer leakage, dead-code evaluators). Most attack classes assume an **executing agent** inside a sandbox that shares trust boundary with the evaluator. SynthBench is a **submission-artifact benchmark** — submitters POST a JSON file, we score it — so six of the eight attack classes are structurally inapplicable.

But the paper's underlying threat model — *"attackers defeat the evaluator, not the task"* — applies directly. For SynthBench the analogues are:

| Berkeley class              | SynthBench analogue                                                                                  |
| --------------------------- | ---------------------------------------------------------------------------------------------------- |
| Filesystem answer leakage   | Public `human_distribution` fields are the answer key. 80/20 split is our mitigation.                |
| Dead-code evaluation        | Warning-only Tier-3 detectors effectively *are* dead code — they never fail a submission.            |
| Normalization collisions    | 4-decimal rounding of distributions plus loose metric recompute tolerances create collision surface. |
| Null-agent recommendation   | We have baselines (random, majority) but do not treat them as a validator tripwire.                  |
| LLM-judge prompt injection  | N/A — we have no LLM judge.                                                                          |
| eval() / binary trojans     | N/A — submissions are inert JSON.                                                                    |

**Headline recommendations** (ordered by ROI):

1. **Promote `HOLDOUT_DIVERGENCE` from WARNING to ERROR at production scale** (effort: S). This is the highest-signal existing detector and is currently toothless.
2. **Add a near-copy detector** computing per-question JSD of the submitted `model_distribution` against the *public* `human_distribution` at the submission's own resolution (effort: M). Closes the dominant fabrication shortcut.
3. **Adopt a quarterly-rotated private-holdout salt** without changing the 20% fraction (effort: S, policy: M). Increases temporal diversity without burning coverage or statistical power.
4. **Add an adversarial test suite as a CI gate** with ≥7 fabrications that MUST fail validation (effort: M). Converts our validator from "no known false negatives" to "measured true-positive rate."
5. **Publish a methodology / anti-gaming page** citing the Berkeley paper (effort: S). Reputational rather than technical, but important.

The rest of this document works through each.

---

## 2. Tier-3 detectors — should warnings become errors?

### 2.1 Current state

From `anomaly.py` and `validation.py`:

| Code                   | Tier | Severity | Triggered on                                                        |
| ---------------------- | ---- | -------- | ------------------------------------------------------------------- |
| `ANOMALY_PERFECTION`   | 3    | WARNING  | `mean_jsd < 0.005` OR `std_jsd < 0.005`                             |
| `ANOMALY_NO_REFUSAL`   | 3    | WARNING  | `model_refusal_rate ≡ 0` on datasets humans refuse on (≥3 q, ≥5%)  |
| `ANOMALY_PEER_OUTLIER` | 3    | WARNING  | `\|mean_delta\| > 0.15` vs same-family peers, ≥5 shared questions   |
| `HOLDOUT_DIVERGENCE`   | 1    | WARNING  | `\|sps_public − sps_private\| > max(0.05, 0.5/√min_side)`           |
| `HOLDOUT_MISSING_PRIVATE` | 1 | ERROR    | 0 private rows on a holdout dataset with ≥25 questions              |
| `HOLDOUT_COVERAGE`     | 1    | ERROR    | private ratio < 5% on ≥25-question submission                       |
| `RAW_RESPONSES_*`      | 3    | WARNING  | missing raw samples, wrong length profile, mode disagreement        |
| `REPRO_*`              | 3    | WARNING  | missing reproducibility block / fields                              |

### 2.2 Evaluation by detector

**`ANOMALY_PERFECTION` → PROMOTE TO ERROR (production submissions only).**
The threshold (0.005) sits an order of magnitude below the noise floor of any honest LLM run we have on file (real `mean_jsd` lives in `[0.05, 0.55]`, `std_jsd` in `[0.10, 0.30]`). A submission with mean or std below 0.005 on ≥50 questions is statistically indistinguishable from "copy the answer key to 4 decimals." The only plausible false positive is a tiny debug fixture, which we already guard on by requiring `len(jsd_values) ≥ 5`. **Recommendation:** bump minimum to `≥ 25` and promote to ERROR. Keep the WARNING path for smaller-N submissions so test fixtures keep working.

**`HOLDOUT_DIVERGENCE` → PROMOTE TO ERROR at N ≥ 50 private rows.**
This is the single most informative signal we have, and it's currently a WARNING because at small N the thresholding widens out to cover legitimate sampling noise. But at production scale (the reference haiku n=100 case gave 13 private rows with ~0.07 delta; a full OpinionsQA run has ~300 private rows), the adaptive threshold `0.5/√min_side` collapses toward the `0.05` floor, and an honest run should not clear it. I recommend promoting to ERROR specifically when `min_side ≥ 50`, which is the regime where the threshold is governed by the fabrication floor rather than sampling noise. At that point, if public/private SPS differ by more than 0.05, either the submitter "knew" the public answers or there's a legitimate distribution shift — in either case, human adjudication is required, and the right default is to reject until a reviewer overrides.

**`ANOMALY_NO_REFUSAL` → KEEP AS WARNING, AND CURRENTLY NOT DISPATCHED.**
The docstring in `anomaly.py:278` already explains: every provider prompt in `providers/` ends with `"Respond with ONLY the letter of your choice"`, so `model_refusal_rate ≡ 0` is the *architectural* baseline for every legitimate submission. Promoting would false-positive 100% of current legitimate runs. The right sequencing is: (a) add a refusal-capable prompt variant, (b) characterize the legitimate refusal-rate distribution, (c) reintroduce the detector, (d) then debate severity. Until then, leave undispatched.

**`ANOMALY_PEER_OUTLIER` → KEEP AS WARNING.**
The 0.15 delta threshold is principled but this detector fires on a correlated set of issues (claimed-model mismatch, temperature drift, prompt drift, seed variance) that are not all gaming. A submitter running the same model with a different prompt template will trip it legitimately. It's a good signal for a reviewer's attention but a poor auto-reject trigger.

**`RAW_RESPONSES_*` → KEEP AS WARNING UNTIL SCHEMA-v2, THEN ERROR.**
Existing leaderboard files predate this field. Graduating now would invalidate the published leaderboard. Correct path: version bump (schema_version → 2), backfill existing runs, then promote on v2 only.

**`REPRO_*` → KEEP AS WARNING.**
Missing reproducibility metadata is a documentation problem, not a fabrication signal. Noisy to promote.

### 2.3 Summary recommendation table

| Code                   | Current | Recommend                                 | Effort | Notes                                                |
| ---------------------- | ------- | ----------------------------------------- | ------ | ---------------------------------------------------- |
| `ANOMALY_PERFECTION`   | WARN    | **ERROR at n ≥ 25**                        | S      | Strong evidence; threshold already far below noise   |
| `HOLDOUT_DIVERGENCE`   | WARN    | **ERROR at min_side ≥ 50**                 | S      | Best signal we have; threshold adaptive              |
| `ANOMALY_NO_REFUSAL`   | WARN (not dispatched) | KEEP / re-architect first   | L      | Needs refusal-capable prompt first                   |
| `ANOMALY_PEER_OUTLIER` | WARN    | KEEP                                      | —      | Too many legitimate causes                           |
| `RAW_RESPONSES_*`      | WARN    | KEEP → ERROR on schema-v2                  | M      | Ecosystem migration                                  |
| `REPRO_*`              | WARN    | KEEP                                      | —      | Documentation, not fabrication                       |

---

## 3. Near-copy detector — closing the public-distribution shortcut

### 3.1 The attack

A submitter scrapes the public leaderboard or dataset file, obtains `human_distribution` for every public key (80% of the dataset), adds zero-mean noise `ε ~ U(−0.02, 0.02)` to each probability, renormalizes, and sets `model_distribution = human + ε`. They fabricate private-subset distributions by sampling a Dirichlet around the marginal mean. What happens under current validators?

- **Tier 1 schema / bounds / distributions** — pass (distributions are valid).
- **Tier 1 `QSET_HASH`** — pass (they used real keys).
- **Tier 1 `HOLDOUT_MISSING_PRIVATE` / `HOLDOUT_COVERAGE`** — pass (they generated private rows).
- **Tier 1 `HOLDOUT_DIVERGENCE`** — *the attacker's private rows are drawn from the marginal, not the true per-question private distribution.* Expected public SPS ≈ 0.98; expected private SPS ≈ 0.75 (the marginal-against-true-distribution baseline). Delta ≈ 0.23 → **flagged** (but only WARNING today).
- **Tier 2 recompute** — pass (they computed JSD/tau from their own distributions).
- **Tier 3 `ANOMALY_PERFECTION`** — on the *full* dataset, `mean_jsd ≈ 0.12` (public ~0.01, private ~0.25 averaged) which is *above* the 0.005 threshold. **Does not fire.** If we restrict to the public subset, mean would be ~0.01 — firing — but we don't currently slice the perfection check by subset.
- **Tier 3 peer outlier** — may or may not fire depending on peer availability.

**So the bypass is real:** with current Tier-3-as-WARNING configuration, `HOLDOUT_DIVERGENCE` would be the only tripwire and it's non-blocking. The paper's key insight (normalization / rounding / warning-only gates are insufficient) applies directly.

### 3.2 Proposed detector: `ANOMALY_NEAR_COPY_PUBLIC`

**Definition.** On holdout-enabled datasets, compute per-question JSD between `model_distribution` and `human_distribution` *restricted to the public subset*. Let:

```
jsd_public = [q.jsd for q in per_question if not is_private_holdout(dataset, q.key)]
mean_jsd_public = mean(jsd_public)
std_jsd_public  = std(jsd_public)
```

Flag when *both* of the following hold, at production N:

1. `mean_jsd_public < NEAR_COPY_MEAN_JSD` — default **0.02**
2. `std_jsd_public  < NEAR_COPY_STD_JSD`  — default **0.03**

Severity: **ERROR** if `n_public ≥ 50` and both conditions hold; **WARNING** otherwise.

**Rationale for thresholds.** We have real public-subset distributions across 4 providers in `leaderboard-results/`. Empirically, the best-performing real model's public-subset `mean_jsd` is in the `[0.08, 0.20]` range with `std_jsd` in `[0.10, 0.22]`. A near-copy with `ε ~ U(−0.02, 0.02)` produces `mean_jsd ≈ 0.006` and `std_jsd ≈ 0.004`. The thresholds 0.02 / 0.03 leave a factor of 4× headroom above the attack floor and a factor of 4× below the legitimate floor — clean separation.

**Why both mean AND std (not OR).** Unlike `ANOMALY_PERFECTION` (which uses OR because either alone is a smoking gun for total copy), a partial attacker can drive either one low on its own through a clever construction — e.g., constant-offset copying pins std low without touching mean. But driving *both* low means the per-question dispersion is tight and uniformly small — the fingerprint of a noise-floor attack. AND reduces false-positive risk on genuinely-good real models.

**Interaction with `HOLDOUT_DIVERGENCE`.** The two detectors are complementary:

- `HOLDOUT_DIVERGENCE` catches *asymmetric* attacks (good public, poor private).
- `ANOMALY_NEAR_COPY_PUBLIC` catches *implausibly good public* regardless of what the attacker did on private.

A sophisticated attacker could match public *and* fabricate plausible private rows by Dirichlet-sampling from the true marginal — but they don't have the per-question private ground truth, so public JSD will still be suspiciously low relative to private. Our deepest defense is the *conjunction* of both checks.

**Edge case.** A genuinely-better-than-human model *could* in principle hit `mean_jsd_public ≈ 0.02`. We have never seen this in real data (the best provider run lives at ~0.08). If it ever happens, the fallback is human review — the detector ERRORs, the submitter appeals, a reviewer looks. This is the correct failure mode: err toward false positives on a leaderboard, let humans override.

### 3.3 Extension: constant-offset fingerprint

A meta-attack worth naming: `model[opt] = human[opt] + c` for option-independent constant `c`, renormalized. This produces `std_jsd` much tighter than natural sampling noise. A cheap adjacent detector:

```
per_question_jsd_rank_correlation = spearman(jsd, len(options))
```

If JSD correlates >0.9 with the number of options, the submitter is likely producing JSD deterministically from distribution shape rather than stochastic sampling. This is a second-pass check to file separately.

---

## 4. Holdout split evaluation

### 4.1 Current design

- **Fraction:** 20% private / 80% public.
- **Mechanism:** SHA-256(`base_dataset_name + ":" + key`) mod 100 < 20.
- **Rotation:** None. The hash is static.
- **Datasets:** 8 (eurobarometer, globalopinionqa, gss, michigan, ntia, opinionsqa, subpop, wvs).

### 4.2 Statistical-power analysis

For `HOLDOUT_DIVERGENCE` to be a credible fabrication detector, we need the power to distinguish the null (honest submission with public≈private SPS) from the fabrication alternative (public SPS − private SPS ≥ 0.2) at our working threshold (0.05).

SPS is a bounded-variance sample mean. Approximate per-question SPS variance in the real leaderboard is σ² ≈ 0.05 (observed across haiku-4-5, sonnet-4-6, random, majority). The standard error on a subset of size n is σ/√n ≈ 0.22/√n.

| Split | OpinionsQA (≈1500q) | MichiganConsumer (≈200q) | SubPOP (≈300q) |
| ----- | ------------------- | ------------------------ | -------------- |
| 20% private | n_priv=300, SE=0.013 | n_priv=40, SE=0.035 | n_priv=60, SE=0.028 |
| 30% private | n_priv=450, SE=0.010 | n_priv=60, SE=0.028 | n_priv=90, SE=0.023 |
| 40% private | n_priv=600, SE=0.009 | n_priv=80, SE=0.025 | n_priv=120, SE=0.020 |
| 50% private | n_priv=750, SE=0.008 | n_priv=100, SE=0.022 | n_priv=150, SE=0.018 |

At the 0.05 threshold, 20% private is already >3σ at OpinionsQA scale. On the smaller datasets, 20% private gives <2σ resolution — a fabrication delta of 0.10 would blur into honest-noise. Moving to 40% would push Michigan/SubPOP from ~1.5σ to ~2σ resolution — a real but modest gain — at the cost of shrinking the public score (the thing we report on the leaderboard) by ~25%.

**My recommendation: keep 20% on large datasets (N ≥ 500), move to 40% on small (N < 200).** Concretely:

- OpinionsQA, WVS, GSS → stay at 20%.
- Michigan, NTIA, Eurobarometer (slice-dependent) → 40%.
- SubPOP, GlobalOpinionQA → 30% (middle ground).

This preserves public leaderboard statistical identity on the headline benchmark while increasing fabrication resolution where we're weakest. Heterogeneous fractions can be encoded per-dataset in `HOLDOUT_ENABLED_DATASETS` (promote to a `dict[str, int]`).

### 4.3 Rotation

The Berkeley paper recommends rotating splits. The operational concern is that rotating re-exposes previously-private keys to the public leaderboard's human distribution — we lose anti-contamination value for those keys permanently. But there's a cheap, correct form of rotation:

**Salt-based rotation.** Introduce a global salt `HOLDOUT_SALT` (e.g., `"2026Q2"`) into the hash: `SHA-256(salt + ":" + base_dataset_name + ":" + key)`. When we rotate the salt (say, quarterly):

- Previously-private keys that *become public* have their `human_distribution` republished. This is acceptable because the benchmark version bumps, and prior submissions on the old salt are labeled `schema_version < N` and archived.
- Previously-public keys that *become private* now participate in fabrication detection on a fresh population, forcing cheaters to maintain fresh answer keys.
- Old submissions remain valid under the old salt for historical comparison.

This mirrors the "version bump" discipline already in the codebase. The cost is: we can't directly compare a Q1 submission to a Q2 submission without re-scoring — but that's already true whenever the question set changes, so it's a non-novel constraint.

**My recommendation: implement salt rotation at a quarterly cadence, starting 2026-Q3.** Give submitters 30 days' notice before each rotation and retain the old salt's evaluation pathway for one rotation cycle.

### 4.4 Adversary model for holdout

Worth stating explicitly: the hash construction (`sha256(base + ":" + key)`) is **not a cryptographic commitment** — the attacker can trivially compute it themselves. The 80/20 split is not secret; what is secret is the `human_distribution` on private keys. An attacker who compromises the private answer key (by repo clone, by social engineering, by insider access) defeats the whole holdout regardless of rotation cadence. Defenses here are operational (limit who has access to raw private distributions, audit access logs) not cryptographic.

---

## 5. Adversarial test suite

### 5.1 Objective

Convert the validation pipeline from "no known false negatives" to "measured true-positive rate" by maintaining a directory of fabricated submissions that **must** fail validation. The suite runs in CI. When a new detector is proposed, it must be evaluated against the full suite before merge. When a detector is tuned (threshold changes), the suite must still pass.

### 5.2 Location & format

```
tests/adversarial/
  fixtures/
    pure_copy.json              # 100% human copy + noise
    public_copy_fake_private.json   # public copied, private marginal-sampled
    model_swap_sonnet_as_haiku.json # claim haiku, run sonnet
    constant_offset.json        # model = human + 0.05 per option
    zero_jsd.json               # all JSD set to 0
    impossible_sps.json         # sps > 1
    fabricated_refusal.json     # refusal=0 with refusing dataset
    peer_mismatch.json          # deviant vs same-family peers
  expected.json                 # map from fixture -> required error codes
  test_adversarial_suite.py
```

### 5.3 The 8 fabrications (at least)

| # | Name | Attack | Expected codes (MUST fire) |
| - | ---- | ------ | -------------------------- |
| 1 | `pure_copy` | `model = human` on every question | `ANOMALY_PERFECTION`, `HOLDOUT_DIVERGENCE` (if holdout dataset) |
| 2 | `near_pure_copy` | `model = human + ε`, ε ~ U(−0.02,0.02) | `ANOMALY_NEAR_COPY_PUBLIC` (new), `ANOMALY_PERFECTION` |
| 3 | `public_copy_fake_private` | public copied, private from marginal Dirichlet | `ANOMALY_NEAR_COPY_PUBLIC` (new), `HOLDOUT_DIVERGENCE` (≥0.05) |
| 4 | `constant_offset` | `model[opt] = human[opt] + c` renormalized | `ANOMALY_NEAR_COPY_PUBLIC` via low std; constant-offset detector |
| 5 | `impossible_bounds` | `sps = 1.2`, `mean_jsd = -0.1` | `BOUNDS_RANGE` (3 hits) |
| 6 | `lied_aggregate` | per-question correct, aggregate fabricated | `AGG_MEAN_JSD`, `AGG_MEAN_TAU`, `AGG_COMPOSITE` |
| 7 | `zero_private_rows` | 300 public rows, 0 private (holdout dataset) | `HOLDOUT_MISSING_PRIVATE` |
| 8 | `wrong_keys` | fabricated rows use non-dataset keys | `QSET_HASH_DATASET` |
| 9 | `null_agent` | uniform distribution everywhere | NOT an error (uniform is a valid baseline), but SPS must be in the "random baseline" band — assertion test, not validator test |
| 10 | `raw_response_desync` | raw_text says "B" but `selected_option = "A"` | `RAW_RESPONSES_MODE` |

The suite must assert *both* directions: expected codes fire, and *unexpected* codes do not fire. This is how detector tuning can be regression-tested without manual review.

### 5.4 The "null agent" discipline

Per the Berkeley paper's checklist ("Run a null agent that takes no actions. If it's not zero, something is wrong."), SynthBench's equivalent is our `random` and `majority` baselines. We should:

1. Track their SPS over time — any *upward* drift in baseline SPS on a stable dataset is a sign that the scoring function has developed a systematic bias.
2. Assert `random_baseline_sps < 0.70` and `majority_baseline_sps < 0.85` in CI; promote to test failure if broken.
3. Publish these values on the methodology page as "the floor any benchmark-serious model must clear."

### 5.5 Harness

The adversarial suite runs under `pytest tests/adversarial/` and is part of the standard CI gate. Each fixture is a static JSON file checked into the repo — deterministic, no fuzzing, no flaky detectors. Fuzz tests (random noise around a legitimate submission) go elsewhere; this suite is a **known-bad acceptance gate**.

---

## 6. Methodology page language (draft)

For publication at `synthbench.org/methodology`, after the scoring/SPS section. Citations are numbered — the BibTeX entry goes at the end.

---

### Anti-gaming and adversarial robustness

SynthBench takes the threat of benchmark gaming seriously. Our threat model and defences are informed directly by recent adversarial analyses of AI benchmarks — in particular, Wang et al. (UC Berkeley, 2026) [¹], who broke eight widely-used agent benchmarks to near-perfect scores *without solving a single task*.

SynthBench is a submission-artifact benchmark — participants submit a JSON file, we score it — so attacks that assume a co-resident evaluating agent (sandbox escapes, `eval()` on agent input, binary trojan wrappers, LLM-judge prompt injection) are structurally inapplicable. But the *pattern* behind Wang et al.'s attacks — attack the evaluator, not the task — applies to us, and we have designed three lines of defence.

**1. Private holdout.** Each holdout-enabled dataset is deterministically partitioned into a public 80% (whose human-response distributions are published on the leaderboard) and a private 20% (whose distributions are withheld). A submitter who copies published distributions has no signal for the private subset, so their public-vs-private SPS must diverge. A separation larger than 0.05 on production-scale submissions is flagged as a validation error. The split is keyed on a versioned salt rotated quarterly so that the partition is not permanently fixed.

**2. Tiered statistical validation.** Every submission runs through three progressively deeper checks. Tier 1 verifies schema, bounds, and distribution validity. Tier 2 recomputes JSD, Kendall's τ, and composite parity from per-question distributions and rejects any submission whose reported aggregates do not reconcile with its claimed per-question data. Tier 3 applies statistical-anomaly detectors that compare the submission against the distribution of legitimate runs: *implausibly perfect* per-question JSD, *suspiciously-close-to-public-human* distributions, and *same-family peer deviation*.

**3. Adversarial regression suite.** Our test harness maintains a set of fabricated submissions that *must* fail validation — pure answer-key copies, public-copy-with-fabricated-private attacks, constant-offset noise attacks, aggregate inflation, claimed-model-swap. New detectors are evaluated against this suite before merge, and any tuning of existing detector thresholds must keep the suite passing. The suite is versioned alongside the validator.

Following Wang et al.'s recommendation, we additionally maintain baseline "null agent" submissions — uniform-random and majority-class baselines — and track their composite parity over time. An increase in the floor any model must clear to appear non-trivial is itself a scoring-function bug, not a success.

We intend this posture to be *conservative*. The correct failure mode for a scientific leaderboard is to reject a legitimate superhuman submission for human review, not to accept a fabricated one. Submitters whose runs are flagged can appeal, but the null hypothesis at validation time is that suspicious-looking data was fabricated.

---

**References**

[¹] Wang, Y., Mang, K., Cheung, T., Sen, S., & Song, D. (2026). *How We Broke Top AI Agent Benchmarks*. UC Berkeley RDI. <https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/>

---

## 7. Effort estimates & bead plan

Converted to bead proposals (for mayor to schedule):

| Bead | Title | Effort | Priority | Depends on |
| ---- | ----- | ------ | -------- | ---------- |
| A | Promote `ANOMALY_PERFECTION` to ERROR at n≥25 | S | P0 | — |
| B | Promote `HOLDOUT_DIVERGENCE` to ERROR at min_side≥50 | S | P0 | — |
| C | Implement `ANOMALY_NEAR_COPY_PUBLIC` detector | M | P0 | — |
| D | Per-dataset holdout fractions (20/30/40 by size) | S | P1 | — |
| E | Salt-based holdout rotation (quarterly) | M | P1 | — |
| F | Adversarial test suite — 10 fixtures + harness | M | P0 | A, B, C |
| G | Methodology page / anti-gaming section | S | P1 | — |
| H | Constant-offset fingerprint detector | S | P2 | C |
| I | Baseline SPS drift CI assertion | XS | P2 | F |
| J | Schema-v2 + raw_responses graduation to ERROR | L | P2 | F |

Legend: S = ≤1 day, M = 1–3 days, L = 3–7 days, XS = ≤2 hours.

---

## 8. Open questions for mayor / architect

1. **Appeal process.** If we promote `HOLDOUT_DIVERGENCE` to ERROR, what's the escalation path for a flagged honest submitter? Propose: a `--override-flag=<reviewer_id>` on the validator CLI, with the override logged to the leaderboard entry.
2. **Schema v2 timing.** Graduating raw-responses to ERROR requires bumping the schema version. Worth coordinating with the leaderboard UI milestone.
3. **Salt rotation cadence.** Quarterly is a first guess. Should it be tied to benchmark version releases instead (one salt per release)?
4. **Private distribution access policy.** Who has read access to the private `human_distribution` files today, and is that documented anywhere? A compromise here defeats every detector in this document.

End.
