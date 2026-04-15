# Supabase schema for SynthBench

Migrations applied to the SynthBench Supabase project. Apply with:

```bash
# From the Supabase dashboard SQL editor, or:
supabase db push
```

## Migrations

- `20260415_submissions.sql` — creates `public.submissions` (sb-me0f). The
  Worker (`workers/data-proxy/src/submit.ts`) inserts rows when a user uploads
  via `/submit/upload`; the `process-submission` GH Action flips status to
  `published` or `rejected` after running the full Python validator against
  the staged R2 object. RLS policies: owner-read, published-row public-read,
  service-role full access.

## Pre-existing tables (not in this tree)

The `user_profiles` (sb-8o4) and `data_access_log` (sb-io1) tables were
provisioned via the Supabase dashboard before we started tracking migrations
in-repo. Future changes should add new migrations here.
