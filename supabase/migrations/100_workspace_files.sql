-- Migration 100: Agent Workspace Architecture (ADR-106)
--
-- Virtual filesystem over Postgres for agent workspaces.
-- Agents interact via path-based operations through a storage-agnostic abstraction.
--
-- Path conventions:
--   /workspace.md                              — global user context
--   /preferences.md                            — learned preferences
--   /knowledge/slack/{channel}/{date}.md       — perception pipeline output
--   /agents/{slug}/AGENT.md                    — identity + instructions (like CLAUDE.md)
--   /agents/{slug}/thesis.md                   — self-evolving domain understanding
--   /agents/{slug}/memory/observations.md      — accumulated observations
--   /agents/{slug}/memory/preferences.md       — learned from edit history
--   /agents/{slug}/memory/{topic}.md           — topic-scoped memory
--   /agents/{slug}/runs/v{N}.md                — output per run
--   /agents/{slug}/working/{topic}.md          — intermediate research

-- =============================================================================
-- 1. workspace_files table
-- =============================================================================

CREATE TABLE workspace_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    summary TEXT,
    content_type TEXT NOT NULL DEFAULT 'text/markdown',
    metadata JSONB NOT NULL DEFAULT '{}',
    tags TEXT[] NOT NULL DEFAULT '{}',
    embedding vector(1536),
    size_bytes INTEGER GENERATED ALWAYS AS (octet_length(content)) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(user_id, path)
);

-- Path-based access (exact + prefix)
CREATE INDEX idx_ws_path ON workspace_files(user_id, path);
CREATE INDEX idx_ws_path_prefix ON workspace_files(user_id, path text_pattern_ops);

-- Semantic search
CREATE INDEX idx_ws_embedding ON workspace_files
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
    WHERE embedding IS NOT NULL;

-- Full-text search
CREATE INDEX idx_ws_fts ON workspace_files
    USING gin (to_tsvector('english', content));

-- Tag-based discovery
CREATE INDEX idx_ws_tags ON workspace_files USING gin (tags);

-- Recent changes
CREATE INDEX idx_ws_updated ON workspace_files(user_id, updated_at DESC);

-- Agent-scoped listing (common query pattern)
CREATE INDEX idx_ws_agent_files ON workspace_files(user_id, path text_pattern_ops)
    WHERE path LIKE '/agents/%';

-- Auto-update updated_at
CREATE TRIGGER workspace_files_updated_at
    BEFORE UPDATE ON workspace_files
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- 2. RLS policies
-- =============================================================================

ALTER TABLE workspace_files ENABLE ROW LEVEL SECURITY;

-- Users can read their own workspace files
CREATE POLICY "Users can view own workspace files" ON workspace_files
    FOR SELECT USING (user_id = auth.uid());

-- Service role manages workspace files (agents write via service key)
CREATE POLICY "Service role manages workspace files" ON workspace_files
    TO service_role USING (true);

-- =============================================================================
-- 3. Helper RPC: full-text search within workspace
-- =============================================================================

CREATE OR REPLACE FUNCTION search_workspace(
    p_user_id UUID,
    p_query TEXT,
    p_path_prefix TEXT DEFAULT NULL,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    path TEXT,
    summary TEXT,
    content TEXT,
    rank REAL,
    updated_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT
        wf.id,
        wf.path,
        wf.summary,
        wf.content,
        ts_rank(to_tsvector('english', wf.content), plainto_tsquery('english', p_query)) AS rank,
        wf.updated_at
    FROM workspace_files wf
    WHERE wf.user_id = p_user_id
      AND (p_path_prefix IS NULL OR wf.path LIKE p_path_prefix || '%')
      AND to_tsvector('english', wf.content) @@ plainto_tsquery('english', p_query)
    ORDER BY rank DESC
    LIMIT p_limit;
$$;
