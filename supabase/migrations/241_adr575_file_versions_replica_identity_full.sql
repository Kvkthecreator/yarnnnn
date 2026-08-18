-- Migration 241 (ADR-575 D6): REPLICA IDENTITY FULL on workspace_file_versions.
--
-- FOUND BY DRIVING THE DEPLOYED SURFACE, not by a gate.
--
-- Migration 240 published the table and the browser subscribed cleanly:
--
--   ["1",null,"realtime:file-revisions:%2Fworkspace%2FDocuments%2Fadr572-click-pass.md",
--    "system",{"message":"Subscribed to PostgreSQL","status":"ok",
--              "extension":"postgres_changes", ...}]
--
-- with the correct server-side filter (`path=eq./workspace/Documents/…`). A peer
-- then wrote through the real API (revision b5da51e9…, confirmed present in
-- `workspace_file_versions`). **No INSERT frame was ever delivered** — only
-- Phoenix heartbeats. Subscribed, filtered, and silent.
--
-- THREE THEORIES WERE REFUTED BY MEASUREMENT before this one:
--   1. "the table isn't published"  — it is (240 verified the catalog).
--   2. "RLS forbids the subscriber" — it does not: as the real principal, in a
--      ROLLBACK txn, `SELECT … WHERE id=b5da51e9…` returns 1 row.
--   3. "the policy subquery is too complex" — `session_messages`' working
--      policy also subqueries another table, and it delivers today.
--
-- THE ACTUAL CAUSE. Realtime re-checks RLS for each subscriber against the row
-- as reconstructed FROM THE WAL RECORD. Under `REPLICA IDENTITY DEFAULT` the
-- record carries only the PRIMARY KEY, so every other column reads NULL during
-- that check. This table's SELECT policy is:
--
--   workspace_id IN (owned ∪ actively-granted)
--
-- and `workspace_id` is NOT the primary key — so it is NULL in the WAL record,
-- the predicate cannot be satisfied, and Realtime drops the row **silently**
-- rather than erroring. `session_messages` was unaffected because its policy
-- keys on `session_id`, which its own record carries.
--
-- ⭐ The failure mode is the one migration 240's header warned about in the
-- abstract and did not actually prevent: a subscription that reports SUBSCRIBED
-- and delivers nothing. Publishing a table is necessary and NOT sufficient.
--
-- COST, stated rather than glossed: FULL puts every column of the OLD row into
-- the WAL for UPDATE/DELETE. This table is INSERT-mostly by construction
-- (ADR-209 — revisions are appended, never updated; `write_revision()` is the
-- single write path), and it carries no `content` column (content lives in
-- `workspace_files` / the CAS blob), so the row is small metadata. The WAL cost
-- is bounded and the correctness is not optional.
--
-- Idempotent: ALTER … REPLICA IDENTITY is a no-op when already set.

ALTER TABLE public.workspace_file_versions REPLICA IDENTITY FULL;

-- Verify the LIVE object. 'f' = FULL, 'd' = DEFAULT (primary key only).
-- The runner's exit code is not verification.
DO $$
DECLARE
  ident "char";
BEGIN
  SELECT relreplident INTO ident
    FROM pg_class WHERE relname = 'workspace_file_versions';
  IF ident <> 'f' THEN
    RAISE EXCEPTION
      'Migration 241 failed: workspace_file_versions REPLICA IDENTITY is %, expected f (FULL). Realtime would re-check RLS against a WAL record whose workspace_id is NULL, and drop every row silently.',
      ident;
  END IF;
END $$;
