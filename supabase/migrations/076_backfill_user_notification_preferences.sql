-- Migration: 076_backfill_user_notification_preferences.sql
-- Backfills user_notification_preferences for existing users who don't have a row
-- Migration 074 added the signal_last_manual_trigger_at column but didn't create initial rows

-- Insert rows for all users who don't already have one (using actual column names)
INSERT INTO user_notification_preferences (
    user_id,
    email_deliverable_ready,
    email_deliverable_failed,
    email_work_complete,
    email_weekly_digest,
    email_suggestion_created,
    signal_meeting_prep,
    signal_silence_alert,
    signal_contact_drift,
    signal_last_manual_trigger_at
)
SELECT
    u.id,
    true,  -- email_deliverable_ready
    true,  -- email_deliverable_failed
    true,  -- email_work_complete
    true,  -- email_weekly_digest
    true,  -- email_suggestion_created
    true,  -- signal_meeting_prep
    true,  -- signal_silence_alert
    true,  -- signal_contact_drift
    NULL   -- signal_last_manual_trigger_at (no previous trigger)
FROM auth.users u
WHERE NOT EXISTS (
    SELECT 1
    FROM user_notification_preferences unp
    WHERE unp.user_id = u.id
);
