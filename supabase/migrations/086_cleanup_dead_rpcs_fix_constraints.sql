-- Migration: 086_cleanup_dead_rpcs_fix_constraints.sql
-- Date: 2026-03-03
--
-- 1. Drop dead get_due_work_templates RPC (ADR-017 legacy, never matched
--    current work_tickets schema — columns is_active/frequency_cron don't exist)
-- 2. Fix notifications_source_type_check to include 'suggestion'
--    (nightly analysis creates suggestion notifications — blocked since Feb 24)

-- =============================================================================
-- 1. DROP DEAD RPCs
-- =============================================================================

DROP FUNCTION IF EXISTS get_due_work_templates(TIMESTAMPTZ);
DROP FUNCTION IF EXISTS get_due_work(TIMESTAMPTZ);

-- =============================================================================
-- 2. FIX notifications_source_type_check
-- =============================================================================

ALTER TABLE notifications
DROP CONSTRAINT IF EXISTS notifications_source_type_check;

ALTER TABLE notifications
ADD CONSTRAINT notifications_source_type_check
CHECK (source_type IN ('system', 'monitor', 'tp', 'deliverable', 'event_trigger', 'suggestion'));
