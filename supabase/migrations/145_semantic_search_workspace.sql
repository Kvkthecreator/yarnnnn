-- Migration 145: Semantic search for workspace context files (ADR-174 Phase 2)
--
-- Adds search_workspace_semantic() RPC for cosine similarity search over
-- workspace_files embeddings. Used by QueryKnowledge as the primary search
-- path, with BM25 (search_workspace) as fallback.
--
-- Prerequisites: embedding vector(1536) column and ivfflat index already exist
-- on workspace_files from migration 100_workspace_files.sql.

CREATE OR REPLACE FUNCTION search_workspace_semantic(
    p_user_id UUID,
    p_query_embedding vector(1536),
    p_path_prefix TEXT DEFAULT NULL,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    path TEXT,
    summary TEXT,
    content TEXT,
    similarity REAL,
    updated_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT
        wf.id,
        wf.path,
        wf.summary,
        wf.content,
        (1 - (wf.embedding <=> p_query_embedding))::REAL AS similarity,
        wf.updated_at
    FROM workspace_files wf
    WHERE wf.user_id = p_user_id
      AND wf.embedding IS NOT NULL
      AND (p_path_prefix IS NULL OR wf.path LIKE p_path_prefix || '%')
    ORDER BY wf.embedding <=> p_query_embedding
    LIMIT p_limit;
$$;

COMMENT ON FUNCTION search_workspace_semantic IS
'Semantic similarity search over workspace_files using pgvector cosine distance.
Scoped to files with non-null embeddings. Used by QueryKnowledge (ADR-174 Phase 2)
as the primary search path for /workspace/context/ files. BM25 (search_workspace)
is the fallback when embedding API is unavailable or returns no results.';
