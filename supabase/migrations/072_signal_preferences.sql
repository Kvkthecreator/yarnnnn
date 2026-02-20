-- Migration: 072_signal_preferences.sql
-- ADR-068 Phase 3: User signal preferences
--
-- Extends user_notification_preferences with signal type toggles.
-- Users can opt-in/opt-out of specific signal types (meeting_prep, silence_alert, etc.)
--
-- Default: All signal types enabled (opt-in by default, user can disable)

ALTER TABLE user_notification_preferences
    ADD COLUMN IF NOT EXISTS signal_meeting_prep BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS signal_silence_alert BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS signal_contact_drift BOOLEAN DEFAULT true;

COMMENT ON COLUMN user_notification_preferences.signal_meeting_prep IS 'ADR-068: Receive proactive meeting prep briefs for upcoming calendar events';
COMMENT ON COLUMN user_notification_preferences.signal_silence_alert IS 'ADR-068: Receive alerts for Gmail threads that have gone quiet';
COMMENT ON COLUMN user_notification_preferences.signal_contact_drift IS 'ADR-068: Receive alerts when key contacts haven''t been contacted in N days';
