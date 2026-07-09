-- ResearchMind AI Supabase schema
-- Paste this whole file into the Supabase SQL Editor and run it once.

create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  full_name text,
  avatar_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null default 'New chat',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.user_security_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  save_chat_history boolean not null default true,
  require_action_confirmation boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

drop trigger if exists conversations_set_updated_at on public.conversations;
create trigger conversations_set_updated_at
before update on public.conversations
for each row execute function public.set_updated_at();

drop trigger if exists user_security_settings_set_updated_at on public.user_security_settings;
create trigger user_security_settings_set_updated_at
before update on public.user_security_settings
for each row execute function public.set_updated_at();

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, full_name, avatar_url)
  values (
    new.id,
    new.email,
    new.raw_user_meta_data ->> 'full_name',
    new.raw_user_meta_data ->> 'avatar_url'
  )
  on conflict (id) do nothing;

  insert into public.user_security_settings (user_id)
  values (new.id)
  on conflict (user_id) do nothing;

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

alter table public.profiles enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.user_security_settings enable row level security;

drop policy if exists "Users can read own profile" on public.profiles;
create policy "Users can read own profile"
on public.profiles for select
to authenticated
using ((select auth.uid()) = id);

drop policy if exists "Users can update own profile" on public.profiles;
create policy "Users can update own profile"
on public.profiles for update
to authenticated
using ((select auth.uid()) = id)
with check ((select auth.uid()) = id);

drop policy if exists "Users can read own conversations" on public.conversations;
create policy "Users can read own conversations"
on public.conversations for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "Users can create own conversations" on public.conversations;
create policy "Users can create own conversations"
on public.conversations for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update own conversations" on public.conversations;
create policy "Users can update own conversations"
on public.conversations for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can delete own conversations" on public.conversations;
create policy "Users can delete own conversations"
on public.conversations for delete
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "Users can read own messages" on public.messages;
create policy "Users can read own messages"
on public.messages for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "Users can create own messages" on public.messages;
create policy "Users can create own messages"
on public.messages for insert
to authenticated
with check (
  (select auth.uid()) = user_id
  and exists (
    select 1 from public.conversations
    where conversations.id = messages.conversation_id
    and conversations.user_id = (select auth.uid())
  )
);

drop policy if exists "Users can delete own messages" on public.messages;
create policy "Users can delete own messages"
on public.messages for delete
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "Users can read own security settings" on public.user_security_settings;
create policy "Users can read own security settings"
on public.user_security_settings for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "Users can update own security settings" on public.user_security_settings;
create policy "Users can update own security settings"
on public.user_security_settings for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can create own security settings" on public.user_security_settings;
create policy "Users can create own security settings"
on public.user_security_settings for insert
to authenticated
with check ((select auth.uid()) = user_id);

create index if not exists conversations_user_id_created_at_idx
on public.conversations (user_id, created_at desc);

create index if not exists messages_conversation_id_created_at_idx
on public.messages (conversation_id, created_at asc);

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
