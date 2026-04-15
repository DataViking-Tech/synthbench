// sb-me0f: `public.submissions` row writer + publish-pipeline dispatcher.
//
// Unlike the audit log, these writes are NOT fire-and-forget — the caller
// waits for the Supabase insert so it can return the new row id in the 202
// response. Failures surface to the Worker handler which maps them to a 5xx.

import type { SubmissionMetadata } from "./submit";

export interface SubmissionsConfig {
  supabaseUrl: string;
  serviceRoleKey: string;
  /** Injection seam for tests. Defaults to global fetch. */
  fetchImpl?: typeof fetch;
}

export interface InsertRowInput {
  userId: string;
  filePath: string;
  requestIp: string | null;
  userAgent: string | null;
  meta: SubmissionMetadata;
  /** sb-t61h: id of the api_keys row that authenticated this upload, or
   *  null for browser/JWT-flow uploads. Powers per-key rate limit + audit. */
  apiKeyId: number | null;
}

export interface InsertedRow {
  id: number;
  submitted_at: string;
  status: string;
}

/**
 * Insert a new `validating` row and return the Supabase-generated id. We
 * request `return=representation` (the default) so we can hand the id back
 * to the client — it's used to deep-link the user to the submission detail
 * page while validation is still in flight.
 */
export async function insertSubmission(
  input: InsertRowInput,
  config: SubmissionsConfig,
): Promise<InsertedRow> {
  const url = `${config.supabaseUrl.replace(/\/+$/, "")}/rest/v1/submissions`;
  const body = JSON.stringify({
    user_id: input.userId,
    model_name: input.meta.modelName,
    dataset: input.meta.dataset,
    framework: input.meta.framework,
    n_questions: input.meta.nQuestions,
    file_path: input.filePath,
    status: "validating",
    request_ip: input.requestIp,
    user_agent: input.userAgent,
    api_key_id: input.apiKeyId,
  });
  const doFetch = config.fetchImpl ?? fetch;
  const res = await doFetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: config.serviceRoleKey,
      Authorization: `Bearer ${config.serviceRoleKey}`,
      Prefer: "return=representation",
    },
    body,
  });
  if (!res.ok) {
    throw new Error(`submissions insert failed: ${res.status} ${res.statusText}`);
  }
  const data = (await res.json()) as InsertedRow[] | InsertedRow;
  // PostgREST returns an array; some proxies unwrap it. Tolerate both.
  const row = Array.isArray(data) ? data[0] : data;
  if (!row || typeof row.id !== "number") {
    throw new Error("submissions insert returned unexpected shape");
  }
  return row;
}

/**
 * sb-ymux: Fetch a submission by id, scoped to a specific user.
 *
 * Returns `null` when either no row matches or the row belongs to another
 * user — the Worker maps both to 404 so an attacker can't differentiate a
 * missing id from a cross-user id by status code alone. Only the columns the
 * CLI poller cares about come back, so an accidentally-leaked service-role
 * response never exposes more than status + final artifact link.
 */
export interface StatusRow {
  id: number;
  status: string;
  submitted_at: string;
  rejection_reason: string | null;
  leaderboard_entry_id: string | null;
  model_name: string | null;
  dataset: string | null;
}

export async function getSubmissionForUser(
  submissionId: number,
  userId: string,
  config: SubmissionsConfig,
): Promise<StatusRow | null> {
  const url = new URL(`${config.supabaseUrl.replace(/\/+$/, "")}/rest/v1/submissions`);
  url.searchParams.set("id", `eq.${submissionId}`);
  url.searchParams.set("user_id", `eq.${userId}`);
  url.searchParams.set(
    "select",
    "id,status,submitted_at,rejection_reason,leaderboard_entry_id,model_name,dataset",
  );
  url.searchParams.set("limit", "1");

  const doFetch = config.fetchImpl ?? fetch;
  const res = await doFetch(url.toString(), {
    method: "GET",
    headers: {
      apikey: config.serviceRoleKey,
      Authorization: `Bearer ${config.serviceRoleKey}`,
      Accept: "application/json",
    },
  });
  if (!res.ok) {
    throw new Error(`submissions lookup ${res.status} ${res.statusText}`);
  }
  const rows = (await res.json()) as StatusRow[];
  return rows[0] ?? null;
}

/** Mark a row rejected with a reason. Used when inline Tier-1 fails AFTER
 * we've already uploaded — rare, but keeps the audit trail honest. */
export async function markRejected(
  submissionId: number,
  reason: string,
  config: SubmissionsConfig,
): Promise<void> {
  const url = `${config.supabaseUrl.replace(/\/+$/, "")}/rest/v1/submissions?id=eq.${submissionId}`;
  const doFetch = config.fetchImpl ?? fetch;
  await doFetch(url, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      apikey: config.serviceRoleKey,
      Authorization: `Bearer ${config.serviceRoleKey}`,
      Prefer: "return=minimal",
    },
    body: JSON.stringify({ status: "rejected", rejection_reason: reason }),
  });
}

export interface DispatchConfig {
  /** GitHub owner/repo pair, e.g. "DataViking-Tech/synthbench". */
  repo: string;
  /** Workflow filename or numeric id, e.g. "process-submission.yml". */
  workflowFile: string;
  /** Git ref to dispatch against (typically "main"). */
  ref: string;
  /** GitHub REST API token — a fine-grained PAT or App-installation token. */
  token: string;
  /** Injection seam for tests. */
  fetchImpl?: typeof fetch;
}

export interface DispatchInput {
  submissionId: number;
  filePath: string;
}

/**
 * Fire `workflow_dispatch` so the GH Actions runner picks up the staged
 * submission, runs the full Python validator, and (if clean) commits it to
 * `leaderboard-results/`. Returns void because GH's API responds 204 with
 * no body; non-204 throws so the Worker handler can surface a 5xx to the
 * client rather than silently dropping the submission.
 */
export async function dispatchProcessWorkflow(
  input: DispatchInput,
  config: DispatchConfig,
): Promise<void> {
  const url = `https://api.github.com/repos/${config.repo}/actions/workflows/${config.workflowFile}/dispatches`;
  const doFetch = config.fetchImpl ?? fetch;
  const res = await doFetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      Authorization: `Bearer ${config.token}`,
      // GitHub requires a User-Agent on API requests.
      "User-Agent": "synthbench-data-proxy",
    },
    body: JSON.stringify({
      ref: config.ref,
      inputs: {
        submission_id: String(input.submissionId),
        file_path: input.filePath,
      },
    }),
  });
  if (!res.ok) {
    throw new Error(`workflow_dispatch failed: ${res.status} ${res.statusText}`);
  }
}
