// sb-t61h: client-side helpers for the /account API Keys section.
//
// Key generation happens entirely in the browser:
//   1. Pull 32 random hex chars from WebCrypto.
//   2. Form `sb_<hex>` and compute its sha256 + first-8 prefix.
//   3. INSERT into the api_keys table via the user's Supabase client (RLS
//      pins user_id = auth.uid()).
//   4. Show the plaintext to the user ONCE and zero out the in-memory copy.
//
// The raw key never leaves the browser except to the Worker /submit
// endpoint at the user's discretion. Even the Supabase service role can't
// reverse the stored hash to recover it.

import { getSupabaseClient } from "@/lib/auth";

export type ApiKeyScope = "read" | "submit" | "both";

export interface ApiKeyRow {
  id: number;
  name: string;
  key_prefix: string;
  scope: ApiKeyScope;
  expires_at: string | null;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface CreateApiKeyInput {
  name: string;
  scope: ApiKeyScope;
  /** Optional ISO timestamp; null/undefined means no expiry. */
  expiresAt?: string | null;
}

export interface CreateApiKeyResult {
  /** The full plaintext key — surface to the user ONCE then drop. */
  plaintext: string;
  row: ApiKeyRow;
}

/** Per-user cap. Mirrors the bead spec; UI enforces, DB does not. */
export const MAX_ACTIVE_KEYS_PER_USER = 5;

const KEY_BODY_LEN = 32;
const PREFIX_LEN = 8;

/** Generate `sb_<32-hex>` from WebCrypto. */
export function generatePlaintextKey(): string {
  const bytes = new Uint8Array(KEY_BODY_LEN / 2);
  crypto.getRandomValues(bytes);
  let body = "";
  for (const b of bytes) body += b.toString(16).padStart(2, "0");
  return `sb_${body}`;
}

/** Hex-encoded sha256 of an ASCII string. Mirrors the Worker's `sha256Hex`. */
export async function sha256Hex(input: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(input));
  const bytes = new Uint8Array(buf);
  let out = "";
  for (const b of bytes) out += b.toString(16).padStart(2, "0");
  return out;
}

export function lookupPrefix(key: string): string {
  return key.slice(0, PREFIX_LEN);
}

/**
 * List the signed-in user's api keys, newest first. Includes revoked rows so
 * the UI can render the "Revoked" badge (users can manually delete to purge).
 */
export async function listMyApiKeys(userId: string): Promise<ApiKeyRow[]> {
  const client = getSupabaseClient();
  const { data, error } = await client
    .from("api_keys")
    .select("id, name, key_prefix, scope, expires_at, created_at, last_used_at, revoked_at")
    .eq("user_id", userId)
    .order("created_at", { ascending: false });
  if (error) {
    console.warn("[apiKeys] list failed", error.message);
    return [];
  }
  return (data ?? []) as ApiKeyRow[];
}

/**
 * Mint a fresh api key. The plaintext is returned ONLY in the result and is
 * never persisted server-side; callers must surface it immediately and zero
 * any captured copy after the user has acknowledged it.
 */
export async function createApiKey(
  userId: string,
  input: CreateApiKeyInput,
): Promise<CreateApiKeyResult> {
  const trimmedName = input.name.trim();
  if (!trimmedName) throw new Error("Key name is required.");

  const plaintext = generatePlaintextKey();
  const keyHash = await sha256Hex(plaintext);
  const keyPrefix = lookupPrefix(plaintext);

  const client = getSupabaseClient();
  const { data, error } = await client
    .from("api_keys")
    .insert({
      user_id: userId,
      name: trimmedName,
      key_hash: keyHash,
      key_prefix: keyPrefix,
      scope: input.scope,
      expires_at: input.expiresAt ?? null,
    })
    .select("id, name, key_prefix, scope, expires_at, created_at, last_used_at, revoked_at")
    .single();

  if (error) throw new Error(error.message);
  if (!data) throw new Error("Key creation returned no row.");
  return { plaintext, row: data as ApiKeyRow };
}

/**
 * Flip `revoked_at = now()`. Revocation is one-way; users who want a fresh
 * key generate a new row rather than re-activating a revoked one. The RLS
 * UPDATE policy lets a user only update their own rows.
 */
export async function revokeApiKey(keyId: number): Promise<{ error: string | null }> {
  const client = getSupabaseClient();
  const { error } = await client
    .from("api_keys")
    .update({ revoked_at: new Date().toISOString() })
    .eq("id", keyId);
  return { error: error?.message ?? null };
}

/** Hard-delete a key row (typically after the user has revoked it). */
export async function deleteApiKey(keyId: number): Promise<{ error: string | null }> {
  const client = getSupabaseClient();
  const { error } = await client.from("api_keys").delete().eq("id", keyId);
  return { error: error?.message ?? null };
}

/** Pretty short label for the scope dropdown + chip. */
export function scopeLabel(scope: ApiKeyScope): string {
  switch (scope) {
    case "read":
      return "Read gated data";
    case "submit":
      return "Submit runs";
    case "both":
      return "Read + submit";
  }
}
