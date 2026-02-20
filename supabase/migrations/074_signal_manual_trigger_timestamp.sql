-- Migration: 074_signal_manual_trigger_timestamp.sql
-- ADR-068: Manual signal processing trigger
--
-- Adds timestamp tracking for manual signal processing triggers
-- to implement 5-minute rate limiting on the manual trigger button.

ALTER TABLE user_notification_preferences
    ADD COLUMN IF NOT EXISTS signal_last_manual_trigger_at TIMESTAMPTZ DEFAULT NULL;

COMMENT ON COLUMN user_notification_preferences.signal_last_manual_trigger_at IS 'ADR-068: Last time user manually triggered signal processing (for rate limiting)';
