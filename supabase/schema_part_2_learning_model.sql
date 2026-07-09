create table if not exists public.learning_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  topic text not null,
  level text not null default 'beginner',
  goal text,
  study_plan text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.learning_resources (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  session_id uuid references public.learning_sessions(id) on delete set null,
  title text not null,
  url text not null,
  resource_type text not null check (resource_type in ('page', 'video', 'document', 'course', 'repo', 'other')),
  provider text,
  is_free boolean not null default true,
  read_status text not null default 'pending' check (read_status in ('pending', 'read', 'snippet_only', 'read_failed', 'missing_video_id', 'missing_pypdf_dependency', 'missing_youtube_transcript_dependency')),
  quality_score numeric(4, 2) default 0,
  summary text,
  why_useful text,
  raw_excerpt text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.learning_steps (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  session_id uuid not null references public.learning_sessions(id) on delete cascade,
  order_index integer not null,
  title text not null,
  goal text not null,
  task text not null,
  is_completed boolean not null default false,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (session_id, order_index)
);

create table if not exists public.resource_ingestion_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  session_id uuid references public.learning_sessions(id) on delete cascade,
  source_url text not null,
  status text not null default 'queued' check (status in ('queued', 'reading', 'summarizing', 'completed', 'failed')),
  error_message text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.user_progress (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  session_id uuid not null references public.learning_sessions(id) on delete cascade,
  resource_id uuid references public.learning_resources(id) on delete set null,
  progress_type text not null check (progress_type in ('viewed', 'read', 'watched', 'solved', 'reviewed', 'mastered')),
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists public.model_training_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  run_name text not null,
  base_model text default 'researchmind-slm',
  dataset_path text,
  status text not null default 'queued' check (status in ('queued', 'preparing_data', 'training', 'evaluating', 'completed', 'failed')),
  metrics jsonb not null default '{}'::jsonb,
  error_message text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.model_checkpoints (
  id uuid primary key default gen_random_uuid(),
  training_run_id uuid references public.model_training_runs(id) on delete cascade,
  checkpoint_path text not null,
  tokenizer_path text,
  model_config jsonb not null default '{}'::jsonb,
  eval_metrics jsonb not null default '{}'::jsonb,
  is_active boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists public.feedback_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  message_id uuid references public.messages(id) on delete set null,
  resource_id uuid references public.learning_resources(id) on delete set null,
  rating integer check (rating between 1 and 5),
  feedback text,
  created_at timestamptz not null default now()
);

drop trigger if exists learning_sessions_set_updated_at on public.learning_sessions;
create trigger learning_sessions_set_updated_at
before update on public.learning_sessions
for each row execute function public.set_updated_at();

drop trigger if exists learning_resources_set_updated_at on public.learning_resources;
create trigger learning_resources_set_updated_at
before update on public.learning_resources
for each row execute function public.set_updated_at();

alter table public.learning_sessions enable row level security;
alter table public.learning_resources enable row level security;
alter table public.learning_steps enable row level security;
alter table public.resource_ingestion_jobs enable row level security;
alter table public.user_progress enable row level security;
alter table public.model_training_runs enable row level security;
alter table public.model_checkpoints enable row level security;
alter table public.feedback_events enable row level security;

drop policy if exists "Users can manage own learning sessions" on public.learning_sessions;
create policy "Users can manage own learning sessions"
on public.learning_sessions for all
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can manage own learning resources" on public.learning_resources;
create policy "Users can manage own learning resources"
on public.learning_resources for all
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can manage own learning steps" on public.learning_steps;
create policy "Users can manage own learning steps"
on public.learning_steps for all
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can manage own ingestion jobs" on public.resource_ingestion_jobs;
create policy "Users can manage own ingestion jobs"
on public.resource_ingestion_jobs for all
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can manage own progress" on public.user_progress;
create policy "Users can manage own progress"
on public.user_progress for all
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can manage own feedback" on public.feedback_events;
create policy "Users can manage own feedback"
on public.feedback_events for all
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can read model training runs they started" on public.model_training_runs;
create policy "Users can read model training runs they started"
on public.model_training_runs for select
to authenticated
using (user_id is null or (select auth.uid()) = user_id);

drop policy if exists "Users can create own model training runs" on public.model_training_runs;
create policy "Users can create own model training runs"
on public.model_training_runs for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can read checkpoints for visible runs" on public.model_checkpoints;
create policy "Users can read checkpoints for visible runs"
on public.model_checkpoints for select
to authenticated
using (
  exists (
    select 1 from public.model_training_runs
    where model_training_runs.id = model_checkpoints.training_run_id
    and (model_training_runs.user_id is null or model_training_runs.user_id = (select auth.uid()))
  )
);

create index if not exists learning_sessions_user_id_created_at_idx
on public.learning_sessions (user_id, created_at desc);

create index if not exists learning_resources_user_session_idx
on public.learning_resources (user_id, session_id, created_at desc);

create index if not exists learning_resources_type_score_idx
on public.learning_resources (resource_type, quality_score desc);

create index if not exists learning_steps_session_order_idx
on public.learning_steps (session_id, order_index);

create index if not exists ingestion_jobs_user_status_idx
on public.resource_ingestion_jobs (user_id, status, created_at desc);

create index if not exists user_progress_session_idx
on public.user_progress (user_id, session_id, created_at desc);

create index if not exists model_training_runs_status_idx
on public.model_training_runs (status, created_at desc);
