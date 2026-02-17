-- Migration: 053_get_active_users_for_analysis.sql
-- ADR-060: Background Conversation Analyst
-- Date: 2026-02-17
--
-- Creates helper function to get users with recent chat activity
-- for the conversation analysis phase.

-- =============================================================================
-- 1. GET ACTIVE USERS FOR ANALYSIS
-- =============================================================================

CREATE OR REPLACE FUNCTION get_active_users_for_analysis(days_back INT DEFAULT 7)
RETURNS TABLE (
    user_id UUID,
    session_count BIGINT,
    last_session_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        cs.user_id,
        COUNT(*) as session_count,
        MAX(cs.started_at) as last_session_at
    FROM chat_sessions cs
    WHERE cs.started_at > NOW() - (days_back || ' days')::INTERVAL
    GROUP BY cs.user_id
    HAVING COUNT(*) >= 2  -- Minimum 2 sessions to be considered for analysis
    ORDER BY session_count DESC, last_session_at DESC;
END;
$$;

COMMENT ON FUNCTION get_active_users_for_analysis IS
'ADR-060: Returns users with recent chat activity for conversation analysis.
Filters to users with at least 2 sessions in the specified period.';
