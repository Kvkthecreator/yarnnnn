-- 198_adr373_member_write_scope.sql
-- ADR-373 Phase 1 (sweep spine, ADR-404 step 4) — two additions that make a
-- MEMBER's writes land correctly in the commons:
--
-- 1. UNIQUE (workspace_id, path) on workspace_files — the live-row identity
--    under the workspace binding. The write path's workspace-keyed
--    update-or-insert relies on this to converge concurrent creators onto
--    one row. Prod pre-verified 1:1 by migration 189's checks (every
--    (user_id, path) maps to exactly one workspace_id), so the index builds
--    without repair. Replaces the redundant non-unique idx_ws_files_wsid_path.
--
--    NOTE: the legacy UNIQUE(user_id, path) is deliberately KEPT here — the
--    deployed code still upserts on it until this commit's code is live
--    (deploy-window safety). It drops in migration 199 (the invites commit),
--    after which a member-created file no longer collides with a same-path
--    file in the member's own workspace.
--
-- 2. Membership-scoped WRITE RLS — migration 189 added membership SELECT
--    only; a member writing through their own JWT needs INSERT/UPDATE/DELETE
--    on workspace_files and INSERT on workspace_file_versions, scoped to
--    workspaces they hold an active grant into. The existing user_id
--    policies remain (transition — either grants access; in N=1 identical).
--    workspace_blobs already allows all authenticated principals (global
--    content-addressed store — scoping lives at the revision layer).
--
-- Idempotent: IF NOT EXISTS / DROP POLICY IF EXISTS guards throughout.

-- -----------------------------------------------------------------------------
-- 1. The live-row identity under the workspace binding
-- -----------------------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS uq_ws_files_wsid_path
    ON workspace_files(workspace_id, path);

DROP INDEX IF EXISTS idx_ws_files_wsid_path;  -- redundant with the unique form

COMMENT ON INDEX uq_ws_files_wsid_path IS
    'ADR-373: one live row per (workspace, path) — the commons'' file identity. '
    'The workspace-keyed write path (authored_substrate._upsert_workspace_file) '
    'converges concurrent creators on it.';

-- -----------------------------------------------------------------------------
-- 2. Membership-scoped write RLS (SELECT came in 189)
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Members insert workspace files" ON workspace_files;
CREATE POLICY "Members insert workspace files"
    ON workspace_files FOR INSERT
    WITH CHECK (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
            UNION
            SELECT workspace_id FROM principal_grants
            WHERE principal_id = auth.uid()::text AND status = 'active'
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
            WHERE principal_id = auth.uid()::text AND status = 'active'
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
            WHERE principal_id = auth.uid()::text AND status = 'active'
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
            WHERE principal_id = auth.uid()::text AND status = 'active'
        )
    );

-- =============================================================================
-- Verification (manual):
--   SELECT indexname FROM pg_indexes WHERE tablename='workspace_files'
--     AND indexname IN ('uq_ws_files_wsid_path','idx_ws_files_wsid_path');
--   -- Expect: only uq_ws_files_wsid_path.
--   SELECT policyname, cmd FROM pg_policies WHERE tablename='workspace_files';
--   -- Expect the three Members write policies alongside the legacy user_id set.
-- =============================================================================
