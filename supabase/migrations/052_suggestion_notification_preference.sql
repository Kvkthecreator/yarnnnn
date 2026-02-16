-- Migration: 052_suggestion_notification_preference.sql
-- ADR-060: Background Conversation Analyst
-- Date: 2026-02-16
--
-- Adds notification preference for suggested deliverables.

-- =============================================================================
-- 1. ADD COLUMN FOR SUGGESTION NOTIFICATIONS
-- =============================================================================

ALTER TABLE user_notification_preferences
ADD COLUMN IF NOT EXISTS email_suggestion_created BOOLEAN DEFAULT true;

COMMENT ON COLUMN user_notification_preferences.email_suggestion_created IS
'ADR-060: Whether to send email when Conversation Analyst creates deliverable suggestions.';

-- =============================================================================
-- 2. UPDATE HELPER FUNCTION
-- =============================================================================

-- Drop existing function first (return type changed)
DROP FUNCTION IF EXISTS get_notification_preferences(UUID);

CREATE OR REPLACE FUNCTION get_notification_preferences(p_user_id UUID)
RETURNS TABLE (
    email_deliverable_ready BOOLEAN,
    email_deliverable_failed BOOLEAN,
    email_work_complete BOOLEAN,
    email_weekly_digest BOOLEAN,
    email_suggestion_created BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(np.email_deliverable_ready, true),
        COALESCE(np.email_deliverable_failed, true),
        COALESCE(np.email_work_complete, true),
        COALESCE(np.email_weekly_digest, true),
        COALESCE(np.email_suggestion_created, true)
    FROM (SELECT 1) dummy
    LEFT JOIN user_notification_preferences np ON np.user_id = p_user_id;
END;
$$;
