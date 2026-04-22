-- Migration 156: ADR-207 P2 Mandate backfill + Obs 07 orphan-run reap
--
-- Two independent-but-cohesive changes landing together:
--
-- 1. ADR-207 P2: backfill empty MANDATE.md skeleton at
--    `/workspace/context/_shared/MANDATE.md` for every workspace that
--    doesn't already have one. Skeleton matches the shape workspace_init
--    now seeds on fresh signup. Operators author real content via
--    `UpdateContext(target="mandate")`; the hard gate in ManageTask
--    prevents task scaffolding until the file is non-skeleton.
--
-- 2. Obs 07 fix: reap any `agent_runs` rows stuck in status='generating'
--    for >10 minutes at migration time. Forward-going, the unified_scheduler
--    watchdog (ticked every 5 min) does this continuously.

BEGIN;

-- Step 1: Backfill MANDATE.md skeleton
-- -----------------------------------
-- Per-workspace (by owner user_id). Skip if a row already exists at that path.

INSERT INTO public.workspace_files (user_id, path, content, summary, created_at, updated_at)
SELECT
  w.owner_id,
  '/workspace/context/_shared/MANDATE.md',
  E'# Mandate\n\n<!-- This file declares what this workspace is running.\n     Authored via YARNNN conversation at first use; revised when\n     the operator decides. No forced revision cadence. -->\n\n## Primary Action\n_<not yet declared — talk to YARNNN to author your mandate>_\n\n## Success Criteria\n\n## Boundary Conditions\n',
  'Mandate skeleton — workspace north star (ADR-207 P2 backfill)',
  now(),
  now()
FROM public.workspaces w
WHERE w.owner_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM public.workspace_files wf
    WHERE wf.user_id = w.owner_id
      AND wf.path = '/workspace/context/_shared/MANDATE.md'
  );

-- Step 2: Reap stuck agent_runs
-- -----------------------------
-- Obs 07 (docs/alpha/observations/2026-04-22-adr206-trader-e2e-07.md):
-- agent_runs rows stuck in 'generating' status with no completion are
-- orphaned by deploy restarts, OOMs, or upstream API failures that
-- didn't propagate status. Flip to 'error' with a diagnostic.

UPDATE public.agent_runs
SET
  status = 'failed',
  final_content = '[watchdog-migration] Run orphaned at migration 156 — generating status exceeded 10 minutes. Likely a pre-ADR-207 deploy/OOM interruption or silent upstream failure. Re-trigger the task to retry.'
WHERE status = 'generating'
  AND created_at < (now() - interval '10 minutes');

COMMIT;

-- Sanity checks
DO $$
DECLARE
  mandate_count INT;
  workspace_count INT;
  stuck_remaining INT;
BEGIN
  SELECT COUNT(*) INTO workspace_count FROM public.workspaces WHERE owner_id IS NOT NULL;
  SELECT COUNT(*) INTO mandate_count FROM public.workspace_files WHERE path = '/workspace/context/_shared/MANDATE.md';
  SELECT COUNT(*) INTO stuck_remaining FROM public.agent_runs WHERE status = 'generating' AND created_at < (now() - interval '10 minutes');
  RAISE NOTICE '[ADR-207 P2] MANDATE.md skeletons: % of % workspaces', mandate_count, workspace_count;
  RAISE NOTICE '[Obs 07] agent_runs still stuck after reap: % (expected 0)', stuck_remaining;
END $$;
