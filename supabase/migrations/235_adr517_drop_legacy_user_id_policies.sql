-- 235_adr517_drop_legacy_user_id_policies.sql
-- ADR-517 click-pass finding (2026-08-04, adr517-share-governance-click-pass,
-- step viewer-write-refused-at-db): the RLS INSERT probe as a viewer-role
-- principal SUCCEEDED. Root cause: the pre-ADR-373 single-principal policies
-- ("Users can … own workspace files", keyed user_id = auth.uid() with NO
-- workspace constraint) were left in place by migration 198 as "transition —
-- either grants access" and never dropped. Permissive policies OR together,
-- so they bypass BOTH the membership predicate and migration 234's viewer
-- write-exclusion — and the INSERT shape is a cross-workspace write door:
-- any authenticated principal could insert a row into ANY workspace by
-- stamping their own user_id.
--
-- Post-ADR-373 the legacy policies guard nothing legitimate: every row
-- carries workspace_id (migration 189 re-key), an owner's writes pass the
-- owner branch, a member's pass the grant branch. Singular Implementation:
-- the membership policies are the only write/read law.
--
-- Idempotent. No inner BEGIN/COMMIT — the runner owns the transaction.

DROP POLICY IF EXISTS "Users can insert own workspace files" ON workspace_files;
DROP POLICY IF EXISTS "Users can update own workspace files" ON workspace_files;
DROP POLICY IF EXISTS "Users can delete own workspace files" ON workspace_files;
DROP POLICY IF EXISTS "Users can view own workspace files"   ON workspace_files;

DROP POLICY IF EXISTS "Authenticated users can insert own workspace file versions" ON workspace_file_versions;
DROP POLICY IF EXISTS "Users can view own workspace file versions" ON workspace_file_versions;

-- =============================================================================
-- Verification (manual):
--   SELECT policyname, cmd FROM pg_policies
--     WHERE tablename IN ('workspace_files','workspace_file_versions')
--     ORDER BY tablename, cmd;
--   -- Expect ONLY the service-role policy + the Members policies on each.
--   -- Probe (must ERROR 42501):
--   BEGIN;
--   SELECT set_config('request.jwt.claims', '{"sub":"<viewer uuid>","role":"authenticated"}', true);
--   SET LOCAL ROLE authenticated;
--   INSERT INTO workspace_files (workspace_id, user_id, path, content)
--     VALUES ('<ws>', '<viewer uuid>', '/workspace/operation/_probe.md', 'x');
--   ROLLBACK;
-- =============================================================================
