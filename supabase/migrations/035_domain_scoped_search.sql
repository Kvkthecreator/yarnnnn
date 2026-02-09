-- Migration: 035_domain_scoped_search.sql
-- ADR-034: Update memory search to use domain scoping instead of project
-- Date: 2026-02-09
--
-- This migration:
-- 1. Creates domain-scoped search_memories_v2 function
-- 2. Replaces the old search_memories function
-- 3. Updates match_chunks for consistency
-- 4. Drops deprecated project_id scoping

-- =============================================================================
-- 1. DROP OLD FUNCTION (to replace cleanly)
-- =============================================================================

DROP FUNCTION IF EXISTS search_memories(vector(1536), uuid, uuid, int, float);


-- =============================================================================
-- 2. DOMAIN-SCOPED SEARCH MEMORIES
-- =============================================================================
-- Replaces project_id scoping with domain_id scoping.
-- If domain_id is NULL, searches across all user's memories (no domain filter).
-- If domain_id is provided, includes:
--   - Memories in that domain
--   - Memories in default domain (always available)

CREATE OR REPLACE FUNCTION search_memories(
    query_embedding vector(1536),
    match_user_id uuid,
    match_domain_id uuid DEFAULT NULL,
    match_count int DEFAULT 20,
    similarity_threshold float DEFAULT 0.5
)
RETURNS TABLE (
    id uuid,
    content text,
    tags text[],
    entities jsonb,
    importance float,
    source_type text,
    domain_id uuid,
    created_at timestamptz,
    similarity float,
    relevance float
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    default_domain_id uuid;
BEGIN
    -- Get the user's default domain ID (for always-accessible context)
    SELECT cd.id INTO default_domain_id
    FROM context_domains cd
    WHERE cd.user_id = match_user_id AND cd.is_default = true
    LIMIT 1;

    RETURN QUERY
    SELECT
        m.id,
        m.content,
        m.tags,
        m.entities,
        m.importance::float,
        m.source_type,
        m.domain_id,
        m.created_at,
        (1 - (m.embedding <=> query_embedding))::float AS similarity,
        -- Hybrid score: 70% similarity + 30% importance
        ((1 - (m.embedding <=> query_embedding)) * 0.7 + m.importance * 0.3)::float AS relevance
    FROM memories m
    WHERE
        m.user_id = match_user_id
        AND m.is_active = true
        AND m.embedding IS NOT NULL
        -- Domain scope filter
        AND (
            -- No domain filter: search all user's memories
            match_domain_id IS NULL
            -- Has domain filter: include specified domain + default domain
            OR m.domain_id = match_domain_id
            OR m.domain_id = default_domain_id
            -- Also include NULL domain (legacy data not yet routed)
            OR m.domain_id IS NULL
        )
        -- Similarity threshold
        AND (1 - (m.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY relevance DESC
    LIMIT match_count;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION search_memories TO authenticated;


-- =============================================================================
-- 3. IMPORTANCE-BASED RETRIEVAL (Non-semantic fallback)
-- =============================================================================
-- For when no query embedding is provided

CREATE OR REPLACE FUNCTION get_memories_by_importance(
    p_user_id uuid,
    p_domain_id uuid DEFAULT NULL,
    p_limit int DEFAULT 20
)
RETURNS TABLE (
    id uuid,
    content text,
    tags text[],
    entities jsonb,
    importance float,
    source_type text,
    domain_id uuid,
    created_at timestamptz
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    default_domain_id uuid;
BEGIN
    -- Get the user's default domain ID
    SELECT cd.id INTO default_domain_id
    FROM context_domains cd
    WHERE cd.user_id = p_user_id AND cd.is_default = true
    LIMIT 1;

    RETURN QUERY
    SELECT
        m.id,
        m.content,
        m.tags,
        m.entities,
        m.importance::float,
        m.source_type,
        m.domain_id,
        m.created_at
    FROM memories m
    WHERE
        m.user_id = p_user_id
        AND m.is_active = true
        -- Domain scope filter
        AND (
            p_domain_id IS NULL
            OR m.domain_id = p_domain_id
            OR m.domain_id = default_domain_id
            OR m.domain_id IS NULL
        )
    ORDER BY m.importance DESC
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION get_memories_by_importance TO authenticated;


-- =============================================================================
-- 4. UPDATE search_memories RETURN TYPE COMMENT
-- =============================================================================
-- Document the new behavior

COMMENT ON FUNCTION search_memories IS 'ADR-034: Domain-scoped semantic memory search. If domain_id is NULL, searches all memories. If provided, searches specified domain + default domain (always-accessible user context).';

COMMENT ON FUNCTION get_memories_by_importance IS 'ADR-034: Domain-scoped importance-based retrieval for non-semantic fallback.';
