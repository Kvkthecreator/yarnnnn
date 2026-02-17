-- Migration: 054_analyst_cold_start_tracking.sql
-- ADR-060 Amendment 001: Behavioral Pattern Detection
-- Date: 2026-02-17
--
-- Tracks whether user has received the analyst cold start message
-- explaining the feature when no patterns are detected.

-- =============================================================================
-- 1. ADD COLD START TRACKING COLUMN
-- =============================================================================

ALTER TABLE user_notification_preferences
ADD COLUMN IF NOT EXISTS analyst_cold_start_sent BOOLEAN DEFAULT false;

COMMENT ON COLUMN user_notification_preferences.analyst_cold_start_sent IS
'ADR-060 Amendment 001: Whether user has received the analyst cold start message explaining the feature exists.';
