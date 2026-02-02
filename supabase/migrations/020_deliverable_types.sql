-- Migration: 020_deliverable_types.sql
-- ADR-019: Deliverable Types System
-- Date: 2026-02-02
--
-- Adds type system to deliverables:
-- - deliverable_type: Enum for supported types
-- - type_config: Type-specific configuration JSONB
-- - Migrates existing deliverables to 'custom' type

-- =============================================================================
-- 1. ADD DELIVERABLE TYPE COLUMNS
-- =============================================================================

-- Add deliverable_type column with default 'custom' for backwards compatibility
ALTER TABLE deliverables
    ADD COLUMN IF NOT EXISTS deliverable_type TEXT
    NOT NULL DEFAULT 'custom'
    CHECK (deliverable_type IN (
        'status_report',
        'stakeholder_update',
        'research_brief',
        'meeting_summary',
        'custom'
    ));

-- Add type_config JSONB column for type-specific settings
ALTER TABLE deliverables
    ADD COLUMN IF NOT EXISTS type_config JSONB DEFAULT '{}';

-- =============================================================================
-- 2. MIGRATE EXISTING DATA
-- =============================================================================

-- Migrate existing deliverables: move template_structure content to type_config for 'custom' type
UPDATE deliverables
SET type_config = COALESCE(template_structure, '{}')
WHERE deliverable_type = 'custom'
  AND (type_config IS NULL OR type_config = '{}');

-- =============================================================================
-- 3. ADD INDEX FOR TYPE QUERIES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_deliverables_type ON deliverables(deliverable_type);

-- =============================================================================
-- 4. VALIDATION RESULTS TABLE (for quality tracking)
-- =============================================================================

CREATE TABLE IF NOT EXISTS deliverable_validation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID NOT NULL REFERENCES deliverable_versions(id) ON DELETE CASCADE,

    -- Validation outcome
    is_valid BOOLEAN NOT NULL,
    validation_score FLOAT, -- 0.0 to 1.0

    -- Issues found
    issues JSONB DEFAULT '[]', -- Array of issue strings

    -- Metadata
    validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    validator_version TEXT -- Track which validation logic was used
);

-- Index for querying validation by version
CREATE INDEX IF NOT EXISTS idx_validation_version ON deliverable_validation_results(version_id);

-- RLS (via version -> deliverable ownership)
ALTER TABLE deliverable_validation_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view validation results for their deliverables"
    ON deliverable_validation_results FOR SELECT
    USING (
        version_id IN (
            SELECT dv.id FROM deliverable_versions dv
            JOIN deliverables d ON dv.deliverable_id = d.id
            WHERE d.user_id = auth.uid()
        )
    );

-- =============================================================================
-- 5. TYPE METRICS VIEW (for quality dashboard)
-- =============================================================================

CREATE OR REPLACE VIEW deliverable_type_metrics AS
SELECT
    d.user_id,
    d.deliverable_type,
    COUNT(DISTINCT d.id) as deliverable_count,
    COUNT(dv.id) as total_versions,
    COUNT(dv.id) FILTER (WHERE dv.status = 'approved') as approved_versions,
    COUNT(dv.id) FILTER (WHERE dv.status = 'rejected') as rejected_versions,
    AVG(dv.edit_distance_score) FILTER (WHERE dv.status = 'approved') as avg_edit_distance,
    COUNT(dv.id) FILTER (WHERE dv.edit_distance_score < 0.3 AND dv.status = 'approved') as low_edit_count,
    COUNT(dv.id) FILTER (WHERE dv.edit_distance_score >= 0.3 AND dv.status = 'approved') as high_edit_count
FROM deliverables d
LEFT JOIN deliverable_versions dv ON d.id = dv.deliverable_id
GROUP BY d.user_id, d.deliverable_type;

-- =============================================================================
-- 6. COMMENTS
-- =============================================================================

COMMENT ON COLUMN deliverables.deliverable_type IS 'ADR-019: Type of deliverable (status_report, stakeholder_update, research_brief, meeting_summary, custom)';
COMMENT ON COLUMN deliverables.type_config IS 'ADR-019: Type-specific configuration (audience, sections, depth, etc.)';
COMMENT ON TABLE deliverable_validation_results IS 'ADR-019: Quality validation results for each generated version';
COMMENT ON VIEW deliverable_type_metrics IS 'ADR-019: Aggregated quality metrics by deliverable type per user';
