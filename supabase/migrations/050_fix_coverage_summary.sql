-- Migration 050: Recreate get_coverage_summary for ADR-058 schema
--
-- The original function was dropped in migration 045 because it used
-- integration_coverage table which no longer exists.
-- This creates a simplified version using sync_registry.

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
SET search_path = public
AS $$
DECLARE
    stale_threshold INTERVAL := INTERVAL '24 hours';
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INTEGER as total_resources,
        -- Covered: synced within threshold and has items
        COUNT(*) FILTER (
            WHERE sr.last_synced_at IS NOT NULL
            AND sr.last_synced_at > NOW() - stale_threshold
            AND sr.item_count > 0
        )::INTEGER as covered_count,
        -- Partial: synced but few items (less than 10)
        COUNT(*) FILTER (
            WHERE sr.last_synced_at IS NOT NULL
            AND sr.last_synced_at > NOW() - stale_threshold
            AND sr.item_count > 0 AND sr.item_count < 10
        )::INTEGER as partial_count,
        -- Stale: synced but older than threshold
        COUNT(*) FILTER (
            WHERE sr.last_synced_at IS NOT NULL
            AND sr.last_synced_at <= NOW() - stale_threshold
        )::INTEGER as stale_count,
        -- Uncovered: never synced
        COUNT(*) FILTER (
            WHERE sr.last_synced_at IS NULL
        )::INTEGER as uncovered_count,
        -- Excluded: none in new model (kept for API compatibility)
        0::INTEGER as excluded_count,
        -- Coverage percentage
        CASE
            WHEN COUNT(*) = 0 THEN 0
            ELSE ROUND(
                (COUNT(*) FILTER (
                    WHERE sr.last_synced_at IS NOT NULL
                    AND sr.last_synced_at > NOW() - stale_threshold
                )::NUMERIC / COUNT(*)::NUMERIC) * 100,
                1
            )
        END as coverage_percentage
    FROM sync_registry sr
    WHERE sr.user_id = p_user_id
      AND sr.platform = p_provider;
END;
$$;

GRANT EXECUTE ON FUNCTION get_coverage_summary TO authenticated;


-- =============================================================================
-- Also recreate find_domain_for_source for ADR-058 schema
-- =============================================================================

-- The original function used domain_sources table which was dropped.
-- In ADR-058, sources are stored as JSONB array in knowledge_domains.sources

CREATE OR REPLACE FUNCTION find_domain_for_source(
    p_user_id UUID,
    p_provider TEXT,
    p_resource_id TEXT
)
RETURNS UUID AS $$
DECLARE
    v_domain_id UUID;
BEGIN
    -- Search knowledge_domains.sources JSONB array for matching source
    -- sources format: [{"platform": "slack", "resource_id": "C123", "resource_name": "#general"}]
    SELECT kd.id INTO v_domain_id
    FROM knowledge_domains kd,
         jsonb_array_elements(COALESCE(kd.sources, '[]'::jsonb)) AS source
    WHERE kd.user_id = p_user_id
      AND kd.is_active = true
      AND source->>'platform' = p_provider
      AND source->>'resource_id' = p_resource_id
    LIMIT 1;

    RETURN v_domain_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

GRANT EXECUTE ON FUNCTION find_domain_for_source TO authenticated;
