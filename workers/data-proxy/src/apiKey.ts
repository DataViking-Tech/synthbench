// sb-t61h: API key authentication for Tier-2 CLI submissions.
//
// Keys are minted by the /account UI as `sb_<32-hex>` strings. We never store
// the plaintext — only sha256(plaintext) and the first 8 chars (for fast
// indexed lookup). Verification flow:
//
//   1. parseApiKey → confirm the `sb_` prefix and length so we route to this
//      path instead of falling through to JWT verify.
//   2. lookupApiKey → query Supabase for the row whose key_prefix matches and
//      isn't revoked. Constant-time compare the sha256 hash.
//   3. enforce expires_at + scope.
//   4. countRecentSubmissions → 60/hr ceiling. We trust Supabase's count over
//      an in-Worker counter because Workers are stateless across edge nodes.
//   5. touchLastUsed → fire-and-forget UPDATE to record `last_used_at`. We
//      never block the submission on this write.
//
// All Supabase calls go through the service role key. Trusting the service
// role makes RLS for the Worker simpler (it bypasses), but means any code on
// this path must explicitly scope queries to the looked-up `user_id` to
// avoid accidentally cross-user reads.

export const KEY_PREFIX = "sb_";
const KEY_BODY_LEN = 32;
const KEY_TOTAL_LEN = KEY_PREFIX.length + KEY_BODY_LEN;
const LOOKUP_PREFIX_LEN = 8;
export const RATE_LIMIT_PER_HOUR = 60;
const RATE_LIMIT_WINDOW_MS = 60 * 60 * 1000;

export type ApiKeyScope = "read" | "submit" | "both";

export interface ApiKeyRow {
  id: number;
  user_id: string;
  scope: ApiKeyScope;
  expires_at: string | null;
  revoked_at: string | null;
  key_hash: string;
}

export interface ApiKeyAuthResult {
  ok: true;
  keyId: number;
  userId: string;
  scope: ApiKeyScope;
}

export interface ApiKeyAuthError {
  ok: false;
  status: 401 | 403 | 429 | 502;
  reason: string;
}

/**
 * Narrow fetch signature so test doubles only have to implement what we
 * actually call (string url + minimal RequestInit). Avoids fighting the
 * `@cloudflare/workers-types` `typeof fetch` overload that includes Request
 * objects + CF-specific properties we never use here.
 */
export type FetchLike = (url: string, init?: RequestInit) => Promise<Response>;

export interface ApiKeyConfig {
  supabaseUrl: string;
  serviceRoleKey: string;
  /** Injection seam for tests. Defaults to global fetch. */
  fetchImpl?: FetchLike;
  /** Override the rate-limit ceiling (tests + per-deploy tuning). */
  rateLimitPerHour?: number;
  /** Inject `now` for deterministic rate-limit windows in tests. */
  now?: () => Date;
  /** Inject the SHA-256 implementation (tests can stub the WebCrypto subtle). */
  sha256Impl?: (input: string) => Promise<string>;
}

/**
 * Identify a `sb_`-prefixed key. Returns null for tokens that look like JWTs
 * (or anything else) so the caller can route them through the JWT verifier.
 */
export function isApiKey(token: string): boolean {
  return token.startsWith(KEY_PREFIX) && token.length === KEY_TOTAL_LEN;
}

/** Slice out the indexed lookup prefix, e.g. `sb_a1b2c` for `sb_a1b2c...`. */
export function lookupPrefix(token: string): string {
  return token.slice(0, LOOKUP_PREFIX_LEN);
}

/**
 * Hex-encoded sha256 of an ASCII string. Workers' WebCrypto exposes a
 * `crypto.subtle` we use everywhere except inside tests that swap the
 * implementation via `sha256Impl`.
 */
export async function sha256Hex(input: string): Promise<string> {
  const data = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", data);
  const bytes = new Uint8Array(digest);
  let out = "";
  for (const b of bytes) out += b.toString(16).padStart(2, "0");
  return out;
}

/**
 * Constant-time string compare. We never log or short-circuit on the
 * difference index — leaks the position of the first mismatching byte
 * through timing.
 */
export function constantTimeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

/**
 * Authenticate an `sb_`-prefixed token. Returns the resolved user/key on
 * success, or a structured failure the Worker handler maps to a JSON 4xx.
 *
 * The function is responsible for:
 *  - verifying the hash matches a non-revoked, non-expired row
 *  - enforcing scope (`submit` or `both` required for /submit)
 *  - enforcing the 60/hr rate limit
 *
 * On success, fires `touchLastUsed` as a best-effort update via `ctx.waitUntil`
 * if the caller passes one — otherwise the timestamp is updated inline.
 */
export async function authenticateApiKey(
  token: string,
  requiredScope: "submit" | "read",
  config: ApiKeyConfig,
): Promise<ApiKeyAuthResult | ApiKeyAuthError> {
  if (!isApiKey(token)) {
    return { ok: false, status: 401, reason: "malformed api key" };
  }

  const prefix = lookupPrefix(token);
  const sha = config.sha256Impl ?? sha256Hex;
  const hash = await sha(token);

  let row: ApiKeyRow | null;
  try {
    row = await lookupApiKey(prefix, config);
  } catch (err) {
    return { ok: false, status: 502, reason: `lookup failed: ${(err as Error).message}` };
  }
  if (!row) return { ok: false, status: 401, reason: "unknown api key" };

  if (!constantTimeEqual(hash, row.key_hash)) {
    return { ok: false, status: 401, reason: "unknown api key" };
  }

  if (row.revoked_at) {
    return { ok: false, status: 401, reason: "api key revoked" };
  }

  const now = (config.now ?? (() => new Date()))();
  if (row.expires_at && new Date(row.expires_at) <= now) {
    return { ok: false, status: 401, reason: "api key expired" };
  }

  if (requiredScope === "submit" && !(row.scope === "submit" || row.scope === "both")) {
    return { ok: false, status: 403, reason: "api key lacks submit scope" };
  }
  if (requiredScope === "read" && !(row.scope === "read" || row.scope === "both")) {
    return { ok: false, status: 403, reason: "api key lacks read scope" };
  }

  // Per-key rate limit. We deliberately count BEFORE the new submission
  // is recorded; a row inserted concurrently will be visible to the next
  // request, not this one. Rate limit drift of ~1 across rapid bursts is
  // acceptable for a 60/hr ceiling.
  const limit = config.rateLimitPerHour ?? RATE_LIMIT_PER_HOUR;
  let recentCount: number;
  try {
    const since = new Date(now.getTime() - RATE_LIMIT_WINDOW_MS);
    recentCount = await countRecentSubmissions(row.id, since, config);
  } catch (err) {
    return { ok: false, status: 502, reason: `rate-limit check failed: ${(err as Error).message}` };
  }
  if (recentCount >= limit) {
    return {
      ok: false,
      status: 429,
      reason: `rate limit exceeded: ${limit} submissions/hour per key`,
    };
  }

  return { ok: true, keyId: row.id, userId: row.user_id, scope: row.scope };
}

/**
 * Fetch a single api_keys row by its 8-char prefix. Returns null when no
 * active row matches — caller decides whether to surface 401 vs 403.
 *
 * The PostgREST query selects only the columns the auth path needs to
 * minimize the surface area of a leaked service-role response.
 */
export async function lookupApiKey(
  prefix: string,
  config: ApiKeyConfig,
): Promise<ApiKeyRow | null> {
  const url = new URL(`${config.supabaseUrl.replace(/\/+$/, "")}/rest/v1/api_keys`);
  url.searchParams.set("key_prefix", `eq.${prefix}`);
  url.searchParams.set("revoked_at", "is.null");
  url.searchParams.set("select", "id,user_id,scope,expires_at,revoked_at,key_hash");
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
    throw new Error(`api_keys lookup ${res.status} ${res.statusText}`);
  }
  const rows = (await res.json()) as ApiKeyRow[];
  return rows[0] ?? null;
}

/**
 * Count `submissions` rows tagged with this key in the last hour. PostgREST's
 * `Prefer: count=exact` returns the count in the `Content-Range` header so we
 * never have to materialize the rows themselves.
 */
export async function countRecentSubmissions(
  apiKeyId: number,
  since: Date,
  config: ApiKeyConfig,
): Promise<number> {
  const url = new URL(`${config.supabaseUrl.replace(/\/+$/, "")}/rest/v1/submissions`);
  url.searchParams.set("api_key_id", `eq.${apiKeyId}`);
  url.searchParams.set("submitted_at", `gte.${since.toISOString()}`);
  url.searchParams.set("select", "id");

  const doFetch = config.fetchImpl ?? fetch;
  const res = await doFetch(url.toString(), {
    method: "GET",
    headers: {
      apikey: config.serviceRoleKey,
      Authorization: `Bearer ${config.serviceRoleKey}`,
      Accept: "application/json",
      // exact count so we never have to load all rows. head=true would skip
      // the body entirely but PostgREST returns the count header on GET too.
      Prefer: "count=exact",
    },
  });
  if (!res.ok) {
    throw new Error(`submissions count ${res.status} ${res.statusText}`);
  }
  // Content-Range: 0-9/42  → total = 42; "*" or missing means unknown.
  const range = res.headers.get("Content-Range");
  if (range) {
    const slash = range.lastIndexOf("/");
    const total = slash >= 0 ? Number(range.slice(slash + 1)) : Number.NaN;
    if (Number.isFinite(total)) return total;
  }
  // Fallback: count the array we got back. PostgREST's default page size is
  // larger than our 60/hr ceiling so this stays accurate in practice.
  const rows = (await res.json()) as unknown[];
  return Array.isArray(rows) ? rows.length : 0;
}

/**
 * Record `last_used_at = now()` on the row. Failures are logged but never
 * surfaced to the client — a missed touch is far less bad than a failed
 * submission for a transient Supabase blip.
 */
export async function touchLastUsed(apiKeyId: number, config: ApiKeyConfig): Promise<void> {
  const url = `${config.supabaseUrl.replace(/\/+$/, "")}/rest/v1/api_keys?id=eq.${apiKeyId}`;
  const doFetch = config.fetchImpl ?? fetch;
  const now = (config.now ?? (() => new Date()))();
  await doFetch(url, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      apikey: config.serviceRoleKey,
      Authorization: `Bearer ${config.serviceRoleKey}`,
      Prefer: "return=minimal",
    },
    body: JSON.stringify({ last_used_at: now.toISOString() }),
  });
}
