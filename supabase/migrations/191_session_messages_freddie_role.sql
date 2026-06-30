-- Migration 191: add 'freddie' to session_messages.role CHECK
--
-- Bug: the actor-identity unification (2026-06-30) renamed the persona-bearing
-- seat Reviewer → Freddie and swapped the application-layer narrative role
-- `reviewer` → `freddie` (services/narrative.py::VALID_ROLES, whose comment
-- claims it "Mirrors the session_messages.role CHECK constraint"). But NO
-- migration updated the DB constraint — it still allowed only `reviewer`
-- (migration 167). Every Freddie ADDRESSED reply has since hit
-- `session_messages_role_check` (code 23514) on persist. The wake succeeded and
-- the SSE frame rendered the reply live ONCE, but write_freddie_message →
-- write_narrative_entry (best-effort, swallows the error) never saved it — so on
-- any re-render the chat pane shows the operator's question and a BLANK panel.
-- Receipt: a live addressed wake (user 2abf3f96, 2026-06-30T23:38, status=success,
-- 675 output tokens) produced a reply that does NOT exist in session_messages;
-- reproducing the exact write_narrative_entry(role='freddie') call surfaced the
-- constraint violation directly.
--
-- Fix: add 'freddie' to the allowed roles. Keep 'reviewer' (historical rows +
-- the seat-vs-occupant `reviewer:` attribution lineage). The constraint becomes
-- the union; VALID_ROLES (the app layer) and the DB constraint are realigned.

ALTER TABLE session_messages DROP CONSTRAINT IF EXISTS session_messages_role_check;

ALTER TABLE session_messages
  ADD CONSTRAINT session_messages_role_check
  CHECK (role IN ('user', 'assistant', 'system', 'reviewer', 'freddie', 'agent', 'external', 'system_agent'));
