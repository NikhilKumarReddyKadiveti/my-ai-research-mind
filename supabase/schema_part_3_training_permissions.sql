-- Optional ResearchMind training permissions patch.
-- Run this after schema.sql if you want authenticated users to update their
-- own training runs and create checkpoints for those runs.

drop policy if exists "Users can update own model training runs" on public.model_training_runs;
create policy "Users can update own model training runs"
on public.model_training_runs for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Users can create checkpoints for own runs" on public.model_checkpoints;
create policy "Users can create checkpoints for own runs"
on public.model_checkpoints for insert
to authenticated
with check (
  exists (
    select 1 from public.model_training_runs
    where model_training_runs.id = model_checkpoints.training_run_id
    and model_training_runs.user_id = (select auth.uid())
  )
);
