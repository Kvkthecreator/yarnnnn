-- Migration 115: Fix search_knowledge_by_metadata RPC after skill→role rename
--
-- Migration 114 created a SECOND overload (p_agent_id UUID) instead of replacing
-- the original (p_agent_id TEXT) because CREATE OR REPLACE cannot change param types.
-- Result: two functions with same name, PostgREST ambiguity risk.
--
-- Also:
-- - Migration 114 dropped p_content_class (code still passes it)
-- - Migration 114 dropped `summary` from return (code still reads it)
-- - Old function still filters on metadata->>'skill' (should be 'role')
--
-- This migration:
-- 1. Drops BOTH overloads
-- 2. Creates single correct function matching code expectations
-- 3. Removes 'orchestrate' from agents.role CHECK constraint (removed from code)

-- 1. Drop both overloads of search_knowledge_by_metadata
DROP FUNCTION IF EXISTS search_knowledge_by_metadata(uuid, text, text, text, text, integer);
DROP FUNCTION IF EXISTS search_knowledge_by_metadata(uuid, text, uuid, text, text, integer);

-- 2. Create single correct function
-- Matches workspace.py search_by_metadata() caller:
--   p_user_id, p_content_class, p_agent_id (text), p_role, p_query, p_limit
-- Returns: id, path, summary, content, metadata, tags, updated_at
CREATE OR REPLACE FUNCTION search_knowledge_by_metadata(
    p_user_id UUID,
    p_content_class TEXT DEFAULT NULL,
    p_agent_id TEXT DEFAULT NULL,
    p_role TEXT DEFAULT NULL,
    p_query TEXT DEFAULT NULL,
    p_limit INT DEFAULT 10
) RETURNS TABLE (
    id UUID,
    path TEXT,
    summary TEXT,
    content TEXT,
    metadata JSONB,
    tags TEXT[],
    updated_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        wf.id,
        wf.path,
        wf.summary,
        wf.content,
        wf.metadata,
        wf.tags,
        wf.updated_at
    FROM workspace_files wf
    WHERE wf.user_id = p_user_id
      AND wf.path LIKE '/knowledge/%'
      -- Content class filter: matches directory (e.g., /knowledge/digests/%)
      AND (p_content_class IS NULL OR wf.path LIKE '/knowledge/' || p_content_class || '/%')
      -- Agent ID filter: matches metadata.agent_id
      AND (p_agent_id IS NULL OR wf.metadata->>'agent_id' = p_agent_id)
      -- Role filter: matches metadata.role (renamed from skill in migration 114)
      AND (p_role IS NULL OR wf.metadata->>'role' = p_role)
      -- Text search: optional full-text filter
      AND (p_query IS NULL OR to_tsvector('english', wf.content) @@ plainto_tsquery('english', p_query))
    ORDER BY wf.updated_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION search_knowledge_by_metadata TO authenticated;
GRANT EXECUTE ON FUNCTION search_knowledge_by_metadata TO service_role;

-- 3. Update CHECK constraint: remove 'orchestrate' (removed from code in b6aadf6)
ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_role_check;
ALTER TABLE agents ADD CONSTRAINT agents_role_check
    CHECK (role IN ('digest', 'prepare', 'synthesize', 'monitor', 'research', 'act', 'custom'));
