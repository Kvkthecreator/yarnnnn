-- Migration 099: Clean stale deliverable terminology from DB
-- Part of ADR-103 agentic rename — removes columns and objects that still reference "deliverable"
-- These columns have ZERO code references and are safe to drop.

-- 1. Rename stale columns on user_notification_preferences
ALTER TABLE user_notification_preferences
  RENAME COLUMN email_deliverable_ready TO email_agent_ready;

ALTER TABLE user_notification_preferences
  RENAME COLUMN email_deliverable_failed TO email_agent_failed;

-- 2. Rename stale column on user_interaction_patterns
ALTER TABLE user_interaction_patterns
  RENAME COLUMN proposed_deliverable_id TO proposed_agent_id;

-- 3. Drop signal_history table (ADR-092 dissolved signal processing, zero code references)
DROP TABLE IF EXISTS signal_history CASCADE;

-- 4. Drop stale RPC functions with zero code callers
DROP FUNCTION IF EXISTS spawn_ticket_from_template CASCADE;
DROP FUNCTION IF EXISTS get_knowledge_entries_by_importance CASCADE;
DROP FUNCTION IF EXISTS get_effective_profile CASCADE;
DROP FUNCTION IF EXISTS get_work_status CASCADE;
DROP FUNCTION IF EXISTS get_project_resources CASCADE;
DROP FUNCTION IF EXISTS get_user_integrations CASCADE;
