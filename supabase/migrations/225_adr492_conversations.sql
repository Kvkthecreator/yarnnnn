-- Migration 225: ADR-492 — the shared Conversation store (rooms; comment threads later)
--
-- WORKSPACE-CONTENT scope (DP35): part of the commons, attributed, readable by
-- grant-holders. This is the D2 taxonomy crossing made concrete — a shared
-- conversation is NOT a flag on chat_sessions (that store is declared
-- member-experience; one scope per store), it is a new object.
--
-- ONE grammar, one owner (ADR-492 D1): rooms today; artifact-bound comment
-- threads later ride the SAME tables via `binding` (D4 — binding-capable from
-- birth). No second messaging object, ever.
--
-- Invariants encoded here:
--   * Never-ambient: every message row carries author_principal_id — the HUMAN
--     whose act it is. An engine turn is the member's hands (via_model set,
--     agent_slug = the face); there is no authorless row shape.
--   * Agents are named hands, not principals (ADR-460): an agent member is an
--     agent_slug, never a principal_grants row.
--   * Append-only: messages take no CAS precondition (ADR-406 appender rule).
--   * Resolution is a state transition on the conversation (ADR-492 D4) — the
--     fact mention To-do derivation will key on (resolution ≠ read cursor).

BEGIN;

CREATE TABLE IF NOT EXISTS conversations (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  title         text NOT NULL DEFAULT 'New room',
  created_by    uuid NOT NULL,
  status        text NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived')),
  binding       jsonb,
  resolved_at   timestamptz,
  resolved_by   uuid,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE conversations IS
  'ADR-492: shared-scope Conversation objects (rooms; bound comment threads '
  'later via binding). Workspace-content scope — part of the commons. Private '
  'lanes stay in chat_sessions (member-experience); scope is set at birth and '
  'never flips (D6.b).';

CREATE INDEX IF NOT EXISTS idx_conversations_workspace
  ON conversations(workspace_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS conversation_members (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id  uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  workspace_id     uuid NOT NULL,
  member_kind      text NOT NULL CHECK (member_kind IN ('human','agent')),
  principal_id     uuid,
  agent_slug       text,
  invited_by       uuid NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now(),
  CHECK (
    (member_kind = 'human' AND principal_id IS NOT NULL AND agent_slug IS NULL)
    OR
    (member_kind = 'agent' AND agent_slug IS NOT NULL AND principal_id IS NULL)
  )
);

COMMENT ON TABLE conversation_members IS
  'ADR-492 D6: room membership. Humans by principal_id (must hold a workspace '
  'grant); Agents by slug (named hands — ADR-460, never principals). '
  'invited_by is the attributed act.';

CREATE UNIQUE INDEX IF NOT EXISTS uq_conversation_member_human
  ON conversation_members(conversation_id, principal_id) WHERE member_kind = 'human';
CREATE UNIQUE INDEX IF NOT EXISTS uq_conversation_member_agent
  ON conversation_members(conversation_id, agent_slug) WHERE member_kind = 'agent';
CREATE INDEX IF NOT EXISTS idx_conversation_members_conv
  ON conversation_members(conversation_id);

CREATE TABLE IF NOT EXISTS conversation_messages (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id      uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  workspace_id         uuid NOT NULL,
  author_principal_id  uuid NOT NULL,
  via_model            text,
  agent_slug           text,
  content              text NOT NULL,
  mentions             jsonb,
  created_at           timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE conversation_messages IS
  'ADR-492: turns of a shared Conversation. author_principal_id = the human '
  'whose act this is (never-ambient — always present). via_model NULL = the '
  'human speaking; via_model set = an engine turn as the member''s hands '
  '(member:{id} via {model}), agent_slug = the addressed face. mentions = D3 '
  'addressing metadata (content fact; attention derives OS-side).';

CREATE INDEX IF NOT EXISTS idx_conversation_messages_conv
  ON conversation_messages(conversation_id, created_at);

-- Service-role only (the API mediates: workspace grant + room membership) —
-- member_state / wake_queue precedent.
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS conversations_service_only ON conversations;
CREATE POLICY conversations_service_only ON conversations
  FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS conversation_members_service_only ON conversation_members;
CREATE POLICY conversation_members_service_only ON conversation_members
  FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS conversation_messages_service_only ON conversation_messages;
CREATE POLICY conversation_messages_service_only ON conversation_messages
  FOR ALL TO service_role USING (true) WITH CHECK (true);

COMMIT;
