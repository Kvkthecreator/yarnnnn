-- 248 — Retire the pre-ADR-596 agent model: drop its eight tables and the
--       dangling FK columns live tables still carry into them.
--
-- WHAT THIS RETIRES
-- ADR-109's Scope x Role x Trigger model — an agent as a per-workspace DB row
-- with runs, versions, quality scores and a review queue. ADR-596/600 replaced
-- it: an agent is a BEING, one row in `services/agents_registry.AGENTS`, which
-- is static kernel data. Two models for one word is the ambiguity Singular
-- Implementation exists to prevent, and the retired one has no readers left —
-- commit 083d25d deleted its router and ManageAgent; the commit carrying this
-- migration deletes SearchEntities, DiscoverAgents, ReadAgentFile, the
-- `agent`/`version` entity types, and every remaining service that read them.
--
-- MEASURED BEFORE WRITING (production, 2026-08-26, PostgREST exact counts):
--   agents                     0 rows      agent_proposals            0 rows
--   agent_runs                 0 rows      agent_role_metrics         0 rows
--   agent_context_log          0 rows      agent_source_runs          0 rows
--   agent_export_preferences   0 rows      agent_validation_results   0 rows
-- Six of the eight also have ZERO references anywhere in the codebase — they
-- are schema fossils of a model that stopped being written to long ago.
--
-- ⭐ THE FK COLUMNS ARE THE REASON THIS IS A MIGRATION AND NOT A DROP
-- Four LIVE tables carry a column pointing into the retired model. Each was
-- measured 100% NULL, and each has no writer:
--   chat_sessions.agent_id         (mig 098) — 0 non-null
--   execution_events.agent_run_id  (mig 165) — 0 non-null; telemetry.py accepts
--                                   the kwarg but NO caller passes it
--   export_log.agent_run_id                  — 0 non-null; its only writer was
--                                   the deleted agent-run delivery path
--   action_proposals.agent_slug              — 0 non-null
-- They are dropped FIRST so the table drops need no CASCADE. A CASCADE here
-- would silently take whatever else happens to reference these tables; naming
-- the columns means the migration fails loudly if the graph is not what we
-- measured, which is the point.
--
-- REVERSIBILITY: none, deliberately. There is nothing to preserve — every
-- table is empty and every FK column is null. Restoring the MODEL would mean
-- restoring ADR-109, which ADR-596 superseded.

BEGIN;

-- 1. Dangling FK columns on live tables (all measured 100% NULL).
ALTER TABLE chat_sessions     DROP COLUMN IF EXISTS agent_id;
ALTER TABLE execution_events  DROP COLUMN IF EXISTS agent_run_id;
ALTER TABLE export_log        DROP COLUMN IF EXISTS agent_run_id;
ALTER TABLE action_proposals  DROP COLUMN IF EXISTS agent_slug;

-- session_messages.thread_agent_id (mig 123) — dropped if it still exists.
ALTER TABLE session_messages  DROP COLUMN IF EXISTS thread_agent_id;

-- 2. The model's own tables. Children before parents so no CASCADE is needed;
--    `agents` and `agent_runs` last because the other six reference them.
DROP TABLE IF EXISTS agent_validation_results;
DROP TABLE IF EXISTS agent_source_runs;
DROP TABLE IF EXISTS agent_role_metrics;
DROP TABLE IF EXISTS agent_proposals;
DROP TABLE IF EXISTS agent_export_preferences;
DROP TABLE IF EXISTS agent_context_log;
DROP TABLE IF EXISTS agent_runs;
DROP TABLE IF EXISTS agents;

COMMIT;

-- Verify (the runner's exit code is not verification — this makes the
-- migration itself refuse to report success on a half-applied state).
DO $$
DECLARE
  leftover TEXT;
  cols     TEXT;
BEGIN
  SELECT string_agg(table_name, ', ' ORDER BY table_name) INTO leftover
  FROM information_schema.tables
  WHERE table_schema = 'public'
    AND table_name IN (
      'agents', 'agent_runs', 'agent_context_log', 'agent_export_preferences',
      'agent_proposals', 'agent_role_metrics', 'agent_source_runs',
      'agent_validation_results'
    );
  IF leftover IS NOT NULL THEN
    RAISE EXCEPTION 'agent-model tables still present: %', leftover;
  END IF;

  SELECT string_agg(table_name || '.' || column_name, ', ') INTO cols
  FROM information_schema.columns
  WHERE table_schema = 'public'
    AND (
      (table_name = 'chat_sessions'    AND column_name = 'agent_id')
      OR (table_name = 'execution_events' AND column_name = 'agent_run_id')
      OR (table_name = 'export_log'       AND column_name = 'agent_run_id')
      OR (table_name = 'action_proposals' AND column_name = 'agent_slug')
      OR (table_name = 'session_messages' AND column_name = 'thread_agent_id')
    );
  IF cols IS NOT NULL THEN
    RAISE EXCEPTION 'dangling agent FK columns still present: %', cols;
  END IF;

  RAISE NOTICE 'migration 248: the pre-ADR-596 agent model is retired.';
END $$;
