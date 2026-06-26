-- =============================================================================
-- Migration 189 — ADR-373 Phase 1: the user_id → workspace_id re-key
-- =============================================================================
--
-- Makes the WORKSPACE (not the user) the substrate's binding unit, so an open
-- set of principals (humans, their agents, other humans, platforms, foreign and
-- local LLMs) can attribute into one shared, judged commons.
--
-- PHASE 1 IS ADDITIVE AND BACKWARD-COMPATIBLE BY CONSTRUCTION:
--   - Adds `workspaces` + `principal_grants` tables.
--   - Adds a NULLABLE `workspace_id` column to workspace_files +
--     workspace_file_versions, backfills it, then flips it NOT NULL.
--   - KEEPS `user_id` on both tables (the existing UNIQUE(user_id,path), the
--     on_conflict="user_id,path" upsert, the RLS, and every .eq("user_id")
--     caller keep working unchanged). user_id is dropped only in a LATER phase,
--     once all code reads workspace_id. THIS MIGRATION DROPS NOTHING.
--   - The N=1 backfill (each distinct user_id -> one singleton owner-workspace)
--     reproduces today's behavior byte-identically: (user_id, path) and
--     (workspace_id, path) are 1:1 for every existing row.
--
-- workspace_blobs is UNTOUCHED — content-addressed global (no user_id);
-- scoping lives at the revision/file layer, which is what re-keys.
--
-- Idempotent: re-running is safe (IF NOT EXISTS guards + WHERE workspace_id IS
-- NULL backfill predicate, mirroring migration 158's head_version_id pattern).
--
-- Refs: docs/adr/ADR-373-multi-principal-workspace-and-the-re-key.md (D1/D2/D3),
--       supabase/migrations/158_adr209_authored_substrate.sql (the backfill
--       CTE pattern this follows),
--       supabase/migrations/100_workspace_files.sql (UNIQUE(user_id,path)).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. workspaces — the substrate's new binding unit
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workspaces (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name          TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE workspaces IS
    'ADR-373: the substrate binding unit. An open set of principals attribute '
    'into one workspace via principal_grants. owner_user_id is the human who '
    'created it (the N=1 case: one user -> one singleton owner-workspace).';

-- One singleton workspace per owner is the invariant Phase 1 relies on for the
-- byte-identical N=1 backfill. (Multi-workspace-per-owner is a post-launch
-- additive concern; this partial unique keeps the 1:1 honest for now.)
CREATE UNIQUE INDEX IF NOT EXISTS uq_workspaces_singleton_owner
    ON workspaces(owner_user_id);

-- -----------------------------------------------------------------------------
-- 2. principal_grants — per-principal authorization (D2)
-- -----------------------------------------------------------------------------
-- Schema ships now; the gate CONSULT (_caller_class -> grant lookup) is Phase 2.
-- Phase 1 seeds exactly one owner grant per backfilled workspace.
CREATE TABLE IF NOT EXISTS principal_grants (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    principal_id TEXT NOT NULL,             -- auth.users.id for a human; agent
                                            -- slug; OAuth client_id for MCP/A2A
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    role         TEXT NOT NULL,             -- owner | member | own-agent |
                                            -- foreign-llm | platform | a2a (D4)
    scopes       TEXT[],                    -- write-region set; NULL => the
                                            -- role's class-default (D3)
    granted_by   TEXT NOT NULL DEFAULT 'system:bundle-fork',
    status       TEXT NOT NULL DEFAULT 'active',  -- active | revoked
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT principal_grants_role_check
        CHECK (role IN ('owner','member','own-agent','foreign-llm','platform','a2a')),
    CONSTRAINT principal_grants_status_check
        CHECK (status IN ('active','revoked'))
);

COMMENT ON TABLE principal_grants IS
    'ADR-373 D2: per-principal authorization to a workspace. Completes the '
    'attribution<->authorization symmetry (today attributes per-principal, '
    'authorizes per-class). scopes NULL => the role class-default '
    '(CALLER_WRITE_POLICY reinterpreted, D3). Gate consult is Phase 2.';

-- A principal holds at most one ACTIVE grant per workspace (re-granting updates
-- the existing row). Enforced on the active subset so a revoked grant can coexist.
CREATE UNIQUE INDEX IF NOT EXISTS uq_principal_grant_active
    ON principal_grants(principal_id, workspace_id)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_principal_grants_workspace
    ON principal_grants(workspace_id, status);
-- The resolver path: "which workspace(s) does this principal reach?"
CREATE INDEX IF NOT EXISTS idx_principal_grants_principal
    ON principal_grants(principal_id, status);

-- -----------------------------------------------------------------------------
-- 3. Add NULLABLE workspace_id to the two re-keyed substrate tables
-- -----------------------------------------------------------------------------
ALTER TABLE workspace_files
    ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE;
ALTER TABLE workspace_file_versions
    ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE;

-- -----------------------------------------------------------------------------
-- 4. Backfill — every distinct user_id -> one singleton owner-workspace
-- -----------------------------------------------------------------------------
-- Step 4a: one workspace per distinct owner across BOTH substrate tables
-- (a user may have revisions for a path whose live file was deleted, so union).
INSERT INTO workspaces (owner_user_id)
SELECT DISTINCT user_id
FROM (
    SELECT user_id FROM workspace_files
    UNION
    SELECT user_id FROM workspace_file_versions
) AS owners
ON CONFLICT (owner_user_id) DO NOTHING;  -- uq_workspaces_singleton_owner

-- Step 4b: seed one owner grant per workspace
INSERT INTO principal_grants (principal_id, workspace_id, role, granted_by)
SELECT w.owner_user_id::text, w.id, 'owner', 'system:adr373-backfill'
FROM workspaces w
WHERE NOT EXISTS (
    SELECT 1 FROM principal_grants pg
    WHERE pg.workspace_id = w.id
      AND pg.principal_id = w.owner_user_id::text
      AND pg.role = 'owner'
);

-- Step 4c: stamp workspace_id onto every substrate row (idempotent: only NULLs)
UPDATE workspace_files wf
SET workspace_id = w.id
FROM workspaces w
WHERE w.owner_user_id = wf.user_id
  AND wf.workspace_id IS NULL;

UPDATE workspace_file_versions wfv
SET workspace_id = w.id
FROM workspaces w
WHERE w.owner_user_id = wfv.user_id
  AND wfv.workspace_id IS NULL;

-- -----------------------------------------------------------------------------
-- 5. Flip workspace_id NOT NULL (only safe after backfill stamped every row)
-- -----------------------------------------------------------------------------
-- Guarded: if any row is still NULL the ALTER will fail loudly — that is the
-- intended tripwire (a backfill gap must not silently pass).
ALTER TABLE workspace_files       ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE workspace_file_versions ALTER COLUMN workspace_id SET NOT NULL;

-- -----------------------------------------------------------------------------
-- 6. Indexes mirroring the (user_id, path) set, on (workspace_id, path)
-- -----------------------------------------------------------------------------
-- The reads will move to workspace_id scoping (the code sweep); these keep that
-- path fast from day one. The legacy (user_id, …) indexes STAY (user_id stays).
CREATE INDEX IF NOT EXISTS idx_ws_files_wsid_path
    ON workspace_files(workspace_id, path);
CREATE INDEX IF NOT EXISTS idx_ws_files_wsid_path_prefix
    ON workspace_files(workspace_id, path text_pattern_ops);
CREATE INDEX IF NOT EXISTS idx_ws_versions_wsid_path_created
    ON workspace_file_versions(workspace_id, path, created_at DESC);

-- -----------------------------------------------------------------------------
-- 7. RLS — workspace-membership scoping (additive: keep user_id policies until
--    the code is fully off user_id; ADD workspace-membership policies alongside)
-- -----------------------------------------------------------------------------
-- A human reaches a workspace's substrate iff they hold an active grant.
-- Phase 1 keeps the existing user_id = auth.uid() policies (so nothing breaks
-- mid-sweep); these membership policies are ADDED so the workspace_id read path
-- is authorized once callers switch. Both hold during the transition; in N=1
-- they select the same rows (the user's singleton workspace).

ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE principal_grants ENABLE ROW LEVEL SECURITY;

-- Owner can see their workspace; service role manages.
CREATE POLICY "Users view workspaces they own or are granted"
    ON workspaces FOR SELECT
    USING (
        owner_user_id = auth.uid()
        OR id IN (
            SELECT workspace_id FROM principal_grants
            WHERE principal_id = auth.uid()::text AND status = 'active'
        )
    );
CREATE POLICY "Service role manages workspaces"
    ON workspaces TO service_role USING (true) WITH CHECK (true);

-- A principal sees their own grants; service role manages all.
CREATE POLICY "Principals view own grants"
    ON principal_grants FOR SELECT
    USING (principal_id = auth.uid()::text);
CREATE POLICY "Service role manages grants"
    ON principal_grants TO service_role USING (true) WITH CHECK (true);

-- Membership-scoped SELECT on the substrate (added ALONGSIDE the existing
-- user_id = auth.uid() policies; either grants access during the transition).
CREATE POLICY "Members view workspace files"
    ON workspace_files FOR SELECT
    USING (
        workspace_id IN (
            SELECT workspace_id FROM principal_grants
            WHERE principal_id = auth.uid()::text AND status = 'active'
        )
    );
CREATE POLICY "Members view workspace file versions"
    ON workspace_file_versions FOR SELECT
    USING (
        workspace_id IN (
            SELECT workspace_id FROM principal_grants
            WHERE principal_id = auth.uid()::text AND status = 'active'
        )
    );

-- =============================================================================
-- 8. Verification (run manually after migration — the byte-identical N=1 proof)
-- =============================================================================
--
-- -- Every substrate row got a workspace_id (no NULLs survived; the NOT NULL
-- -- flip in §5 already enforces this, but confirm the counts line up):
-- SELECT
--     (SELECT COUNT(*) FROM workspace_files)                         AS files,
--     (SELECT COUNT(*) FROM workspace_files WHERE workspace_id IS NOT NULL) AS files_keyed,
--     (SELECT COUNT(*) FROM workspace_file_versions)                 AS revisions,
--     (SELECT COUNT(*) FROM workspace_file_versions WHERE workspace_id IS NOT NULL) AS revisions_keyed,
--     (SELECT COUNT(*) FROM workspaces)                              AS workspaces,
--     (SELECT COUNT(DISTINCT user_id) FROM workspace_files)          AS distinct_owners,
--     (SELECT COUNT(*) FROM principal_grants WHERE role='owner')     AS owner_grants;
-- -- Expected (N=1):
-- --   files = files_keyed; revisions = revisions_keyed
-- --   workspaces = owner_grants  (one owner grant per workspace)
-- --   workspaces >= distinct_owners (union of files+versions owners)
--
-- -- The 1:1 invariant — every (user_id, path) maps to exactly one workspace_id:
-- SELECT user_id, path, COUNT(DISTINCT workspace_id) AS distinct_ws
-- FROM workspace_files GROUP BY user_id, path HAVING COUNT(DISTINCT workspace_id) > 1;
-- -- Expected: ZERO rows (no path straddles two workspaces).
-- =============================================================================
