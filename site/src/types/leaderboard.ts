export type TopicCategory =
  | "Politics & Governance"
  | "International Relations & Security"
  | "Economy & Work"
  | "Technology & Digital Life"
  | "Media & Information"
  | "Health & Science"
  | "Social Values & Religion"
  | "Identity & Demographics"
  | "Trust & Wellbeing"
  | "General Attitudes";

export interface LeaderboardEntry {
  rank: number;
  /**
   * Canonical config slug (framework--model--t<temp>--tpl<name>--<hash8>).
   * Used to link rows to /config/<id>/. Emitted by publish.py.
   */
  config_id?: string;
  provider: string;
  model: string;
  dataset: string;
  framework: string;

  sps: number;
  /**
   * Position in the meaningful evaluation range: (SPS - P_unconditioned) /
   * (P_ceiling - P_unconditioned). Expressed in [0, ~1]. Present only when a
   * raw-LLM baseline and dataset ceiling are both available. Raw LLMs resolve
   * to 0 (they ARE the unconditioned reference); baselines are omitted.
   */
  normalized_sps?: number;

  p_dist: number;
  p_rank: number;
  p_refuse: number;
  p_cond?: number;
  p_sub?: number;

  jsd: number;
  tau: number;

  n: number;
  samples_per_question?: number;
  temperature?: number;
  template?: string;

  ci_lower: number;
  ci_upper: number;

  is_baseline: boolean;
  is_ensemble: boolean;

  /**
   * Number of raw result files aggregated into this row — replicates for
   * this exact (model, framework, dataset, temperature, template) config.
   * Emitted by publish.py so the default view can hide under-replicated
   * configs without re-grouping in JS.
   */
  run_count?: number;
  /**
   * Number of distinct datasets this (model, framework, temperature, template)
   * config has runs on. Used for the default view's coverage filter.
   */
  dataset_coverage_count?: number;

  /**
   * Total USD spent on the LLM calls aggregated into this row, computed by
   * publish.py from token_usage × pricing_snapshot. ``null`` for self-hosted,
   * unknown-provider, or pre-tracking rows. See `_compute_cost_fields` in
   * publish.py.
   */
  cost_usd?: number | null;
  /** Cost normalized per 100 questions answered. ``null`` when cost_usd or n is unavailable. */
  cost_per_100q?: number | null;
  /** USD per 1.0 SPS point — only populated when sps ≥ 0.01 to avoid amplification. */
  cost_per_sps_point?: number | null;
  /** True when pricing was estimated (e.g., fallback table) rather than authoritative. */
  is_cost_estimated?: boolean | null;
  /** Total input tokens across all LLM calls aggregated into this row. */
  input_tokens?: number | null;
  /** Total output tokens across all LLM calls aggregated into this row. */
  output_tokens?: number | null;

  topic_scores?: Record<TopicCategory, number>;
  topic_metrics?: Record<TopicCategory, TopicMetricBreakdown>;
  demographic_scores?: DemographicBreakdown[];
  replicates?: ReplicateRun[];

  /**
   * SPS recomputed over the public 80% of the dataset's holdout split.
   * Present only on holdout-enabled datasets with enough per-question rows
   * to compute a subset mean. See `synthbench.private_holdout`.
   */
  sps_public?: number;
  /**
   * SPS recomputed over the private 20% of the dataset's holdout split.
   * The hidden answer key means this score is what our server computes,
   * not what the submitter could fake against public distributions.
   */
  sps_private?: number;
  /** |sps_public − sps_private|. Large values suggest fabrication or contamination. */
  sps_public_private_delta?: number;
  /**
   * Verification badge derived from `sps_public_private_delta` vs
   * `SPS_DIVERGENCE_THRESHOLD` (0.05). "verified" = delta within threshold,
   * "flagged" = delta exceeds threshold (submission warrants review).
   * Absent when the split cannot be computed.
   */
  verification_badge?: "verified" | "flagged";
}

export interface TopicMetricBreakdown {
  sps: number;
  n: number;
  p_dist?: number;
  p_rank?: number;
  p_refuse?: number;
}

export interface DemographicBreakdown {
  attribute: string;
  group: string;
  p_dist: number;
  p_cond: number;
  n_questions: number;
}

export interface ReplicateRun {
  rep: number;
  sps: number;
  p_dist: number;
  p_rank: number;
}

export interface FindingsData {
  temperature_sweep: TemperatureSweepPoint[];
  ensemble_comparison: EnsembleComparison[];
  conditioning_results: ConditioningResult[];
  lever_hierarchy: Lever[];
}

export interface TemperatureSweepPoint {
  model: string;
  temperature: number;
  sps: number;
  std?: number;
}

export interface EnsembleComparison {
  dataset: string;
  best_single_model: string;
  best_single_sps: number;
  ensemble_sps: number;
  improvement: number;
}

export interface ConditioningResult {
  attribute: string;
  group: string;
  p_dist: number;
  p_cond: number;
  p_cond_std?: number;
  n_replications: number;
}

export interface Lever {
  name: string;
  effect_min: number;
  effect_max: number;
  cost: "zero" | "low" | "moderate" | "high";
  status: "done" | "actionable" | "scientific";
}

export interface ConvergencePoint {
  model: string;
  dataset: string;
  rep_count: number;
  sps: number;
}

export interface TemporalDriftByYearGap {
  mean_jsd: number;
  n_pairs: number;
}

export interface TemporalDriftFloor {
  mean_drift: number;
  ci_low: number;
  ci_high: number;
  n_pairs: number;
  n_stems: number;
  by_year_gap: Record<string, TemporalDriftByYearGap>;
  method?: string;
}

export interface Baselines {
  temporal_drift?: TemporalDriftFloor;
}

/**
 * Runtime pricing manifest captured by publish.py at publish time (sb-tbm
 * Slice 3). Documents which synthpanel pricing rates were applied to cost
 * fields in this leaderboard build.
 */
export interface PricingSnapshot {
  generated_at: string;
  synth_panel_version: string;
  snapshot_date: string;
  rates: Record<string, number | Record<string, number>>;
}

/**
 * Per-dataset cross-provider JSD matrix. Operationalizes HBR's "trendslop"
 * hypothesis (cross-model consensus without ground truth): the 2-D matrix is
 * pairwise mean JSD between raw-LLM model distributions, symmetric with a
 * zero diagonal; ``mean_cross_model_jsd`` / ``mean_human_jsd`` give the 1-D
 * quadrant summary pair (cross-model agreement vs. ground-truth accuracy).
 */
export interface CrossProviderConcordanceBlock {
  models: string[];
  matrix: (number | null)[][];
  mean_cross_model_jsd: number | null;
  mean_human_jsd: number | null;
}

export type RedistributionPolicy = "full" | "aggregates_only" | "citation_only";

/** One row of the dataset policy manifest emitted by publish.py. */
export interface DatasetPolicyEntry {
  name: string;
  redistribution_policy: RedistributionPolicy;
  license_url: string | null;
  citation: string | null;
}

export interface SynthBenchData {
  generated_at: string;
  synthbench_version: string;
  datasets: string[];
  entries: LeaderboardEntry[];
  convergence: ConvergencePoint[];
  findings: FindingsData;
  baselines?: Baselines;
  pricing_snapshot?: PricingSnapshot;
  cross_provider_concordance?: Record<string, CrossProviderConcordanceBlock>;
  /** Per-dataset redistribution policy + provenance. */
  dataset_policies?: DatasetPolicyEntry[];
}

/** @deprecated Use SynthBenchData — alias kept for existing component imports */
export type LeaderboardData = SynthBenchData;
