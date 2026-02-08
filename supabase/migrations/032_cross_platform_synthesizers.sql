-- ADR-031 Phase 6: Cross-Platform Synthesizers
-- Migration 032: Schema changes for cross-platform deliverable synthesis
--
-- This migration adds support for:
-- 1. project_resources table - Maps projects to platform resources
-- 2. Multi-destination deliverables
-- 3. Cross-platform context assembly tracking
-- 4. Updated deliverable columns for synthesizer support

-- =============================================================================
-- 1. Project-to-Resource Mapping Table
-- =============================================================================
-- Maps abstract "projects" to concrete platform resources (Slack channels,
-- Gmail labels, Notion pages). This enables cross-platform synthesizers to
-- pull context from multiple platforms for the same logical project.

CREATE TABLE IF NOT EXISTS project_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Platform configuration
    platform TEXT NOT NULL,  -- slack, gmail, notion, calendar
    resource_type TEXT NOT NULL,  -- channel, label, page, database, calendar
    resource_id TEXT NOT NULL,  -- Platform-specific ID (C123, label:work, page_id)
    resource_name TEXT,  -- Human-readable name for display

    -- Mapping metadata
    is_primary BOOLEAN DEFAULT false,  -- Primary resource for this platform
    auto_discovered BOOLEAN DEFAULT false,  -- Was this auto-suggested by YARNNN?

    -- Filtering options
    include_filters JSONB DEFAULT '{}',  -- e.g., {"message_types": ["user"], "senders": ["U123"]}
    exclude_filters JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    last_synced_at TIMESTAMPTZ,  -- When context was last pulled from this resource

    -- Ensure no duplicate mappings
    UNIQUE(project_id, platform, resource_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_project_resources_project ON project_resources(project_id);
CREATE INDEX IF NOT EXISTS idx_project_resources_user ON project_resources(user_id);
CREATE INDEX IF NOT EXISTS idx_project_resources_platform ON project_resources(platform, resource_id);

-- RLS
ALTER TABLE project_resources ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own project resources" ON project_resources
    FOR ALL USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Service role can manage all project resources" ON project_resources
    FOR ALL TO service_role USING (true);


-- =============================================================================
-- 2. Multi-Destination Support on Deliverables
-- =============================================================================
-- Allows a single deliverable to output to multiple destinations.
-- For backward compatibility, destination (singular) remains as the primary destination.

-- destinations array for multi-destination deliverables
ALTER TABLE deliverables ADD COLUMN IF NOT EXISTS destinations JSONB DEFAULT '[]';

-- Comment explaining the schema
COMMENT ON COLUMN deliverables.destinations IS 'Array of destination configs for multi-destination deliverables. Schema: [{"platform": "slack", "target": "#team", "format": "blocks", "options": {}}]';

-- Index for querying by platform in destinations
CREATE INDEX IF NOT EXISTS idx_deliverables_destinations ON deliverables
    USING GIN (destinations jsonb_path_ops)
    WHERE destinations IS NOT NULL AND destinations != '[]'::jsonb;


-- =============================================================================
-- 3. Cross-Platform Context Assembly Tracking
-- =============================================================================
-- Track which resources were used when assembling context for synthesizers.

CREATE TABLE IF NOT EXISTS synthesizer_context_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID NOT NULL REFERENCES deliverable_versions(id) ON DELETE CASCADE,
    deliverable_id UUID NOT NULL REFERENCES deliverables(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Context assembly details
    sources_assembled JSONB NOT NULL DEFAULT '[]',  -- Array of {platform, resource_id, items_count, time_range}
    total_items_pulled INTEGER DEFAULT 0,
    total_items_after_dedup INTEGER DEFAULT 0,  -- After cross-platform deduplication

    -- Timing
    assembly_started_at TIMESTAMPTZ DEFAULT now(),
    assembly_completed_at TIMESTAMPTZ,
    assembly_duration_ms INTEGER,

    -- Quality metrics
    context_overlap_score FLOAT,  -- 0-1: How much context overlapped between platforms
    freshness_score FLOAT  -- 0-1: How recent the context was on average
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_synth_context_version ON synthesizer_context_log(version_id);
CREATE INDEX IF NOT EXISTS idx_synth_context_deliverable ON synthesizer_context_log(deliverable_id);

-- RLS
ALTER TABLE synthesizer_context_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own synthesizer logs" ON synthesizer_context_log
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Service role can manage all synthesizer logs" ON synthesizer_context_log
    FOR ALL TO service_role USING (true);


-- =============================================================================
-- 4. Synthesizer Type Flag on Deliverables
-- =============================================================================
-- Quick way to identify cross-platform synthesizer deliverables.

ALTER TABLE deliverables ADD COLUMN IF NOT EXISTS is_synthesizer BOOLEAN DEFAULT false;

-- Index for synthesizer deliverables
CREATE INDEX IF NOT EXISTS idx_deliverables_synthesizer ON deliverables(is_synthesizer)
    WHERE is_synthesizer = true;


-- =============================================================================
-- 5. Helper Function: Get Project Resources
-- =============================================================================

CREATE OR REPLACE FUNCTION get_project_resources(
    p_project_id UUID,
    p_platform TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    platform TEXT,
    resource_type TEXT,
    resource_id TEXT,
    resource_name TEXT,
    is_primary BOOLEAN,
    include_filters JSONB,
    last_synced_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pr.id,
        pr.platform,
        pr.resource_type,
        pr.resource_id,
        pr.resource_name,
        pr.is_primary,
        pr.include_filters,
        pr.last_synced_at
    FROM project_resources pr
    WHERE pr.project_id = p_project_id
      AND (p_platform IS NULL OR pr.platform = p_platform)
    ORDER BY pr.is_primary DESC, pr.platform, pr.resource_name;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- =============================================================================
-- 6. Helper Function: Get Cross-Platform Context Summary
-- =============================================================================

CREATE OR REPLACE FUNCTION get_cross_platform_context_summary(
    p_user_id UUID,
    p_project_id UUID,
    p_since TIMESTAMPTZ DEFAULT now() - INTERVAL '7 days'
)
RETURNS TABLE (
    platform TEXT,
    resource_id TEXT,
    resource_name TEXT,
    item_count BIGINT,
    latest_item TIMESTAMPTZ,
    oldest_item TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ec.platform,
        ec.resource_id,
        pr.resource_name,
        COUNT(*)::BIGINT as item_count,
        MAX(ec.source_timestamp) as latest_item,
        MIN(ec.source_timestamp) as oldest_item
    FROM ephemeral_context ec
    LEFT JOIN project_resources pr ON (
        pr.platform = ec.platform
        AND pr.resource_id = ec.resource_id
        AND pr.project_id = p_project_id
    )
    WHERE ec.user_id = p_user_id
      AND ec.created_at >= p_since
      AND ec.expires_at > now()
      AND (
          -- Either directly part of the project's resources
          pr.id IS NOT NULL
          -- Or we'll include all if no project resources defined (for initial setup)
          OR NOT EXISTS (
              SELECT 1 FROM project_resources
              WHERE project_id = p_project_id
          )
      )
    GROUP BY ec.platform, ec.resource_id, pr.resource_name
    ORDER BY item_count DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- =============================================================================
-- 7. Destination Delivery Log (for multi-destination tracking)
-- =============================================================================

CREATE TABLE IF NOT EXISTS destination_delivery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID NOT NULL REFERENCES deliverable_versions(id) ON DELETE CASCADE,
    deliverable_id UUID NOT NULL REFERENCES deliverables(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Destination details
    destination_index INTEGER NOT NULL,  -- Index in destinations array
    destination JSONB NOT NULL,  -- The destination config
    platform TEXT NOT NULL,

    -- Delivery result
    status TEXT NOT NULL,  -- pending, delivering, delivered, failed
    external_id TEXT,
    external_url TEXT,
    error_message TEXT,

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_dest_delivery_version ON destination_delivery_log(version_id);
CREATE INDEX IF NOT EXISTS idx_dest_delivery_status ON destination_delivery_log(status);

-- RLS
ALTER TABLE destination_delivery_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own delivery logs" ON destination_delivery_log
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Service role can manage all delivery logs" ON destination_delivery_log
    FOR ALL TO service_role USING (true);

