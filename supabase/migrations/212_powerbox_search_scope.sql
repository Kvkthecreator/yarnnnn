-- 212_powerbox_search_scope.sql
-- THE POWERBOX (2026-07-10) — push read-scoping INTO the search RPCs.
--
-- Half A filtered search results in Python, AFTER the RPC applied its LIMIT. At
-- scale that is a correctness bug, not just a perf cost: a narrowed principal
-- could get a SHORT or EMPTY page because the DB limited to 20 rows BEFORE the
-- app dropped the out-of-scope ones — in-scope matches past the limit vanish.
--
-- Fix: both search RPCs gain an optional `p_allowed_prefixes text[]`. When
-- non-NULL, a row is included iff its path is under ANY allowed prefix (an
-- absolute `/workspace/...` form the caller passes). The LIMIT then applies to
-- IN-SCOPE rows only — the page is full and correct for a narrowed principal.
--
-- POLARITY: the caller passes
--   NULL  → no read scoping (owner / NULL read axis) — byte-identical to before.
--   {}    → deny-all (empty array) → NO row matches → empty result.
--   {..}  → allow-list of absolute path prefixes (arbitrary depth).
--
-- SINGULAR IMPLEMENTATION: we DROP the prior 4-arg overloads first. Adding the
-- 5th param via CREATE OR REPLACE would leave TWO functions of the same name;
-- a 4-arg call (every live caller) then errors "function is not unique". So the
-- old signatures are dropped and the 5-arg form (new param DEFAULT NULL) is the
-- single definition — a 4-arg call binds to it with p_allowed_prefixes := NULL
-- = unscoped = byte-identical.
DROP FUNCTION IF EXISTS public.search_workspace(uuid, text, text, integer);
DROP FUNCTION IF EXISTS public.search_workspace_semantic(uuid, vector, text, integer);

-- -----------------------------------------------------------------------------
-- search_workspace (BM25) + read-scope
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.search_workspace(
    p_workspace_id uuid,
    p_query text,
    p_path_prefix text DEFAULT NULL::text,
    p_limit integer DEFAULT 20,
    p_allowed_prefixes text[] DEFAULT NULL::text[]
)
RETURNS TABLE(id uuid, path text, summary text, content text, rank real, updated_at timestamptz)
LANGUAGE sql STABLE
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
      AND to_tsvector('english', wf.content) @@ plainto_tsquery('english', p_query)
    ORDER BY rank DESC
    LIMIT p_limit;
$function$;

-- -----------------------------------------------------------------------------
-- search_workspace_semantic (vector) + read-scope
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.search_workspace_semantic(
    p_workspace_id uuid,
    p_query_embedding vector,
    p_path_prefix text DEFAULT NULL::text,
    p_limit integer DEFAULT 20,
    p_allowed_prefixes text[] DEFAULT NULL::text[]
)
RETURNS TABLE(id uuid, path text, summary text, content text, similarity real, updated_at timestamptz)
LANGUAGE sql STABLE
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
    ORDER BY wf.embedding <=> p_query_embedding
    LIMIT p_limit;
$function$;

-- =============================================================================
-- Verification (manual):
--   -- Unscoped call is byte-identical (p_allowed_prefixes defaults NULL):
--   SELECT count(*) FROM search_workspace('<ws>', 'test');
--   -- Scoped to operation/ only:
--   SELECT count(*) FROM search_workspace('<ws>', 'test', NULL, 20,
--       ARRAY['/workspace/operation/']);
--   -- Deny-all:
--   SELECT count(*) FROM search_workspace('<ws>', 'test', NULL, 20, ARRAY[]::text[]);
--   -- Expect: 0.
-- =============================================================================
