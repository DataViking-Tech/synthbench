# Supabase schema for SynthBench

Migrations applied to the SynthBench Supabase project. Do **not** apply
manually — see [`DATABASE-MIGRATIONS.md`](../DATABASE-MIGRATIONS.md) for the
merge-to-main → CI-auto-apply discipline (sb-i8yk).

## Migrations

Filenames follow the Supabase CLI convention `<YYYYMMDDHHMMSS>_<name>.sql`.
The 14-digit timestamp is the migration version tracked in
`supabase_migrations.schema_migrations` on the remote database.

- `20260415065524_cf_gate_identity_layer.sql` — **stub backfill** (no-op
  `select 1;`). The original DDL provisioned `public.user_profiles` (sb-8o4)
  and the cf-gate identity layer via the Supabase dashboard before in-repo
  tracking existed. File exists only so the remote `schema_migrations` row
  has a matching local version for `supabase db push` reconciliation.
- `20260415065540_harden_touch_updated_at.sql` — **stub backfill** (no-op
  `select 1;`). The original DDL hardened the shared
  `public.touch_updated_at()` trigger function used by `user_profiles` and
  `data_access_log` (sb-io1), applied via the Supabase dashboard. Same
  reconciliation-only purpose as above.
- `20260415190844_submissions.sql` — creates `public.submissions` (sb-me0f). The
  Worker (`workers/data-proxy/src/submit.ts`) inserts rows when a user uploads
  via `/submit/upload`; the `process-submission` GH Action flips status to
  `published` or `rejected` after running the full Python validator against
  the staged R2 object. RLS policies: owner-read, published-row public-read,
  service-role full access.
- `20260415190854_api_keys.sql` — creates `public.api_keys` (sb-t61h). Stores
  `sb_<32-hex>` personal API keys as sha256 hashes (plaintext shown once at
  creation, never persisted). The Worker `/submit` endpoint accepts these via
  `Authorization: Bearer sb_<key>` for the `synthbench submit` CLI flow. RLS:
  authenticated users CRUD their own rows, service role bypasses for the
  Worker auth lookup + `last_used_at` touch.

The two `submissions` / `api_keys` migrations were originally applied to prod
via Supabase MCP on 2026-04-15 (violating the discipline rule, hence sb-i8yk).
Prod `schema_migrations` records versions `20260415190844` and `20260415190854`;
local filenames were renamed to match so the CI `supabase db push` skips them
as already applied.

## Pre-existing tables (schema not in this tree)

The `user_profiles` (sb-8o4) and `data_access_log` (sb-io1) tables were
provisioned via the Supabase dashboard before in-repo migration tracking. The
DDL is not reconstructed here; only the stub files above exist to satisfy
version reconciliation. Future changes to those tables must add new
migrations in this directory like any other schema change.
