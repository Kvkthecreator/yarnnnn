-- Migration 202: ADR-407 Phase 3 — member_state, the member-experience home
--
-- The first store in the MEMBER-EXPERIENCE scope (ADR-407 D1/D7): one
-- principal's first-person state WITHIN a workspace — shell/window layout,
-- the attention read cursor, notification delivery preferences, drafts.
-- Keyed (workspace_id, principal_id, key): each member's desktop follows
-- them across devices and each workspace gets its own desktop (retiring the
-- invite-accept clearShellState symptom-patch).
--
-- Explicitly NOT substrate: presentation state, not authored content — it
-- does not flow through write_revision, carries no attribution ceremony,
-- and is NEVER consulted for authorization (ADR-405 D5 preserved).
-- Precedent: wake_queue as non-authoritative compute (ADR-298). Losing a
-- row loses a layout, never work.
--
-- KV-per-key jsonb: 'shell' (window manager state), 'attention' (read
-- cursor), 'notification_prefs' (mute/digest — presentation-layer). New
-- keys need no migration.

BEGIN;

CREATE TABLE IF NOT EXISTS member_state (
  workspace_id  uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  principal_id  uuid NOT NULL,
  key           text NOT NULL,
  value         jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, principal_id, key)
);

COMMENT ON TABLE member_state IS
  'ADR-407 Phase 3: member-experience scope — one principal''s first-person '
  'state within a workspace (shell layout, read cursor, notification prefs). '
  'Presentation state, not substrate; never consulted for authorization.';

-- Service-role only (the API scopes by the authenticated principal +
-- resolved workspace; no direct client access) — wake_queue precedent.
ALTER TABLE member_state ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS member_state_service_only ON member_state;
CREATE POLICY member_state_service_only ON member_state
  FOR ALL TO service_role USING (true) WITH CHECK (true);

COMMIT;
