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
  provider: string;
  model: string;
  dataset: string;
  framework: string;

  sps: number;

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

  topic_scores?: Record<TopicCategory, number>;
  demographic_scores?: DemographicBreakdown[];
  replicates?: ReplicateRun[];
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

export interface SynthBenchData {
  generated_at: string;
  synthbench_version: string;
  datasets: string[];
  entries: LeaderboardEntry[];
  convergence: ConvergencePoint[];
  findings: FindingsData;
}
