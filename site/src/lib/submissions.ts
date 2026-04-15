// sb-me0f: client-side helpers for the web upload flow.
//
// `uploadSubmission` POSTs a parsed submission JSON to the Worker's /submit
// endpoint with the current Supabase JWT. `listMySubmissions` reads the
// user's own rows from the Supabase `submissions` table (owner-read RLS,
// provisioned by `supabase/migrations/20260415_submissions.sql`).

import { getSession, getSupabaseClient, isAuthConfigured } from "@/lib/auth";

export interface SubmissionRow {
  id: number;
  submitted_at: string;
  model_name: string | null;
  dataset: string | null;
  framework: string | null;
  n_questions: number | null;
  file_path: string;
  status: "validating" | "rejected" | "published";
  rejection_reason: string | null;
  leaderboard_entry_id: string | null;
}

export type SubmissionStatus = SubmissionRow["status"];

export interface UploadOk {
  ok: true;
  submissionId: number;
  status: SubmissionStatus;
  filePath: string;
  warning?: string;
}

export interface UploadErr {
  ok: false;
  status: number;
  message: string;
}

export type UploadResult = UploadOk | UploadErr;

function gatedApiBase(): string | null {
  const raw = import.meta.env.PUBLIC_GATED_API_BASE;
  if (!raw) return null;
  return raw.replace(/\/$/, "");
}

/**
 * Upload a parsed submission body to the Worker. Returns a discriminated
 * union the caller can switch on without re-parsing error shapes.
 *
 * On success the caller gets the Supabase `submissions.id` so it can
 * deep-link the user to `/account/submissions/<id>` (or the list page).
 */
export async function uploadSubmission(body: unknown): Promise<UploadResult> {
  if (!isAuthConfigured()) {
    return { ok: false, status: 0, message: "Authentication is not configured for this site." };
  }
  const base = gatedApiBase();
  if (!base) {
    return {
      ok: false,
      status: 0,
      message: "Upload endpoint is not configured (set PUBLIC_GATED_API_BASE).",
    };
  }
  const session = await getSession();
  if (!session?.access_token) {
    return { ok: false, status: 401, message: "Sign in to submit a run." };
  }

  let res: Response;
  try {
    res = await fetch(`${base}/submit`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
  } catch (err) {
    return {
      ok: false,
      status: 0,
      message: err instanceof Error ? err.message : String(err),
    };
  }

  const payload = await res.json().catch(() => ({}) as Record<string, unknown>);

  if (!res.ok) {
    const errField = (payload as { error?: unknown }).error;
    const message =
      typeof errField === "string" && errField.length > 0
        ? errField
        : `Upload failed (HTTP ${res.status}).`;
    return { ok: false, status: res.status, message };
  }

  const data = payload as {
    submission_id?: number;
    status?: SubmissionStatus;
    file_path?: string;
    warning?: string;
  };
  if (typeof data.submission_id !== "number" || !data.status || !data.file_path) {
    return { ok: false, status: res.status, message: "Unexpected response shape from /submit." };
  }
  const result: UploadOk = {
    ok: true,
    submissionId: data.submission_id,
    status: data.status,
    filePath: data.file_path,
  };
  if (data.warning) result.warning = data.warning;
  return result;
}

/**
 * Load the current user's submissions, newest first. Uses Supabase RLS
 * (select-own policy) so the anon key is safe to expose; users only see
 * their own rows regardless of query shape.
 */
export async function listMySubmissions(userId: string): Promise<SubmissionRow[]> {
  const client = getSupabaseClient();
  const { data, error } = await client
    .from("submissions")
    .select(
      "id, submitted_at, model_name, dataset, framework, n_questions, file_path, status, rejection_reason, leaderboard_entry_id",
    )
    .eq("user_id", userId)
    .order("submitted_at", { ascending: false })
    .limit(200);
  if (error) {
    console.warn("[submissions] list failed", error.message);
    return [];
  }
  return (data ?? []) as SubmissionRow[];
}

/**
 * Best-effort client-side pre-flight check. Gives users immediate feedback
 * about obviously-malformed uploads without a server round-trip. Matches
 * the Tier-1 subset the Worker enforces; deliberately lenient so the
 * server remains the source of truth.
 */
export interface PreviewMeta {
  modelName: string | null;
  dataset: string | null;
  framework: string | null;
  nQuestions: number | null;
}

export interface PreviewOk {
  ok: true;
  meta: PreviewMeta;
}

export interface PreviewErr {
  ok: false;
  error: string;
}

export function previewSubmission(raw: unknown): PreviewOk | PreviewErr {
  if (raw === null || typeof raw !== "object" || Array.isArray(raw)) {
    return { ok: false, error: "File is not a JSON object." };
  }
  const obj = raw as Record<string, unknown>;
  if (obj.benchmark !== "synthbench") {
    return { ok: false, error: 'Top-level "benchmark" must equal "synthbench".' };
  }
  const config = obj.config;
  const aggregate = obj.aggregate;
  const perQuestion = obj.per_question;
  if (config === null || typeof config !== "object") {
    return { ok: false, error: 'Missing "config" object.' };
  }
  if (aggregate === null || typeof aggregate !== "object") {
    return { ok: false, error: 'Missing "aggregate" object.' };
  }
  if (!Array.isArray(perQuestion)) {
    return { ok: false, error: 'Missing "per_question" array.' };
  }
  const cfg = config as Record<string, unknown>;
  const agg = aggregate as Record<string, unknown>;
  const meta: PreviewMeta = {
    modelName:
      (typeof cfg.model === "string" && cfg.model) ||
      (typeof cfg.provider === "string" && cfg.provider) ||
      null,
    dataset: typeof cfg.dataset === "string" ? cfg.dataset : null,
    framework: typeof cfg.framework === "string" ? cfg.framework : null,
    nQuestions: typeof agg.n_questions === "number" ? agg.n_questions : null,
  };
  return { ok: true, meta };
}
