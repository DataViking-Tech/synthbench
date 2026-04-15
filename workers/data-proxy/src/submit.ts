// sb-me0f: /submit endpoint helpers.
//
// Lightweight Tier-1 schema validation we can run inline in the Worker (no
// Python available). Catches structurally-invalid uploads so we never stage
// garbage to R2; the full Tier 1+2+3 validator still runs in the GH Actions
// process-submission workflow before the file is committed to
// `leaderboard-results/`. See src/synthbench/validation.py for the canonical
// rules — this is a defensive subset, not a replacement.

export interface SubmissionMetadata {
  modelName: string | null;
  dataset: string | null;
  framework: string | null;
  nQuestions: number | null;
}

export interface ValidateOk {
  ok: true;
  meta: SubmissionMetadata;
}

export interface ValidateErr {
  ok: false;
  error: string;
}

export type ValidateResult = ValidateOk | ValidateErr;

const SUM_TOLERANCE = 5e-3;

/**
 * Tier-1 schema + bounds + sums check. Returns structural metadata on
 * success so the caller can record `model_name`/`dataset`/`framework` in
 * the submissions table without re-parsing the body.
 *
 * Rejects anything that couldn't pass Tier 1 in the Python validator:
 *  - wrong top-level shape
 *  - out-of-bounds composite_parity / mean_jsd
 *  - per_question length mismatch
 *  - distributions that don't sum to 1.0±5e-3 or have negatives
 *
 * Deliberately NOT re-computed: JSD/tau recompute (Tier 2), anomaly
 * detection (Tier 3). Those need numerical libs and peer data; the GH
 * Action handles them.
 */
export function validateTier1(raw: unknown): ValidateResult {
  if (!isObject(raw)) return fail("body is not a JSON object");

  if (raw.benchmark !== "synthbench") {
    return fail('top-level "benchmark" must equal "synthbench"');
  }

  const config = raw.config;
  if (!isObject(config)) return fail('missing or invalid "config"');

  const aggregate = raw.aggregate;
  if (!isObject(aggregate)) return fail('missing or invalid "aggregate"');

  const perQuestion = raw.per_question;
  if (!Array.isArray(perQuestion)) return fail('missing or invalid "per_question"');

  const nQuestions = aggregate.n_questions;
  if (typeof nQuestions !== "number" || !Number.isFinite(nQuestions) || nQuestions < 0) {
    return fail('"aggregate.n_questions" must be a non-negative number');
  }
  if (nQuestions !== perQuestion.length) {
    return fail(
      `"aggregate.n_questions" (${nQuestions}) does not match per_question length (${perQuestion.length})`,
    );
  }

  // Scalar bounds. These are the same bounds the Python validator enforces
  // in tier 1; failing here means no amount of deeper analysis can rescue it.
  const parity = aggregate.composite_parity;
  if (parity != null && !inRange(parity, 0, 1)) {
    return fail('"aggregate.composite_parity" must be in [0, 1]');
  }
  const meanJsd = aggregate.mean_jsd;
  if (meanJsd != null && !inRange(meanJsd, 0, 1)) {
    return fail('"aggregate.mean_jsd" must be in [0, 1]');
  }
  const meanTau = aggregate.mean_tau;
  if (meanTau != null && !inRange(meanTau, -1, 1)) {
    return fail('"aggregate.mean_tau" must be in [-1, 1]');
  }

  // Per-question distribution sanity. We only check a cheap structural
  // invariant (sums, non-negativity) — recompute stays in the Python
  // validator where we have the metrics code already.
  for (let i = 0; i < perQuestion.length; i++) {
    const q = perQuestion[i];
    if (!isObject(q)) return fail(`per_question[${i}] is not an object`);
    const human = q.human_distribution;
    const model = q.model_distribution;
    if (human !== undefined) {
      const err = checkDistribution(human, `per_question[${i}].human_distribution`);
      if (err) return fail(err);
    }
    if (model !== undefined) {
      const err = checkDistribution(model, `per_question[${i}].model_distribution`);
      if (err) return fail(err);
    }
  }

  const meta: SubmissionMetadata = {
    modelName: readString(config.model) ?? readString(config.provider),
    dataset: readString(config.dataset),
    framework: readString(config.framework),
    nQuestions,
  };

  return { ok: true, meta };
}

function fail(error: string): ValidateErr {
  return { ok: false, error };
}

function isObject(v: unknown): v is Record<string, unknown> {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}

function inRange(v: unknown, lo: number, hi: number): boolean {
  return typeof v === "number" && Number.isFinite(v) && v >= lo && v <= hi;
}

function readString(v: unknown): string | null {
  return typeof v === "string" && v.length > 0 ? v : null;
}

function checkDistribution(v: unknown, path: string): string | null {
  if (!isObject(v) && !Array.isArray(v)) {
    return `${path} must be an object or array`;
  }
  const values: unknown[] = Array.isArray(v) ? v : Object.values(v);
  let sum = 0;
  for (const p of values) {
    if (typeof p !== "number" || !Number.isFinite(p)) {
      return `${path} contains a non-numeric probability`;
    }
    if (p < 0) return `${path} contains a negative probability`;
    sum += p;
  }
  if (values.length > 0 && Math.abs(sum - 1) > SUM_TOLERANCE) {
    return `${path} sums to ${sum.toFixed(4)}, expected 1.0 ±${SUM_TOLERANCE}`;
  }
  return null;
}

/** Max request body size. 2 MB fits a 1000-question run with room to spare. */
export const MAX_BODY_BYTES = 2 * 1024 * 1024;

/** Generate an R2 staging key. Timestamp + random suffix keeps writes unique. */
export function stagingKeyFor(userId: string, now: Date = new Date()): string {
  const y = now.getUTCFullYear();
  const m = String(now.getUTCMonth() + 1).padStart(2, "0");
  const d = String(now.getUTCDate()).padStart(2, "0");
  const ts = now.toISOString().replace(/[:.]/g, "-");
  // 8-char random suffix collision-protects same-user same-second submissions.
  const suffix = randomSuffix(8);
  // User id prefix keeps ownership auditable by bucket path alone.
  return `submissions/${y}/${m}/${d}/${userId}/${ts}-${suffix}.json`;
}

function randomSuffix(n: number): string {
  const bytes = new Uint8Array(n);
  // Workers runtime provides crypto.getRandomValues; Math.random fallback
  // should never fire in production but keeps unit tests happy if the global
  // is stubbed away.
  const g = (globalThis as { crypto?: Crypto }).crypto;
  if (g && typeof g.getRandomValues === "function") {
    g.getRandomValues(bytes);
  } else {
    for (let i = 0; i < bytes.length; i++) bytes[i] = Math.floor(Math.random() * 256);
  }
  let out = "";
  for (const b of bytes) out += b.toString(16).padStart(2, "0");
  return out.slice(0, n);
}
