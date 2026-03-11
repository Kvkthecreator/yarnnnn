-- ADR-087 Phase 3: Deliverable-scoped chat sessions
-- Updates get_or_create_chat_session() to filter by deliverable_id,
-- so deliverable workspace chats get their own sessions separate from global TP.

-- Drop old 5-arg signature before replacing with 6-arg version
DROP FUNCTION IF EXISTS get_or_create_chat_session(uuid, uuid, text, text, integer);

CREATE OR REPLACE FUNCTION get_or_create_chat_session(
    p_user_id UUID,
    p_project_id UUID,
    p_session_type TEXT DEFAULT 'thinking_partner',
    p_scope TEXT DEFAULT 'daily',
    p_inactivity_hours INTEGER DEFAULT 4,
    p_deliverable_id UUID DEFAULT NULL
)
RETURNS chat_sessions
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_session chat_sessions;
    v_inactivity_cutoff TIMESTAMPTZ;
BEGIN
    -- For 'conversation' scope, always create new
    IF p_scope = 'conversation' THEN
        INSERT INTO chat_sessions (user_id, project_id, session_type, status, deliverable_id)
        VALUES (p_user_id, p_project_id, p_session_type, 'active', p_deliverable_id)
        RETURNING * INTO v_session;
        RETURN v_session;
    END IF;

    -- 'daily' scope: inactivity-based boundary (ADR-067 Phase 2)
    -- Now also scoped by deliverable_id (ADR-087 Phase 3)
    IF p_scope = 'daily' THEN
        v_inactivity_cutoff := NOW() - (p_inactivity_hours || ' hours')::INTERVAL;

        SELECT * INTO v_session
        FROM chat_sessions
        WHERE user_id = p_user_id
          AND (
              (p_project_id IS NULL AND project_id IS NULL)
              OR project_id = p_project_id
          )
          AND (
              (p_deliverable_id IS NULL AND deliverable_id IS NULL)
              OR deliverable_id = p_deliverable_id
          )
          AND session_type = p_session_type
          AND status = 'active'
          AND updated_at >= v_inactivity_cutoff
        ORDER BY updated_at DESC
        LIMIT 1;
    ELSIF p_scope = 'project' THEN
        SELECT * INTO v_session
        FROM chat_sessions
        WHERE user_id = p_user_id
          AND (
              (p_project_id IS NULL AND project_id IS NULL)
              OR project_id = p_project_id
          )
          AND (
              (p_deliverable_id IS NULL AND deliverable_id IS NULL)
              OR deliverable_id = p_deliverable_id
          )
          AND session_type = p_session_type
          AND status = 'active'
        ORDER BY started_at DESC
        LIMIT 1;
    END IF;

    -- If found, return existing session
    IF v_session.id IS NOT NULL THEN
        RETURN v_session;
    END IF;

    -- Otherwise create new session (with deliverable_id if scoped)
    INSERT INTO chat_sessions (user_id, project_id, session_type, status, deliverable_id)
    VALUES (p_user_id, p_project_id, p_session_type, 'active', p_deliverable_id)
    RETURNING * INTO v_session;

    RETURN v_session;
END;
$$;

GRANT EXECUTE ON FUNCTION get_or_create_chat_session TO authenticated;
