-- 246: search covers the NAME, and an all-words miss DEGRADES instead of concluding.
--
-- Receipted live (2026-08-22, workspace d5b9029b): `search("downturn companies
-- deck")` returned confidence "none" — the tool's own strongest "nothing here"
-- signal — over a deck whose <title> is "Build in the Downturn", sitting beside
-- a CSV literally named downturn-companies.csv. The calling model believed it
-- and told the operator the material didn't exist. Two mechanisms, both here:
--
--   1. The tsvector covered CONTENT ONLY. A file's name/path never participated,
--      so downturn-companies.csv could not match its own name — and the only
--      "deck" in deck.html sits inside an HTML tag (`data-template="deck"`),
--      which ts_parse drops wholesale (tag tokens are not indexed). Measured:
--      all three files matched 'downturn' and 'compani', none matched 'deck'.
--
--   2. plainto_tsquery AND-matches every lexeme, so ONE absent word zeroed the
--      whole result — and a zero was reported as a true miss ("none"), though
--      two of three query words matched three files. A search that confidently
--      says nothing exists gets believed; a loud failure gets retried.
--
-- The recut:
--   - tsvector = path tokens (weight A) || summary (B) || content (C) — the
--     name is the strongest signal a caller who KNOWS the file gives us.
--   - strict (all words) first; when strict yields ZERO rows the same call
--     answers with the any-word pass, each row labelled match_mode='loose'.
--     The label is the honesty carrier: Python grades loose results as WEAK,
--     never "high", never "none". No second round trip.
--   - workspace / prefix / powerbox / lifecycle filters byte-identical to 218.
--
-- Return type gains match_mode, so this is DROP + CREATE (CREATE OR REPLACE
-- cannot change a return type). Single transaction; PostgREST told to reload.

DROP FUNCTION IF EXISTS public.search_workspace(uuid, text, text, integer, text[]);

CREATE FUNCTION public.search_workspace(
    p_workspace_id uuid,
    p_query text,
    p_path_prefix text DEFAULT NULL::text,
    p_limit integer DEFAULT 20,
    p_allowed_prefixes text[] DEFAULT NULL::text[]
)
RETURNS TABLE(
    id uuid, path text, summary text, content text,
    rank real, updated_at timestamp with time zone,
    match_mode text
)
LANGUAGE sql
STABLE
AS $function$
    WITH scoped AS (
        SELECT
            wf.id, wf.path, wf.summary, wf.content, wf.updated_at,
            -- The name is a search target: '/', '-', '_' and '.' become word
            -- boundaries so `downturn-companies.csv` yields downturn/companies/csv.
            setweight(to_tsvector('english', translate(coalesce(wf.path, ''), '/-_.', '    ')), 'A')
              || setweight(to_tsvector('english', coalesce(wf.summary, '')), 'B')
              || setweight(to_tsvector('english', coalesce(wf.content, '')), 'C') AS tsv
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
    ),
    strict AS (
        SELECT s.id, s.path, s.summary, s.content,
               ts_rank(s.tsv, plainto_tsquery('english', p_query)) AS rank,
               s.updated_at, 'strict'::text AS match_mode
        FROM scoped s
        WHERE s.tsv @@ plainto_tsquery('english', p_query)
    ),
    loose AS (
        -- Same lexemes, OR-joined. plainto output is sanitized quoted lexemes
        -- separated by ' & ' — english lexemes cannot contain the separator,
        -- so the textual rewrite is exact.
        SELECT s.id, s.path, s.summary, s.content,
               ts_rank(s.tsv, replace(plainto_tsquery('english', p_query)::text, ' & ', ' | ')::tsquery) AS rank,
               s.updated_at, 'loose'::text AS match_mode
        FROM scoped s
        WHERE plainto_tsquery('english', p_query)::text <> ''
          AND s.tsv @@ replace(plainto_tsquery('english', p_query)::text, ' & ', ' | ')::tsquery
    )
    SELECT * FROM (
        SELECT * FROM strict
        UNION ALL
        SELECT * FROM loose
        WHERE NOT EXISTS (SELECT 1 FROM strict)
    ) matched
    ORDER BY rank DESC
    LIMIT p_limit;
$function$;

-- PostgREST serves both RPC callers (QueryKnowledge + SearchFiles); a stale
-- schema cache would 404 the new signature (PGRST205).
NOTIFY pgrst, 'reload schema';

-- Verify: the live function carries the name-in-tsvector and the degrade.
DO $$
DECLARE
    src text;
BEGIN
    SELECT prosrc INTO src FROM pg_proc
    WHERE proname = 'search_workspace'
      AND pronamespace = 'public'::regnamespace;
    IF src IS NULL THEN
        RAISE EXCEPTION 'search_workspace missing after recreate';
    END IF;
    IF src NOT LIKE '%translate(coalesce(wf.path%' THEN
        RAISE EXCEPTION 'search_workspace does not index the path';
    END IF;
    IF src NOT LIKE '%loose%' THEN
        RAISE EXCEPTION 'search_workspace lost the degrade pass';
    END IF;
    IF src NOT LIKE '%lifecycle%' THEN
        RAISE EXCEPTION 'search_workspace lost the trash filter (218 regression)';
    END IF;
END $$;
