-- Migration 114: Rename agents.skill → agents.role (ADR-118 Resolved Decision #4)
--
-- The `skill` column on `agents` describes what an agent DOES (its behavioral role:
-- digest, monitor, synthesize, etc.). ADR-118 introduced output gateway "skills"
-- (what an agent can PRODUCE). To eliminate naming overload, the behavioral axis
-- is renamed from "skill" to "role".
--
-- This migration:
-- 1. Renames the column
-- 2. Updates the CHECK constraint
-- 3. Recreates the metrics view with new naming
-- 4. Updates the knowledge search RPC to use "role" in metadata

-- 1. Rename column
ALTER TABLE agents RENAME COLUMN skill TO role;

-- 2. Update CHECK constraint
ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_skill_check;
ALTER TABLE agents ADD CONSTRAINT agents_role_check
    CHECK (role IN ('digest', 'prepare', 'synthesize', 'monitor', 'research', 'orchestrate', 'act', 'custom'));

-- 3. Recreate metrics view with new naming
DROP VIEW IF EXISTS agent_skill_metrics;

CREATE OR REPLACE VIEW agent_role_metrics
WITH (security_invoker = true)
AS
SELECT
    a.id AS agent_id,
    a.title,
    a.scope,
    a.role,
    a.mode,
    a.status,
    COUNT(ar.id) AS total_runs,
    COUNT(CASE WHEN ar.status = 'delivered' THEN 1 END) AS delivered_runs,
    COUNT(CASE WHEN ar.status = 'failed' THEN 1 END) AS failed_runs,
    MAX(ar.created_at) AS last_run_at,
    a.created_at AS agent_created_at
FROM agents a
LEFT JOIN agent_runs ar ON ar.agent_id = a.id
GROUP BY a.id, a.title, a.scope, a.role, a.mode, a.status, a.created_at;

-- 4. Update knowledge search RPC to use "role" in metadata
-- The function stores agent metadata in workspace_files; update the key name
CREATE OR REPLACE FUNCTION search_knowledge_by_metadata(
    p_user_id UUID,
    p_query TEXT DEFAULT NULL,
    p_agent_id UUID DEFAULT NULL,
    p_role TEXT DEFAULT NULL,
    p_scope TEXT DEFAULT NULL,
    p_limit INT DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    path TEXT,
    content TEXT,
    metadata JSONB,
    tags TEXT[],
    updated_at TIMESTAMPTZ,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        wf.id,
        wf.path,
        wf.content,
        wf.metadata,
        wf.tags,
        wf.updated_at,
        CASE
            WHEN p_query IS NOT NULL AND wf.embedding IS NOT NULL
            THEN 1 - (wf.embedding <=> (
                SELECT embedding FROM workspace_files
                WHERE user_id = p_user_id AND content ILIKE '%' || p_query || '%'
                LIMIT 1
            ))
            ELSE 0.0
        END AS similarity
    FROM workspace_files wf
    WHERE wf.user_id = p_user_id
        AND wf.path LIKE '/knowledge/%'
        AND (p_agent_id IS NULL OR wf.metadata->>'agent_id' = p_agent_id::text)
        AND (p_role IS NULL OR wf.metadata->>'role' = p_role)
        AND (p_scope IS NULL OR wf.metadata->>'scope' = p_scope)
    ORDER BY
        CASE WHEN p_query IS NOT NULL THEN similarity ELSE 0 END DESC,
        wf.updated_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
