// Cloudflare Worker entrypoint. Serves two routes:
//
//   GET/HEAD /data/<key>  — gated-tier R2 proxy (sb-io1). JWT-gated read of
//                           publish artifacts (run/<id>.json, config/<id>.json,
//                           question/<dataset>/<key>.json) with audit logging.
//
//   POST     /submit       — web upload endpoint (sb-me0f). JWT-gated upload of
//                           a submission JSON → Tier-1 schema check → R2 stage
//                           → Supabase `submissions` row → GH Actions dispatch
//                           to run the full Python validator + commit to
//                           `leaderboard-results/` on pass.
//
//   GET      /submit/<id>  — submission status poll (sb-ymux). `sb_` API-key
//                           gated (same key used for POST /submit), returns
//                           status/rejection_reason/leaderboard_entry_id so
//                           `synthbench run --submit --wait` can block until
//                           validation completes.
//
// Common plumbing (CORS allowlist, JWT verification, Supabase audit writer)
// is shared across both. Every branch has a matching unit test in tests/.

import { type ApiKeyConfig, authenticateApiKey, isApiKey, touchLastUsed } from "./apiKey";
import { type AuditConfig, clientIpFor, writeAuditLog } from "./audit";
import { parseBearer, verifySupabaseJwt } from "./auth";
import { corsHeadersFor, parseAllowedOrigins, preflightResponse } from "./cors";
import { parseRequestPath } from "./path";
import {
  type DispatchConfig,
  dispatchProcessWorkflow,
  getSubmissionForUser,
  insertSubmission,
} from "./submissions";
import { MAX_BODY_BYTES, stagingKeyFor, validateTier1 } from "./submit";

export interface Env {
  DATA_BUCKET: R2Bucket;
  SUBMISSIONS_BUCKET: R2Bucket;
  SUPABASE_URL: string;
  SUPABASE_JWT_AUD: string;
  SUPABASE_SERVICE_ROLE_KEY: string;
  ALLOWED_ORIGINS: string;
  GITHUB_DISPATCH_TOKEN: string;
  GITHUB_DISPATCH_REPO: string;
  GITHUB_DISPATCH_WORKFLOW: string;
  GITHUB_DISPATCH_REF: string;
}

function jsonResponse(
  body: unknown,
  status: number,
  extraHeaders: Record<string, string>,
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...extraHeaders,
    },
  });
}

function envConfigOk(env: Env): boolean {
  // Shared prerequisites for both routes. Missing = 500 rather than silent
  // 401s — easier to catch misconfig in preview deploys.
  return Boolean(env.SUPABASE_URL && env.SUPABASE_JWT_AUD && env.SUPABASE_SERVICE_ROLE_KEY);
}

function submitConfigOk(env: Env): boolean {
  // /submit needs the staging bucket + GH dispatch credentials. /data can
  // still serve when these are missing, so we check them per-route rather
  // than globally.
  return Boolean(
    env.SUBMISSIONS_BUCKET &&
      env.GITHUB_DISPATCH_TOKEN &&
      env.GITHUB_DISPATCH_REPO &&
      env.GITHUB_DISPATCH_WORKFLOW &&
      env.GITHUB_DISPATCH_REF,
  );
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const origin = request.headers.get("Origin");
    const allowed = parseAllowedOrigins(env.ALLOWED_ORIGINS);

    if (request.method === "OPTIONS") {
      return preflightResponse(origin, allowed);
    }

    const cors = corsHeadersFor(origin, allowed);

    if (!envConfigOk(env)) {
      return jsonResponse({ error: "server misconfigured" }, 500, cors);
    }

    const url = new URL(request.url);

    if (url.pathname === "/submit") {
      return handleSubmit(request, env, ctx, cors);
    }
    // sb-ymux: `GET /submit/<id>` polls validation status for one submission.
    // Other `/submit/...` shapes fall through to the POST handler which will
    // 405 them, so we don't leak new 404 semantics on the legacy route.
    const statusId = parseSubmissionStatusPath(url.pathname);
    if (statusId !== null) {
      return handleSubmitStatus(request, env, cors, statusId);
    }
    if (url.pathname.startsWith("/submit/")) {
      return handleSubmit(request, env, ctx, cors);
    }

    return handleData(request, env, ctx, cors, url);
  },
};

async function handleData(
  request: Request,
  env: Env,
  ctx: ExecutionContext,
  cors: Record<string, string>,
  url: URL,
): Promise<Response> {
  const parsed = parseRequestPath(request.method, url.pathname);
  if (!parsed.ok) {
    const status = parsed.error === "bad_method" ? 405 : parsed.error === "bad_path" ? 400 : 404;
    const message =
      parsed.error === "bad_method"
        ? "method not allowed"
        : parsed.error === "bad_path"
          ? "bad path"
          : "not found";
    return jsonResponse({ error: message }, status, cors);
  }

  const token = parseBearer(request.headers.get("Authorization"));
  if (!token) {
    return jsonResponse({ error: "sign in to view" }, 401, cors);
  }

  const claims = await verifySupabaseJwt(token, {
    supabaseUrl: env.SUPABASE_URL,
    expectedAudience: env.SUPABASE_JWT_AUD,
  });
  if (!claims) {
    return jsonResponse({ error: "invalid token" }, 401, cors);
  }

  const { bucketKey, dataset } = parsed.value;

  const obj = await env.DATA_BUCKET.get(bucketKey);
  if (!obj) {
    return jsonResponse({ error: "not found" }, 404, cors);
  }

  // HEAD must not return a body — match R2's metadata-only response shape.
  if (request.method === "HEAD") {
    return new Response(null, {
      status: 200,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "private, max-age=60",
        ...cors,
      },
    });
  }

  const auditConfig: AuditConfig = {
    supabaseUrl: env.SUPABASE_URL,
    serviceRoleKey: env.SUPABASE_SERVICE_ROLE_KEY,
  };
  ctx.waitUntil(
    writeAuditLog(
      {
        userId: claims.sub,
        dataset,
        artifactPath: bucketKey,
        requestIp: clientIpFor(request),
        userAgent: request.headers.get("User-Agent"),
      },
      auditConfig,
    ),
  );

  return new Response(obj.body, {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "private, max-age=60",
      ...cors,
    },
  });
}

/**
 * sb-ymux: Parse `/submit/<id>` for the polling GET route. Returns the numeric
 * id or null if the path isn't in that shape — the caller falls through to
 * the POST handler (which returns 405 for non-POST /submit) in that case.
 */
function parseSubmissionStatusPath(pathname: string): number | null {
  // Canonical path is `/submit/<id>` with no trailing slash or extra segments.
  // Anything else is deliberately rejected so we don't invite ambiguous routes
  // like `/submit/123/foo` later.
  const match = /^\/submit\/(\d+)$/.exec(pathname);
  if (!match) return null;
  const id = Number(match[1]);
  return Number.isFinite(id) && id > 0 ? id : null;
}

async function handleSubmitStatus(
  request: Request,
  env: Env,
  cors: Record<string, string>,
  submissionId: number,
): Promise<Response> {
  if (request.method !== "GET") {
    return jsonResponse({ error: "method not allowed" }, 405, cors);
  }

  const token = parseBearer(request.headers.get("Authorization"));
  if (!token) {
    return jsonResponse({ error: "sign in or pass an API key to view status" }, 401, cors);
  }

  // The CLI `run --submit --wait` flow authenticates exclusively with an
  // `sb_` API key — JWT polling is something the browser already does via
  // Supabase RLS. Keeping the surface narrow (api-key only) means we don't
  // have to re-verify RLS semantics here.
  if (!isApiKey(token)) {
    return jsonResponse({ error: "status endpoint requires an sb_ API key" }, 401, cors);
  }

  const apiKeyConfig: ApiKeyConfig = {
    supabaseUrl: env.SUPABASE_URL,
    serviceRoleKey: env.SUPABASE_SERVICE_ROLE_KEY,
  };
  // `submit` scope also grants status reads — the polling step is part of
  // the same workflow as the write, so forcing a separate scope would just
  // mean every submit-capable key needs `both`.
  const auth = await authenticateApiKey(token, "submit", apiKeyConfig);
  if (!auth.ok) {
    return jsonResponse({ error: auth.reason }, auth.status, cors);
  }

  let row: Awaited<ReturnType<typeof getSubmissionForUser>>;
  try {
    row = await getSubmissionForUser(submissionId, auth.userId, {
      supabaseUrl: env.SUPABASE_URL,
      serviceRoleKey: env.SUPABASE_SERVICE_ROLE_KEY,
    });
  } catch (err) {
    return jsonResponse({ error: `status lookup failed: ${(err as Error).message}` }, 502, cors);
  }
  // Don't differentiate "no such id" from "id belongs to another user" — both
  // resolve to 404 so attackers can't enumerate submission ids by status code.
  if (!row) {
    return jsonResponse({ error: "not found" }, 404, cors);
  }

  return jsonResponse(
    {
      submission_id: row.id,
      status: row.status,
      submitted_at: row.submitted_at,
      rejection_reason: row.rejection_reason,
      leaderboard_entry_id: row.leaderboard_entry_id,
      model_name: row.model_name,
      dataset: row.dataset,
    },
    200,
    cors,
  );
}

async function handleSubmit(
  request: Request,
  env: Env,
  ctx: ExecutionContext,
  cors: Record<string, string>,
): Promise<Response> {
  if (request.method !== "POST") {
    return jsonResponse({ error: "method not allowed" }, 405, cors);
  }
  if (!submitConfigOk(env)) {
    return jsonResponse({ error: "submissions not configured" }, 503, cors);
  }

  const token = parseBearer(request.headers.get("Authorization"));
  if (!token) {
    return jsonResponse({ error: "sign in or pass an API key to submit" }, 401, cors);
  }

  // Two auth modes share /submit:
  //   • `sb_<32-hex>` → CLI personal API key (sb-t61h). Resolved via Supabase
  //                     api_keys table, rate-limited 60/hr per key.
  //   • everything else → Supabase JWT (sb-me0f browser flow).
  // We pick the path purely by token shape so a malformed JWT never reaches
  // the api-key lookup and vice versa.
  let userId: string;
  let apiKeyId: number | null;
  if (isApiKey(token)) {
    const apiKeyConfig: ApiKeyConfig = {
      supabaseUrl: env.SUPABASE_URL,
      serviceRoleKey: env.SUPABASE_SERVICE_ROLE_KEY,
    };
    const auth = await authenticateApiKey(token, "submit", apiKeyConfig);
    if (!auth.ok) {
      return jsonResponse({ error: auth.reason }, auth.status, cors);
    }
    userId = auth.userId;
    apiKeyId = auth.keyId;
    // Best-effort touch of last_used_at — never block the submission on it.
    ctx.waitUntil(
      touchLastUsed(auth.keyId, apiKeyConfig).catch((err: unknown) => {
        console.warn("[apiKey] last_used_at touch failed", (err as Error).message);
      }),
    );
  } else {
    const claims = await verifySupabaseJwt(token, {
      supabaseUrl: env.SUPABASE_URL,
      expectedAudience: env.SUPABASE_JWT_AUD,
    });
    if (!claims) {
      return jsonResponse({ error: "invalid token" }, 401, cors);
    }
    userId = claims.sub;
    apiKeyId = null;
  }

  // Enforce a body size ceiling before parse. R2 put is happy with much
  // larger, but a 2 MB cap keeps a malicious client from tying up the
  // Worker's 128 MB memory + 30s CPU budget parsing garbage.
  const contentLength = Number(request.headers.get("Content-Length") ?? "0");
  if (contentLength > MAX_BODY_BYTES) {
    return jsonResponse({ error: "submission too large (max 2 MB)" }, 413, cors);
  }

  const rawBody = await request.text();
  if (rawBody.length > MAX_BODY_BYTES) {
    return jsonResponse({ error: "submission too large (max 2 MB)" }, 413, cors);
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(rawBody);
  } catch (err) {
    return jsonResponse({ error: `invalid JSON: ${(err as Error).message}` }, 400, cors);
  }

  const tier1 = validateTier1(parsed);
  if (!tier1.ok) {
    return jsonResponse({ error: tier1.error }, 400, cors);
  }

  const key = stagingKeyFor(userId);

  try {
    await env.SUBMISSIONS_BUCKET.put(key, rawBody, {
      httpMetadata: { contentType: "application/json" },
      customMetadata: {
        user_id: userId,
        model_name: tier1.meta.modelName ?? "",
        dataset: tier1.meta.dataset ?? "",
        // Stamp the auth path on the staged object so a forensic reader of
        // the R2 bucket can tell browser uploads from CLI uploads at a glance.
        auth_method: apiKeyId === null ? "jwt" : "api_key",
      },
    });
  } catch (err) {
    return jsonResponse({ error: `staging upload failed: ${(err as Error).message}` }, 502, cors);
  }

  let row: Awaited<ReturnType<typeof insertSubmission>>;
  try {
    row = await insertSubmission(
      {
        userId,
        filePath: key,
        requestIp: clientIpFor(request),
        userAgent: request.headers.get("User-Agent"),
        meta: tier1.meta,
        apiKeyId,
      },
      {
        supabaseUrl: env.SUPABASE_URL,
        serviceRoleKey: env.SUPABASE_SERVICE_ROLE_KEY,
      },
    );
  } catch (err) {
    return jsonResponse(
      { error: `recording submission failed: ${(err as Error).message}` },
      502,
      cors,
    );
  }

  // Dispatch the GH Actions workflow that runs the full Python validator
  // and commits to leaderboard-results/. A dispatch failure leaves the row
  // in `validating`; the operator can retry via
  //   gh workflow run process-submission.yml -f submission_id=<n> -f file_path=<k>
  // which is less bad than double-processing if the dispatch half-succeeded.
  const dispatchConfig: DispatchConfig = {
    repo: env.GITHUB_DISPATCH_REPO,
    workflowFile: env.GITHUB_DISPATCH_WORKFLOW,
    ref: env.GITHUB_DISPATCH_REF,
    token: env.GITHUB_DISPATCH_TOKEN,
  };
  try {
    await dispatchProcessWorkflow({ submissionId: row.id, filePath: key }, dispatchConfig);
  } catch (err) {
    return jsonResponse(
      {
        submission_id: row.id,
        status: row.status,
        file_path: key,
        warning: `queued but workflow dispatch failed — operator will retry: ${(err as Error).message}`,
      },
      202,
      cors,
    );
  }

  return jsonResponse(
    {
      submission_id: row.id,
      status: row.status,
      file_path: key,
      submitted_at: row.submitted_at,
    },
    202,
    cors,
  );
}
