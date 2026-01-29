-- Migration: 007_search_memories_rpc.sql
-- ADR-005: Semantic search function for memories
-- Date: 2026-01-29
--
-- Creates an RPC function for hybrid semantic search:
-- - Vector similarity (cosine distance)
-- - Importance weighting
-- - Scope filtering (user + optional project)

-- =============================================================================
-- SEARCH MEMORIES FUNCTION
-- =============================================================================

CREATE OR REPLACE FUNCTION search_memories(
    query_embedding vector(1536),
    match_user_id uuid,
    match_project_id uuid DEFAULT NULL,
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
    project_id uuid,
    created_at timestamptz,
    similarity float,
    relevance float
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.content,
        m.tags,
        m.entities,
        m.importance::float,
        m.source_type,
        m.project_id,
        m.created_at,
        (1 - (m.embedding <=> query_embedding))::float AS similarity,
        -- Hybrid score: 70% similarity + 30% importance
        ((1 - (m.embedding <=> query_embedding)) * 0.7 + m.importance * 0.3)::float AS relevance
    FROM memories m
    WHERE
        m.user_id = match_user_id
        AND m.is_active = true
        AND m.embedding IS NOT NULL
        -- Scope filter: user-scoped OR matching project
        AND (
            m.project_id IS NULL
            OR m.project_id = match_project_id
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
-- MATCH CHUNKS FUNCTION (for document retrieval)
-- =============================================================================

CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(1536),
    match_document_id uuid,
    match_count int DEFAULT 5,
    similarity_threshold float DEFAULT 0.5
)
RETURNS TABLE (
    id uuid,
    content text,
    chunk_index int,
    page_number int,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.content,
        c.chunk_index,
        c.page_number,
        c.metadata,
        (1 - (c.embedding <=> query_embedding))::float AS similarity
    FROM chunks c
    WHERE
        c.document_id = match_document_id
        AND c.embedding IS NOT NULL
        AND (1 - (c.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION match_chunks TO authenticated;
