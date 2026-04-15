/**
 * Question-explorer types (sb-eiv).
 *
 * Shapes emitted by `synthbench publish-questions`:
 *   - `data/question/<dataset>/index.json`    → QuestionIndex (per-dataset catalog)
 *   - `data/question/<dataset>/<key>.json`    → QuestionPayload (full per-question rollup)
 *
 * Inverts the per-run pivot: organizes every model's answer to a given
 * question side-by-side, surfacing trendslop indicators (cross-model JSD
 * spread, consensus option, refusal-rate spread).
 */

import type { Dataset, RunFramework } from "./runs";

export interface QuestionModelResponse {
  config_id: string;
  model: string;
  framework: RunFramework;
  base_provider: string;
  distribution: Record<string, number>;
  n_samples: number;
  jsd_to_human: number | null;
  refusal_rate: number | null;
  run_id: string;
  temperature?: number | null;
  template?: string | null;
}

export interface QuestionSummary {
  n_models: number;
  cross_model_jsd_mean: number | null;
  cross_model_jsd_max: number | null;
  consensus_option: string | null;
  human_top_option: string | null;
  refusal_rate_spread: number | null;
  jsd_to_human_mean: number | null;
}

export type RedistributionPolicy = "full" | "aggregates_only" | "citation_only";

export interface DatasetPolicyInfo {
  redistribution_policy: RedistributionPolicy;
  license_url: string | null;
  citation: string | null;
}

export interface QuestionPayload {
  dataset: Dataset;
  key: string;
  question: string;
  options: string[];
  /**
   * Per-question human distribution. `{}` when the dataset's redistribution
   * policy is `aggregates_only` — the field stays present so consumers can
   * branch on emptiness rather than key existence.
   */
  human_distribution: Record<string, number>;
  human_refusal_rate: number | null;
  model_responses: QuestionModelResponse[];
  summary: QuestionSummary;
  dataset_policy?: DatasetPolicyInfo;
  topic?: string;
  temporal_year?: number | null;
}

export interface QuestionIndexEntry {
  key: string;
  question_excerpt: string;
  n_models: number;
  cross_model_jsd_mean: number | null;
  cross_model_jsd_max: number | null;
  jsd_to_human_mean: number | null;
  consensus_option: string | null;
  human_top_option: string | null;
  refusal_rate_spread: number | null;
  topic?: string;
}

export interface QuestionIndex {
  generated_at: string;
  synthbench_version: string;
  dataset: Dataset;
  n_questions: number;
  questions: QuestionIndexEntry[];
}
