-- Migration 167: add 'system_agent' to session_messages.role CHECK — ADR-252 Phase 1
--
-- ADR-252 D4: role='system_agent' replaces role='assistant' for new System Agent
-- writes. role='assistant' stays valid for historical rows — no retroactive migration.
-- The new role maps to 'system-agent-bubble' in MessageDispatch.tsx, labeled
-- "System Agent" (not "YARNNN", not "system").
--
-- Sequence:
--   migration 160 — added 'reviewer'
--   migration 161 — added 'agent', 'external' (full Identity taxonomy)
--   migration 167 — adds 'system_agent' (System Agent execution narration)

ALTER TABLE session_messages DROP CONSTRAINT IF EXISTS session_messages_role_check;

ALTER TABLE session_messages
  ADD CONSTRAINT session_messages_role_check
  CHECK (role IN ('user', 'assistant', 'system', 'reviewer', 'agent', 'external', 'system_agent'));

COMMENT ON COLUMN session_messages.role IS
  'Identity class of the narrative entry per FOUNDATIONS Axiom 2.
   user         — operator message
   assistant    — legacy System Agent response (pre-ADR-252; preserved for history)
   system_agent — System Agent execution narration (ADR-252 D4)
   system       — mechanical system event (back-office, housekeeping)
   reviewer     — Reviewer judgment entry (verdict, reflection, addressed assessment)
   agent        — user-authored domain agent output
   external     — MCP foreign-LLM write-back';
