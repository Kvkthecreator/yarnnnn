-- Migration 160: widen session_messages.role CHECK to include 'reviewer'
--
-- Context: unified chat-thread work (Option A, 2026-04-23 post-LAYER-MAPPING).
-- Under ADR-212's sharp Agent/Orchestration mapping, the Reviewer is an Agent
-- (judgment-bearing). Reviewer verdicts should surface in the same timeline
-- the operator uses to talk to YARNNN, not only on the dedicated /review page.
--
-- Today the role constraint is ('user', 'assistant', 'system'). Verdicts
-- write to action_proposals + /workspace/review/decisions.md only; operator
-- must context-switch to /review to see them.
--
-- This migration widens the constraint to include 'reviewer', enabling
-- write_reviewer_message() in the backend to emit verdict cards into the
-- active chat session. /review remains the dedicated audit stream.
--
-- Non-destructive: existing rows keep their values; constraint addition
-- widens the allowed set. No backfill required.

BEGIN;

-- Drop the existing constraint; recreate with the widened enum.
ALTER TABLE session_messages DROP CONSTRAINT IF EXISTS session_messages_role_check;

ALTER TABLE session_messages
  ADD CONSTRAINT session_messages_role_check
  CHECK (role IN ('user', 'assistant', 'system', 'reviewer'));

COMMENT ON COLUMN session_messages.role IS
  'Sender class: user (operator), assistant (YARNNN Agent), system (workspace event), reviewer (Reviewer Agent verdict on a proposal). Added reviewer 2026-04-23 per unified-chat-thread design.';

COMMIT;
