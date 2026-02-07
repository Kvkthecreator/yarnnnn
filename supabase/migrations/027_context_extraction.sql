-- Migration: 027_context_extraction.sql
-- ADR-030: Context Extraction Methodology
-- Date: 2026-02-06
--
-- Adds schema for:
-- 1. Platform landscape discovery (what resources exist)
-- 2. Coverage tracking (what's extracted vs. not)
-- 3. Scope parameters for import jobs
-- 4. Delta extraction for recurring deliverables

-- =============================================================================
-- 1. EXTEND USER_INTEGRATIONS FOR LANDSCAPE
-- =============================================================================

-- Add landscape snapshot to user_integrations
-- This stores discovered resources (channels, labels, pages) for each platform
ALTER TABLE user_integrations
    ADD COLUMN IF NOT EXISTS landscape JSONB DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS landscape_discovered_at TIMESTAMPTZ DEFAULT NULL;

COMMENT ON COLUMN user_integrations.landscape IS
'ADR-030: Discovered platform resources. Gmail: {labels: [...]}. Slack: {channels: [...]}. Notion: {pages: [...]}';

COMMENT ON COLUMN user_integrations.landscape_discovered_at IS
'ADR-030: When landscape was last discovered. NULL = never discovered.';

-- =============================================================================
-- 2. INTEGRATION_COVERAGE TABLE
-- =============================================================================
-- Tracks coverage state for each resource in the landscape

CREATE TABLE IF NOT EXISTS integration_coverage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Which integration and resource
    provider TEXT NOT NULL,  -- 'gmail', 'slack', 'notion'
    resource_id TEXT NOT NULL,  -- label_id, channel_id, page_id
    resource_name TEXT,  -- Display name: "Primary", "#engineering", "Project Wiki"
    resource_type TEXT,  -- 'label', 'channel', 'page', 'database'

    -- Coverage state
    -- uncovered: exists, never extracted
    -- partial: extracted with constraints (e.g., last 7 days only)
    -- covered: fully extracted within defined scope
    -- stale: covered, but last sync > staleness threshold
    -- excluded: user explicitly marked as not relevant
    coverage_state TEXT NOT NULL DEFAULT 'uncovered',

    -- Scope constraints (when covered/partial)
    scope JSONB DEFAULT NULL,
    -- Gmail: {"recency_days": 7, "max_messages": 100, "include_sent": true}
    -- Slack: {"recency_days": 7, "max_messages": 200, "include_threads": true}
    -- Notion: {"max_depth": 2, "max_pages": 10}

    -- Extraction stats
    last_extracted_at TIMESTAMPTZ,
    items_extracted INTEGER DEFAULT 0,
    blocks_created INTEGER DEFAULT 0,

    -- Staleness threshold (hours) - default 168 = 7 days
    staleness_threshold_hours INTEGER DEFAULT 168,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- One coverage record per resource per user
    UNIQUE(user_id, provider, resource_id),

    CONSTRAINT valid_coverage_state CHECK (
        coverage_state IN ('uncovered', 'partial', 'covered', 'stale', 'excluded')
    ),
    CONSTRAINT valid_coverage_provider CHECK (
        provider IN ('gmail', 'slack', 'notion')
    )
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_coverage_user_provider
    ON integration_coverage(user_id, provider);
CREATE INDEX IF NOT EXISTS idx_coverage_state
    ON integration_coverage(coverage_state);

-- RLS
ALTER TABLE integration_coverage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own coverage"
    ON integration_coverage FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own coverage"
    ON integration_coverage FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role can manage all coverage"
    ON integration_coverage FOR ALL
    TO service_role
    USING (true);


-- =============================================================================
-- 3. EXTEND INTEGRATION_IMPORT_JOBS WITH SCOPE
-- =============================================================================

-- Add scope parameters to import jobs
ALTER TABLE integration_import_jobs
    ADD COLUMN IF NOT EXISTS scope JSONB DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS progress_details JSONB DEFAULT NULL;

-- Update provider constraint to include gmail
ALTER TABLE integration_import_jobs
    DROP CONSTRAINT IF EXISTS valid_provider;
ALTER TABLE integration_import_jobs
    ADD CONSTRAINT valid_provider CHECK (provider IN ('slack', 'notion', 'gmail'));

COMMENT ON COLUMN integration_import_jobs.scope IS
'ADR-030: Extraction scope parameters. {recency_days, max_items, mode: "delta"|"fixed_window", ...}';

COMMENT ON COLUMN integration_import_jobs.progress_details IS
'ADR-030: Detailed progress. {phase, items_total, items_completed, current_resource, eta_seconds}';


-- =============================================================================
-- 4. EXTEND DELIVERABLES WITH SOURCE SCOPE
-- =============================================================================

-- The sources JSONB array already exists on deliverables.
-- Each source should support scope configuration per ADR-030:
-- {
--   "type": "integration_import",
--   "provider": "gmail",
--   "source": "inbox",
--   "scope": {
--     "mode": "delta",           -- "delta" or "fixed_window"
--     "fallback_days": 7,        -- If no last_run, go back 7 days
--     "max_items": 200,          -- Safety cap
--     "recency_days": null       -- For fixed_window mode
--   }
-- }
--
-- No schema change needed - sources is already JSONB.
-- This is documented here for reference.


-- =============================================================================
-- 5. HELPER FUNCTIONS
-- =============================================================================

-- Function to compute coverage state based on last_extracted_at and threshold
CREATE OR REPLACE FUNCTION compute_coverage_state(
    p_last_extracted_at TIMESTAMPTZ,
    p_staleness_threshold_hours INTEGER,
    p_current_state TEXT
)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
BEGIN
    -- If excluded, stay excluded
    IF p_current_state = 'excluded' THEN
        RETURN 'excluded';
    END IF;

    -- If never extracted, uncovered
    IF p_last_extracted_at IS NULL THEN
        RETURN 'uncovered';
    END IF;

    -- Check if stale
    IF p_last_extracted_at < (now() - (p_staleness_threshold_hours || ' hours')::interval) THEN
        RETURN 'stale';
    END IF;

    -- Otherwise return current state (covered or partial)
    RETURN COALESCE(p_current_state, 'covered');
END;
$$;


-- Function to get coverage summary for a user+provider
CREATE OR REPLACE FUNCTION get_coverage_summary(
    p_user_id UUID,
    p_provider TEXT
)
RETURNS TABLE (
    total_resources INTEGER,
    covered_count INTEGER,
    partial_count INTEGER,
    stale_count INTEGER,
    uncovered_count INTEGER,
    excluded_count INTEGER,
    coverage_percentage NUMERIC
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INTEGER as total_resources,
        COUNT(*) FILTER (WHERE coverage_state = 'covered')::INTEGER as covered_count,
        COUNT(*) FILTER (WHERE coverage_state = 'partial')::INTEGER as partial_count,
        COUNT(*) FILTER (WHERE coverage_state = 'stale')::INTEGER as stale_count,
        COUNT(*) FILTER (WHERE coverage_state = 'uncovered')::INTEGER as uncovered_count,
        COUNT(*) FILTER (WHERE coverage_state = 'excluded')::INTEGER as excluded_count,
        CASE
            WHEN COUNT(*) = 0 THEN 0
            ELSE ROUND(
                (COUNT(*) FILTER (WHERE coverage_state IN ('covered', 'partial'))::NUMERIC /
                 NULLIF(COUNT(*) FILTER (WHERE coverage_state != 'excluded'), 0)::NUMERIC) * 100,
                1
            )
        END as coverage_percentage
    FROM integration_coverage
    WHERE user_id = p_user_id
      AND provider = p_provider;
END;
$$;


-- =============================================================================
-- 6. UPDATE TRIGGER
-- =============================================================================

CREATE OR REPLACE FUNCTION update_coverage_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_integration_coverage_timestamp
    BEFORE UPDATE ON integration_coverage
    FOR EACH ROW
    EXECUTE FUNCTION update_coverage_timestamp();


-- =============================================================================
-- 7. COMMENTS
-- =============================================================================

COMMENT ON TABLE integration_coverage IS
'ADR-030: Tracks extraction coverage per resource. Shows what YARNNN knows vs. what exists.';
