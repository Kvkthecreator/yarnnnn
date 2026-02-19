-- ADR-067: Session Compaction and Conversational Continuity
-- Adds session summary and compaction columns to chat_sessions.
-- Updates get_or_create_chat_session() to use inactivity-based boundary.
--
-- Phase 1: summary column — written by nightly cron after memory extraction,
--          read by working_memory.py _get_recent_sessions() (reader already live)
-- Phase 2: inactivity-based session boundary — replaces DATE(started_at) = CURRENT_DATE
--          Note: updated_at is already set on every message append by append_session_message()
--          RPC, so it serves as last_message_at with no additional column needed.
-- Phase 3: compaction_summary column — written by build_history_for_claude() when
--          history budget hits 80%; prepended as <summary> block on subsequent turns.

-- =============================================================================
-- Phase 1 + 3: New columns
-- =============================================================================

ALTER TABLE chat_sessions
    ADD COLUMN IF NOT EXISTS summary TEXT,
    ADD COLUMN IF NOT EXISTS compaction_summary TEXT;

COMMENT ON COLUMN chat_sessions.summary IS
    'Prose summary of session written by nightly cron (ADR-067 Phase 1). '
    'Injected into next-session working memory as "Recent conversations" block. '
    'Equivalent to Claude Code auto memory (MEMORY.md).';

COMMENT ON COLUMN chat_sessions.compaction_summary IS
    'In-session compaction summary written by build_history_for_claude() when '
    'history budget hits 80% of MAX_HISTORY_TOKENS (ADR-067 Phase 3). '
    'Prepended as assistant <summary> block; prior messages dropped from API calls. '
    'Equivalent to Claude Code auto-compaction block.';

-- =============================================================================
-- Phase 2: Inactivity-based session boundary
-- Replace DATE(started_at) = CURRENT_DATE with updated_at-based inactivity check.
-- updated_at is already bumped on every message append by append_session_message().
-- Default inactivity window: 4 hours. Configurable via p_inactivity_hours parameter.
-- =============================================================================

-- Drop old 4-arg signature before replacing with 5-arg version
DROP FUNCTION IF EXISTS get_or_create_chat_session(uuid, uuid, text, text);

CREATE OR REPLACE FUNCTION get_or_create_chat_session(
    p_user_id UUID,
    p_project_id UUID,
    p_session_type TEXT DEFAULT 'thinking_partner',
    p_scope TEXT DEFAULT 'daily',
    p_inactivity_hours INTEGER DEFAULT 4
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
        INSERT INTO chat_sessions (user_id, project_id, session_type, status)
        VALUES (p_user_id, p_project_id, p_session_type, 'active')
        RETURNING * INTO v_session;
        RETURN v_session;
    END IF;

    -- 'daily' scope: inactivity-based boundary (ADR-067 Phase 2)
    -- Find the most recent active session; reuse if updated within inactivity window.
    -- updated_at is bumped on every message append, so it acts as last_message_at.
    IF p_scope = 'daily' THEN
        v_inactivity_cutoff := NOW() - (p_inactivity_hours || ' hours')::INTERVAL;

        SELECT * INTO v_session
        FROM chat_sessions
        WHERE user_id = p_user_id
          AND (
              (p_project_id IS NULL AND project_id IS NULL)
              OR project_id = p_project_id
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
          AND session_type = p_session_type
          AND status = 'active'
        ORDER BY started_at DESC
        LIMIT 1;
    END IF;

    -- If found, return existing session
    IF v_session.id IS NOT NULL THEN
        RETURN v_session;
    END IF;

    -- Otherwise create new session
    INSERT INTO chat_sessions (user_id, project_id, session_type, status)
    VALUES (p_user_id, p_project_id, p_session_type, 'active')
    RETURNING * INTO v_session;

    RETURN v_session;
END;
$$;

-- =============================================================================
-- Index: support inactivity lookup efficiently
-- =============================================================================

DROP INDEX IF EXISTS idx_chat_sessions_daily;

CREATE INDEX IF NOT EXISTS idx_chat_sessions_inactivity
    ON chat_sessions(user_id, project_id, session_type, status, updated_at DESC)
    WHERE status = 'active';

-- =============================================================================
-- Grants (function already granted in 008; re-apply for OR REPLACE)
-- =============================================================================

GRANT EXECUTE ON FUNCTION get_or_create_chat_session TO authenticated;
