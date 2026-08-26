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
-- ⚠️ SEVEN TABLES AND ONE VIEW, not eight tables. `agent_role_metrics` is a
-- VIEW over agents+agent_runs (a per-role run-quality rollup). The audit read
-- the roster from the PostgREST schema, which does not distinguish relkind, so
-- it was miscounted as a table — and `DROP TABLE` on a view is an ERROR, not a
-- no-op. Caught by --dry-run before it ever reached production. It is also the
-- ONLY dependent object on the seven tables (verified via pg_depend), so once
-- it is gone the drops below need no CASCADE.
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
-- SEVEN live tables carry a column pointing into the retired model. Every one
-- was measured 100% NULL (pg_constraint census + per-column counts, 2026-08-26)
-- and none has a writer:
--   chat_sessions.agent_id             (mig 098) — 0 non-null of 122 rows
--   execution_events.agent_run_id      (mig 165) — 0 non-null of 571 rows;
--                                       telemetry.py accepts the kwarg but NO
--                                       caller ever passes it
--   export_log.agent_run_id                      — 0 non-null; its only writer
--                                       was the deleted delivery path
--   action_proposals.agent_slug                  — 0 non-null
--   trigger_event_log.agent_id / .run_id         — table itself is EMPTY
--   event_trigger_log.agent_id                   — table itself is EMPTY
--   destination_delivery_log.agent_id / .run_id  — table itself is EMPTY
--
-- ⚠️ The last three were MISSED by the audit and caught by --dry-run ("cannot
-- drop table agent_runs because other objects depend on it"). The audit's
-- dependency query walked pg_depend for VIEWS and so saw no CONSTRAINTS. Only
-- their agent COLUMNS are dropped: these three tables have lives of their own
-- (workspace_purge + routes/emissions read them) and are not part of this
-- model. Dropping a table because a column of it pointed here would be a far
-- larger claim than the evidence supports.
-- They are dropped FIRST so the table drops need no CASCADE. A CASCADE here
-- would silently take whatever else happens to reference these tables; naming
-- the columns means the migration fails loudly if the graph is not what we
-- measured, which is the point.
--
-- REVERSIBILITY: none, deliberately. There is nothing to preserve — every
-- table is empty and every FK column is null. Restoring the MODEL would mean
-- restoring ADR-109, which ADR-596 superseded.
--
-- TRANSACTION: supplied by scripts/db/run-migration.sh (--single-transaction).
-- This file must NOT open or close its own — a self-committing migration makes
-- --dry-run APPLY FOR REAL (observed on migration 243, 2026-08-18), and the
-- runner refuses a file carrying BEGIN/COMMIT for exactly that reason.

-- 1. Dangling FK columns on live tables (all measured 100% NULL).
ALTER TABLE chat_sessions     DROP COLUMN IF EXISTS agent_id;
ALTER TABLE execution_events  DROP COLUMN IF EXISTS agent_run_id;
ALTER TABLE export_log        DROP COLUMN IF EXISTS agent_run_id;
ALTER TABLE action_proposals  DROP COLUMN IF EXISTS agent_slug;

-- The three empty log tables: their agent COLUMNS only, never the tables.
ALTER TABLE trigger_event_log        DROP COLUMN IF EXISTS agent_id;
ALTER TABLE trigger_event_log        DROP COLUMN IF EXISTS run_id;
ALTER TABLE event_trigger_log        DROP COLUMN IF EXISTS agent_id;
ALTER TABLE destination_delivery_log DROP COLUMN IF EXISTS agent_id;
ALTER TABLE destination_delivery_log DROP COLUMN IF EXISTS run_id;

-- session_messages.thread_agent_id (mig 123) — dropped if it still exists.
ALTER TABLE session_messages  DROP COLUMN IF EXISTS thread_agent_id;

-- 2. The dependent VIEW and the ROW-TYPE functions, before the tables.
--
-- ⚠️ A function that takes or RETURNS a table's row type depends on the TABLE,
-- so it must go first — no row count and no code-reference census would ever
-- surface that. `get_due_pulse_agents` returns SETOF agents; the others take a
-- uuid and read the tables. All six have ZERO callers in api/ (verified
-- 2026-08-26; `get_agent_domain` merely COLLIDES BY NAME with an unrelated
-- Python helper in services/orchestration.py — different language, different
-- thing). `fill_agent_run_workspace_id` is the exception and is dropped in
-- step 4, because its trigger lives ON agent_runs.
--
-- ⚠️ Also missed by the audit and caught by --dry-run ("function
-- get_due_pulse_agents depends on type agents" — a function taking or
-- returning a table's ROW TYPE depends on the table, which no row-count or
-- code-reference census would ever surface). Six SQL functions over the
-- retired model, ALL with zero callers in api/ (verified 2026-08-26;
-- `get_agent_domain` collides by name with an unrelated PYTHON helper in
-- services/orchestration.py — different language, different thing).
-- `fill_agent_run_workspace_id` backs trg_fill_workspace_id ON agent_runs, so
-- the trigger dies with its table; the function is dropped here explicitly.
DROP VIEW IF EXISTS agent_role_metrics;

DROP FUNCTION IF EXISTS get_agent_domain(uuid);
DROP FUNCTION IF EXISTS get_agent_export_history(uuid, integer);
DROP FUNCTION IF EXISTS get_due_pulse_agents(timestamp with time zone);
DROP FUNCTION IF EXISTS get_next_run_number(uuid);
DROP FUNCTION IF EXISTS get_suggested_agent_runs(uuid);

-- 3. The model's own tables. Children before parents so no CASCADE is needed;
--    `agents` and `agent_runs` last because the others reference them.
DROP TABLE IF EXISTS agent_validation_results;
DROP TABLE IF EXISTS agent_source_runs;
DROP TABLE IF EXISTS agent_proposals;
DROP TABLE IF EXISTS agent_export_preferences;
DROP TABLE IF EXISTS agent_context_log;
DROP TABLE IF EXISTS agent_runs;
DROP TABLE IF EXISTS agents;

-- 4. The TRIGGER function, AFTER its table — the other half of the split.
--
-- ⚠️ `fill_agent_run_workspace_id` backs `trg_fill_workspace_id ON agent_runs`,
-- so dropping it BEFORE the table is refused ("trigger ... depends on
-- function"). The row-type functions in step 2 have the opposite constraint.
-- The six functions therefore CANNOT drop together, and the split is the whole
-- reason this file has four steps instead of two. Every ordering here was
-- established by --dry-run, not by reasoning about it.
DROP FUNCTION IF EXISTS fill_agent_run_workspace_id();

-- Verify (the runner's exit code is not verification — this makes the
-- migration itself refuse to report success on a half-applied state).
DO $$
DECLARE
  leftover TEXT;
  cols     TEXT;
BEGIN
  -- information_schema.tables lists VIEWS too (table_type='VIEW'), so this one
  -- query covers the seven tables and the view alike.
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
      OR (table_name = 'trigger_event_log' AND column_name IN ('agent_id', 'run_id'))
      OR (table_name = 'event_trigger_log' AND column_name = 'agent_id')
      OR (table_name = 'destination_delivery_log' AND column_name IN ('agent_id', 'run_id'))
      OR (table_name = 'session_messages' AND column_name = 'thread_agent_id')
    );
  IF cols IS NOT NULL THEN
    RAISE EXCEPTION 'dangling agent FK columns still present: %', cols;
  END IF;

  IF EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.proname IN ('fill_agent_run_workspace_id', 'get_agent_domain',
                        'get_agent_export_history', 'get_due_pulse_agents',
                        'get_next_run_number', 'get_suggested_agent_runs')
  ) THEN
    RAISE EXCEPTION 'agent-model SQL functions still present';
  END IF;

  -- The three FK-holding tables must SURVIVE. Two are live surfaces
  -- (destination_delivery_log backs /api/emissions; event_trigger_log is named
  -- by three purge paths), so a CASCADE would have taken working features with
  -- it. Assert survival, so a future edit reaching for CASCADE fails here
  -- instead of silently deleting them.
  SELECT string_agg(t.name, ', ' ORDER BY t.name) INTO cols
  FROM (VALUES ('trigger_event_log'), ('event_trigger_log'),
               ('destination_delivery_log')) AS t(name)
  WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = t.name
  );
  IF cols IS NOT NULL THEN
    RAISE EXCEPTION 'live tables destroyed by this migration: %', cols;
  END IF;

  RAISE NOTICE 'migration 248: the pre-ADR-596 agent model is retired.';
END $$;
