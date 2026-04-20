-- Migration 153 — ADR-194 v2 Phase 2b: impersonation column prep
--
-- Schema-only preparation for ADR-194 v2's impersonation substrate.
-- Admin endpoints (POST /api/admin/impersonate/{workspace_id}, etc.)
-- are deferred to Phase 2c along with the frontend admin UI. This
-- migration lands the columns so the frontend work can be done against
-- real schema instead of waiting on a late-bound schema change.
--
-- Per FOUNDATIONS v6.0, these columns are Identity-dimension metadata:
--   - workspaces.impersonation_persona is a Substrate marker that this
--     workspace is a persona test account (Identity context for every
--     action taken within it).
--   - user_admin_flags.can_impersonate is an admin-gated Identity flag
--     — only true for founders running the conglomerate alpha per
--     ADR-191.
--
-- Not a Substrate-kind violation: both columns are scheduling-index
-- metadata (permitted row kind 1), narrow attributes on existing rows.
--
-- Note on schema: YARNNN does not have a public.users table — users
-- live in auth.users (Supabase-managed). Rather than modifying auth.users,
-- we create a small user_admin_flags table keyed by user_id, following
-- the pattern of other per-user admin state (the table is narrow, lazy-
-- written only for users who receive admin flags; the absence of a row
-- means can_impersonate=false).

ALTER TABLE workspaces
    ADD COLUMN IF NOT EXISTS impersonation_persona text;

CREATE TABLE IF NOT EXISTS user_admin_flags (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    can_impersonate BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS: users can read their own flags; admins (the app itself via
-- service key) write. No user-update path — can_impersonate is granted
-- manually via psql for founders.
ALTER TABLE user_admin_flags ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_admin_flags_user_select
    ON user_admin_flags FOR SELECT
    USING (user_id = auth.uid());

-- Service role bypasses RLS. No INSERT/UPDATE policies for user JWTs —
-- these flags are granted out-of-band, not self-service.

COMMENT ON COLUMN workspaces.impersonation_persona IS
    'ADR-194 v2 Phase 2b: persona slug (e.g., "day-trader-alpha", "ecommerce-alpha") when this workspace is a founder-operated persona test account. NULL for normal workspaces. Surfaced in UI chrome as a banner during impersonation sessions (Phase 2c).';

COMMENT ON TABLE user_admin_flags IS
    'ADR-194 v2 Phase 2b: per-user admin flags. Lazy-written — absence of a row means all flags false. Granted out-of-band via psql for founders running the conglomerate alpha per ADR-191.';

COMMENT ON COLUMN user_admin_flags.can_impersonate IS
    'ADR-194 v2 Phase 2b: admin flag. Only users with can_impersonate=true may switch into persona workspaces via POST /api/admin/impersonate (Phase 2c endpoints).';
