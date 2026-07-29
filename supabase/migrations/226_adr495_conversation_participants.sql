-- Migration 226: ADR-495 — the Conversation is participants + turns
--
-- Supersedes migration 225 (ADR-492's two-store rooms model). That migration's
-- `conversations` / `conversation_messages` tables shipped 2026-07-28 and were
-- NEVER USED (prod read 2026-07-29: 0 rows). They are dropped here, not
-- migrated — there is nothing to migrate.
--
-- THE MODEL (ADR-495 D1): a Conversation is PARTICIPANTS + TURNS. There is no
-- `scope` column, because `private|shared` was a proxy for "how many humans" —
-- species law in substrate costume (ADR-405 forbids rules keyed on
-- human-vs-AI). What we called a "private lane" is a conversation with two
-- participants, one of whom (Freddie) reads every word; it read as private only
-- because one participant CLASS was silently assumed not to count as a reader.
--
-- PRIVACY (ADR-495 D2): readability follows CAST MEMBERSHIP — a grant question,
-- which is where DP35 always wanted it (so DP35 needs no amendment). The one
-- remaining question is the VISIBILITY WINDOW: from when may this participant
-- read? Anchored on `session_messages.sequence_number` (monotonic per
-- conversation, already uniquely indexed via `unique_sequence_per_session`).
--   visible_from_sequence = 0  → full history
--   visible_from_sequence = N  → sees turns with sequence_number >= N
-- Asked identically of humans and Agents (ADR-495 D3); the class-differing
-- DEFAULTS are dial settings (ADR-405 D4), never rules that read the class.
--
-- The store is `chat_sessions` grown, not a new table: it carries 87 references
-- across 25 non-test files, most of them NOT chat features (narrative, working
-- memory, session continuity, wake queue, MCP, purge). Direction of travel is
-- decided by mass.

BEGIN;

-- ── 1. The cast table, re-pointed at chat_sessions ─────────────────────────
-- Retained from migration 225 (well-shaped, empty). The FK moves from
-- `conversations` to `chat_sessions`; `visible_from_sequence` is added.
-- Recreated rather than ALTERed: it holds no rows, so a clean definition
-- beats a scar (Singular Implementation).

DROP TABLE IF EXISTS conversation_members;

CREATE TABLE conversation_members (
  id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id        uuid NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  workspace_id           uuid,
  member_kind            text NOT NULL CHECK (member_kind IN ('human','agent')),
  principal_id           uuid,
  agent_slug             text,
  -- ADR-495 D2 — the visibility window. 0 = full history. Never NULL: an
  -- unset window would be an unanswered disclosure question.
  visible_from_sequence  integer NOT NULL DEFAULT 0,
  invited_by             uuid NOT NULL,
  created_at             timestamptz NOT NULL DEFAULT now(),
  CHECK (
    (member_kind = 'human' AND principal_id IS NOT NULL AND agent_slug IS NULL)
    OR
    (member_kind = 'agent' AND agent_slug IS NOT NULL AND principal_id IS NULL)
  ),
  CHECK (visible_from_sequence >= 0)
);

COMMENT ON TABLE conversation_members IS
  'ADR-495: the CAST of a conversation — participants + turns is the whole '
  'object. Humans by principal_id, Agents by agent_slug (named hands, ADR-460 '
  '— never principals). Membership IS read authorization; '
  'visible_from_sequence is the window (0 = full history). One species-blind '
  'invite: class-differing defaults are dial settings (ADR-405 D4), never '
  'rules keyed on species.';

COMMENT ON COLUMN conversation_members.visible_from_sequence IS
  'ADR-495 D2 — from which session_messages.sequence_number this participant '
  'may read. 0 = full history. Widening later is a new disclosure decision; '
  'narrowing does not un-read and is not offered as a privacy control.';

CREATE UNIQUE INDEX uq_conversation_member_human
  ON conversation_members(conversation_id, principal_id) WHERE member_kind = 'human';
CREATE UNIQUE INDEX uq_conversation_member_agent
  ON conversation_members(conversation_id, agent_slug) WHERE member_kind = 'agent';
CREATE INDEX idx_conversation_members_conv
  ON conversation_members(conversation_id);
-- The authorization lookup: "which conversations may this principal read?"
CREATE INDEX idx_conversation_members_principal
  ON conversation_members(principal_id) WHERE member_kind = 'human';

ALTER TABLE conversation_members ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS conversation_members_service_only ON conversation_members;
CREATE POLICY conversation_members_service_only ON conversation_members
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ── 2. Backfill the cast from existing conversations ───────────────────────
-- Every existing lane becomes a Conversation whose cast is (its owner) +
-- (its Agent, if lane_meta.agent is set). Both windows are 0 — these
-- participants have always seen the whole transcript, so full history is the
-- byte-identical choice, not a widening.

INSERT INTO conversation_members
  (conversation_id, workspace_id, member_kind, principal_id, visible_from_sequence, invited_by)
SELECT id, workspace_id, 'human', user_id, 0, user_id
FROM chat_sessions
WHERE session_type = 'lane'
ON CONFLICT DO NOTHING;

INSERT INTO conversation_members
  (conversation_id, workspace_id, member_kind, agent_slug, visible_from_sequence, invited_by)
SELECT
  id,
  workspace_id,
  'agent',
  context_metadata->'lane'->>'agent',
  0,
  user_id
FROM chat_sessions
WHERE session_type = 'lane'
  AND context_metadata->'lane'->>'agent' IS NOT NULL
  AND length(trim(context_metadata->'lane'->>'agent')) > 0
ON CONFLICT DO NOTHING;

-- ── 3. Drop the superseded ADR-492 stores ──────────────────────────────────
-- 0 rows each (prod-verified 2026-07-29). `conversation_messages` first: it
-- FKs `conversations`.

DROP TABLE IF EXISTS conversation_messages;
DROP TABLE IF EXISTS conversations;

COMMIT;
