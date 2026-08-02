-- 231_adr465_share_as_view.sql
-- ADR-465 D3 (ratified 2026-08-02 via ADR-512 §7) — the second share shape.
--
-- A prominent Share draws the "I just want them to SEE this deck" case; under
-- broad-member-only every such share silently over-granted full workspace
-- membership (the failure D3 names). The share row now records which shape the
-- sharer chose:
--   role = 'member'  → accept mints the broad member grant (unchanged default)
--   role = 'viewer'  → accept mints a BIRTH-NARROWED member grant (one grant
--                      model, ADR-437 D4.3): powerbox axes write_scopes=[]
--                      (explicit deny-all) + read_scopes=[artifact_path] (or
--                      class-default read when the share carries no artifact).
--
-- The grant row's role stays 'member' — the narrowing lives on the scope axes
-- (migration 211), never on a new access object. An existing broader grant is
-- never downgraded by a later view-link accept (the accept path returns the
-- existing grant untouched).

ALTER TABLE workspace_shares
    DROP CONSTRAINT IF EXISTS workspace_shares_role_check;

ALTER TABLE workspace_shares
    ADD CONSTRAINT workspace_shares_role_check
    CHECK (role IN ('member', 'viewer'));

COMMENT ON COLUMN workspace_shares.role IS
    'The grant shape the sharer chose (ADR-465 D3): member = broad class-default '
    'grant on accept; viewer = birth-narrowed member grant (write_scopes=[], '
    'read_scopes=[artifact_path]). The grant row role is always member — one '
    'grant model, narrowed by the powerbox axes.';
