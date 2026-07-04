-- 199_adr404_member_invites.sql
-- ADR-404 step 5 — member invites (the ADR-373 D4 provisioning UX) + the
-- legacy live-row identity retires.
--
-- APPLY ORDER GUARD: run this only AFTER the ADR-373 sweep-spine code
-- (commit "the sweep spine", migration 198) is DEPLOYED on API + Scheduler.
-- The spine removed every on_conflict="user_id,path" upsert from the write
-- path; older builds still upsert on that constraint and would fail once
-- it drops.
--
-- 1. workspace_invites — invite transport (the GRANT is the authorization
--    fact; an invite just carries the offer to an email address).
-- 2. Drop UNIQUE(user_id, path) on workspace_files. Under the workspace
--    binding the live-row identity is UNIQUE(workspace_id, path) (migration
--    198). The legacy constraint would make a member's first write to a
--    standard path (persona/IDENTITY.md …) collide with the same path in
--    the member's OWN workspace — the cross-workspace collision ADR-373
--    always planned to retire. A plain (user_id, path) index remains for
--    the transition's legacy-scoped reads.

-- -----------------------------------------------------------------------------
-- 1. workspace_invites
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workspace_invites (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id           UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    email                  TEXT NOT NULL,
    role                   TEXT NOT NULL DEFAULT 'member'
                           CHECK (role IN ('member')),
    token                  TEXT NOT NULL UNIQUE,
    invited_by             TEXT NOT NULL,
    status                 TEXT NOT NULL DEFAULT 'pending'
                           CHECK (status IN ('pending','accepted','revoked','expired')),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at             TIMESTAMPTZ NOT NULL,
    accepted_at            TIMESTAMPTZ,
    accepted_principal_id  TEXT
);

COMMENT ON TABLE workspace_invites IS
    'ADR-404 step 5: member-invite transport. Accepting mints the '
    'principal_grants row (ADR-386 lifecycle) — the grant is the '
    'authorization fact, the invite is not.';

CREATE INDEX IF NOT EXISTS idx_workspace_invites_ws_status
    ON workspace_invites(workspace_id, status);

ALTER TABLE workspace_invites ENABLE ROW LEVEL SECURITY;

-- Service-role-only: the routes enforce owner checks and the accept path
-- matches the acceptor's JWT email server-side.
DROP POLICY IF EXISTS "Service role manages workspace invites" ON workspace_invites;
CREATE POLICY "Service role manages workspace invites"
    ON workspace_invites TO service_role USING (true) WITH CHECK (true);

-- -----------------------------------------------------------------------------
-- 2. Retire the legacy live-row identity
-- -----------------------------------------------------------------------------
ALTER TABLE workspace_files
    DROP CONSTRAINT IF EXISTS workspace_files_user_id_path_key;

-- Transition support for remaining legacy-scoped reads (route filters not
-- yet swept — the ADR-373 named remainder).
CREATE INDEX IF NOT EXISTS idx_ws_files_user_path
    ON workspace_files(user_id, path);
