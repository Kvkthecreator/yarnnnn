-- Migration: 021_beta_deliverable_types.sql
-- ADR-019: Beta Tier Deliverable Types
-- Date: 2026-02-02
--
-- Adds Beta tier types to deliverables:
-- - client_proposal
-- - performance_self_assessment
-- - newsletter_section
-- - changelog
-- - one_on_one_prep
-- - board_update

-- =============================================================================
-- 1. UPDATE DELIVERABLE TYPE CHECK CONSTRAINT
-- =============================================================================

-- Drop existing constraint and add new one with Beta types
ALTER TABLE deliverables
    DROP CONSTRAINT IF EXISTS deliverables_deliverable_type_check;

ALTER TABLE deliverables
    ADD CONSTRAINT deliverables_deliverable_type_check
    CHECK (deliverable_type IN (
        -- Tier 1 (Stable)
        'status_report',
        'stakeholder_update',
        'research_brief',
        'meeting_summary',
        'custom',
        -- Beta Tier
        'client_proposal',
        'performance_self_assessment',
        'newsletter_section',
        'changelog',
        'one_on_one_prep',
        'board_update'
    ));

-- =============================================================================
-- 2. ADD TIER INDICATOR COLUMN
-- =============================================================================

-- Track which tier a deliverable type belongs to (for UI display)
ALTER TABLE deliverables
    ADD COLUMN IF NOT EXISTS type_tier TEXT
    DEFAULT 'stable'
    CHECK (type_tier IN ('stable', 'beta', 'experimental'));

-- Set tier based on type for existing records
UPDATE deliverables
SET type_tier = CASE
    WHEN deliverable_type IN ('status_report', 'stakeholder_update', 'research_brief', 'meeting_summary') THEN 'stable'
    WHEN deliverable_type IN ('client_proposal', 'performance_self_assessment', 'newsletter_section', 'changelog', 'one_on_one_prep', 'board_update') THEN 'beta'
    ELSE 'experimental'
END;

-- =============================================================================
-- 3. UPDATE TYPE METRICS VIEW
-- =============================================================================

-- Recreate view with tier information
DROP VIEW IF EXISTS deliverable_type_metrics;

CREATE VIEW deliverable_type_metrics AS
SELECT
    d.user_id,
    d.deliverable_type,
    d.type_tier,
    COUNT(DISTINCT d.id) as deliverable_count,
    COUNT(dv.id) as total_versions,
    COUNT(dv.id) FILTER (WHERE dv.status = 'approved') as approved_versions,
    COUNT(dv.id) FILTER (WHERE dv.status = 'rejected') as rejected_versions,
    AVG(dv.edit_distance_score) FILTER (WHERE dv.status = 'approved') as avg_edit_distance,
    COUNT(dv.id) FILTER (WHERE dv.edit_distance_score < 0.3 AND dv.status = 'approved') as low_edit_count,
    COUNT(dv.id) FILTER (WHERE dv.edit_distance_score >= 0.3 AND dv.status = 'approved') as high_edit_count
FROM deliverables d
LEFT JOIN deliverable_versions dv ON d.id = dv.deliverable_id
GROUP BY d.user_id, d.deliverable_type, d.type_tier;

-- =============================================================================
-- 4. COMMENTS
-- =============================================================================

COMMENT ON COLUMN deliverables.type_tier IS 'ADR-019: Tier classification (stable, beta, experimental) for quality expectation setting';
