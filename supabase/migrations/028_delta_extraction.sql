-- Migration: 028_delta_extraction.sql
-- ADR-030 Phase 5: Delta Extraction for Recurring Deliverables
-- Date: 2026-02-07
--
-- Adds schema for:
-- 1. Source fetch tracking (last fetch time, status, errors)
-- 2. Delta extraction parameters in source configuration
-- 3. Failure handling for recurring deliverable runs

-- =============================================================================
-- 1. DELIVERABLE_SOURCE_RUNS TABLE
-- =============================================================================
-- Tracks each time a source is fetched for a deliverable run

CREATE TABLE IF NOT EXISTS deliverable_source_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Links
    deliverable_id UUID NOT NULL REFERENCES deliverables(id) ON DELETE CASCADE,
    version_id UUID REFERENCES deliverable_versions(id) ON DELETE SET NULL,

    -- Source identification
    source_index INTEGER NOT NULL,  -- Index in the deliverable.sources array
    source_type TEXT NOT NULL,  -- 'integration_import', 'url', 'document', 'description'
    provider TEXT,  -- 'gmail', 'slack', 'notion' for integration sources
    resource_id TEXT,  -- Channel ID, label ID, page ID

    -- Fetch parameters used
    scope_used JSONB DEFAULT NULL,  -- The actual scope params used for this fetch
    time_range_start TIMESTAMPTZ,  -- Start of time range fetched (for delta)
    time_range_end TIMESTAMPTZ,  -- End of time range fetched

    -- Results
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'fetching', 'completed', 'failed', 'skipped')),
    items_fetched INTEGER DEFAULT 0,
    items_filtered INTEGER DEFAULT 0,
    content_summary TEXT,  -- Brief summary of what was fetched

    -- Error tracking
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,

    -- Unique per source per version
    UNIQUE(version_id, source_index)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_source_runs_deliverable
    ON deliverable_source_runs(deliverable_id);
CREATE INDEX IF NOT EXISTS idx_source_runs_version
    ON deliverable_source_runs(version_id);
CREATE INDEX IF NOT EXISTS idx_source_runs_status
    ON deliverable_source_runs(status);

-- RLS
ALTER TABLE deliverable_source_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view source runs for their deliverables"
    ON deliverable_source_runs FOR SELECT
    USING (
        deliverable_id IN (
            SELECT id FROM deliverables WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Service role can manage all source runs"
    ON deliverable_source_runs FOR ALL
    TO service_role
    USING (true);


-- =============================================================================
-- 2. EXTEND DELIVERABLE_VERSIONS WITH SOURCE FETCH SUMMARY
-- =============================================================================

ALTER TABLE deliverable_versions
    ADD COLUMN IF NOT EXISTS source_fetch_summary JSONB DEFAULT NULL;

COMMENT ON COLUMN deliverable_versions.source_fetch_summary IS
'ADR-030: Summary of source fetches for this version. {sources_total, sources_succeeded, sources_failed, delta_mode_used}';


-- =============================================================================
-- 3. HELPER FUNCTIONS
-- =============================================================================

-- Function to get the last successful fetch time for a source
CREATE OR REPLACE FUNCTION get_last_source_fetch_time(
    p_deliverable_id UUID,
    p_source_index INTEGER
)
RETURNS TIMESTAMPTZ
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    last_time TIMESTAMPTZ;
BEGIN
    SELECT completed_at
    INTO last_time
    FROM deliverable_source_runs
    WHERE deliverable_id = p_deliverable_id
      AND source_index = p_source_index
      AND status = 'completed'
    ORDER BY completed_at DESC
    LIMIT 1;

    RETURN last_time;
END;
$$;


-- Function to get source freshness for a deliverable
CREATE OR REPLACE FUNCTION get_deliverable_source_freshness(
    p_deliverable_id UUID
)
RETURNS TABLE (
    source_index INTEGER,
    source_type TEXT,
    provider TEXT,
    last_fetched_at TIMESTAMPTZ,
    last_status TEXT,
    items_fetched INTEGER,
    is_stale BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    WITH latest_runs AS (
        SELECT DISTINCT ON (dsr.source_index)
            dsr.source_index,
            dsr.source_type,
            dsr.provider,
            dsr.completed_at as last_fetched_at,
            dsr.status as last_status,
            dsr.items_fetched,
            -- Stale if older than 7 days or never fetched
            (dsr.completed_at IS NULL OR
             dsr.completed_at < (now() - interval '7 days')) as is_stale
        FROM deliverable_source_runs dsr
        WHERE dsr.deliverable_id = p_deliverable_id
        ORDER BY dsr.source_index, dsr.completed_at DESC NULLS LAST
    )
    SELECT * FROM latest_runs;
END;
$$;


-- =============================================================================
-- 4. COMMENTS
-- =============================================================================

COMMENT ON TABLE deliverable_source_runs IS
'ADR-030 Phase 5: Tracks each source fetch for recurring deliverables. Enables delta extraction and freshness tracking.';

COMMENT ON COLUMN deliverable_source_runs.scope_used IS
'ADR-030: Scope parameters used for this fetch. For delta mode: {mode: "delta", since: "2026-02-06T..."}, for fixed: {mode: "fixed_window", recency_days: 7}';

COMMENT ON COLUMN deliverable_source_runs.time_range_start IS
'ADR-030: For delta mode, the timestamp we started fetching from (usually last_run_at or fallback_days ago)';
