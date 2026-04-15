-- sb-me0f: submissions table for Tier 1 web upload MVP.
--
-- Every run submitted via /submit/upload gets a row here. The Worker inserts
-- with status='validating' after uploading the raw JSON to R2 staging; the
-- process-submission GitHub Actions workflow flips status to 'published' or
-- 'rejected' once the full Python validator has run.
--
-- RLS mirrors the data_access_log pattern (sb-8o4 / sb-io1):
--   • Service role: full access (Worker insert, GH Action update).
--   • Signed-in users: read their own rows only.
--   • Anon: read rows with status='published' (public submissions feed).

create table if not exists public.submissions (
  id bigserial primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  submitted_at timestamptz not null default now(),
  model_name text,
  dataset text,
  framework text,
  n_questions int,
  file_path text not null,
  status text not null check (status in ('validating', 'rejected', 'published')),
  rejection_reason text,
  leaderboard_entry_id text,
  request_ip text,
  user_agent text
);

create index if not exists submissions_user_submitted_idx
  on public.submissions (user_id, submitted_at desc);

create index if not exists submissions_status_submitted_idx
  on public.submissions (status, submitted_at desc);

alter table public.submissions enable row level security;

-- Service role bypasses RLS (Supabase grants service_role to bypass). These
-- policies target the authenticated + anon roles used by the site and by
-- public visitors.

drop policy if exists "submissions_select_own" on public.submissions;
create policy "submissions_select_own"
  on public.submissions
  for select
  to authenticated
  using (auth.uid() = user_id);

drop policy if exists "submissions_select_published_anon" on public.submissions;
create policy "submissions_select_published_anon"
  on public.submissions
  for select
  to anon, authenticated
  using (status = 'published');

-- Authenticated users never INSERT/UPDATE/DELETE directly — all writes go
-- through the Worker (service role) or the GH Action. No policies granted
-- for those verbs means authenticated requests are denied by default.
