-- Migration 201: ADR-407 Phase 1 — the operational read layer re-keys to the workspace
--
-- ADR-373 re-keyed the substrate spine (workspace_files + versions, migration
-- 189); ADR-407 Phase 0 re-keyed the money ledger (execution_events, migration
-- 200). This migration re-keys the remaining WORKSPACE-CONTENT tables (ADR-407
-- D3 + the §3 scope registry): tasks, agents, agent_runs, activity_log,
-- wake_queue, action_proposals, platform_connections, sync_registry — plus the
-- two workspace-files search RPCs still keyed p_user_id.
--
-- Pattern per table (identical to migrations 189/200):
--   * ADD COLUMN workspace_id uuid REFERENCES workspaces(id)  (nullable —
--     code stamps going forward; reads fall back to user_id when NULL-scoped)
--   * backfill via the owner mapping (every historical row was written in the
--     N=1 world, where the acting workspace IS the actor's owner workspace)
--   * scope index
--   * uniqueness that encoded per-user identity moves to per-workspace
--     (tasks slug, wake_queue dedup) — same constraint NAME kept where code
--     matches on it (wake_queue enqueue catches 'wake_queue_dedup_unique').
--
-- user_id columns are KEPT everywhere as attribution (who acted), per the
-- ADR-373 vestige discipline. N=1 byte-identity: owner-mapped backfill makes
-- every workspace-scoped read return exactly the rows the user-scoped read
-- returned (verified post-run: per-table old-vs-new row-set counts).
--
-- DEPLOY ORDER: the search RPC signatures change (p_user_id → p_workspace_id);
-- run this migration immediately around the deploy of the same commit (the
-- Python fallback path degrades search to empty results in the window, never
-- an error surface).

BEGIN;

-- ── 1. tasks (the recurrence scheduling index, ADR-231) ─────────────────────

ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id);

UPDATE tasks t SET workspace_id = w.id
FROM workspaces w WHERE w.owner_id = t.user_id AND t.workspace_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_tasks_workspace ON tasks (workspace_id);

-- Slug identity is per-workspace now (two members must not fork the slug space).
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_user_slug_unique;
ALTER TABLE tasks ADD CONSTRAINT tasks_workspace_slug_unique UNIQUE (workspace_id, slug);

-- ── 2. agents ────────────────────────────────────────────────────────────────

ALTER TABLE agents
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id);

UPDATE agents a SET workspace_id = w.id
FROM workspaces w WHERE w.owner_id = a.user_id AND a.workspace_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_agents_workspace ON agents (workspace_id);

-- ── 3. agent_runs (no user_id column — scope arrives via agents) ────────────

ALTER TABLE agent_runs
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id);

UPDATE agent_runs r SET workspace_id = a.workspace_id
FROM agents a WHERE a.id = r.agent_id AND r.workspace_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_agent_runs_workspace ON agent_runs (workspace_id);

-- ── 4. activity_log ──────────────────────────────────────────────────────────

ALTER TABLE activity_log
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id);

UPDATE activity_log l SET workspace_id = w.id
FROM workspaces w WHERE w.owner_id = l.user_id AND l.workspace_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_activity_log_workspace
  ON activity_log (workspace_id, created_at DESC);

-- ── 5. wake_queue ────────────────────────────────────────────────────────────
-- Dedup identity moves to the workspace (ADR-407 D3: one queue per commons —
-- two principals proposing the same wake dedup against each other). The
-- constraint NAME is load-bearing (services/wake_queue.py enqueue matches
-- 'wake_queue_dedup_unique' in the violation message) — kept.

ALTER TABLE wake_queue
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id);

UPDATE wake_queue q SET workspace_id = w.id
FROM workspaces w WHERE w.owner_id = q.user_id AND q.workspace_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_wake_queue_workspace ON wake_queue (workspace_id, status);

ALTER TABLE wake_queue DROP CONSTRAINT IF EXISTS wake_queue_dedup_unique;
ALTER TABLE wake_queue ADD CONSTRAINT wake_queue_dedup_unique
  UNIQUE (workspace_id, wake_source, dedup_key);

-- ── 6. action_proposals (the witness queue — visibility rules land Phase 2) ─

ALTER TABLE action_proposals
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id);

UPDATE action_proposals p SET workspace_id = w.id
FROM workspaces w WHERE w.owner_id = p.user_id AND p.workspace_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_action_proposals_workspace
  ON action_proposals (workspace_id, status);

-- ── 7. platform_connections + sync_registry (ADR-407 D5: the connection is a
--       workspace peripheral; the credential's grantor stays in user_id) ─────

ALTER TABLE platform_connections
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id);

UPDATE platform_connections c SET workspace_id = w.id
FROM workspaces w WHERE w.owner_id = c.user_id AND c.workspace_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_platform_connections_workspace
  ON platform_connections (workspace_id);

ALTER TABLE sync_registry
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id);

UPDATE sync_registry s SET workspace_id = w.id
FROM workspaces w WHERE w.owner_id = s.user_id AND s.workspace_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_sync_registry_workspace
  ON sync_registry (workspace_id);

-- ── 8. Search RPCs re-keyed (the query layer sees the commons) ───────────────
-- Same shape as migration 200's RPC re-key: parameter rename requires DROP.
-- Bodies filter wf.workspace_id — the column migration 189 added and 199 made
-- the live-row identity.

DROP FUNCTION IF EXISTS public.search_workspace(uuid, text, text, integer);

CREATE FUNCTION public.search_workspace(
    p_workspace_id uuid, p_query text,
    p_path_prefix text DEFAULT NULL::text, p_limit integer DEFAULT 20)
  RETURNS TABLE(id uuid, path text, summary text, content text, rank real, updated_at timestamp with time zone)
  LANGUAGE sql STABLE
AS $function$
    SELECT
        wf.id, wf.path, wf.summary, wf.content,
        ts_rank(to_tsvector('english', wf.content), plainto_tsquery('english', p_query)) AS rank,
        wf.updated_at
    FROM workspace_files wf
    WHERE wf.workspace_id = p_workspace_id
      AND (p_path_prefix IS NULL OR wf.path LIKE p_path_prefix || '%')
      AND to_tsvector('english', wf.content) @@ plainto_tsquery('english', p_query)
    ORDER BY rank DESC
    LIMIT p_limit;
$function$;

DROP FUNCTION IF EXISTS public.search_workspace_semantic(uuid, vector, text, integer);

CREATE FUNCTION public.search_workspace_semantic(
    p_workspace_id uuid, p_query_embedding vector,
    p_path_prefix text DEFAULT NULL::text, p_limit integer DEFAULT 20)
  RETURNS TABLE(id uuid, path text, summary text, content text, similarity real, updated_at timestamp with time zone)
  LANGUAGE sql STABLE
AS $function$
    SELECT
        wf.id, wf.path, wf.summary, wf.content,
        (1 - (wf.embedding <=> p_query_embedding))::REAL AS similarity,
        wf.updated_at
    FROM workspace_files wf
    WHERE wf.workspace_id = p_workspace_id
      AND wf.embedding IS NOT NULL
      AND (p_path_prefix IS NULL OR wf.path LIKE p_path_prefix || '%')
    ORDER BY wf.embedding <=> p_query_embedding
    LIMIT p_limit;
$function$;

GRANT EXECUTE ON FUNCTION search_workspace(uuid, text, text, integer) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION search_workspace_semantic(uuid, vector, text, integer) TO authenticated, service_role;

-- ── 9. Insert-scoping safety net ─────────────────────────────────────────────
-- The DB-level mirror of effective_workspace_id's owner-resolution fallback
-- (workspace_context.py step 3): any INSERT that arrives without workspace_id
-- gets the actor's owner workspace. App code stamps the ACTING workspace
-- explicitly on request paths (a member under a grant overrides this default);
-- the trigger guarantees no unswept legacy write site can mint an unscoped
-- row. Identical rule, two layers — N=1 byte-identical by construction.

CREATE OR REPLACE FUNCTION public.fill_workspace_id_from_owner()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.workspace_id IS NULL AND NEW.user_id IS NOT NULL THEN
    SELECT id INTO NEW.workspace_id FROM workspaces WHERE owner_id = NEW.user_id LIMIT 1;
  END IF;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.fill_agent_run_workspace_id()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.workspace_id IS NULL AND NEW.agent_id IS NOT NULL THEN
    SELECT workspace_id INTO NEW.workspace_id FROM agents WHERE id = NEW.agent_id LIMIT 1;
  END IF;
  RETURN NEW;
END;
$$;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'tasks','agents','activity_log','wake_queue','action_proposals',
    'platform_connections','sync_registry','execution_events'
  ] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_fill_workspace_id ON %I', t);
    EXECUTE format(
      'CREATE TRIGGER trg_fill_workspace_id BEFORE INSERT ON %I
       FOR EACH ROW EXECUTE FUNCTION fill_workspace_id_from_owner()', t);
  END LOOP;
END $$;

DROP TRIGGER IF EXISTS trg_fill_workspace_id ON agent_runs;
CREATE TRIGGER trg_fill_workspace_id BEFORE INSERT ON agent_runs
  FOR EACH ROW EXECUTE FUNCTION fill_agent_run_workspace_id();

COMMIT;
