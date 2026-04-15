# Supabase schema for SynthBench

Migrations applied to the SynthBench Supabase project. Do **not** apply
manually — see [`DATABASE-MIGRATIONS.md`](../DATABASE-MIGRATIONS.md) for the
merge-to-main → CI-auto-apply discipline (sb-i8yk).

## Migrations

Filenames follow the Supabase CLI convention `<YYYYMMDDHHMMSS>_<name>.sql`.
The 14-digit timestamp is the migration version tracked in
`supabase_migrations.schema_migrations` on the remote database.

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

Both were originally applied to prod via Supabase MCP on 2026-04-15
(violating the discipline rule, hence sb-i8yk). Prod `schema_migrations`
records versions `20260415190844` and `20260415190854`; local filenames were
renamed to match so the CI `supabase db push` skips them as already applied.

## Pre-existing tables (not in this tree)

The `user_profiles` (sb-8o4) and `data_access_log` (sb-io1) tables were
provisioned via the Supabase dashboard before we started tracking migrations
in-repo. Their MCP-recorded migrations (`20260415065524_cf_gate_identity_layer`,
`20260415065540_harden_touch_updated_at`) exist on the remote but are not in
this tree — `supabase db push` only cares that local migrations are applied,
so remote-only rows are harmless. Future changes must add new migrations here.
