-- Migration: 047_fix_memory_rpcs.sql
-- ADR-058: Knowledge Base Architecture - Fix RPC functions
-- Date: 2026-02-13
--
-- The search_memories and get_memories_by_importance RPCs still reference
-- the dropped `memories` table. This migration updates them to use
-- `knowledge_entries` instead.

-- =============================================================================
-- DROP OLD FUNCTIONS
-- =============================================================================

DROP FUNCTION IF EXISTS search_memories(vector(1536), uuid, uuid, int, float);
DROP FUNCTION IF EXISTS get_memories_by_importance(uuid, uuid, int);

-- =============================================================================
-- RECREATE search_memories FOR knowledge_entries
-- =============================================================================

CREATE OR REPLACE FUNCTION search_memories(
    query_embedding vector(1536),
    match_user_id uuid,
    match_domain_id uuid DEFAULT NULL,
    match_count int DEFAULT 20,
    similarity_threshold float DEFAULT 0.0
)
RETURNS TABLE (
    id uuid,
    content text,
    importance float,
    tags text[],
    entities jsonb,
    source_type text,
    domain_id uuid,
    similarity float
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    default_domain_id uuid;
BEGIN
    -- Get user's default domain ID (for user profile context)
    SELECT kd.id INTO default_domain_id
    FROM knowledge_domains kd
    WHERE kd.user_id = match_user_id AND kd.is_default = true
    LIMIT 1;

    RETURN QUERY
    SELECT
        ke.id,
        ke.content,
        ke.importance::float,
        ke.tags,
        '{}'::jsonb as entities,  -- knowledge_entries doesn't have entities column
        ke.source as source_type,
        ke.domain_id,
        1 - (ke.embedding <=> query_embedding) as similarity
    FROM knowledge_entries ke
    WHERE
        ke.user_id = match_user_id
        AND ke.is_active = true
        AND ke.embedding IS NOT NULL
        AND (
            -- If no domain specified, search all
            match_domain_id IS NULL
            OR
            -- Search specified domain + default domain (user profile always accessible)
            ke.domain_id = match_domain_id
            OR ke.domain_id = default_domain_id
            OR ke.domain_id IS NULL  -- Entries without domain are globally accessible
        )
        AND (1 - (ke.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY ke.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

GRANT EXECUTE ON FUNCTION search_memories TO authenticated;

-- =============================================================================
-- RECREATE get_memories_by_importance FOR knowledge_entries
-- =============================================================================

CREATE OR REPLACE FUNCTION get_memories_by_importance(
    p_user_id uuid,
    p_domain_id uuid DEFAULT NULL,
    p_limit int DEFAULT 20
)
RETURNS TABLE (
    id uuid,
    content text,
    importance float,
    tags text[],
    entities jsonb,
    source_type text,
    domain_id uuid
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    default_domain_id uuid;
BEGIN
    -- Get user's default domain ID
    SELECT kd.id INTO default_domain_id
    FROM knowledge_domains kd
    WHERE kd.user_id = p_user_id AND kd.is_default = true
    LIMIT 1;

    RETURN QUERY
    SELECT
        ke.id,
        ke.content,
        ke.importance::float,
        ke.tags,
        '{}'::jsonb as entities,
        ke.source as source_type,
        ke.domain_id
    FROM knowledge_entries ke
    WHERE
        ke.user_id = p_user_id
        AND ke.is_active = true
        AND (
            -- If no domain specified, return all
            p_domain_id IS NULL
            OR
            -- Domain-scoped + default domain
            ke.domain_id = p_domain_id
            OR ke.domain_id = default_domain_id
            OR ke.domain_id IS NULL
        )
    ORDER BY ke.importance DESC, ke.created_at DESC
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION get_memories_by_importance TO authenticated;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON FUNCTION search_memories IS
'ADR-058: Semantic search over knowledge_entries. Domain-scoped with default domain always accessible.';

COMMENT ON FUNCTION get_memories_by_importance IS
'ADR-058: Importance-based retrieval from knowledge_entries for non-semantic fallback.';
