-- Migration: 094_monthly_message_count.sql
-- ADR-100: Monthly message count replaces daily token budget as primary gate
-- Date: 2026-03-09
--
-- Counts user-sent messages per calendar month for free tier enforcement.
-- Called by check_monthly_message_limit() in platform_limits.py.
-- Keeps get_daily_token_usage() intact for analytics.

-- =============================================================================
-- MONTHLY MESSAGE COUNT FUNCTION
-- =============================================================================

CREATE OR REPLACE FUNCTION get_monthly_message_count(
    p_user_id UUID,
    p_month_start DATE DEFAULT date_trunc('month', CURRENT_DATE)::date
)
RETURNS INTEGER
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT COUNT(*)::int
    FROM session_messages sm
    JOIN chat_sessions cs ON cs.id = sm.session_id
    WHERE cs.user_id = p_user_id
      AND sm.role = 'user'
      AND sm.created_at >= p_month_start::timestamp
      AND sm.created_at < (p_month_start + interval '1 month')::timestamp;
$$;

COMMENT ON FUNCTION get_monthly_message_count IS
'ADR-100: Count user-sent messages for a given month. Used for monthly message limit enforcement (Free tier = 50/month).';

-- =============================================================================
-- INDEX FOR EFFICIENT MONTHLY QUERIES
-- =============================================================================
-- Partial index on user messages for the monthly count query.

CREATE INDEX IF NOT EXISTS idx_session_messages_user_created
    ON session_messages(created_at)
    WHERE role = 'user';

-- =============================================================================
-- COMPLETION LOG
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE 'ADR-100: Monthly message count function created. Replaces daily token budget as primary gate.';
END $$;
