-- 244 — ADR-580: the connector derive step's ledger groundwork.
--
-- (1) platform_connections.connected_by — the connecting principal, the
--     attribution record derived material rides "on behalf of"
--     (intake-pipeline.md §3). Named by ADR-407 D5, deferred by ADR-425 AD5,
--     extended to grants by ADR-431 — never built on THIS table until now
--     (principal_grants.connected_by already exists; this is its
--     platform_connections sibling). Backfill = user_id: every live
--     connection was made by its owning principal (measured 2026-08-18:
--     3 rows, one owner). NOT NULL after backfill so a connect door that
--     forgets the stamp fails loudly instead of writing silent
--     unattributable reach.
--
-- (2) Relabel the 48 historical slack raw rows revision_kind
--     'authored' → 'observation'. Raw intake is an OBSERVATION
--     (intake-pipeline.md §3); these rows were written before ADR-423
--     introduced the vocabulary (last on 2026-07-03; the writer was fixed by
--     f355d26 on 2026-07-09) and were mislabeled by migration 208's blanket
--     DEFAULT 'authored' backfill. Content, authorship, and parent pointers
--     are untouched — this corrects a classification flag to the truth the
--     vocabulary now expresses, not the revision chain (ADR-209 intact).

-- ── (1) connected_by ────────────────────────────────────────────────────────

ALTER TABLE platform_connections
    ADD COLUMN IF NOT EXISTS connected_by uuid REFERENCES auth.users(id);

UPDATE platform_connections
SET connected_by = user_id
WHERE connected_by IS NULL;

ALTER TABLE platform_connections
    ALTER COLUMN connected_by SET NOT NULL;

-- ── (2) slack raw relabel ───────────────────────────────────────────────────

UPDATE workspace_file_versions
SET revision_kind = 'observation'
WHERE revision_kind = 'authored'
  AND authored_by = 'system:sync-platform-state'
  AND path LIKE '%/inbound/%';

-- ── Verify (in-transaction; the runner rolls back on RAISE) ────────────────

DO $$
DECLARE
    n_null integer;
    n_mislabeled integer;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'platform_connections'
          AND column_name = 'connected_by'
    ) THEN
        RAISE EXCEPTION 'connected_by column missing after ALTER';
    END IF;

    SELECT count(*) INTO n_null
    FROM platform_connections WHERE connected_by IS NULL;
    IF n_null > 0 THEN
        RAISE EXCEPTION 'connected_by backfill left % NULL row(s)', n_null;
    END IF;

    SELECT count(*) INTO n_mislabeled
    FROM workspace_file_versions
    WHERE revision_kind = 'authored'
      AND authored_by = 'system:sync-platform-state'
      AND path LIKE '%/inbound/%';
    IF n_mislabeled > 0 THEN
        RAISE EXCEPTION 'slack raw relabel left % authored row(s)', n_mislabeled;
    END IF;

    RAISE NOTICE 'migration 244 verified: connected_by NOT NULL, inbound raw all observation';
END $$;
