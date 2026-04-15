// sb-sj6: client-side data fetcher that routes gated-tier requests to the
// Cloudflare Worker proxy with a Supabase JWT, and full-tier requests to the
// static Pages origin.
//
// Consumers call `fetchTieredJson(path, {dataset})`:
//   • ``full`` (or unknown) datasets → ``<BASE_URL>/data/<path>``
//   • ``gated`` datasets → ``<PUBLIC_GATED_API_BASE>/<path>`` with
//     ``Authorization: Bearer <jwt>`` from the current Supabase session
//
// A 401/403 response on the gated path surfaces as ``{ok:false, gated:true}``
// so the caller can swap the UI to a sign-in gate instead of a generic error
// state. Every other failure returns ``{ok:false, gated:false, status, ...}``.

import { getSession, isAuthConfigured, withBase } from "@/lib/auth";
import type { DatasetPolicyEntry, RedistributionPolicy } from "@/types/leaderboard";

/** Resolved tier for a dataset, as returned by `lookupDatasetTier`. */
export type ResolvedTier = RedistributionPolicy | "unknown";

/** Result of a tiered fetch. Callers branch on `ok` and `gated`. */
export type TieredFetchResult<T> =
  | { ok: true; data: T; tier: ResolvedTier }
  | { ok: false; gated: true; tier: "gated"; status: number; message: string }
  | { ok: false; gated: false; tier: ResolvedTier; status: number; message: string };

/** Runtime config read from Vite env. Missing gated base disables gated fetches. */
interface RuntimeConfig {
  base: string;
  gatedApiBase: string | null;
}

function getRuntimeConfig(): RuntimeConfig {
  const rawBase = import.meta.env.BASE_URL || "/";
  const base = rawBase.endsWith("/") ? rawBase.slice(0, -1) : rawBase;
  const gated = (import.meta.env.PUBLIC_GATED_API_BASE as string | undefined) ?? null;
  const gatedApiBase = gated ? gated.replace(/\/$/, "") : null;
  return { base, gatedApiBase };
}

/**
 * Resolve a dataset's tier from the leaderboard policy manifest. Caller
 * passes the already-loaded `dataset_policies` array (shipped in
 * leaderboard.json) so this module stays fetch-free for pages that have
 * the manifest in scope.
 */
export function lookupDatasetTier(
  datasetName: string,
  manifest: DatasetPolicyEntry[] | null | undefined,
): ResolvedTier {
  if (!manifest) return "unknown";
  // Strip country/year filter suffixes like "gss (2018)" — the publish step
  // keys the manifest on the bare adapter name (see `_base_name` in
  // `datasets/policy.py`).
  const base = datasetName.split(" ", 1)[0]?.trim() ?? datasetName;
  const hit = manifest.find((p) => p.name === base);
  return hit ? hit.redistribution_policy : "unknown";
}

async function buildAuthHeaders(): Promise<Record<string, string>> {
  if (!isAuthConfigured()) return {};
  const session = await getSession();
  if (!session?.access_token) return {};
  return { Authorization: `Bearer ${session.access_token}` };
}

/**
 * Fetch a tier-aware JSON artifact.
 *
 * @param path artifact path relative to the data root, e.g. `run/<id>.json`,
 *             `config/<id>.json`, `question/<dataset>/<key>.json`.
 * @param tier the dataset's redistribution tier, resolved via
 *             `lookupDatasetTier`. Pass `"unknown"` when the caller can't
 *             resolve the tier — the fetcher falls back to the local path,
 *             which is the right answer for tier-less artifacts like
 *             `runs-index.json`.
 */
export async function fetchTieredJson<T>(
  path: string,
  tier: ResolvedTier,
): Promise<TieredFetchResult<T>> {
  const { base, gatedApiBase } = getRuntimeConfig();
  const cleanPath = path.replace(/^\//, "");

  if (tier === "gated") {
    if (!gatedApiBase) {
      return {
        ok: false,
        gated: false,
        tier,
        status: 0,
        message: "Gated data origin is not configured (set PUBLIC_GATED_API_BASE).",
      };
    }
    const headers = await buildAuthHeaders();
    const url = `${gatedApiBase}/data/${cleanPath}`;
    let res: Response;
    try {
      res = await fetch(url, { headers });
    } catch (err) {
      return {
        ok: false,
        gated: false,
        tier,
        status: 0,
        message: err instanceof Error ? err.message : String(err),
      };
    }
    if (res.status === 401 || res.status === 403) {
      return {
        ok: false,
        gated: true,
        tier: "gated",
        status: res.status,
        message:
          res.status === 401
            ? "Sign in to view per-question data for this dataset."
            : "This account is not yet authorized for gated-tier access.",
      };
    }
    if (!res.ok) {
      return {
        ok: false,
        gated: false,
        tier,
        status: res.status,
        message: `HTTP ${res.status} loading ${url}`,
      };
    }
    const data = (await res.json()) as T;
    return { ok: true, data, tier };
  }

  // full / unknown → static Pages origin.
  const url = `${base}/data/${cleanPath}`;
  let res: Response;
  try {
    res = await fetch(url);
  } catch (err) {
    return {
      ok: false,
      gated: false,
      tier,
      status: 0,
      message: err instanceof Error ? err.message : String(err),
    };
  }
  if (!res.ok) {
    return {
      ok: false,
      gated: false,
      tier,
      status: res.status,
      message: `HTTP ${res.status} loading ${url}`,
    };
  }
  const data = (await res.json()) as T;
  return { ok: true, data, tier };
}

/**
 * Render a sign-in gate into the given container element. Exported so
 * page-specific scripts can swap their "loading" state out for the gate
 * when a `gated:true` result comes back.
 */
export function renderSignInGate(
  container: HTMLElement,
  opts: { datasetLabel?: string | null; message?: string } = {},
): void {
  const label = opts.datasetLabel ? ` for ${escapeHtml(opts.datasetLabel)}` : "";
  const message =
    opts.message ?? `Per-question distributions${label} require a verified research-use account.`;
  const accountHref = withBase("account/");
  const nextPath =
    typeof window !== "undefined" ? window.location.pathname + window.location.search : "";
  const signInHref = `${accountHref}?next=${encodeURIComponent(nextPath)}`;
  container.innerHTML = `
    <div class="rounded-lg border border-muted/30 bg-muted/5 p-5 text-sm">
      <strong class="block mb-1">Sign in to view per-question distributions</strong>
      <p class="text-muted">${escapeHtml(message)}</p>
      <div class="mt-3">
        <a
          href="${signInHref}"
          class="inline-block rounded bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:opacity-90"
        >
          Sign in
        </a>
      </div>
    </div>
  `;
}

function escapeHtml(s: unknown): string {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
