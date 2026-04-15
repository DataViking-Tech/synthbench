// CORS handling for the data proxy. The frontend (Astro site) calls this
// Worker from synthbench.org and needs to send Authorization headers, which
// requires an allow-credentials CORS grant tied to an explicit origin (never
// `*`). Origins not on the allowlist still get responses but without CORS
// headers — the browser will then block the read, which is the correct
// outcome for unknown origins.

const ALLOWED_METHODS = "GET, HEAD, POST, OPTIONS";
const ALLOWED_HEADERS = "Authorization, Content-Type";
const MAX_AGE_SECONDS = "86400";

export function parseAllowedOrigins(raw: string | undefined): ReadonlySet<string> {
  if (!raw) return new Set();
  return new Set(
    raw
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0),
  );
}

export function corsHeadersFor(
  origin: string | null,
  allowed: ReadonlySet<string>,
): Record<string, string> {
  if (!origin || !allowed.has(origin)) {
    // No Access-Control-Allow-Origin → browser blocks cross-origin access.
    // `Vary: Origin` is still correct so caches don't leak one caller's
    // response to another.
    return { Vary: "Origin" };
  }
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": ALLOWED_METHODS,
    "Access-Control-Allow-Headers": ALLOWED_HEADERS,
    Vary: "Origin",
  };
}

export function preflightResponse(origin: string | null, allowed: ReadonlySet<string>): Response {
  const headers = corsHeadersFor(origin, allowed);
  headers["Access-Control-Max-Age"] = MAX_AGE_SECONDS;
  // 204 has no body per HTTP; keep a plain empty body to make preview logs
  // readable and avoid surprise "missing body" errors on some proxies.
  return new Response(null, { status: 204, headers });
}
