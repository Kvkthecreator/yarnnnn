-- 229_security_enable_rls_on_tasks.sql
-- Security audit (2026-08-01, Phase 2): CLOSE the tasks RLS gap.
--
-- FINDING: `public.tasks` (the thin scheduling index — user_id, workspace_id,
-- slug, schedule, next_run_at) has had CREATE POLICY statements attached since
-- migration 129 (and member-read added in 227), but NO migration ever ran
-- `ALTER TABLE tasks ENABLE ROW LEVEL SECURITY`. With RLS disabled, every
-- attached policy is INERT: the table is governed only by the default
-- `authenticated` grant, so a raw PostgREST request to /rest/v1/tasks (bypassing
-- the API's own .eq("user_id", …) filters in routes/radar.py) returns EVERY
-- user's scheduling rows — a cross-tenant metadata leak (which recurrences a
-- workspace runs, on what cadence).
--
-- The scheduler (api/jobs/unified_scheduler.py) reads tasks via the SERVICE
-- client, which bypasses RLS — so enabling RLS does not affect scheduling.
-- The user-facing reader is routes/radar.py via auth.client, which SHOULD be
-- RLS-bound; these policies make that real.

ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;

-- Owner/self write+read: the principal whose user_id owns the row, or the
-- owner of the row's workspace. Covers the legacy per-user rows (workspace_id
-- NULL) and the workspace-keyed rows (post-ADR-407).
DROP POLICY IF EXISTS "Owner manages own tasks" ON public.tasks;
CREATE POLICY "Owner manages own tasks"
  ON public.tasks
  FOR ALL
  USING (
    user_id = auth.uid()
    OR (workspace_id IS NOT NULL AND public.is_workspace_member(workspace_id))
  )
  WITH CHECK (
    user_id = auth.uid()
    OR (workspace_id IS NOT NULL AND public.is_workspace_member(workspace_id))
  );

-- Member read reach (re-declares the intent of migration 227, which was inert
-- while RLS was off). Additive/permissive: OR-combines with the owner policy
-- for SELECT. Members read, but write only through the owner policy's grant.
DROP POLICY IF EXISTS "Members read workspace tasks" ON public.tasks;
CREATE POLICY "Members read workspace tasks"
  ON public.tasks
  FOR SELECT
  USING (
    workspace_id IS NOT NULL
    AND public.is_workspace_member(workspace_id)
  );

COMMENT ON TABLE public.tasks IS
  'Thin scheduling index (ADR-231). RLS ENABLED 2026-08-01 (mig 229) — policies were inert before. Scheduler reads via service client (RLS bypass).';
