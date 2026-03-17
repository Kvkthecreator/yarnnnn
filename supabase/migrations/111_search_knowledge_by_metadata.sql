-- ADR-116 Phase 1: Knowledge Metadata Search
-- Enables QueryKnowledge to filter by producing agent, skill, scope
-- workspace_files.metadata JSONB already contains agent_id, skill, scope, content_class
-- written by agent_execution.py at delivery time (ADR-107)

CREATE OR REPLACE FUNCTION search_knowledge_by_metadata(
    p_user_id UUID,
    p_content_class TEXT DEFAULT NULL,
    p_agent_id TEXT DEFAULT NULL,
    p_skill TEXT DEFAULT NULL,
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
      -- Skill filter: matches metadata.skill
      AND (p_skill IS NULL OR wf.metadata->>'skill' = p_skill)
      -- Text search: optional full-text filter
      AND (p_query IS NULL OR to_tsvector('english', wf.content) @@ plainto_tsquery('english', p_query))
    ORDER BY wf.updated_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute to authenticated users and service role
GRANT EXECUTE ON FUNCTION search_knowledge_by_metadata TO authenticated;
GRANT EXECUTE ON FUNCTION search_knowledge_by_metadata TO service_role;

-- Note: No GIN index on metadata->>'agent_id' yet — workspace_files is small per user.
-- ADR-116 Open Question 3: add index if query performance degrades at scale.
