-- Migration: 033_platform_centric_drafts.sql
-- ADR-032: Platform-Centric Draft Delivery
-- Date: 2026-02-09
--
-- Adds delivery_mode to track whether deliverables are delivered as drafts
-- (platform-centric) or directly published.

-- =============================================================================
-- 1. ADD DELIVERY MODE TO VERSIONS
-- =============================================================================

-- Track how content was delivered
-- draft = Content pushed to platform as draft (Gmail Drafts, Slack DM, Notion Drafts DB)
-- direct = Content published directly to destination
-- NULL = Legacy/unknown (before this migration)
ALTER TABLE deliverable_versions
ADD COLUMN IF NOT EXISTS delivery_mode TEXT DEFAULT NULL
    CHECK (delivery_mode IN ('draft', 'direct', NULL));

-- Index for querying draft deliveries
CREATE INDEX IF NOT EXISTS idx_versions_delivery_mode
ON deliverable_versions (delivery_mode)
WHERE delivery_mode IS NOT NULL;


-- =============================================================================
-- 2. ADD NOTION DRAFTS DATABASE TRACKING TO USER INTEGRATIONS
-- =============================================================================

-- Store the user's YARNNN Drafts database ID for Notion
-- This is created on first Notion draft delivery
-- Stored in integration metadata alongside access_token, etc.
-- Schema addition to user_integrations.metadata:
--   notion.drafts_database_id: "uuid"

-- No schema change needed - this goes in the existing metadata JSONB column


-- =============================================================================
-- 3. ADD SLACK USER ID CACHE
-- =============================================================================

-- Cache Slack user IDs by email to avoid repeated lookups
-- This is stored per-user, per-team
CREATE TABLE IF NOT EXISTS slack_user_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id TEXT NOT NULL,
    email TEXT NOT NULL,
    slack_user_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, team_id, email)
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_slack_user_cache_lookup
ON slack_user_cache (user_id, team_id, email);

-- RLS
ALTER TABLE slack_user_cache ENABLE ROW LEVEL SECURITY;

-- Users can only see their own cache
CREATE POLICY slack_user_cache_user_policy ON slack_user_cache
    FOR ALL USING (auth.uid() = user_id);

-- Service role can do anything
CREATE POLICY slack_user_cache_service_policy ON slack_user_cache
    FOR ALL USING (auth.role() = 'service_role');


-- =============================================================================
-- 4. COMMENTS
-- =============================================================================

COMMENT ON COLUMN deliverable_versions.delivery_mode IS
'ADR-032: How content was delivered - draft (to user for review) or direct (published immediately)';

COMMENT ON TABLE slack_user_cache IS
'ADR-032: Cache of Slack user IDs by email to avoid repeated lookups for DM drafts';
