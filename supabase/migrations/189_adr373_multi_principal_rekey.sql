-- =============================================================================
-- Migration 189 — ADR-373 Phase 1: the user_id → workspace_id re-key
-- =============================================================================
--
-- Makes the WORKSPACE (not the user) the substrate's binding unit, so an open
-- set of principals (humans, their agents, other humans, platforms, foreign and
-- local LLMs) can attribute into one shared, judged commons.
--
-- PRE-FLIGHT FINDING (2026-06-26): the `workspaces` table ALREADY EXISTS
-- (001_initial_schema.sql — the billing/account root: id, owner_id, name,
-- balance_usd, subscription_*). It is ALREADY 1:1 with users (12 rows / 12
-- distinct owners) and EVERY substrate owner already has one
-- (owners_with_substrate_but_no_ws = 0). So this migration does NOT create a
-- workspaces table — it REUSES the existing one as the binding unit. The
-- workspace is already a first-class entity; substrate just needs to key to it
-- via the existing `owner_id` join (substrate.user_id == workspaces.owner_id ==
-- auth.users.id). This is MORE aligned with ADR-373's thesis than inventing a
-- second table.
--
-- PHASE 1 IS ADDITIVE AND BACKWARD-COMPATIBLE BY CONSTRUCTION:
--   - Adds `principal_grants` (the per-principal authorization table, D2).
--   - Adds a NULLABLE `workspace_id` FK to workspace_files +
--     workspace_file_versions → workspaces(id), backfills via owner_id, then
--     flips NOT NULL.
--   - KEEPS `user_id` on both substrate tables (the existing
--     UNIQUE(user_id,path), the on_conflict="user_id,path" upsert, the RLS, and
--     every .eq("user_id") caller keep working). user_id is dropped only in a
--     LATER phase. THIS MIGRATION DROPS NOTHING.
--   - The N=1 backfill (substrate.user_id -> workspaces.id WHERE owner_id =
--     user_id) reproduces today's behavior byte-identically: (user_id, path)
--     and (workspace_id, path) are 1:1 for every existing row.
--
-- workspace_blobs is UNTOUCHED — content-addressed global (no user_id).
--
-- Idempotent: re-running is safe (IF NOT EXISTS guards + WHERE workspace_id IS
-- NULL backfill predicate, mirroring migration 158's pattern).
--
-- Refs: docs/adr/ADR-373-multi-principal-workspace-and-the-re-key.md (D1/D2/D3),
--       supabase/migrations/001_initial_schema.sql (the existing workspaces),
--       supabase/migrations/158_adr209_authored_substrate.sql (backfill pattern).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. principal_grants — per-principal authorization (D2)
-- -----------------------------------------------------------------------------
-- The existing `workspaces` table is the binding unit (no CREATE here). This
-- table is the NEW authorization fact: which principal reaches which workspace,
-- with what write-region scope. Schema ships now; the gate CONSULT
-- (_caller_class -> grant lookup) is Phase 2. Phase 1 seeds one owner grant per
-- existing workspace.
CREATE TABLE IF NOT EXISTS principal_grants (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    principal_id TEXT NOT NULL,             -- auth.users.id for a human; agent
                                            -- slug; OAuth client_id for MCP/A2A
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    role         TEXT NOT NULL,             -- owner | member | own-agent |
                                            -- foreign-llm | platform | a2a (D4)
    scopes       TEXT[],                    -- write-region set; NULL => the
                                            -- role's class-default (D3)
    granted_by   TEXT NOT NULL DEFAULT 'system:adr373-backfill',
    status       TEXT NOT NULL DEFAULT 'active',  -- active | revoked
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT principal_grants_role_check
        CHECK (role IN ('owner','member','own-agent','foreign-llm','platform','a2a')),
    CONSTRAINT principal_grants_status_check
        CHECK (status IN ('active','revoked'))
);

COMMENT ON TABLE principal_grants IS
    'ADR-373 D2: per-principal authorization to a workspace (the existing '
    'workspaces table is the binding unit). Completes the attribution<->'
    'authorization symmetry. scopes NULL => the role class-default '
    '(CALLER_WRITE_POLICY reinterpreted, D3). Gate consult is Phase 2.';

CREATE UNIQUE INDEX IF NOT EXISTS uq_principal_grant_active
    ON principal_grants(principal_id, workspace_id)
    WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_principal_grants_workspace
    ON principal_grants(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_principal_grants_principal
    ON principal_grants(principal_id, status);

-- -----------------------------------------------------------------------------
-- 2. Add NULLABLE workspace_id to the two re-keyed substrate tables
-- -----------------------------------------------------------------------------
ALTER TABLE workspace_files
    ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE;
ALTER TABLE workspace_file_versions
    ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE;

-- -----------------------------------------------------------------------------
-- 3. Backfill — substrate.user_id -> the user's existing workspace
-- -----------------------------------------------------------------------------
-- Pre-flight confirmed every substrate owner has exactly one workspace
-- (owner_id = user_id). Stamp it. Idempotent (only NULLs).
UPDATE workspace_files wf
SET workspace_id = w.id
FROM workspaces w
WHERE w.owner_id = wf.user_id
  AND wf.workspace_id IS NULL;

UPDATE workspace_file_versions wfv
SET workspace_id = w.id
FROM workspaces w
WHERE w.owner_id = wfv.user_id
  AND wfv.workspace_id IS NULL;

-- Seed one owner grant per workspace that owns substrate.
INSERT INTO principal_grants (principal_id, workspace_id, role, granted_by)
SELECT DISTINCT w.owner_id::text, w.id, 'owner', 'system:adr373-backfill'
FROM workspaces w
WHERE EXISTS (SELECT 1 FROM workspace_files wf WHERE wf.workspace_id = w.id)
  AND NOT EXISTS (
    SELECT 1 FROM principal_grants pg
    WHERE pg.workspace_id = w.id
      AND pg.principal_id = w.owner_id::text
      AND pg.role = 'owner'
  );

-- -----------------------------------------------------------------------------
-- 4. Flip workspace_id NOT NULL (safe only after backfill stamped every row)
-- -----------------------------------------------------------------------------
-- Guarded: if any row is still NULL the ALTER fails loudly — the intended
-- tripwire (a substrate row whose user_id has no workspace would be a real
-- integrity problem to surface, not paper over). Pre-flight showed zero such
-- rows (owners_with_substrate_but_no_ws = 0), so this is expected to pass.
ALTER TABLE workspace_files         ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE workspace_file_versions ALTER COLUMN workspace_id SET NOT NULL;

-- -----------------------------------------------------------------------------
-- 5. Indexes mirroring the (user_id, path) set, on (workspace_id, path)
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_ws_files_wsid_path
    ON workspace_files(workspace_id, path);
CREATE INDEX IF NOT EXISTS idx_ws_files_wsid_path_prefix
    ON workspace_files(workspace_id, path text_pattern_ops);
CREATE INDEX IF NOT EXISTS idx_ws_versions_wsid_path_created
    ON workspace_file_versions(workspace_id, path, created_at DESC);

-- -----------------------------------------------------------------------------
-- 6. RLS — workspace-membership scoping (added ALONGSIDE existing user_id
--    policies, so nothing breaks mid-sweep; both hold during the transition;
--    in N=1 they select the same rows — the user's own workspace)
-- -----------------------------------------------------------------------------
ALTER TABLE principal_grants ENABLE ROW LEVEL SECURITY;

-- DROP-then-CREATE for genuine idempotency: Postgres has no
-- `CREATE POLICY IF NOT EXISTS`, so a bare re-run would abort on a duplicate
-- policy name. DROP IF EXISTS makes section 6 re-runnable like the rest of the
-- migration (honoring the header's idempotency contract).

-- A principal sees their own grants; service role manages all.
DROP POLICY IF EXISTS "Principals view own grants" ON principal_grants;
CREATE POLICY "Principals view own grants"
    ON principal_grants FOR SELECT
    USING (principal_id = auth.uid()::text);
DROP POLICY IF EXISTS "Service role manages grants" ON principal_grants;
CREATE POLICY "Service role manages grants"
    ON principal_grants TO service_role USING (true) WITH CHECK (true);

-- Membership-scoped SELECT on the substrate. A human reaches a workspace's
-- substrate iff they own it OR hold an active grant. (The existing
-- user_id = auth.uid() policies remain; either grants access in the transition.)
DROP POLICY IF EXISTS "Members view workspace files" ON workspace_files;
CREATE POLICY "Members view workspace files"
    ON workspace_files FOR SELECT
    USING (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
            UNION
            SELECT workspace_id FROM principal_grants
            WHERE principal_id = auth.uid()::text AND status = 'active'
        )
    );
DROP POLICY IF EXISTS "Members view workspace file versions" ON workspace_file_versions;
CREATE POLICY "Members view workspace file versions"
    ON workspace_file_versions FOR SELECT
    USING (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
            UNION
            SELECT workspace_id FROM principal_grants
            WHERE principal_id = auth.uid()::text AND status = 'active'
        )
    );

-- =============================================================================
-- 7. Verification (run manually after migration — the byte-identical N=1 proof)
-- =============================================================================
--
-- -- Every substrate row got a workspace_id (the NOT NULL flip enforces it):
-- SELECT
--     (SELECT COUNT(*) FROM workspace_files)                                  AS files,
--     (SELECT COUNT(*) FROM workspace_files WHERE workspace_id IS NOT NULL)   AS files_keyed,
--     (SELECT COUNT(*) FROM workspace_file_versions)                          AS revisions,
--     (SELECT COUNT(*) FROM workspace_file_versions WHERE workspace_id IS NOT NULL) AS revisions_keyed,
--     (SELECT COUNT(*) FROM principal_grants WHERE role='owner')              AS owner_grants;
-- -- Expected (N=1): files = files_keyed; revisions = revisions_keyed.
--
-- -- The 1:1 invariant — every (user_id, path) maps to exactly one workspace_id:
-- SELECT user_id, path, COUNT(DISTINCT workspace_id) AS distinct_ws
-- FROM workspace_files GROUP BY user_id, path HAVING COUNT(DISTINCT workspace_id) > 1;
-- -- Expected: ZERO rows.
--
-- -- workspace_id always matches the owner's workspace (no cross-owner leak):
-- SELECT COUNT(*) AS mismatched FROM workspace_files wf
-- JOIN workspaces w ON w.id = wf.workspace_id
-- WHERE w.owner_id <> wf.user_id;
-- -- Expected: 0.
-- =============================================================================
