-- ADR-006: Session and Message Architecture
-- Normalizes chat sessions and messages for better queryability
-- Supports both project-scoped and global (user-level) chat

-- =============================================================================
-- PHASE 1: Create new normalized tables
-- =============================================================================

-- Chat sessions (replaces agent_sessions for chat, keeps agent_sessions for work tickets)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Direct ownership (not via project chain)
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Scope (nullable for global/user-level chat)
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,

    -- Session metadata
    session_type TEXT NOT NULL DEFAULT 'thinking_partner',
    status TEXT NOT NULL DEFAULT 'active',  -- active, completed, archived

    -- Lifecycle
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,

    -- Context snapshot at session start
    context_metadata JSONB DEFAULT '{}',
    -- Example: {memories_count: 10, context_type: "user_and_project", model: "claude-sonnet-4"}

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Session messages (normalized, individual rows)
CREATE TABLE IF NOT EXISTS session_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,

    -- Message content
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,

    -- Ordering (monotonically increasing per session)
    sequence_number INTEGER NOT NULL,

    -- Optional metadata
    metadata JSONB DEFAULT '{}',
    -- Example: {tokens: 150, latency_ms: 1200, model: "claude-sonnet-4"}

    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure unique sequence per session
    CONSTRAINT unique_sequence_per_session UNIQUE (session_id, sequence_number)
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Chat sessions: user lookup (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user
    ON chat_sessions(user_id, created_at DESC);

-- Chat sessions: project lookup
CREATE INDEX IF NOT EXISTS idx_chat_sessions_project
    ON chat_sessions(project_id, created_at DESC)
    WHERE project_id IS NOT NULL;

-- Chat sessions: active sessions for reuse lookup
CREATE INDEX IF NOT EXISTS idx_chat_sessions_active
    ON chat_sessions(user_id, project_id, session_type, status)
    WHERE status = 'active';

-- Chat sessions: daily session lookup (for DAILY scope)
CREATE INDEX IF NOT EXISTS idx_chat_sessions_daily
    ON chat_sessions(user_id, project_id, session_type, DATE(started_at))
    WHERE status = 'active';

-- Session messages: session + order (primary access pattern)
CREATE INDEX IF NOT EXISTS idx_session_messages_session_order
    ON session_messages(session_id, sequence_number);

-- Session messages: recent messages (for pagination from end)
CREATE INDEX IF NOT EXISTS idx_session_messages_recent
    ON session_messages(session_id, sequence_number DESC);

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_messages ENABLE ROW LEVEL SECURITY;

-- Chat sessions: direct user ownership (simple and fast)
CREATE POLICY "Users own their chat sessions"
    ON chat_sessions FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Session messages: inherit from session ownership
CREATE POLICY "Users can access messages in their sessions"
    ON session_messages FOR ALL
    USING (
        session_id IN (
            SELECT id FROM chat_sessions WHERE user_id = auth.uid()
        )
    )
    WITH CHECK (
        session_id IN (
            SELECT id FROM chat_sessions WHERE user_id = auth.uid()
        )
    );

-- =============================================================================
-- GRANTS
-- =============================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON chat_sessions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON session_messages TO authenticated;

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Auto-update updated_at on chat_sessions
CREATE TRIGGER chat_sessions_updated_at
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Function to get or create a session based on scope
-- Usage: SELECT * FROM get_or_create_chat_session(user_id, project_id, 'thinking_partner', 'daily');
CREATE OR REPLACE FUNCTION get_or_create_chat_session(
    p_user_id UUID,
    p_project_id UUID,  -- Can be NULL for global chat
    p_session_type TEXT DEFAULT 'thinking_partner',
    p_scope TEXT DEFAULT 'daily'  -- 'conversation', 'daily', 'project'
)
RETURNS chat_sessions
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_session chat_sessions;
BEGIN
    -- For 'conversation' scope, always create new
    IF p_scope = 'conversation' THEN
        INSERT INTO chat_sessions (user_id, project_id, session_type, status)
        VALUES (p_user_id, p_project_id, p_session_type, 'active')
        RETURNING * INTO v_session;
        RETURN v_session;
    END IF;

    -- Try to find existing active session
    IF p_scope = 'daily' THEN
        -- Match by user, project, type, and today's date
        SELECT * INTO v_session
        FROM chat_sessions
        WHERE user_id = p_user_id
          AND (
              (p_project_id IS NULL AND project_id IS NULL)
              OR project_id = p_project_id
          )
          AND session_type = p_session_type
          AND status = 'active'
          AND DATE(started_at) = CURRENT_DATE
        ORDER BY started_at DESC
        LIMIT 1;
    ELSIF p_scope = 'project' THEN
        -- Match by user, project, type (any date)
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

    -- If found, return it
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

-- Function to append a message to a session
-- Handles sequence_number automatically
CREATE OR REPLACE FUNCTION append_session_message(
    p_session_id UUID,
    p_role TEXT,
    p_content TEXT,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS session_messages
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_next_seq INTEGER;
    v_message session_messages;
BEGIN
    -- Get next sequence number (with lock to prevent race conditions)
    SELECT COALESCE(MAX(sequence_number), 0) + 1 INTO v_next_seq
    FROM session_messages
    WHERE session_id = p_session_id
    FOR UPDATE;

    -- Insert message
    INSERT INTO session_messages (session_id, role, content, sequence_number, metadata)
    VALUES (p_session_id, p_role, p_content, v_next_seq, p_metadata)
    RETURNING * INTO v_message;

    -- Update session updated_at
    UPDATE chat_sessions SET updated_at = NOW() WHERE id = p_session_id;

    RETURN v_message;
END;
$$;

-- Grant execute on functions
GRANT EXECUTE ON FUNCTION get_or_create_chat_session TO authenticated;
GRANT EXECUTE ON FUNCTION append_session_message TO authenticated;

-- =============================================================================
-- NOTES FOR PHASE 2 (Future migration)
-- =============================================================================
-- Phase 2 will:
-- 1. Migrate existing agent_sessions data to chat_sessions/session_messages
-- 2. Update work ticket agents to use chat_sessions
-- 3. Add user_id column to agent_sessions (if keeping for work tickets)
--
-- Phase 3 will:
-- 1. Drop agent_sessions table OR
-- 2. Repurpose agent_sessions for work ticket execution logs only
