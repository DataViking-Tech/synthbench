/**
 * Run Explorer types — Slice 8.1 data contracts.
 *
 * Shapes emitted by `synthbench publish-runs`:
 *   - `data/runs-index.json`    → RunIndex (catalog)
 *   - `data/config/<id>.json`   → ConfigRollup (per-config replicate rollup)
 *   - `data/run/<id>.json`      → RunDetail   (full per-question detail)
 *
 * Fields that appear only for specific benchmarks (SubPOP demographic
 * breakdown, OpinionsQA temporal year) are preserved on the detail shape
 * and rendered conditionally by the UI.
 */

import type { DemographicBreakdown, TopicCategory } from "./leaderboard";

export type RunFramework = "synthpanel" | "openrouter" | "raw" | "ensemble" | "baseline" | string;

export type Dataset = "opinionsqa" | "globalopinionqa" | "subpop" | string;

/** ---------- runs-index.json ---------- */

export interface RunIndex {
  generated_at: string;
  synthbench_version: string;
  n_runs: number;
  n_configs: number;
  runs: RunIndexEntry[];
}

export interface RunIndexEntry {
  run_id: string;
  config_id: string;
  framework: RunFramework;
  base_provider: string | null;
  model: string;
  display_name: string;
  dataset: Dataset;
  temperature: number | null;
  template: string | null;
  samples_per_question: number | null;
  n_questions: number;
  n_topics: number;
  sps: number | null;
  p_dist: number | null;
  p_rank: number | null;
  p_refuse: number | null;
  jsd: number | null;
  tau: number | null;
  timestamp: string | null;
  is_baseline: boolean;
  is_ensemble: boolean;
}

/** ---------- config/<id>.json ---------- */

export interface ReplicateRecord {
  run_id: string;
  timestamp: string | null;
  sps: number | null;
  p_dist: number | null;
  p_rank: number | null;
  p_refuse: number | null;
  jsd: number | null;
  tau: number | null;
  n_questions: number;
}

export interface MeanStd {
  mean: number | null;
  std: number | null;
}

export interface TopicAggregate {
  mean: number | null;
  std: number | null;
  n_replicates: number;
}

export interface VarianceSummary {
  n_replicates: number;
  sps_mean?: number | null;
  sps_std?: number | null;
  sps_range?: [number | null, number | null];
  sps_cv?: number | null;
}

export interface ConfigRollup {
  config_id: string;
  framework: RunFramework;
  base_provider: string | null;
  model: string;
  display_name: string;
  dataset: Dataset;
  temperature: number | null;
  template: string | null;
  samples_per_question: number | null;
  is_baseline: boolean;
  is_ensemble: boolean;
  n_replicates: number;
  replicates: ReplicateRecord[];
  aggregate: {
    sps: MeanStd;
    jsd: MeanStd;
    tau: MeanStd;
  };
  variance_summary: VarianceSummary;
  topic_breakdown: Partial<Record<TopicCategory, TopicAggregate>>;
}

/** ---------- run/<id>.json ---------- */

export interface RunScores {
  sps: number | null;
  p_dist: number | null;
  p_rank: number | null;
  p_refuse: number | null;
  p_cond?: number | null;
  p_sub?: number | null;
}

export interface RunAggregate {
  mean_jsd: number | null;
  median_jsd: number | null;
  mean_kendall_tau: number | null;
  composite_parity: number | null;
  n_questions: number | null;
  elapsed_seconds: number | null;
  per_metric_ci: Record<string, [number, number]> | null;
  n_parse_failures: number | null;
}

export interface PerQuestionRow {
  key: string;
  text: string;
  topic?: TopicCategory | string;
  options: string[];
  human_distribution: Record<string, number>;
  model_distribution: Record<string, number>;
  jsd: number;
  kendall_tau: number;
  parity: number;
  n_samples: number;
  n_parse_failures?: number;
  model_refusal_rate?: number;
  human_refusal_rate?: number;
  /** Only present on OpinionsQA runs. */
  temporal_year?: number | null;
}

export interface RunDetail {
  run_id: string;
  config_id: string;
  benchmark: string;
  version: string | null;
  timestamp: string | null;
  framework: RunFramework;
  base_provider: string | null;
  model: string;
  display_name: string;
  is_baseline: boolean;
  is_ensemble: boolean;
  dataset: Dataset;
  temperature: number | null;
  template: string | null;
  samples_per_question: number | null;
  n_requested: number | null;
  n_evaluated: number | null;
  question_set_hash: string | null;
  topic_filter: string | null;
  parse_failure_rate: number | null;
  scores: RunScores;
  aggregate: RunAggregate;
  per_question: PerQuestionRow[];
  topic_scores?: Partial<Record<TopicCategory, number>>;
  /** Only present on SubPOP conditioned runs. */
  demographic_breakdown?: Record<string, DemographicBreakdown[]>;
  /** Only present on OpinionsQA runs with wave-level breakdown. */
  temporal_breakdown?: Record<string, number>;
}
