-- Migration: 093_remove_legacy_notification_preferences.sql
-- Removes legacy notification concepts:
-- - email_work_complete
-- - email_weekly_digest
--
-- Keeps active notification controls:
-- - email_deliverable_ready
-- - email_deliverable_failed
-- - email_suggestion_created
--
-- Also removes the legacy weekly digest scheduling function.

ALTER TABLE user_notification_preferences
    DROP COLUMN IF EXISTS email_work_complete,
    DROP COLUMN IF EXISTS email_weekly_digest;

-- Return type changed; recreate helper function.
DROP FUNCTION IF EXISTS get_notification_preferences(UUID);

CREATE OR REPLACE FUNCTION get_notification_preferences(p_user_id UUID)
RETURNS TABLE (
    email_deliverable_ready BOOLEAN,
    email_deliverable_failed BOOLEAN,
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
        COALESCE(np.email_suggestion_created, true)
    FROM (SELECT 1) dummy
    LEFT JOIN user_notification_preferences np ON np.user_id = p_user_id;
END;
$$;

DROP FUNCTION IF EXISTS get_workspaces_due_for_digest(TIMESTAMPTZ);
