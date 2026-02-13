-- Migration: 046_restore_import_jobs.sql
-- ADR-058: Knowledge Base Architecture - Fix
-- Date: 2026-02-13
--
-- The integration_import_jobs table was accidentally dropped in 045.
-- This table is still needed for tracking sync/import operations.
--
-- This migration recreates the table.

-- =============================================================================
-- RECREATE integration_import_jobs TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS integration_import_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Import target
    provider TEXT NOT NULL,  -- 'slack', 'gmail', 'notion'
    resource_id TEXT NOT NULL,  -- channel_id, label, page_id
    resource_name TEXT,  -- #channel-name, label name, page title

    -- Configuration
    instructions TEXT,  -- optional user instructions
    config JSONB DEFAULT '{}',  -- job-specific config
    scope JSONB DEFAULT '{}',  -- ADR-030: scope parameters (max_items, recency_days, etc.)

    -- Status tracking
    status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
    progress INTEGER DEFAULT 0,  -- 0-100 percent
    progress_details JSONB DEFAULT '{}',  -- ADR-030: phase, items_total, items_completed, etc.

    -- Results
    result JSONB,  -- extraction result
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Index for querying pending jobs
CREATE INDEX IF NOT EXISTS idx_import_jobs_pending
ON integration_import_jobs(status, created_at)
WHERE status = 'pending';

-- Index for user's jobs
CREATE INDEX IF NOT EXISTS idx_import_jobs_user
ON integration_import_jobs(user_id, created_at DESC);

-- RLS
ALTER TABLE integration_import_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own import jobs"
ON integration_import_jobs FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own import jobs"
ON integration_import_jobs FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own import jobs"
ON integration_import_jobs FOR UPDATE
USING (auth.uid() = user_id);

COMMENT ON TABLE integration_import_jobs IS
'Tracks platform sync/import operations. Used by unified_scheduler and import_jobs.py.';
