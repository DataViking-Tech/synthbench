#!/usr/bin/env python3
"""Optimal-temperature ensemble blending experiment for SynthBench.

Compares two ensemble strategies on the SAME 100 questions:
  1. DEFAULT-TEMP ensemble: each model at its API default temperature
  2. OPTIMAL-TEMP ensemble: each model at its empirically-best temperature

Models:
  - Haiku:       default vs t=0.85
  - Gemini:      default vs t=2.0
  - GPT-4o-mini: default vs t=1.0

Pure arithmetic on existing result files -- NO API calls.
"""

import json
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.spatial.distance import jensenshannon
from scipy.stats import kendalltau


# ---------------------------------------------------------------------------
# Metrics (matching synthbench.metrics exactly)
# ---------------------------------------------------------------------------


def jensen_shannon_divergence(p: dict[str, float], q: dict[str, float]) -> float:
    """JSD between two distributions. Returns value in [0, 1] (base-2 log)."""
    keys = sorted(set(p) | set(q))
    p_vec = np.array([p.get(k, 0.0) for k in keys], dtype=np.float64)
    q_vec = np.array([q.get(k, 0.0) for k in keys], dtype=np.float64)
    p_vec = np.maximum(p_vec, 0.0)
    q_vec = np.maximum(q_vec, 0.0)
    p_sum = p_vec.sum()
    q_sum = q_vec.sum()
    if p_sum == 0 or q_sum == 0:
        return 1.0
    p_vec /= p_sum
    q_vec /= q_sum
    jsd = jensenshannon(p_vec, q_vec, base=2) ** 2
    return float(jsd)


def kendall_tau_b(p: dict[str, float], q: dict[str, float]) -> float:
    """Kendall's tau-b between two distributions."""
    keys = sorted(set(p) | set(q))
    if len(keys) < 2:
        return 0.0
    p_vals = [p.get(k, 0.0) for k in keys]
    q_vals = [q.get(k, 0.0) for k in keys]
    tau, _ = kendalltau(p_vals, q_vals, variant="b")
    if tau != tau:  # NaN
        return 0.0
    return float(tau)


def sps_from_components(
    mean_jsd: float, mean_tau: float, p_refuse: float = 1.0
) -> float:
    """SPS = mean(p_dist, p_rank, p_refuse)."""
    p_dist = 1.0 - mean_jsd
    p_rank = (1.0 + mean_tau) / 2.0
    return (p_dist + p_rank + p_refuse) / 3.0


# ---------------------------------------------------------------------------
# File selection
# ---------------------------------------------------------------------------

RESULTS_DIR = Path(__file__).parent / "leaderboard-results"

# --- Optimal-temperature file patterns (all n=100 on OpinionsQA) ---
OPTIMAL_TEMP_PATTERNS = {
    "Haiku": {
        "opinionsqa": lambda f: (
            "claude-haiku" in f
            and "synthpanel" in f
            and " t=0.85" in f
            and " tpl=" not in f
        ),
    },
    "Gemini": {
        "opinionsqa": lambda f: (
            "gemini" in f and "synthpanel" in f and " t=2.0" in f and " tpl=" not in f
        ),
    },
    "GPT-4o-mini": {
        "opinionsqa": lambda f: (
            "gpt-4o-mini" in f
            and "synthpanel" in f
            and " t=1.0" in f
            and " tpl=" not in f
        ),
    },
}

# --- Default-temperature file patterns (no t= in filename) ---
DEFAULT_TEMP_PATTERNS = {
    "Haiku": lambda f: (
        "claude-haiku" in f
        and "synthpanel" in f
        and " t=" not in f
        and " tpl=" not in f
    ),
    "Gemini": lambda f: (
        "gemini" in f and "synthpanel" in f and " t=" not in f and " tpl=" not in f
    ),
    "GPT-4o-mini": lambda f: (
        "gpt-4o-mini" in f and "synthpanel" in f and " t=" not in f and " tpl=" not in f
    ),
}


def find_best_file(dataset: str, model_name: str, matcher) -> Optional[Path]:
    """Find the file with highest SPS for a model/dataset/matcher.

    Among n=100 files: pick highest SPS.
    Among larger files: pick largest n_questions (for default-temp baselines).
    Filters out degenerate (uniform) distributions.
    """
    candidates = []
    for f in RESULTS_DIR.glob(f"{dataset}_*.json"):
        fname = f.name
        if not matcher(fname):
            continue
        try:
            data = json.loads(f.read_text())
            n_q = data["aggregate"]["n_questions"]
            sps = data["scores"]["sps"]
            # Check for non-uniform
            pq = data.get("per_question", [])
            if pq:
                jsds = [q["jsd"] for q in pq]
                jsd_var = np.var(jsds)
                if jsd_var < 1e-10:
                    continue
            candidates.append((n_q, sps, f))
        except (KeyError, json.JSONDecodeError):
            continue

    if not candidates:
        return None
    # Pick highest SPS, break ties by largest n_questions
    candidates.sort(key=lambda x: (x[1], x[0]), reverse=True)
    return candidates[0][2]


# ---------------------------------------------------------------------------
# Blending logic
# ---------------------------------------------------------------------------


def blend_distributions(
    dists: list[dict[str, float]], weights: list[float]
) -> dict[str, float]:
    """Weighted average of distributions."""
    all_keys = set()
    for d in dists:
        all_keys.update(d.keys())
    total_w = sum(weights)
    result = {}
    for k in all_keys:
        val = sum(w * d.get(k, 0.0) for d, w in zip(dists, weights))
        result[k] = val / total_w
    return result


def compute_blend_metrics(
    per_q_by_model: dict,
    common_keys: list[str],
    model_names: list[str],
    weights: list[float],
) -> dict:
    """Compute JSD/tau for a blend on the common question set."""
    jsds = []
    taus = []
    for key in common_keys:
        human_dist = per_q_by_model[model_names[0]][key]["human_distribution"]
        model_dists = [
            per_q_by_model[mn][key]["model_distribution"] for mn in model_names
        ]
        blended = blend_distributions(model_dists, weights)
        jsds.append(jensen_shannon_divergence(human_dist, blended))
        taus.append(kendall_tau_b(human_dist, blended))
    mean_jsd = float(np.mean(jsds))
    mean_tau = float(np.mean(taus))
    return {
        "mean_jsd": mean_jsd,
        "mean_tau": mean_tau,
        "sps": sps_from_components(mean_jsd, mean_tau),
        "per_q_jsds": jsds,
        "per_q_taus": taus,
    }


def compute_single_model_metrics(
    per_q: dict, common_keys: list[str], p_refuse: float = 1.0
) -> dict:
    """Compute metrics for a single model on the common question set."""
    jsds = []
    taus = []
    for key in common_keys:
        q = per_q[key]
        jsds.append(q["jsd"])
        taus.append(q["kendall_tau"])
    mean_jsd = float(np.mean(jsds))
    mean_tau = float(np.mean(taus))
    return {
        "mean_jsd": mean_jsd,
        "mean_tau": mean_tau,
        "sps": sps_from_components(mean_jsd, mean_tau, p_refuse),
        "per_q_jsds": jsds,
        "per_q_taus": taus,
    }


# ---------------------------------------------------------------------------
# Oracle blend
# ---------------------------------------------------------------------------


def compute_oracle(
    per_q_by_model: dict, common_keys: list[str], model_names: list[str]
) -> dict:
    """Best single model per question (upper bound)."""
    jsds = []
    taus = []
    picks = {mn: 0 for mn in model_names}
    for key in common_keys:
        human_dist = per_q_by_model[model_names[0]][key]["human_distribution"]
        best_jsd = float("inf")
        best_mn = model_names[0]
        for mn in model_names:
            mdist = per_q_by_model[mn][key]["model_distribution"]
            jsd = jensen_shannon_divergence(human_dist, mdist)
            if jsd < best_jsd:
                best_jsd = jsd
                best_mn = mn
        picks[best_mn] += 1
        jsds.append(best_jsd)
        best_dist = per_q_by_model[best_mn][key]["model_distribution"]
        taus.append(kendall_tau_b(human_dist, best_dist))
    mean_jsd = float(np.mean(jsds))
    mean_tau = float(np.mean(taus))
    return {
        "mean_jsd": mean_jsd,
        "mean_tau": mean_tau,
        "sps": sps_from_components(mean_jsd, mean_tau),
        "picks": picks,
    }


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------


def run_optimal_temp_experiment():
    """Compare default-temp vs optimal-temp ensemble blending."""

    dataset = "opinionsqa"
    model_names = ["Haiku", "Gemini", "GPT-4o-mini"]

    print(f"{'=' * 80}")
    print("OPTIMAL-TEMPERATURE ENSEMBLE BLENDING EXPERIMENT")
    print(f"{'=' * 80}")
    print(f"Dataset: {dataset}")
    print()

    # -----------------------------------------------------------------------
    # 1. Load optimal-temp files (n=100, specific temperatures)
    # -----------------------------------------------------------------------
    print("--- Loading optimal-temperature files ---")
    opt_files = {}
    opt_data = {}
    for mn in model_names:
        matcher = OPTIMAL_TEMP_PATTERNS[mn][dataset]
        fpath = find_best_file(dataset, mn, matcher)
        if fpath is None:
            print(f"  ERROR: No optimal-temp file found for {mn}")
            return
        data = json.loads(fpath.read_text())
        opt_files[mn] = fpath
        opt_data[mn] = data
        n_q = data["aggregate"]["n_questions"]
        sps = data["scores"]["sps"]
        print(f"  {mn}: {fpath.name}")
        print(f"    n_q={n_q}, SPS={sps:.6f}")

    # Get common keys for optimal-temp set
    opt_per_q = {}
    for mn in model_names:
        opt_per_q[mn] = {q["key"]: q for q in opt_data[mn]["per_question"]}

    opt_common = sorted(
        set(opt_per_q["Haiku"])
        & set(opt_per_q["Gemini"])
        & set(opt_per_q["GPT-4o-mini"])
    )
    print(f"\n  Common questions (optimal-temp): {len(opt_common)}")

    # -----------------------------------------------------------------------
    # 2. Load default-temp files (largest n_q that covers all 100 questions)
    # -----------------------------------------------------------------------
    print("\n--- Loading default-temperature files ---")
    def_files = {}
    def_data = {}
    for mn in model_names:
        matcher = DEFAULT_TEMP_PATTERNS[mn]
        # Find a file that covers all 100 questions
        best_f = None
        best_sps = -1.0
        for f in RESULTS_DIR.glob(f"{dataset}_*.json"):
            if not matcher(f.name):
                continue
            try:
                d = json.loads(f.read_text())
                keys = set(q["key"] for q in d["per_question"])
                if not set(opt_common).issubset(keys):
                    continue
                # Check non-uniform
                pq_jsds = [q["jsd"] for q in d["per_question"]]
                if np.var(pq_jsds) < 1e-10:
                    continue
                sps = d["scores"]["sps"]
                if sps > best_sps:
                    best_sps = sps
                    best_f = f
            except (KeyError, json.JSONDecodeError):
                continue
        if best_f is None:
            print(
                f"  ERROR: No default-temp file covers all {len(opt_common)} "
                f"questions for {mn}"
            )
            return
        data = json.loads(best_f.read_text())
        def_files[mn] = best_f
        def_data[mn] = data
        n_q = data["aggregate"]["n_questions"]
        sps = data["scores"]["sps"]
        print(f"  {mn}: {best_f.name}")
        print(f"    n_q={n_q} (full), SPS={sps:.6f} (full)")

    # Build per-question lookups for default-temp, restricted to common keys
    def_per_q = {}
    for mn in model_names:
        def_per_q[mn] = {q["key"]: q for q in def_data[mn]["per_question"]}

    # -----------------------------------------------------------------------
    # 3. Compute single-model metrics on the 100 common questions
    # -----------------------------------------------------------------------
    print(f"\n{'=' * 80}")
    print(f"SINGLE-MODEL RESULTS (on {len(opt_common)} common questions)")
    print(f"{'=' * 80}")
    header = (
        f"  {'Model':<14} {'Regime':<14} {'Mean JSD':>10} {'Mean tau':>10} {'SPS':>10}"
    )
    print(header)
    print(f"  {'-' * 14} {'-' * 14} {'-' * 10} {'-' * 10} {'-' * 10}")

    single_stats = {"default": {}, "optimal": {}}
    for mn in model_names:
        for regime, pq in [("default", def_per_q), ("optimal", opt_per_q)]:
            # Use p_refuse from the full-file scores
            src_data = def_data[mn] if regime == "default" else opt_data[mn]
            p_refuse = src_data["scores"].get("p_refuse", 1.0)
            stats = compute_single_model_metrics(pq[mn], opt_common, p_refuse)
            single_stats[regime][mn] = stats
            print(
                f"  {mn:<14} {regime:<14} {stats['mean_jsd']:10.6f} "
                f"{stats['mean_tau']:10.6f} {stats['sps']:10.6f}"
            )

    # -----------------------------------------------------------------------
    # 4. Compute ensemble blends
    # -----------------------------------------------------------------------
    equal_w = [1.0, 1.0, 1.0]

    def_equal = compute_blend_metrics(def_per_q, opt_common, model_names, equal_w)
    opt_equal = compute_blend_metrics(opt_per_q, opt_common, model_names, equal_w)

    # Also compute ORACLE for both regimes
    def_oracle = compute_oracle(def_per_q, opt_common, model_names)
    opt_oracle = compute_oracle(opt_per_q, opt_common, model_names)

    # SCORE_PROP blend (weight by single-model SPS on these questions)
    def_sp_w = [single_stats["default"][mn]["sps"] for mn in model_names]
    opt_sp_w = [single_stats["optimal"][mn]["sps"] for mn in model_names]
    def_score_prop = compute_blend_metrics(def_per_q, opt_common, model_names, def_sp_w)
    opt_score_prop = compute_blend_metrics(opt_per_q, opt_common, model_names, opt_sp_w)

    # INV_JSD blend
    def_inv_w = [
        1.0 / max(single_stats["default"][mn]["mean_jsd"], 0.001) for mn in model_names
    ]
    opt_inv_w = [
        1.0 / max(single_stats["optimal"][mn]["mean_jsd"], 0.001) for mn in model_names
    ]
    def_inv_jsd = compute_blend_metrics(def_per_q, opt_common, model_names, def_inv_w)
    opt_inv_jsd = compute_blend_metrics(opt_per_q, opt_common, model_names, opt_inv_w)

    # -----------------------------------------------------------------------
    # 5. Comparison table
    # -----------------------------------------------------------------------
    print(f"\n{'=' * 80}")
    print("ENSEMBLE COMPARISON: Default-Temp vs Optimal-Temp")
    print(f"({len(opt_common)} common questions, OpinionsQA)")
    print(f"{'=' * 80}")

    rows = [
        (
            "Best Single (def)",
            max(single_stats["default"].values(), key=lambda s: s["sps"]),
        ),
        (
            "Best Single (opt)",
            max(single_stats["optimal"].values(), key=lambda s: s["sps"]),
        ),
        ("EQUAL (default)", def_equal),
        ("EQUAL (optimal)", opt_equal),
        ("SCORE_PROP (def)", def_score_prop),
        ("SCORE_PROP (opt)", opt_score_prop),
        ("INV_JSD (default)", def_inv_jsd),
        ("INV_JSD (optimal)", opt_inv_jsd),
        ("ORACLE (default)", def_oracle),
        ("ORACLE (optimal)", opt_oracle),
    ]

    header = f"  {'Method':<22} {'Mean JSD':>10} {'Mean tau':>10} {'SPS':>10}"
    print(header)
    print(f"  {'-' * 22} {'-' * 10} {'-' * 10} {'-' * 10}")
    for label, stats in rows:
        print(
            f"  {label:<22} {stats['mean_jsd']:10.6f} "
            f"{stats['mean_tau']:10.6f} {stats['sps']:10.6f}"
        )

    # -----------------------------------------------------------------------
    # 6. Delta table (optimal - default for each blend method)
    # -----------------------------------------------------------------------
    print(f"\n{'=' * 80}")
    print("SPS DELTAS: Optimal-Temp minus Default-Temp")
    print(f"{'=' * 80}")
    delta_rows = [
        (
            "Best Single",
            max(single_stats["optimal"].values(), key=lambda s: s["sps"])["sps"]
            - max(single_stats["default"].values(), key=lambda s: s["sps"])["sps"],
        ),
        ("EQUAL blend", opt_equal["sps"] - def_equal["sps"]),
        ("SCORE_PROP", opt_score_prop["sps"] - def_score_prop["sps"]),
        ("INV_JSD", opt_inv_jsd["sps"] - def_inv_jsd["sps"]),
        ("ORACLE", opt_oracle["sps"] - def_oracle["sps"]),
    ]
    print(f"  {'Method':<22} {'SPS Delta':>12} {'Pct Points':>12}")
    print(f"  {'-' * 22} {'-' * 12} {'-' * 12}")
    for label, delta in delta_rows:
        sign = "+" if delta >= 0 else ""
        print(f"  {label:<22} {sign}{delta:11.6f} {sign}{delta * 100:10.2f}pp")

    # -----------------------------------------------------------------------
    # 7. Per-question analysis: EQUAL optimal vs EQUAL default
    # -----------------------------------------------------------------------
    print(f"\n{'=' * 80}")
    print("PER-QUESTION ANALYSIS: EQUAL(optimal) vs EQUAL(default)")
    print(f"{'=' * 80}")
    eq_opt_jsds = opt_equal["per_q_jsds"]
    eq_def_jsds = def_equal["per_q_jsds"]
    improved = sum(1 for a, b in zip(eq_opt_jsds, eq_def_jsds) if a < b)
    worsened = sum(1 for a, b in zip(eq_opt_jsds, eq_def_jsds) if a > b)
    tied = sum(1 for a, b in zip(eq_opt_jsds, eq_def_jsds) if abs(a - b) < 1e-10)
    n = len(opt_common)
    print(f"  JSD improved (opt < def): {improved}/{n} ({100 * improved / n:.1f}%)")
    print(f"  JSD worsened (opt > def): {worsened}/{n} ({100 * worsened / n:.1f}%)")
    print(f"  JSD tied:                 {tied}/{n} ({100 * tied / n:.1f}%)")

    jsd_deltas = [a - b for a, b in zip(eq_opt_jsds, eq_def_jsds)]
    print(
        f"  Mean JSD delta: {np.mean(jsd_deltas):+.6f} (negative = optimal is better)"
    )
    print(f"  Median JSD delta: {np.median(jsd_deltas):+.6f}")

    # Oracle picks comparison
    print(f"\n  ORACLE picks (default): {def_oracle.get('picks', {})}")
    print(f"  ORACLE picks (optimal): {opt_oracle.get('picks', {})}")

    # -----------------------------------------------------------------------
    # 8. Check SubPOP and GlobalOpinionQA availability
    # -----------------------------------------------------------------------
    print(f"\n{'=' * 80}")
    print("ADDITIONAL DATASET AVAILABILITY CHECK")
    print(f"{'=' * 80}")
    for ds in ["subpop", "globalopinionqa"]:
        print(f"\n  {ds}:")
        for mn in model_names:
            if ds in OPTIMAL_TEMP_PATTERNS.get(mn, {}):
                matcher = OPTIMAL_TEMP_PATTERNS[mn][ds]
                f = find_best_file(ds, mn, matcher)
                if f:
                    data = json.loads(f.read_text())
                    print(
                        f"    {mn} optimal-temp: {f.name} "
                        f"(n_q={data['aggregate']['n_questions']})"
                    )
                else:
                    print(f"    {mn} optimal-temp: NOT FOUND")
            else:
                # Try anyway with the OpinionsQA matcher as fallback
                found = False
                for f in RESULTS_DIR.glob(f"{ds}_*.json"):
                    if " t=" in f.name and "synthpanel" in f.name:
                        if (
                            (
                                mn == "Haiku"
                                and "claude-haiku" in f.name
                                and "t=0.85" in f.name
                                and "tpl=" not in f.name
                            )
                            or (
                                mn == "Gemini"
                                and "gemini" in f.name
                                and "t=2.0" in f.name
                            )
                            or (
                                mn == "GPT-4o-mini"
                                and "gpt-4o-mini" in f.name
                                and "t=1.0" in f.name
                            )
                        ):
                            data = json.loads(f.read_text())
                            print(
                                f"    {mn} optimal-temp: {f.name} "
                                f"(n_q={data['aggregate']['n_questions']})"
                            )
                            found = True
                            break
                if not found:
                    print(f"    {mn} optimal-temp: NOT AVAILABLE")

    # -----------------------------------------------------------------------
    # 9. Run SubPOP default-temp ensemble for comparison
    #    (only if all 3 default-temp models available)
    # -----------------------------------------------------------------------
    print(f"\n{'=' * 80}")
    print("SUBPOP DEFAULT-TEMP ENSEMBLE (for reference)")
    print(f"{'=' * 80}")
    sub_def_data = {}
    sub_ok = True
    for mn in model_names:
        matcher = DEFAULT_TEMP_PATTERNS[mn]
        best_f = None
        best_sps = -1.0
        for f in RESULTS_DIR.glob("subpop_*.json"):
            if not matcher(f.name):
                continue
            try:
                d = json.loads(f.read_text())
                pq_jsds = [q["jsd"] for q in d["per_question"]]
                if np.var(pq_jsds) < 1e-10:
                    continue
                sps = d["scores"]["sps"]
                if sps > best_sps:
                    best_sps = sps
                    best_f = f
            except (KeyError, json.JSONDecodeError):
                continue
        if best_f is None:
            print(f"  {mn}: NOT FOUND")
            sub_ok = False
        else:
            data = json.loads(best_f.read_text())
            sub_def_data[mn] = data
            print(
                f"  {mn}: {best_f.name} "
                f"(n_q={data['aggregate']['n_questions']}, "
                f"SPS={data['scores']['sps']:.6f})"
            )

    if sub_ok:
        sub_per_q = {}
        for mn in model_names:
            sub_per_q[mn] = {q["key"]: q for q in sub_def_data[mn]["per_question"]}
        sub_common = sorted(
            set(sub_per_q["Haiku"])
            & set(sub_per_q["Gemini"])
            & set(sub_per_q["GPT-4o-mini"])
        )
        print(f"  Common questions: {len(sub_common)}")
        if sub_common:
            sub_blend = compute_blend_metrics(
                sub_per_q, sub_common, model_names, [1.0, 1.0, 1.0]
            )
            print(f"  EQUAL blend SPS: {sub_blend['sps']:.6f}")
            for mn in model_names:
                stats = compute_single_model_metrics(sub_per_q[mn], sub_common)
                print(f"  {mn} single SPS (common): {stats['sps']:.6f}")
        print(
            "  (No optimal-temp SubPOP ensemble possible -- "
            "Gemini/GPT-4o-mini temp runs not available)"
        )


if __name__ == "__main__":
    run_optimal_temp_experiment()
