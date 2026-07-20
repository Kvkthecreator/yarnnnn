-- Migration 218 — search does not return trashed files
--
-- Surfaced by the file-lifecycle audit (2026-07-20). Delete is trash-not-erase:
-- it writes a new attributed revision with lifecycle='archived' and the row
-- leaves the Files tree (routes/workspace.py:587 filters it). But the two
-- search RPCs carried NO lifecycle predicate, so a trashed file stayed
-- searchable — and every agent search path goes through these functions
-- (SearchFiles, QueryKnowledge, mcp recall). A member who trashed a file kept
-- getting its content back in reasoning.
--
-- The gap is HERE, in SQL, not in the callers: a Python-side filter cannot
-- reach inside the RPC. Fixing it at the source is also what makes it
-- unbypassable — a new caller inherits the behaviour.
--
-- POLARITY: `lifecycle IS NULL OR lifecycle <> 'archived'`, mirroring the Files
-- tree. `<> 'archived'` alone would DROP rows whose lifecycle is NULL (rows
-- written before the column had a default) — a silent, much worse regression
-- than the one being fixed.
--
-- Both bodies below are the LIVE definitions replayed verbatim (read via
-- pg_get_functiondef) with exactly one predicate added. The signatures already
-- carry ADR-373's p_workspace_id and the powerbox p_allowed_prefixes; migration
-- 100's original p_user_id form is long superseded and is NOT what runs.
--
-- NOT changed: archived rows stay READABLE by exact path — Trash lists them and
-- Restore reads them. This is a presentation rule, not an authorization one
-- (which is why it is not RLS).

-- =============================================================================
-- 1. Full-text search
-- =============================================================================

CREATE OR REPLACE FUNCTION public.search_workspace(
    p_workspace_id uuid,
    p_query text,
    p_path_prefix text DEFAULT NULL::text,
    p_limit integer DEFAULT 20,
    p_allowed_prefixes text[] DEFAULT NULL::text[]
)
RETURNS TABLE(
    id uuid, path text, summary text, content text,
    rank real, updated_at timestamp with time zone
)
LANGUAGE sql
STABLE
AS $function$
    SELECT
        wf.id, wf.path, wf.summary, wf.content,
        ts_rank(to_tsvector('english', wf.content), plainto_tsquery('english', p_query)) AS rank,
        wf.updated_at
    FROM workspace_files wf
    WHERE wf.workspace_id = p_workspace_id
      AND (p_path_prefix IS NULL OR wf.path LIKE p_path_prefix || '%')
      -- Powerbox read scope: NULL → unscoped; else the path must be under ANY
      -- allowed prefix. An empty array matches nothing (deny-all).
      AND (
        p_allowed_prefixes IS NULL
        OR EXISTS (
          SELECT 1 FROM unnest(p_allowed_prefixes) AS pref
          WHERE wf.path LIKE pref || '%'
        )
      )
      -- Trashed files are not searchable (migration 218). NULL-tolerant.
      AND (wf.lifecycle IS NULL OR wf.lifecycle <> 'archived')
      AND to_tsvector('english', wf.content) @@ plainto_tsquery('english', p_query)
    ORDER BY rank DESC
    LIMIT p_limit;
$function$;

-- =============================================================================
-- 2. Semantic (vector) search
-- =============================================================================

CREATE OR REPLACE FUNCTION public.search_workspace_semantic(
    p_workspace_id uuid,
    p_query_embedding vector,
    p_path_prefix text DEFAULT NULL::text,
    p_limit integer DEFAULT 20,
    p_allowed_prefixes text[] DEFAULT NULL::text[]
)
RETURNS TABLE(
    id uuid, path text, summary text, content text,
    similarity real, updated_at timestamp with time zone
)
LANGUAGE sql
STABLE
AS $function$
    SELECT
        wf.id, wf.path, wf.summary, wf.content,
        (1 - (wf.embedding <=> p_query_embedding))::REAL AS similarity,
        wf.updated_at
    FROM workspace_files wf
    WHERE wf.workspace_id = p_workspace_id
      AND wf.embedding IS NOT NULL
      AND (p_path_prefix IS NULL OR wf.path LIKE p_path_prefix || '%')
      AND (
        p_allowed_prefixes IS NULL
        OR EXISTS (
          SELECT 1 FROM unnest(p_allowed_prefixes) AS pref
          WHERE wf.path LIKE pref || '%'
        )
      )
      -- Trashed files are not searchable (migration 218). NULL-tolerant.
      AND (wf.lifecycle IS NULL OR wf.lifecycle <> 'archived')
    ORDER BY wf.embedding <=> p_query_embedding
    LIMIT p_limit;
$function$;

-- Verify:
--   SELECT prosrc LIKE '%archived%' FROM pg_proc
--   WHERE proname IN ('search_workspace','search_workspace_semantic');
--   -- expect: t, t
