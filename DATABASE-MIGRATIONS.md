# Database migrations discipline

**Status:** enforced from sb-i8yk (2026-04-15).

SynthBench uses Supabase (Postgres) as its identity + submissions store. Every
schema change is a committed migration file. Applying them to prod is the job
of CI, not of a human and not of the Supabase MCP.

## The rule

> **All production schema changes land via PR → migration file in
> `supabase/migrations/` → merge to main → `.github/workflows/supabase-migrations.yml`
> auto-applies on push.**

Nobody — not the founder, not the mayor, not a polecat — applies migrations
by hand. Specifically, these are all **forbidden** against the prod project
(`synthbench-prod`, ref `kfealsliqlvfxgoymbco`):

- Supabase MCP `apply_migration` / `execute_sql` (DDL)
- Supabase dashboard SQL editor (for DDL)
- Local `supabase db push` against the linked prod project
- Direct `psql` DDL against the prod database

The bypass is audit-hostile: the commit that landed the migration file no
longer matches when the change actually appeared in prod, and no GitHub
Actions log exists to prove the apply succeeded cleanly.

## What's allowed manually

- **Read-only SQL** (SELECTs, `\d`, advisor checks) — fine from MCP, dashboard,
  or psql.
- **Branch / preview project DDL** — fine. Only prod is locked down.
- **Break-glass** — if CI is broken and a migration must land immediately, the
  operator may apply via dashboard SQL editor and must immediately (a) file a
  bead documenting what/why/when and (b) reconcile the local filename to the
  remote `schema_migrations` version before the next merge. This is the
  situation that produced sb-i8yk; the expected frequency is zero per quarter.

## Filename convention

Supabase CLI requires `<YYYYMMDDHHMMSS>_<slug>.sql` (14-digit timestamp +
underscore + snake_case slug). The 14-digit prefix IS the version tracked in
`supabase_migrations.schema_migrations`. Date-only (`YYYYMMDD_*`) filenames
will be treated as a new version `YYYYMMDD` and will fail to match any
MCP-applied rows.

Generate a correct stub with:

```bash
supabase migration new <slug>
```

…which writes `supabase/migrations/<now>_<slug>.sql`. Edit the file, commit,
open a PR. CI will apply on merge.

## How the CI workflow works

`.github/workflows/supabase-migrations.yml` runs on:

- `push` to `main` touching `supabase/migrations/**` or the workflow itself
- `workflow_dispatch` (manual replay from the Actions tab)

It:

1. Installs the Supabase CLI (pinned version).
2. Pulls `SUPABASE_ACCESS_TOKEN` from `dataviking-platform/prd` Doppler and
   `SUPABASE_PROJECT_REF` + `SUPABASE_DB_PASSWORD` from `synthbench/prd` Doppler.
3. `supabase link --project-ref <ref>`.
4. `supabase db push --include-all` — idempotent; only applies versions not
   already in remote `schema_migrations`.
5. Verifies that every 14-digit version in `supabase/migrations/` is present
   on the remote after push. Fails the workflow if anything was silently
   skipped.

Concurrency group: `supabase-migrations` with `cancel-in-progress: false`, so
overlapping merges serialize rather than racing the schema.

## Required secrets

| Secret | Doppler project | Purpose |
| --- | --- | --- |
| `SUPABASE_ACCESS_TOKEN` | `dataviking-platform/prd` | Personal access token for `supabase link` + `db push`. Generated at <https://supabase.com/dashboard/account/tokens>. Account-wide, not project-specific. |
| `SUPABASE_PROJECT_REF` | `synthbench/prd` | Project ref `kfealsliqlvfxgoymbco` used by `supabase link`. |
| `SUPABASE_DB_PASSWORD` | `synthbench/prd` | Database password used by `supabase db push` to open a direct connection. |

The existing `DOPPLER_TOKEN` (synthbench/prd) and `DOPPLER_PLATFORM_TOKEN`
(dataviking-platform/prd read-only) GitHub Actions secrets are reused.

## Verifying a migration landed

After a PR that adds a migration merges:

1. Open the `Supabase Migrations` run on the main branch in GitHub Actions.
2. The "Verify no local-only drift" step prints both the local and remote
   version lists. They should include the new version.
3. Optional: `supabase migration list --linked` locally (read-only) confirms
   the same.

## Pre-existing remote-only migrations (backfilled as stubs)

Two migrations exist on the prod remote that were originally applied via the
Supabase dashboard before migration tracking moved in-repo (covers
`user_profiles` sb-8o4, `data_access_log` sb-io1):

- `20260415065524_cf_gate_identity_layer`
- `20260415065540_harden_touch_updated_at`

`supabase db push --include-all` rejects *remote-only* drift the same way it
rejects *local-only* drift — every version in the remote `schema_migrations`
table needs a matching file. These two are therefore backfilled as **no-op
stubs** (`select 1;` plus a header comment pointing here). The remote
`schema_migrations` rows predate the stub files, so `db push` sees the
versions as already applied and never executes the stub bodies against prod.

The real DDL lives only in the production schema and is not reconstructed
here. Future changes to those tables must add new migrations in this
directory like any other schema change.

## See also

- [`supabase/README.md`](supabase/README.md) — index of tracked migrations and
  what they provision.
- `dvinfra/docs/secrets-conventions.md` — the Doppler / GH Actions secret
  layout this workflow plugs into (external repo).
- sb-i8yk — the bead that established this discipline.
