-- ADR-031: Platform-Native Deliverable Architecture
-- Migration 030: Schema changes for platform-native deliverables
--
-- This migration adds support for:
-- 1. ephemeral_context table for temporal platform data
-- 2. platform_variant and governance_ceiling columns on deliverables
-- 3. user_platform_styles table for learned platform styles
-- 4. Observe loop columns on export_log
--
-- Note: These changes have already been applied directly via psql.
-- This file documents the schema changes for reference.

-- =============================================================================
-- 1. Ephemeral Context Table
-- =============================================================================
-- Stores time-bounded platform data for deliverable generation.
-- Separate from user_memories to avoid pollution of long-term memory.

CREATE TABLE IF NOT EXISTS ephemeral_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,  -- slack, gmail, notion
    resource_id TEXT NOT NULL,  -- channel_id, label, page_id
    resource_name TEXT,
    content TEXT NOT NULL,
    content_type TEXT,  -- message, thread_summary, page_update
    platform_metadata JSONB DEFAULT '{}',  -- thread_ts, reply_count, reactions, etc.
    source_timestamp TIMESTAMPTZ,  -- When it happened on platform
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL  -- TTL for cleanup
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_ephemeral_user_platform ON ephemeral_context(user_id, platform);
CREATE INDEX IF NOT EXISTS idx_ephemeral_expires ON ephemeral_context(expires_at);
CREATE INDEX IF NOT EXISTS idx_ephemeral_resource ON ephemeral_context(user_id, platform, resource_id);

-- RLS policies
ALTER TABLE ephemeral_context ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own ephemeral context" ON ephemeral_context
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Service role can manage all ephemeral context" ON ephemeral_context
    FOR ALL TO service_role USING (true);


-- =============================================================================
-- 2. Platform Variant and Governance Ceiling on Deliverables
-- =============================================================================

-- Platform variant for platform-specific versions of deliverable types
-- e.g., "slack_digest" for a status_report delivered to Slack
ALTER TABLE deliverables ADD COLUMN IF NOT EXISTS platform_variant TEXT;

-- Governance ceiling - system-enforced max based on destination
-- e.g., email to external = "manual", internal Slack = "full_auto"
ALTER TABLE deliverables ADD COLUMN IF NOT EXISTS governance_ceiling TEXT;

-- Add check constraint for governance_ceiling
ALTER TABLE deliverables ADD CONSTRAINT deliverables_governance_ceiling_check
    CHECK (governance_ceiling IS NULL OR governance_ceiling = ANY (ARRAY['manual', 'semi_auto', 'full_auto']));

-- Index for platform variant queries
CREATE INDEX IF NOT EXISTS idx_deliverables_platform_variant ON deliverables(platform_variant) WHERE platform_variant IS NOT NULL;


-- =============================================================================
-- 3. User Platform Styles Table
-- =============================================================================
-- Stores learned communication styles per platform for style matching.

CREATE TABLE IF NOT EXISTS user_platform_styles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,  -- slack, gmail, notion
    style_profile JSONB NOT NULL DEFAULT '{}',
    learned_from_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, platform)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_platform_styles_user ON user_platform_styles(user_id);

-- RLS policies
ALTER TABLE user_platform_styles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own platform styles" ON user_platform_styles
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Service role can manage all platform styles" ON user_platform_styles
    FOR ALL TO service_role USING (true);


-- =============================================================================
-- 4. Observe Loop Columns on Export Log (Phase 3 prep)
-- =============================================================================

-- Platform-specific metadata (message_ts for Slack, etc.)
ALTER TABLE export_log ADD COLUMN IF NOT EXISTS platform_metadata JSONB DEFAULT '{}';

-- Outcome tracking (reactions, replies, corrections)
ALTER TABLE export_log ADD COLUMN IF NOT EXISTS outcome JSONB;

-- When outcome was observed
ALTER TABLE export_log ADD COLUMN IF NOT EXISTS outcome_observed_at TIMESTAMPTZ;
