-- Migration 113: Security hardening
-- Fixes 7 Supabase Security Advisor errors + cleans up stale objects
--
-- Issues fixed:
-- 1. agent_skill_metrics view bypasses RLS (SECURITY DEFINER via postgres owner)
-- 2-5. mcp_oauth_* tables have no RLS (tokens exposed via PostgREST)
-- 6-7. Sensitive columns (token) exposed on mcp_oauth_access_tokens/refresh_tokens
-- 8. Stale RPC: get_last_source_fetch_time references dropped deliverable_source_runs table
-- 9. Stale columns on agents table (template_structure, is_synthesizer, domain_id, destinations, platform_variant)
-- 10. Revoke dangerous anon/authenticated grants on mcp_oauth_* tables

-- =============================================================================
-- 1. Fix agent_skill_metrics view — use security_invoker so RLS is respected
-- =============================================================================

DROP VIEW IF EXISTS agent_skill_metrics;

CREATE VIEW agent_skill_metrics
WITH (security_invoker = true)
AS
SELECT
    a.user_id,
    a.scope,
    a.skill,
    count(DISTINCT a.id) AS agent_count,
    count(ar.id) AS total_runs,
    count(ar.id) FILTER (WHERE ar.status = 'approved') AS approved_runs,
    count(ar.id) FILTER (WHERE ar.status = 'rejected') AS rejected_runs,
    avg(ar.edit_distance_score) FILTER (WHERE ar.status = 'approved') AS avg_edit_distance,
    count(ar.id) FILTER (WHERE ar.edit_distance_score < 0.3 AND ar.status = 'approved') AS low_edit_count,
    count(ar.id) FILTER (WHERE ar.edit_distance_score >= 0.3 AND ar.status = 'approved') AS high_edit_count
FROM agents a
LEFT JOIN agent_runs ar ON a.id = ar.agent_id
GROUP BY a.user_id, a.scope, a.skill;

-- Re-grant SELECT to authenticated (view is read-only)
GRANT SELECT ON agent_skill_metrics TO authenticated;
GRANT SELECT ON agent_skill_metrics TO service_role;

-- =============================================================================
-- 2-5. Enable RLS on mcp_oauth_* tables + add service-role-only policies
-- =============================================================================

-- Revoke all from anon and authenticated first (these tables are service-key only)
REVOKE ALL ON mcp_oauth_clients FROM anon, authenticated;
REVOKE ALL ON mcp_oauth_codes FROM anon, authenticated;
REVOKE ALL ON mcp_oauth_access_tokens FROM anon, authenticated;
REVOKE ALL ON mcp_oauth_refresh_tokens FROM anon, authenticated;

-- Enable RLS
ALTER TABLE mcp_oauth_clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE mcp_oauth_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE mcp_oauth_access_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE mcp_oauth_refresh_tokens ENABLE ROW LEVEL SECURITY;

-- Service role only policies
CREATE POLICY "Service role manages OAuth clients"
    ON mcp_oauth_clients FOR ALL TO service_role USING (true);

CREATE POLICY "Service role manages OAuth codes"
    ON mcp_oauth_codes FOR ALL TO service_role USING (true);

CREATE POLICY "Service role manages OAuth access tokens"
    ON mcp_oauth_access_tokens FOR ALL TO service_role USING (true);

CREATE POLICY "Service role manages OAuth refresh tokens"
    ON mcp_oauth_refresh_tokens FOR ALL TO service_role USING (true);

-- =============================================================================
-- 8. Drop stale RPC referencing deleted deliverable_source_runs table
-- =============================================================================

DROP FUNCTION IF EXISTS get_last_source_fetch_time(uuid, integer);

-- =============================================================================
-- 9. Drop stale columns on agents table
-- Confirmed: all have zero non-default data (except type_config with 1 row
-- containing {"tone": "conversational", "detail_level": "brief"} which is
-- now handled by agent_instructions / skill prompts)
-- =============================================================================

ALTER TABLE agents DROP COLUMN IF EXISTS template_structure;
ALTER TABLE agents DROP COLUMN IF EXISTS is_synthesizer;
ALTER TABLE agents DROP COLUMN IF EXISTS domain_id;
ALTER TABLE agents DROP COLUMN IF EXISTS destinations;
ALTER TABLE agents DROP COLUMN IF EXISTS platform_variant;

-- type_config: 1 agent has data but it's superseded by skill prompts (ADR-104).
-- The unified_scheduler still selects it, so we'll keep it for now and clean up
-- in a follow-up migration after removing scheduler references.
-- ALTER TABLE agents DROP COLUMN IF EXISTS type_config;
-- Note: type_config cleanup deferred — unified_scheduler.py still selects it.
