-- Migration 154: ADR-205 Workspace Primitive Collapse
--
-- Executes Architecture Y of ADR-205:
--   - Only YARNNN (role='thinking_partner', origin='system_bootstrap') persists
--     as scaffolded infrastructure.
--   - Specialists + Platform Bots are no longer pre-scaffolded; they lazy-create
--     on first dispatch (Specialists via ensure_infrastructure_agent) or on
--     platform connect (Platform Bots via routes/integrations.py).
--
-- What this migration does:
--   1. Drops all `origin='system_bootstrap'` rows whose role is NOT
--      'thinking_partner'. FK cascades wipe associated agent_runs,
--      agent_context_log, agent_source_runs, destination_delivery_log,
--      trigger_event_log, agent_export_preferences. Acceptable: no
--      user-authored content rides on these rows and the clean-slate
--      test data policy applies (zero user-authored agents exist — verified
--      at ADR-205 planning time: all 38 rows pre-migration are
--      origin='system_bootstrap').
--   2. For any workspace whose owner has `origin='system_bootstrap'`
--      rows but no remaining `thinking_partner` row, backfills one YARNNN row.
--   3. Dedupes to at most one `thinking_partner` row per user.
--
-- Not touched:
--   - `agents` rows with origin != 'system_bootstrap' (user-authored)
--   - `tasks`, `workspace_files`, `platform_connections`, `balance_*`
--   - Any schema (no DDL changes — `tasks.schedule` is already nullable)

BEGIN;

-- Step 1: Drop all non-YARNNN infrastructure rows.
DELETE FROM public.agents
WHERE origin = 'system_bootstrap'
  AND role <> 'thinking_partner';

-- Step 2: Dedupe to at most one thinking_partner per user.
-- Keep the earliest-created row per user.
WITH ranked AS (
  SELECT id,
         row_number() OVER (PARTITION BY user_id ORDER BY created_at ASC, id ASC) AS rn
  FROM public.agents
  WHERE origin = 'system_bootstrap'
    AND role = 'thinking_partner'
)
DELETE FROM public.agents
WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

-- Step 3: Backfill YARNNN for workspaces missing one.
-- A workspace is considered active if its owner has any rows in `tasks` OR
-- any rows in `workspace_files` OR any rows in `platform_connections`.
-- We use owner_id from workspaces (the stable identity) rather than
-- depending on existing agents rows (which may be zero).
INSERT INTO public.agents (
  user_id, title, role, scope, origin, status,
  agent_instructions, agent_memory, type_config,
  slug,
  created_at, updated_at
)
SELECT
  w.owner_id,
  'Thinking Partner',
  'thinking_partner',
  'autonomous',
  'system_bootstrap',
  'active',
  '',
  '{}'::jsonb,
  '{}'::jsonb,
  'thinking-partner',
  now(),
  now()
FROM public.workspaces w
WHERE w.owner_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM public.agents a
    WHERE a.user_id = w.owner_id
      AND a.role = 'thinking_partner'
      AND a.origin = 'system_bootstrap'
  );

COMMIT;

-- Post-migration sanity checks (informational — no action taken on failure).
DO $$
DECLARE
  bootstrap_count INT;
  yarnnn_count INT;
  non_yarnnn_bootstrap_count INT;
BEGIN
  SELECT COUNT(*) INTO bootstrap_count FROM public.agents WHERE origin = 'system_bootstrap';
  SELECT COUNT(*) INTO yarnnn_count FROM public.agents WHERE origin = 'system_bootstrap' AND role = 'thinking_partner';
  SELECT COUNT(*) INTO non_yarnnn_bootstrap_count FROM public.agents WHERE origin = 'system_bootstrap' AND role <> 'thinking_partner';
  RAISE NOTICE '[ADR-205] system_bootstrap rows remaining: % (YARNNN: %, non-YARNNN: %)',
    bootstrap_count, yarnnn_count, non_yarnnn_bootstrap_count;
END $$;
