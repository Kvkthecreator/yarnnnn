-- Migration: 058_fix_security_definer_view.sql
-- Date: 2026-02-18
--
-- Fixes Supabase Advisor security issue:
-- View `deliverable_type_metrics` was created with SECURITY DEFINER (default)
-- which bypasses RLS policies. This recreates it with SECURITY INVOKER
-- so it respects the calling user's RLS permissions.

-- =============================================================================
-- 1. RECREATE VIEW WITH SECURITY INVOKER
-- =============================================================================

DROP VIEW IF EXISTS deliverable_type_metrics;

CREATE VIEW deliverable_type_metrics
WITH (security_invoker = true)
AS
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
-- 2. COMMENT
-- =============================================================================

COMMENT ON VIEW deliverable_type_metrics IS 'ADR-019: Aggregated quality metrics by deliverable type per user. Uses SECURITY INVOKER to respect RLS.';
