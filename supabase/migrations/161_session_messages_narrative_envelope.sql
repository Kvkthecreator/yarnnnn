-- Migration 161: ADR-219 Commit 2 — narrative substrate enum widening
--
-- Context: FOUNDATIONS v6.8 Axiom 9 ratified that `session_messages` is the
-- single narrative substrate — every invocation in the workspace emits exactly
-- one chat-shaped entry. Migration 160 added 'reviewer' as a role; this
-- migration finishes the widening required for full invocation coverage:
--
--   'agent'    — invocations by user-authored domain Agents. Today these
--                pass through 'assistant', conflating them with YARNNN
--                replies. Splitting them gives the operator-facing timeline
--                clean per-Identity attribution and lets the narrative-by-
--                Identity filter (ADR-219 Commit 5) work without metadata
--                introspection.
--
--   'external' — invocations by foreign LLMs over MCP (ADR-169:
--                pull_context / remember_this / work_on_this). MCP narrative
--                emission lands in ADR-219 Commit 6; the role enum needs to
--                accept the value before Commit 6 writes show up.
--
-- Non-destructive: existing rows keep their values; this widens the allowed
-- set. Migration 160's enum is preserved in full and extended.
--
-- The metadata JSONB envelope (invocation_id / task_slug / pulse / weight /
-- summary / provenance) is application-layer convention only — no schema
-- change here. Validation lives in api/services/narrative.py per ADR-219 D2.
--
-- The append_session_message RPC (migration 008) accepts p_role TEXT and
-- relies on this CHECK constraint for validation. No RPC change required.

BEGIN;

ALTER TABLE session_messages DROP CONSTRAINT IF EXISTS session_messages_role_check;

ALTER TABLE session_messages
  ADD CONSTRAINT session_messages_role_check
  CHECK (role IN ('user', 'assistant', 'system', 'reviewer', 'agent', 'external'));

COMMENT ON COLUMN session_messages.role IS
  'Identity class of the invocation that emitted this narrative entry: '
  'user (operator), assistant (YARNNN orchestration surface), system (workspace event / digest), '
  'reviewer (Reviewer Agent verdict), agent (user-authored domain Agent), '
  'external (foreign LLM via MCP). Per ADR-219 Commit 2 (2026-04-25). '
  'metadata JSONB carries the narrative envelope (invocation_id, task_slug, pulse, weight, summary, provenance).';

COMMIT;
