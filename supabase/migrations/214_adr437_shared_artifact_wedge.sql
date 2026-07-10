-- 214_adr437_shared_artifact_wedge.sql
-- ADR-437 D4 — the shared-artifact wedge.
--
-- A SHARE is the member-invite's generous sibling (ADR-437 D4.3): both mint a
-- broad member grant and both land on one accept surface. A share differs from
-- an invite in three ways:
--   1. It is LINK-based, not email-locked — anyone who opens the link may
--      accept (the Figma default, ADR-437 D4.2: maximum access by default).
--   2. It carries the shared ARTIFACT (a workspace_files path) so the accept
--      surface can show "here is {artifact} + its trace" — the artifact is the
--      landing page (ADR-437 D4).
--   3. Accepting mints a member grant with `scopes=NULL` → the class default
--      (broad operation/ + agents/ write regions, ADR-373 D3) — the owner
--      narrows via the powerbox (ADR-434) if desired, never gates by default.
--
-- The GRANT is the authorization fact (ADR-386); the share row is transport,
-- exactly like workspace_invites. Modeled on migration 199.

CREATE TABLE IF NOT EXISTS workspace_shares (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id           UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    -- The shared artifact — a workspace_files path (e.g. 'operation/report.md').
    -- NULL = a bare workspace share (invite-shaped, no artifact context).
    artifact_path          TEXT,
    -- A human label for the accept-page hero (the artifact's display name or a
    -- short note); optional, best-effort at share time.
    label                  TEXT,
    role                   TEXT NOT NULL DEFAULT 'member'
                           CHECK (role IN ('member')),
    token                  TEXT NOT NULL UNIQUE,
    -- The principal who created the share (the sharer). TEXT to match
    -- workspace_invites.invited_by (a principal-id string).
    shared_by              TEXT NOT NULL,
    -- Link-based: no email lock. `accepted_principal_id` records who bound.
    status                 TEXT NOT NULL DEFAULT 'active'
                           CHECK (status IN ('active','revoked','expired')),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- NULL = never expires (a durable share link); a timestamp = a TTL.
    expires_at             TIMESTAMPTZ,
    last_accepted_at       TIMESTAMPTZ,
    accepted_principal_id  TEXT
);

COMMENT ON TABLE workspace_shares IS
    'ADR-437 D4: shared-artifact transport. A link-based, non-email-locked '
    'sibling of workspace_invites; accepting mints a broad member '
    'principal_grants row (ADR-386 lifecycle, scopes=NULL class default). '
    'The grant is the authorization fact; the share row is transport.';

CREATE INDEX IF NOT EXISTS idx_workspace_shares_ws_status
    ON workspace_shares(workspace_id, status);

ALTER TABLE workspace_shares ENABLE ROW LEVEL SECURITY;

-- Service-role-only: the routes enforce the sharer's grant server-side and the
-- accept path authenticates the acceptor's JWT (any authenticated principal may
-- accept a link — the Figma default).
DROP POLICY IF EXISTS "Service role manages workspace shares" ON workspace_shares;
CREATE POLICY "Service role manages workspace shares"
    ON workspace_shares TO service_role USING (true) WITH CHECK (true);
