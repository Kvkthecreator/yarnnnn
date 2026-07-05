-- Migration 203: ADR-407 Phase 4 — chat sessions scope to (workspace, principal)
--
-- ADR-407 D6: a chat session is MEMBER-EXPERIENCE state — one principal's
-- thread with the system agent WITHIN a workspace (the DM shape), keyed
-- (workspace_id, user_id). Two members in one commons each get their own
-- thread; the same human in two workspaces gets two threads. The SHARED
-- timeline (the workspace Flow) derives from the attributed ledgers, not
-- from any chat table — the FE composition for that is the named Phase-4b
-- follow-on; this migration lands the substrate scoping.
--
-- N=1 byte-identity: backfill maps every session to its user's owner
-- workspace; the RPC's added p_workspace_id parameter DEFAULTS to that same
-- owner resolution, so pre-deploy code calling without it resolves the
-- identical session. No deploy-order window (the old call shape still binds).

BEGIN;

-- ── 1. chat_sessions gains the workspace dimension ──────────────────────────

ALTER TABLE chat_sessions
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id);

UPDATE chat_sessions s SET workspace_id = w.id
FROM workspaces w WHERE w.owner_id = s.user_id AND s.workspace_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_chat_sessions_workspace_user
  ON chat_sessions (workspace_id, user_id, status);

-- Insert safety net — same owner-fallback rule as migration 201 §9. App code
-- (the RPC below + feed.py insert) stamps the ACTING workspace explicitly;
-- the trigger covers unswept legacy inserts.
DROP TRIGGER IF EXISTS trg_fill_workspace_id ON chat_sessions;
CREATE TRIGGER trg_fill_workspace_id BEFORE INSERT ON chat_sessions
  FOR EACH ROW EXECUTE FUNCTION fill_workspace_id_from_owner();

-- ── 2. get_or_create_chat_session — (workspace, principal) resolution ───────
-- Same name + p_workspace_id DEFAULT NULL appended: callers that don't pass
-- it get owner resolution (byte-identical); the feed passes the ACTING
-- workspace so a member's thread lives in the commons, not their singleton.

DROP FUNCTION IF EXISTS public.get_or_create_chat_session(uuid, uuid, text, text, integer, uuid);

CREATE FUNCTION public.get_or_create_chat_session(
    p_user_id uuid,
    p_project_id uuid,
    p_session_type text DEFAULT 'thinking_partner'::text,
    p_scope text DEFAULT 'daily'::text,
    p_inactivity_hours integer DEFAULT 4,
    p_agent_id uuid DEFAULT NULL::uuid,
    p_workspace_id uuid DEFAULT NULL::uuid)
  RETURNS chat_sessions
  LANGUAGE plpgsql
  SECURITY DEFINER
AS $function$
DECLARE
    v_session chat_sessions;
    v_inactivity_cutoff TIMESTAMPTZ;
    v_ws uuid;
BEGIN
    -- The acting workspace: explicit, else the caller's owner workspace
    -- (ADR-407 D6 — the same resolution rule as effective_workspace_id).
    v_ws := COALESCE(
        p_workspace_id,
        (SELECT id FROM workspaces WHERE owner_id = p_user_id LIMIT 1)
    );

    -- 'conversation' scope: always create new
    IF p_scope = 'conversation' THEN
        INSERT INTO chat_sessions (user_id, workspace_id, session_type, status, agent_id)
        VALUES (p_user_id, v_ws, p_session_type, 'active', p_agent_id)
        RETURNING * INTO v_session;
        RETURN v_session;
    END IF;

    -- 'daily' scope: inactivity-based boundary (ADR-067 Phase 2)
    IF p_scope = 'daily' THEN
        v_inactivity_cutoff := NOW() - (p_inactivity_hours || ' hours')::INTERVAL;

        SELECT * INTO v_session
        FROM chat_sessions
        WHERE user_id = p_user_id
          AND (workspace_id = v_ws OR (v_ws IS NULL AND workspace_id IS NULL))
          AND (
              (p_agent_id IS NULL AND agent_id IS NULL)
              OR agent_id = p_agent_id
          )
          AND session_type = p_session_type
          AND status = 'active'
          AND updated_at >= v_inactivity_cutoff
        ORDER BY updated_at DESC
        LIMIT 1;

    -- 'project' scope: most-recent active session (project_id no longer a dimension)
    ELSIF p_scope = 'project' THEN
        SELECT * INTO v_session
        FROM chat_sessions
        WHERE user_id = p_user_id
          AND (workspace_id = v_ws OR (v_ws IS NULL AND workspace_id IS NULL))
          AND (
              (p_agent_id IS NULL AND agent_id IS NULL)
              OR agent_id = p_agent_id
          )
          AND session_type = p_session_type
          AND status = 'active'
        ORDER BY started_at DESC
        LIMIT 1;
    END IF;

    IF v_session.id IS NOT NULL THEN
        RETURN v_session;
    END IF;

    -- Otherwise create new
    INSERT INTO chat_sessions (user_id, workspace_id, session_type, status, agent_id)
    VALUES (p_user_id, v_ws, p_session_type, 'active', p_agent_id)
    RETURNING * INTO v_session;

    RETURN v_session;
END;
$function$;

GRANT EXECUTE ON FUNCTION get_or_create_chat_session(uuid, uuid, text, text, integer, uuid, uuid)
  TO authenticated, service_role;

COMMIT;
