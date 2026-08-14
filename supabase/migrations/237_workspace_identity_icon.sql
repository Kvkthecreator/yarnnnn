-- Workspace identity, phase 1 (2026-08-14): the icon column.
--
-- `workspaces.name` has existed since 001 but was never writable from the
-- product; PATCH /api/workspace now writes it (owner-gated by the existing
-- RLS UPDATE policy, 002). The icon is a short text glyph (emoji), rendered
-- in the workspace switcher and settings — deliberately NOT an image upload:
-- the unauthenticated invite/share landings would need a public serving lane
-- the private workspace-cas bucket rightly refuses (mig 219).
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS icon TEXT;

COMMENT ON COLUMN workspaces.icon IS
  'Short text glyph (emoji) for the workspace; NULL renders the default org glyph.';
