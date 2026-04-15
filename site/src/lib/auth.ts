// sb-8o4: identity layer for the gated tier.
//
// Everything here is browser-only — the site is statically rendered and there
// is no Astro server runtime. The Supabase client is constructed lazily so a
// missing PUBLIC_SUPABASE_URL/PUBLIC_SUPABASE_ANON_KEY at build time does not
// crash the build (CI typecheck/build runs without secrets). At runtime the
// auth UI surfaces a clear "auth unavailable" state instead.

import {
  type AuthError,
  type Provider,
  type Session,
  type SupabaseClient,
  type User,
  createClient,
} from "@supabase/supabase-js";

export type AuthProvider = Extract<Provider, "github" | "google">;

export interface UserProfile {
  id: string;
  research_purpose: string | null;
  affiliation: string | null;
  created_at: string;
  updated_at: string;
}

let cachedClient: SupabaseClient | null = null;

export function isAuthConfigured(): boolean {
  return Boolean(import.meta.env.PUBLIC_SUPABASE_URL && import.meta.env.PUBLIC_SUPABASE_ANON_KEY);
}

export function getSupabaseClient(): SupabaseClient {
  if (cachedClient) return cachedClient;
  const url = import.meta.env.PUBLIC_SUPABASE_URL;
  const key = import.meta.env.PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) {
    throw new Error(
      "Supabase auth is not configured: set PUBLIC_SUPABASE_URL and PUBLIC_SUPABASE_ANON_KEY.",
    );
  }
  cachedClient = createClient(url, key, {
    auth: {
      // Persist the session in localStorage and detect ?code= / #access_token=
      // automatically when the OAuth provider redirects back to /auth/callback.
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
      flowType: "pkce",
    },
  });
  return cachedClient;
}

// Resolve a path relative to the configured Astro base, e.g. "/synthbench/account/".
// Uses BASE_URL injected by Vite at build time so links work under both the
// GH Pages prefix and the Cloudflare Pages root mount.
export function withBase(path: string): string {
  const rawBase = import.meta.env.BASE_URL || "/";
  const base = rawBase.endsWith("/") ? rawBase : `${rawBase}/`;
  const trimmed = path.startsWith("/") ? path.slice(1) : path;
  return `${base}${trimmed}`;
}

export function buildAbsoluteUrl(path: string): string {
  if (typeof window === "undefined") {
    // Server-side prerender — fall back to the Astro site URL. Only used to
    // construct the OAuth redirect_to default; client always overrides.
    const site = import.meta.env.SITE || "";
    return `${site.replace(/\/$/, "")}${withBase(path)}`;
  }
  return new URL(withBase(path), window.location.origin).toString();
}

export async function getSession(): Promise<Session | null> {
  if (!isAuthConfigured()) return null;
  const { data, error } = await getSupabaseClient().auth.getSession();
  if (error) {
    console.warn("[auth] getSession failed", error.message);
    return null;
  }
  return data.session;
}

export async function getUser(): Promise<User | null> {
  const session = await getSession();
  return session?.user ?? null;
}

export interface RequireAuthOptions {
  // Where to send the user after successful sign-in. Defaults to current URL.
  returnTo?: string;
  // Path of the sign-in page to redirect to when no session is present.
  signInPath?: string;
}

// Browser-only guard. Returns the current user if signed in; otherwise
// redirects to the sign-in page with a `next=` parameter and resolves to
// null (caller should bail out of further work).
export async function requireAuth(options: RequireAuthOptions = {}): Promise<User | null> {
  const user = await getUser();
  if (user) return user;
  if (typeof window === "undefined") return null;
  const returnTo = options.returnTo ?? window.location.pathname + window.location.search;
  const signIn = withBase(options.signInPath ?? "account/");
  const next = encodeURIComponent(returnTo);
  window.location.replace(`${signIn}?next=${next}`);
  return null;
}

export async function signInWithProvider(
  provider: AuthProvider,
  redirectPath = "auth/callback/",
): Promise<{ error: AuthError | null }> {
  const client = getSupabaseClient();
  const redirectTo = buildAbsoluteUrl(redirectPath);
  const { error } = await client.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo,
    },
  });
  return { error };
}

export async function signOut(): Promise<{ error: AuthError | null }> {
  if (!isAuthConfigured()) return { error: null };
  const { error } = await getSupabaseClient().auth.signOut();
  return { error };
}

export async function getProfile(userId: string): Promise<UserProfile | null> {
  const { data, error } = await getSupabaseClient()
    .from("user_profiles")
    .select("id, research_purpose, affiliation, created_at, updated_at")
    .eq("id", userId)
    .maybeSingle();
  if (error) {
    console.warn("[auth] getProfile failed", error.message);
    return null;
  }
  return data as UserProfile | null;
}

export interface ProfileInput {
  research_purpose: string;
  affiliation: string;
}

export async function upsertProfile(
  userId: string,
  input: ProfileInput,
): Promise<{ error: string | null }> {
  const { error } = await getSupabaseClient()
    .from("user_profiles")
    .upsert(
      {
        id: userId,
        research_purpose: input.research_purpose.trim() || null,
        affiliation: input.affiliation.trim() || null,
      },
      { onConflict: "id" },
    );
  return { error: error?.message ?? null };
}

// Validates the `next=` query parameter so we never send users to off-site
// URLs after sign-in. Only same-origin paths starting with the Astro base
// prefix are allowed; everything else falls back to the home page.
export function safeNextPath(rawNext: string | null): string {
  const fallback = withBase("");
  if (!rawNext) return fallback;
  let decoded: string;
  try {
    decoded = decodeURIComponent(rawNext);
  } catch {
    return fallback;
  }
  if (!decoded.startsWith("/")) return fallback;
  if (decoded.startsWith("//")) return fallback;
  const base = withBase("");
  // Allow paths under the configured base (or the bare "/" base) only.
  if (base === "/" ? decoded.startsWith("/") : decoded.startsWith(base)) {
    return decoded;
  }
  return fallback;
}
