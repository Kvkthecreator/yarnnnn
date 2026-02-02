-- Migration: 022_user_notification_preferences.sql
-- ADR-018: Deliverable Scheduling - Phase 2
--
-- Adds user notification preferences for email control.

-- =============================================================================
-- User Notification Preferences
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_notification_preferences (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Email notification toggles
    email_deliverable_ready BOOLEAN DEFAULT true,
    email_deliverable_failed BOOLEAN DEFAULT true,
    email_work_complete BOOLEAN DEFAULT true,
    email_weekly_digest BOOLEAN DEFAULT true,

    -- Future: push notifications, Slack, etc.

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- One row per user
    UNIQUE(user_id)
);

-- Index for lookup
CREATE INDEX IF NOT EXISTS idx_notification_prefs_user
    ON user_notification_preferences(user_id);

-- RLS
ALTER TABLE user_notification_preferences ENABLE ROW LEVEL SECURITY;

-- Users can only see/edit their own preferences
CREATE POLICY "Users can view own notification preferences"
    ON user_notification_preferences
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own notification preferences"
    ON user_notification_preferences
    FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own notification preferences"
    ON user_notification_preferences
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Service role can read all (for scheduler)
CREATE POLICY "Service role can read all notification preferences"
    ON user_notification_preferences
    FOR SELECT
    TO service_role
    USING (true);

-- =============================================================================
-- Helper function to get preferences (with defaults)
-- =============================================================================

CREATE OR REPLACE FUNCTION get_notification_preferences(p_user_id UUID)
RETURNS TABLE (
    email_deliverable_ready BOOLEAN,
    email_deliverable_failed BOOLEAN,
    email_work_complete BOOLEAN,
    email_weekly_digest BOOLEAN
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
        COALESCE(np.email_weekly_digest, true)
    FROM (SELECT 1) dummy
    LEFT JOIN user_notification_preferences np ON np.user_id = p_user_id;
END;
$$;
