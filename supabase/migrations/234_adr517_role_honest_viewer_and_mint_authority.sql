-- 234_adr517_role_honest_viewer_and_mint_authority.sql
-- ADR-517 — grants govern, share executes. Four moves, one migration:
--
-- 1. `viewer` becomes a first-class grant role (amends ADR-437 D4.3's
--    role-stays-member decision): the CHECK widens, and viewer-born grants are
--    backfilled BY BIRTHMARK (granted_by LIKE 'share-view:%') with an axes
--    guard (write_scopes = '{}') so a grant an owner has since widened is
--    left alone.
--
-- 2. The four substrate WRITE policies (198's membership-binary set) learn the
--    role-binary: a viewer-role grant no longer reaches INSERT/UPDATE/DELETE
--    at the database. Reads stay grant-broad at the DB and artifact-narrowed
--    in the primitive layer — the enforcement contract is canonized in
--    docs/architecture/grants-and-reach.md (ADR-517 D2).
--
-- 3. `workspaces.share_mint_policy` — the governance dial (ADR-517 D3):
--    'write-holders' (default — any non-viewer with write reach may mint a
--    share link) | 'owner-only'.
--
-- 4. `workspace_shares.artifact_path` canonicalized to the absolute substrate
--    spelling ('/workspace/…', ADR-517 D5) so three origins stop writing two
--    spellings into one column (the 2026-08-03 unrevocable-link defect class).
--
-- Idempotent: guards throughout. NO inner BEGIN/COMMIT — the runner
-- (scripts/db/run-migration.sh) supplies the single transaction, and an inner
-- COMMIT would swallow its dry-run ROLLBACK (the 545f88b lesson).

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. The honest role
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE principal_grants
    DROP CONSTRAINT IF EXISTS principal_grants_role_check;
ALTER TABLE principal_grants
    ADD CONSTRAINT principal_grants_role_check
    CHECK (role IN ('owner','member','viewer','own-agent','foreign-llm','platform','a2a'));

COMMENT ON CONSTRAINT principal_grants_role_check ON principal_grants IS
    'ADR-517 D1: viewer is a first-class role — a role the database cannot '
    'see is a role the database cannot enforce. Widening a viewer is a '
    're-grant (role change), never an axes edit.';

-- Backfill by birthmark, guarded by the axes: only grants born from a
-- share-view accept AND still write-deny-all become viewers. A viewer-born
-- grant the owner later widened (write_scopes repopulated) stays 'member'.
UPDATE principal_grants
SET role = 'viewer'
WHERE role = 'member'
  AND granted_by LIKE 'share-view:%'
  AND write_scopes = '{}';

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. The role-binary in RLS (recreates migration 198's four write policies)
-- ─────────────────────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "Members insert workspace files" ON workspace_files;
CREATE POLICY "Members insert workspace files"
    ON workspace_files FOR INSERT
    WITH CHECK (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
            UNION
            SELECT workspace_id FROM principal_grants
            WHERE principal_id = auth.uid()::text
              AND status = 'active'
              AND role <> 'viewer'
        )
    );

DROP POLICY IF EXISTS "Members update workspace files" ON workspace_files;
CREATE POLICY "Members update workspace files"
    ON workspace_files FOR UPDATE
    USING (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
            UNION
            SELECT workspace_id FROM principal_grants
            WHERE principal_id = auth.uid()::text
              AND status = 'active'
              AND role <> 'viewer'
        )
    );

DROP POLICY IF EXISTS "Members delete workspace files" ON workspace_files;
CREATE POLICY "Members delete workspace files"
    ON workspace_files FOR DELETE
    USING (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
            UNION
            SELECT workspace_id FROM principal_grants
            WHERE principal_id = auth.uid()::text
              AND status = 'active'
              AND role <> 'viewer'
        )
    );

DROP POLICY IF EXISTS "Members insert workspace file versions" ON workspace_file_versions;
CREATE POLICY "Members insert workspace file versions"
    ON workspace_file_versions FOR INSERT
    WITH CHECK (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
            UNION
            SELECT workspace_id FROM principal_grants
            WHERE principal_id = auth.uid()::text
              AND status = 'active'
              AND role <> 'viewer'
        )
    );

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. The governance dial
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE workspaces
    ADD COLUMN IF NOT EXISTS share_mint_policy TEXT NOT NULL DEFAULT 'write-holders';
ALTER TABLE workspaces
    DROP CONSTRAINT IF EXISTS workspaces_share_mint_policy_check;
ALTER TABLE workspaces
    ADD CONSTRAINT workspaces_share_mint_policy_check
    CHECK (share_mint_policy IN ('write-holders','owner-only'));

COMMENT ON COLUMN workspaces.share_mint_policy IS
    'ADR-517 D3: who may mint share links. write-holders (default) = any '
    'non-viewer grant holder with write reach; owner-only = the owner alone. '
    'One gate (assert_may_mint_share) binds both origins (cockpit + MCP).';

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. One spelling for artifact_path (absolute — the substrate identity)
-- ─────────────────────────────────────────────────────────────────────────────

UPDATE workspace_shares
SET artifact_path = '/workspace/' || ltrim(artifact_path, '/')
WHERE artifact_path IS NOT NULL
  AND artifact_path NOT LIKE '/workspace/%';

COMMENT ON COLUMN workspace_shares.artifact_path IS
    'ADR-517 D5: canonical ABSOLUTE spelling (/workspace/…), normalized at '
    'create_share. Readers must not compensate — the write is the normalizer.';

-- =============================================================================
-- Verification (manual):
--   SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
--     WHERE conname IN ('principal_grants_role_check','workspaces_share_mint_policy_check');
--   SELECT policyname, qual FROM pg_policies WHERE tablename='workspace_files'
--     AND policyname LIKE 'Members%';           -- expect the viewer exclusion in all three
--   SELECT count(*) FROM principal_grants WHERE role='viewer';
--   SELECT count(*) FROM workspace_shares
--     WHERE artifact_path IS NOT NULL AND artifact_path NOT LIKE '/workspace/%';  -- 0
-- =============================================================================
