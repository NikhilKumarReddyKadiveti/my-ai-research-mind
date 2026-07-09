-- Optional ResearchMind user API key sync patch.
-- Run this after schema.sql on existing projects to let signed-in users sync
-- encrypted personal AI provider keys across devices.

create table if not exists public.user_api_keys (
  user_id uuid primary key references auth.users(id) on delete cascade,
  provider text not null default 'auto' check (provider in ('auto', 'gemini', 'openai')),
  encrypted_api_key text not null,
  key_hint text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists user_api_keys_set_updated_at on public.user_api_keys;
create trigger user_api_keys_set_updated_at
before update on public.user_api_keys
for each row execute function public.set_updated_at();

alter table public.user_api_keys enable row level security;

drop policy if exists "Users can read own encrypted api key settings" on public.user_api_keys;
create policy "Users can read own encrypted api key settings"
on public.user_api_keys for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "Users can create own encrypted api key settings" on public.user_api_keys;
create policy "Users can create own encrypted api key settings"
on public.user_api_keys for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update own encrypted api key settings" on public.user_api_keys;
create policy "Users can update own encrypted api key settings"
on public.user_api_keys for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can delete own encrypted api key settings" on public.user_api_keys;
create policy "Users can delete own encrypted api key settings"
on public.user_api_keys for delete
to authenticated
using ((select auth.uid()) = user_id);
