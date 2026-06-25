-- Migration 188 — fix get_or_create_chat_session: drop stale project_id refs
--
-- The RPC body (last defined in 097_scoped_sessions.sql) inserts/selects against
-- chat_sessions.project_id and chat_sessions.deliverable_id. Both columns were
-- dropped by the project-layer collapse (ADR-138 band) without updating this
-- function, so EVERY call raises 42703 ("column project_id does not exist") the
-- moment its body touches the column. The failure was invisible because all
-- callers (notifications._insert_chat_notification, feed.py session creation)
-- wrap it in try/except — the symptom is silent absence of a feature, not a crash.
--
-- Fix: redefine the body against the CURRENT chat_sessions schema. The
-- p_project_id parameter is KEPT for signature compatibility (callers pass
-- None) but no longer touched. Scoping keys on (user_id, session_type, status,
-- agent_id, updated_at) — the columns that still exist. Behavior is otherwise
-- identical to the pre-breakage intent.
--
-- See docs/analysis/broken-get-or-create-chat-session-rpc-2026-06-25.md

CREATE OR REPLACE FUNCTION public.get_or_create_chat_session(
    p_user_id uuid,
    p_project_id uuid,                              -- kept for signature compat; ignored (column dropped)
    p_session_type text DEFAULT 'thinking_partner',
    p_scope text DEFAULT 'daily',
    p_inactivity_hours integer DEFAULT 4,
    p_agent_id uuid DEFAULT NULL
)
RETURNS chat_sessions
LANGUAGE plpgsql
SECURITY DEFINER
AS $function$
DECLARE
    v_session chat_sessions;
    v_inactivity_cutoff TIMESTAMPTZ;
BEGIN
    -- 'conversation' scope: always create new
    IF p_scope = 'conversation' THEN
        INSERT INTO chat_sessions (user_id, session_type, status, agent_id)
        VALUES (p_user_id, p_session_type, 'active', p_agent_id)
        RETURNING * INTO v_session;
        RETURN v_session;
    END IF;

    -- 'daily' scope: inactivity-based boundary (ADR-067 Phase 2)
    IF p_scope = 'daily' THEN
        v_inactivity_cutoff := NOW() - (p_inactivity_hours || ' hours')::INTERVAL;

        SELECT * INTO v_session
        FROM chat_sessions
        WHERE user_id = p_user_id
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
    INSERT INTO chat_sessions (user_id, session_type, status, agent_id)
    VALUES (p_user_id, p_session_type, 'active', p_agent_id)
    RETURNING * INTO v_session;

    RETURN v_session;
END;
$function$;

GRANT EXECUTE ON FUNCTION get_or_create_chat_session TO authenticated;
