// sb-me0f: unit tests for the Tier-1 schema validator + staging-key helper.

import { describe, expect, it } from "vitest";
import { stagingKeyFor, validateTier1 } from "../src/submit";

function baseSubmission(overrides: Partial<Record<string, unknown>> = {}): Record<string, unknown> {
  return {
    benchmark: "synthbench",
    config: {
      model: "gpt-5",
      provider: "openai",
      dataset: "globalopinionqa",
      framework: "native",
    },
    aggregate: {
      n_questions: 2,
      composite_parity: 0.7,
      mean_jsd: 0.2,
      mean_tau: 0.55,
    },
    per_question: [
      {
        human_distribution: [0.25, 0.25, 0.5],
        model_distribution: [0.3, 0.3, 0.4],
      },
      {
        human_distribution: [0.5, 0.5],
        model_distribution: [0.4, 0.6],
      },
    ],
    scores: {
      p_dist: 0.8,
      p_rank: 0.6,
    },
    ...overrides,
  };
}

describe("validateTier1", () => {
  it("accepts a minimal well-formed submission and extracts metadata", () => {
    const res = validateTier1(baseSubmission());
    expect(res.ok).toBe(true);
    if (res.ok) {
      expect(res.meta).toEqual({
        modelName: "gpt-5",
        dataset: "globalopinionqa",
        framework: "native",
        nQuestions: 2,
      });
    }
  });

  it("rejects non-object bodies", () => {
    const res = validateTier1("not a submission");
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toMatch(/not a JSON object/i);
  });

  it('requires benchmark === "synthbench"', () => {
    const res = validateTier1(baseSubmission({ benchmark: "other" }));
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toMatch(/benchmark/);
  });

  it("rejects missing config/aggregate/per_question", () => {
    const { config: _config, ...missingConfig } = baseSubmission();
    expect(validateTier1(missingConfig).ok).toBe(false);

    const { aggregate: _agg, ...missingAgg } = baseSubmission();
    expect(validateTier1(missingAgg).ok).toBe(false);

    const { per_question: _pq, ...missingPq } = baseSubmission();
    expect(validateTier1(missingPq).ok).toBe(false);
  });

  it("enforces n_questions matches per_question length", () => {
    const res = validateTier1(baseSubmission({ aggregate: { n_questions: 3 } }));
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toMatch(/n_questions/);
  });

  it("rejects out-of-range composite_parity", () => {
    const res = validateTier1(
      baseSubmission({
        aggregate: { n_questions: 2, composite_parity: 1.7 },
      }),
    );
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toMatch(/composite_parity/);
  });

  it("rejects distributions that don't sum to 1", () => {
    const sub = baseSubmission();
    (sub.per_question as Array<Record<string, unknown>>)[0] = {
      human_distribution: [0.5, 0.1, 0.1],
      model_distribution: [0.3, 0.3, 0.4],
    };
    const res = validateTier1(sub);
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toMatch(/sums to/);
  });

  it("rejects negative probabilities", () => {
    const sub = baseSubmission();
    (sub.per_question as Array<Record<string, unknown>>)[0] = {
      human_distribution: [-0.1, 0.6, 0.5],
      model_distribution: [0.3, 0.3, 0.4],
    };
    const res = validateTier1(sub);
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toMatch(/negative/);
  });

  it("tolerates distributions as dicts in addition to arrays", () => {
    const sub = baseSubmission();
    (sub.per_question as Array<Record<string, unknown>>)[0] = {
      human_distribution: { A: 0.25, B: 0.25, C: 0.5 },
      model_distribution: { A: 0.3, B: 0.3, C: 0.4 },
    };
    expect(validateTier1(sub).ok).toBe(true);
  });

  it("tolerates missing optional aggregate bounds", () => {
    const res = validateTier1(baseSubmission({ aggregate: { n_questions: 2 } }));
    expect(res.ok).toBe(true);
  });
});

describe("stagingKeyFor", () => {
  it("includes user id and a yyyy/mm/dd prefix", () => {
    const key = stagingKeyFor("user-abc", new Date("2026-04-15T12:34:56Z"));
    expect(key.startsWith("submissions/2026/04/15/user-abc/")).toBe(true);
    expect(key.endsWith(".json")).toBe(true);
  });

  it("produces unique keys across calls", () => {
    const t = new Date("2026-04-15T12:34:56Z");
    const a = stagingKeyFor("user-abc", t);
    const b = stagingKeyFor("user-abc", t);
    expect(a).not.toBe(b);
  });
});
