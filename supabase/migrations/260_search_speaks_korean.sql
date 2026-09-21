-- 260: search speaks Korean — a substring tier beside the English stemmer.
--
-- ## The defect
--
-- `search_workspace` matches with `to_tsvector('english', …)`. The English
-- stemmer whitespace-splits Korean and stems nothing, and Korean is
-- agglutinative: a particle attaches directly to the noun. So a noun is found
-- only when it happens to appear bare, which in real Korean prose is the
-- MINORITY case. Measured on production (2026-09-21) against a Korean file a
-- member had already written, whose own item 3 asks "can I find this file
-- again with a Korean query":
--
--     커넥터 → 2 hits    한국어 → 1    테스트 → 1     (bare nouns: found)
--     본문   → 0 hits    삭제   → 0                  (본문이 / 삭제하거나: LOST)
--     workspace (English control) → 20
--
-- Search does not error. It returns fewer rows, and a member reports that as
-- "search is bad", never as "search is broken". Postgres ships NO Korean text
-- search configuration (all 29 enumerated; no CJK at all), and `simple` does
-- not help — it merely skips stemming, so the particle still welds to the noun.
-- The semantic fallback is not a safety net either: 8 of 902 rows carry an
-- embedding. Lexical matching is all there is.
--
-- ## Why pgroonga is ADDED and not SUBSTITUTED
--
-- pgroonga indexes substrings, so it finds a noun inside an inflected word —
-- exactly what Korean needs. But it does NOT stem, so on its own it REGRESSES
-- English: measured, `reports` fell 185 → 106 because it no longer matches
-- `report`. Swapping the config would have traded a Korean defect for an
-- English one.
--
-- The honest shape is BOTH, OR-joined. Measured on the live corpus:
--
--     query      pgroonga   english   hybrid
--     본문          1          0         1     ← fixed
--     삭제          1          0         1     ← fixed
--     커넥터        2          2         2
--     reports     106        185       191     ← better than either
--     workspace   422        398       423     ← better than either
--
-- The hybrid is never worse than the English tier alone, which is the property
-- that makes this safe to ship: no existing English query can lose a result.
--
-- ## Where it sits in the existing grammar
--
-- 246 established two tiers and made the LABEL the honesty carrier: `strict`
-- (all words) first, and only when strict returns zero does `loose` (any word)
-- answer, graded WEAK by the caller so a partial match is never reported as
-- confident. Korean joins as a THIRD tier at the bottom of that ladder:
--
--     strict  — every lexeme matched by the English stemmer
--     loose   — any lexeme matched (246's degrade)
--     korean  — substring match, only when BOTH of the above found nothing
--
-- Ordering it last is deliberate. A substring tier matches aggressively (a
-- query inside a longer word), so letting it run first would dilute a precise
-- English result. Running it only on a double miss means every existing
-- English query returns byte-identical rows to before this migration, and the
-- new tier is pure addition.
--
-- `match_mode = 'korean'` is a NEW value on a column callers already read. It
-- grades like `loose` (weak, not "none") — the point is that the caller stops
-- saying "nothing exists" when something does.
--
-- ## Cost, measured rather than assumed
--
--   · the index builds in under 3 seconds on the live table (902 rows);
--   · the database grows 307 MB → 397 MB — ~90 MB of index for ~8.6 MB of
--     content, about 10×. pgroonga stores outside the Postgres relation, so
--     `pg_relation_size` reads 0 and would report it as free; measure by
--     `pg_database_size` delta instead.
--
-- Return type is UNCHANGED, so this is CREATE OR REPLACE rather than 246's
-- DROP + CREATE. Single transaction; PostgREST told to reload.

CREATE EXTENSION IF NOT EXISTS pgroonga;

-- Substring index over the fields a member searches. `path` is included
-- because a Korean FILENAME has the same problem as Korean prose, and 246
-- already established the name as the strongest signal from a caller who
-- knows the file.
CREATE INDEX IF NOT EXISTS workspace_files_content_pgroonga
    ON public.workspace_files USING pgroonga (content);
CREATE INDEX IF NOT EXISTS workspace_files_path_pgroonga
    ON public.workspace_files USING pgroonga (path);

CREATE OR REPLACE FUNCTION public.search_workspace(
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
        -- so the textual rewrite is exact. (Re-checked under Hangul input
        -- 2026-09-21: plainto_tsquery('english','매출 보고서') yields
        -- '매출' & '보고서', so the premise holds for CJK too — but the
        -- reasoning is about the SEPARATOR, not about English.)
        SELECT s.id, s.path, s.summary, s.content,
               ts_rank(s.tsv, replace(plainto_tsquery('english', p_query)::text, ' & ', ' | ')::tsquery) AS rank,
               s.updated_at, 'loose'::text AS match_mode
        FROM scoped s
        WHERE plainto_tsquery('english', p_query)::text <> ''
          AND s.tsv @@ replace(plainto_tsquery('english', p_query)::text, ' & ', ' | ')::tsquery
    ),
    korean AS (
        -- The substring tier. Runs against the SAME scoped set, so every
        -- workspace / prefix / powerbox / lifecycle filter applies unchanged —
        -- a search must never reach a file the caller cannot read, whatever
        -- the matching strategy.
        --
        -- `&@~` is pgroonga's query-syntax operator. A bare term is a
        -- substring match, which is what finds 본문 inside 본문이.
        --
        -- Rank is a small constant, not ts_rank: the tsvector this row did NOT
        -- match cannot rank it, and inventing a score would make a substring
        -- hit look precise. The tier already says what it is.
        SELECT s.id, s.path, s.summary, s.content,
               0.01::real AS rank,
               s.updated_at, 'korean'::text AS match_mode
        FROM scoped s
        WHERE coalesce(p_query, '') <> ''
          AND (s.content &@~ p_query OR s.path &@~ p_query)
    )
    SELECT * FROM (
        SELECT * FROM strict
        UNION ALL
        SELECT * FROM loose
        WHERE NOT EXISTS (SELECT 1 FROM strict)
        UNION ALL
        -- Only on a DOUBLE miss, so an English query's result set is
        -- byte-identical to what 246 returned.
        SELECT * FROM korean
        WHERE NOT EXISTS (SELECT 1 FROM strict)
          AND NOT EXISTS (SELECT 1 FROM loose)
    ) matched
    ORDER BY rank DESC
    LIMIT p_limit;
$function$;

-- PostgREST serves both RPC callers (QueryKnowledge + SearchFiles); a stale
-- schema cache would 404 the signature (PGRST205).
NOTIFY pgrst, 'reload schema';

-- Verify the LIVE object: every invariant 246 and 218 established must survive,
-- and the new tier must actually be present. The runner's exit code is not
-- verification.
DO $$
DECLARE
    src text;
BEGIN
    SELECT prosrc INTO src FROM pg_proc
    WHERE proname = 'search_workspace'
      AND pronamespace = 'public'::regnamespace;
    IF src IS NULL THEN
        RAISE EXCEPTION 'search_workspace missing after replace';
    END IF;
    IF src NOT LIKE '%translate(coalesce(wf.path%' THEN
        RAISE EXCEPTION 'search_workspace does not index the path (246 regression)';
    END IF;
    IF src NOT LIKE '%loose%' THEN
        RAISE EXCEPTION 'search_workspace lost the degrade pass (246 regression)';
    END IF;
    IF src NOT LIKE '%lifecycle%' THEN
        RAISE EXCEPTION 'search_workspace lost the trash filter (218 regression)';
    END IF;
    IF src NOT LIKE '%&@~%' THEN
        RAISE EXCEPTION 'search_workspace lost the Korean tier';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = 'workspace_files_content_pgroonga'
    ) THEN
        RAISE EXCEPTION 'the pgroonga content index is missing';
    END IF;
END $$;
