-- Migration: 048_fix_domain_rpcs.sql
-- ADR-058: Knowledge Base Architecture - Fix domain RPCs
-- Date: 2026-02-13
--
-- The domain_sources and deliverable_domains tables were dropped in 045.
-- This migration updates the RPC functions to use the new schema:
-- - knowledge_domains.sources JSONB column (replaces domain_sources table)
-- - Compute deliverable associations dynamically (replaces deliverable_domains)

-- =============================================================================
-- DROP OLD FUNCTIONS
-- =============================================================================

DROP FUNCTION IF EXISTS get_user_domains_summary(uuid);
DROP FUNCTION IF EXISTS get_domain_sources(uuid);
DROP FUNCTION IF EXISTS get_deliverable_domain(uuid);

-- =============================================================================
-- RECREATE get_user_domains_summary FOR ADR-058 SCHEMA
-- =============================================================================

CREATE OR REPLACE FUNCTION get_user_domains_summary(p_user_id UUID)
RETURNS TABLE (
    id UUID,
    name TEXT,
    name_source TEXT,
    is_default BOOLEAN,
    source_count INT,
    deliverable_count INT,
    memory_count INT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        kd.id,
        kd.name,
        kd.name_source,
        kd.is_default,
        -- ADR-058: sources is now a JSONB column in knowledge_domains
        COALESCE(jsonb_array_length(kd.sources), 0)::INT as source_count,
        -- ADR-058: compute deliverable count from sources overlap
        (
            SELECT COUNT(DISTINCT d.id)::INT
            FROM deliverables d
            WHERE d.user_id = p_user_id
            AND d.status = 'active'
            AND EXISTS (
                SELECT 1
                FROM jsonb_array_elements(kd.sources) AS ds
                JOIN jsonb_array_elements(d.sources) AS dd ON true
                WHERE ds->>'resource_id' = dd->>'resource_id'
                AND (ds->>'platform' = dd->>'provider' OR ds->>'provider' = dd->>'provider')
            )
        ) as deliverable_count,
        -- Memory count from knowledge_entries
        (
            SELECT COUNT(*)::INT
            FROM knowledge_entries ke
            WHERE ke.domain_id = kd.id AND ke.is_active = true
        ) as memory_count,
        kd.created_at
    FROM knowledge_domains kd
    WHERE kd.user_id = p_user_id
    AND kd.is_active = true
    ORDER BY kd.is_default DESC, kd.name ASC;
END;
$$;

GRANT EXECUTE ON FUNCTION get_user_domains_summary TO authenticated;

-- =============================================================================
-- RECREATE get_deliverable_domain FOR ADR-058 SCHEMA
-- =============================================================================

CREATE OR REPLACE FUNCTION get_deliverable_domain(p_deliverable_id UUID)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_user_id UUID;
    v_domain_id UUID;
BEGIN
    -- Get the deliverable's user
    SELECT user_id INTO v_user_id
    FROM deliverables
    WHERE id = p_deliverable_id;

    IF v_user_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- Find a domain whose sources overlap with this deliverable's sources
    SELECT kd.id INTO v_domain_id
    FROM knowledge_domains kd
    JOIN deliverables d ON d.id = p_deliverable_id
    WHERE kd.user_id = v_user_id
    AND kd.is_active = true
    AND kd.is_default = false
    AND EXISTS (
        SELECT 1
        FROM jsonb_array_elements(kd.sources) AS ds
        JOIN jsonb_array_elements(d.sources) AS dd ON true
        WHERE ds->>'resource_id' = dd->>'resource_id'
        AND (ds->>'platform' = dd->>'provider' OR ds->>'provider' = dd->>'provider')
    )
    LIMIT 1;

    -- If no specific domain found, return default domain
    IF v_domain_id IS NULL THEN
        SELECT id INTO v_domain_id
        FROM knowledge_domains
        WHERE user_id = v_user_id AND is_default = true
        LIMIT 1;
    END IF;

    RETURN v_domain_id;
END;
$$;

GRANT EXECUTE ON FUNCTION get_deliverable_domain TO authenticated;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON FUNCTION get_user_domains_summary IS
'ADR-058: Returns domain summaries using knowledge_domains.sources JSONB column.';

COMMENT ON FUNCTION get_deliverable_domain IS
'ADR-058: Finds domain for a deliverable by matching sources overlap.';
