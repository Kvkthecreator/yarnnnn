-- Migration 223: ADR-489 D4/D5 — the notification-prefs fold + the
-- workspace-stamped transport record.
--
-- D5 (the ADR-407 D7 fold executed): member_state['notification_prefs'] is
-- the ONE notification-preference store — per (workspace, principal), the
-- key migration 202 reserved. The legacy account-scoped table
-- `user_notification_preferences` (migration 022, ADR-018) and its RPC drop.
-- No FE surface ever consumed the legacy routes; non-default rows (if any)
-- are carried into member_state keyed by the user's owner workspace.
--
-- D4 (ADR-407 D8): the `notifications` transport table gains a workspace
-- stamp — the row's user_id IS the recipient principal; workspace_id says
-- which commons the act happened in. Nullable (pre-489 rows + account-level
-- sends without a workspace context).

BEGIN;

-- 1. Carry non-default prefs into member_state (owner workspace keying —
--    the N=1 world; multi-workspace members re-declare per workspace).
INSERT INTO member_state (workspace_id, principal_id, key, value)
SELECT
  w.id,
  p.user_id,
  'notification_prefs',
  jsonb_build_object(
    'delivery_email', COALESCE(p.email_agent_ready, true),
    'failure_email',  COALESCE(p.email_agent_failed, true),
    'witness_email',  'high'
  )
FROM user_notification_preferences p
JOIN workspaces w ON w.owner_id = p.user_id
WHERE COALESCE(p.email_agent_ready, true) IS DISTINCT FROM true
   OR COALESCE(p.email_agent_failed, true) IS DISTINCT FROM true
ON CONFLICT (workspace_id, principal_id, key)
DO UPDATE SET value = member_state.value || EXCLUDED.value,
              updated_at = now();

-- 2. Drop the legacy RPC + table (ADR-489 D5 — singular implementation).
DROP FUNCTION IF EXISTS get_notification_preferences(UUID);
DROP TABLE IF EXISTS user_notification_preferences;

-- 3. The transport record gains the workspace stamp (ADR-407 D8).
ALTER TABLE notifications
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id) ON DELETE SET NULL;

COMMENT ON TABLE notifications IS
  'ADR-405 D3 / ADR-489: outbound TRANSPORT record only (email). A row = an '
  'actual send to a recipient principal (user_id), workspace-stamped. '
  'In-app attention is derivation over the ledgers — never rows here.';
COMMENT ON COLUMN notifications.workspace_id IS
  'ADR-407 D8 — the commons the act happened in; user_id is the recipient.';

COMMIT;
