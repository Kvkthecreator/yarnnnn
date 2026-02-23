-- Migration: 079_daily_token_usage.sql
-- ADR-053: Daily token budget replaces monthly conversation count
-- Date: 2026-02-23
--
-- Creates a SQL function to efficiently sum daily token usage
-- from session_messages.metadata (input_tokens + output_tokens).
-- Called by check_daily_token_budget() in platform_limits.py.

-- =============================================================================
-- DAILY TOKEN USAGE AGGREGATION FUNCTION
-- =============================================================================

CREATE OR REPLACE FUNCTION get_daily_token_usage(
    p_user_id UUID,
    p_date DATE DEFAULT CURRENT_DATE
)
RETURNS INTEGER
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT COALESCE(SUM(
        COALESCE((sm.metadata->>'input_tokens')::int, 0) +
        COALESCE((sm.metadata->>'output_tokens')::int, 0)
    ), 0)::int
    FROM session_messages sm
    JOIN chat_sessions cs ON cs.id = sm.session_id
    WHERE cs.user_id = p_user_id
      AND sm.role = 'assistant'
      AND sm.created_at >= p_date::timestamp
      AND sm.created_at < (p_date + 1)::timestamp;
$$;

COMMENT ON FUNCTION get_daily_token_usage IS
'ADR-053: Sum input_tokens + output_tokens from session_messages.metadata for a user on a given day. Used for daily token budget enforcement.';

-- =============================================================================
-- INDEX FOR EFFICIENT TOKEN QUERIES
-- =============================================================================
-- session_messages already has an index on session_id (FK).
-- Add a partial index on created_at + role for the daily aggregation query.

CREATE INDEX IF NOT EXISTS idx_session_messages_assistant_created
    ON session_messages(created_at)
    WHERE role = 'assistant';

-- =============================================================================
-- COMPLETION LOG
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE 'ADR-053: Daily token budget function created. Token usage persisted in session_messages.metadata.';
END $$;
