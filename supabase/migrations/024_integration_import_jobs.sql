-- Migration: 024_integration_import_jobs
-- Description: Add tables for integration import jobs and sync configuration
-- See ADR-027: Integration Read Architecture
--
-- Tables:
--   - integration_import_jobs: Track import operations (background jobs)
--   - integration_sync_config: Configure continuous sync for resources
--
-- Note: Imported context is stored in the 'memories' table with:
--   - source_type = 'import'
--   - source_ref = JSONB with platform, resource_id, job_id, etc.

-- =============================================================================
-- Import Jobs Table
-- =============================================================================
-- Tracks each import operation. Imports run as background jobs because
-- they involve API calls + LLM processing which can take time.

CREATE TABLE IF NOT EXISTS integration_import_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

    -- What we're importing from
    provider TEXT NOT NULL,  -- 'slack' | 'notion'
    resource_id TEXT NOT NULL,  -- channel_id, page_id
    resource_name TEXT,  -- #channel-name, Page Title (for display)

    -- Job status
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    progress INT DEFAULT 0,  -- 0-100 percentage

    -- User guidance for the agent
    instructions TEXT,

    -- Results (populated on completion)
    result JSONB,  -- { blocks_created, items_processed, items_filtered, summary }
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Index for efficient queries
    CONSTRAINT valid_status CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    CONSTRAINT valid_provider CHECK (provider IN ('slack', 'notion'))
);

-- Index for user's jobs list
CREATE INDEX IF NOT EXISTS idx_import_jobs_user_status
    ON integration_import_jobs(user_id, status);

-- Index for job processor to find pending jobs
CREATE INDEX IF NOT EXISTS idx_import_jobs_pending
    ON integration_import_jobs(status, created_at)
    WHERE status = 'pending';


-- =============================================================================
-- Sync Configuration Table
-- =============================================================================
-- Stores configuration for continuous sync (background polling).
-- Users can set up channels/pages to auto-sync at intervals.

CREATE TABLE IF NOT EXISTS integration_sync_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,

    -- What we're syncing
    provider TEXT NOT NULL,  -- 'slack' | 'notion'
    resource_id TEXT NOT NULL,  -- channel_id, page_id
    resource_name TEXT,  -- For display

    -- Sync settings
    sync_enabled BOOLEAN DEFAULT true,
    sync_interval_hours INT DEFAULT 24,  -- How often to sync

    -- Sync state
    last_synced_at TIMESTAMPTZ,
    sync_cursor TEXT,  -- Provider-specific cursor (Slack ts, Notion edited_time)
    last_sync_result JSONB,  -- Last sync result summary
    last_error TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- One sync config per resource per user
    UNIQUE(user_id, provider, resource_id),

    CONSTRAINT valid_sync_provider CHECK (provider IN ('slack', 'notion')),
    CONSTRAINT valid_sync_interval CHECK (sync_interval_hours >= 1 AND sync_interval_hours <= 168)
);

-- Index for finding configs due for sync
CREATE INDEX IF NOT EXISTS idx_sync_config_due
    ON integration_sync_config(sync_enabled, last_synced_at)
    WHERE sync_enabled = true;


-- =============================================================================
-- Row Level Security
-- =============================================================================

ALTER TABLE integration_import_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration_sync_config ENABLE ROW LEVEL SECURITY;

-- Import jobs: users can only see their own
CREATE POLICY "Users can view own import jobs"
    ON integration_import_jobs
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own import jobs"
    ON integration_import_jobs
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Note: Updates handled by service role (job processor)

-- Sync config: users can manage their own
CREATE POLICY "Users can view own sync config"
    ON integration_sync_config
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own sync config"
    ON integration_sync_config
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sync config"
    ON integration_sync_config
    FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own sync config"
    ON integration_sync_config
    FOR DELETE
    USING (auth.uid() = user_id);


-- =============================================================================
-- Notes on Memory Storage
-- =============================================================================
-- Imported context is stored in the existing 'memories' table, using:
--   source_type = 'import'
--   source_ref = {
--     "platform": "slack" | "notion",
--     "resource_id": "C123..." | "page-uuid",
--     "resource_name": "#channel-name" | "Page Title",
--     "job_id": "uuid",
--     "block_type": "decision" | "action_item" | "context" | "person" | "technical",
--     "metadata": {...agent-provided metadata...}
--   }
--
-- This leverages the existing memories architecture (ADR-005) rather than
-- creating a separate context_sources table.
