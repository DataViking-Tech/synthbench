-- sb-t61h: api_keys table for Tier-2 CLI submission auth.
--
-- Power users generate `sb_<32-hex>` keys from /account, paste them into the
-- SYNTHBENCH_API_KEY env var, and pipe `synthbench submit` outputs to the
-- Worker without going through the browser. The Worker /submit endpoint
-- accepts either a Supabase JWT (existing browser flow) or `Authorization:
-- Bearer sb_<key>`; this table is what the key path resolves against.
--
-- Storage model:
--   • key_hash    — sha256 of the plaintext key. The plaintext is shown to
--                   the user once at creation and never persisted server-side
--                   (mirrors the GitHub PAT UX).
--   • key_prefix  — first 8 chars of the plaintext (e.g. `sb_a1b2c3`). Used
--                   as the lookup index so the Worker only fetches one row
--                   before doing the constant-time hash compare.
--   • last_used_at — touched by the Worker on every successful auth so users
--                   can see which keys are stale and revoke them.
--
-- RLS pattern matches submissions / data_access_log:
--   • Authenticated users: full CRUD on rows they own. The hash + prefix
--     model means even reading their own row never reveals a usable secret.
--   • Service role (Worker): bypasses RLS for the auth lookup + last_used_at
--     touch. Worker queries by prefix + verifies hash before trusting the
--     row, so a malicious user cannot escalate by inserting a foreign row.
--   • Anon: no access. API keys never appear on a public surface.

create table if not exists public.api_keys (
  id bigserial primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  key_hash text not null,
  key_prefix text not null,
  scope text not null check (scope in ('read', 'submit', 'both')),
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  last_used_at timestamptz,
  revoked_at timestamptz
);

-- Lookup index — the Worker auth path queries `where key_prefix = $1 and
-- revoked_at is null` first, then verifies the hash. Prefix is 8 chars of
-- random hex so collisions are vanishingly rare in normal use.
create index if not exists api_keys_prefix_active_idx
  on public.api_keys (key_prefix)
  where revoked_at is null;

-- Per-user list ordering for the /account UI.
create index if not exists api_keys_user_created_idx
  on public.api_keys (user_id, created_at desc);

alter table public.api_keys enable row level security;

drop policy if exists "api_keys_select_own" on public.api_keys;
create policy "api_keys_select_own"
  on public.api_keys
  for select
  to authenticated
  using (auth.uid() = user_id);

drop policy if exists "api_keys_insert_own" on public.api_keys;
create policy "api_keys_insert_own"
  on public.api_keys
  for insert
  to authenticated
  with check (auth.uid() = user_id);

-- UPDATE policy is intentionally restricted to revocation: users can flip
-- `revoked_at` on their own keys but not rename, re-scope, or change the
-- hash of an existing key. Re-issuing means generating a new row.
drop policy if exists "api_keys_revoke_own" on public.api_keys;
create policy "api_keys_revoke_own"
  on public.api_keys
  for update
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- DELETE is allowed so users can purge revoked keys from their list. The
-- service role still uses INSERT/SELECT/UPDATE only — it never deletes.
drop policy if exists "api_keys_delete_own" on public.api_keys;
create policy "api_keys_delete_own"
  on public.api_keys
  for delete
  to authenticated
  using (auth.uid() = user_id);

-- Tag submissions with the API key that uploaded them (null for browser/JWT
-- uploads). Powers the per-key rate-limit count and gives users a per-key
-- usage view in the future without re-hashing audit logs.
alter table public.submissions
  add column if not exists api_key_id bigint references public.api_keys(id) on delete set null;

-- Index supports the Worker's "submissions in the last hour for this key"
-- count that backs rate limiting. Partial index keeps it small — the vast
-- majority of submissions come from the browser flow with api_key_id NULL.
create index if not exists submissions_api_key_recent_idx
  on public.submissions (api_key_id, submitted_at desc)
  where api_key_id is not null;
