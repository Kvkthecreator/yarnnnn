-- Migration 092: Remove Conversation Analyst (ADR-060 superseded)
--
-- The Conversation Analyst system is removed in favor of coordinator deliverables (ADR-092).
-- This migration:
--   1. Deletes suggested versions and their parent deliverables
--   2. Drops the get_suggested_deliverable_versions RPC
--   3. Drops the get_active_users_for_analysis RPC

-- Step 1: Delete suggested versions first (FK constraint)
DELETE FROM deliverable_versions WHERE status = 'suggested';

-- Step 2: Delete orphaned paused deliverables that were analyst-created
-- These have no remaining versions and were created with status='paused'
DELETE FROM deliverables
WHERE status = 'paused'
  AND id NOT IN (SELECT DISTINCT deliverable_id FROM deliverable_versions);

-- Step 3: Drop analyst-specific RPC functions
DROP FUNCTION IF EXISTS get_suggested_deliverable_versions(uuid);
DROP FUNCTION IF EXISTS get_active_users_for_analysis(integer);
