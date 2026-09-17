-- ADR-655 D2 — drop `workspaces.owner_email`: a column with no writer.
--
-- Added twice (003_scheduling_tables.sql, 010_subscription_fields.sql), written
-- by NOTHING in the tree, and NULL on all 21 live workspaces. Its only reader
-- anywhere was `api/routes/admin.py`, whose Users table rendered the literal
-- string "unknown" for every row as a direct result — deleted in the same
-- commit as this migration.
--
-- Not backfilled, dropped: a backfill would invent a writer to feed a consumer
-- that no longer exists. `auth.users` is the writer of record for an account
-- identity (ADR-650); the console resolves it from `owner_id` through
-- `principal_display.resolve_member_names`, the one resolver.
--
-- Dependency check on live before writing this (2026-09-17, read-only probe):
--   pg_proc   with 'owner_email' in prosrc            -> 0 rows
--   views     with 'owner_email' in view_definition   -> 0 rows
--   get_workspaces_due_for_digest (migration 003)     -> 0 rows (long gone,
--       along with every workspaces.digest_* column it read)
-- So nothing in the database reads this column either.

ALTER TABLE workspaces DROP COLUMN IF EXISTS owner_email;

-- Verify the LIVE object — the runner's exit code is not verification:
--   SELECT column_name FROM information_schema.columns
--    WHERE table_schema='public' AND table_name='workspaces'
--      AND column_name='owner_email';   -- expect 0 rows
