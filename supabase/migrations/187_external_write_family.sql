-- 187_external_write_family.sql
-- ADR-307 Phase 5 (2026-06-19) — extend the action_proposals family CHECK to
-- include 'external-write'.
--
-- Migration 181 created `action_proposals_family_check` permitting only
-- ('capital', 'substrate') — the two families that existed then. ADR-307 Phase 5
-- added the 'external-write' family in code (audience-addressing Slack/Notion/
-- email sends — the kernel-universal write_slack/write_notion path) but did NOT
-- migrate the constraint. Consequence: when a specialist's audience-write hits
-- the uniform gate and the gate QUEUEs it, `enqueue_gated_action`'s INSERT with
-- family='external-write' was rejected by the CHECK → the queue silently failed
-- (tool returned queue_failed, no proposal row). Surfaced by the live E2E probe
-- on the yarnnn-author workspace (Slack + Notion connected 2026-06-19): the
-- specialist called platform_slack_send_to_channel but zero external-write
-- proposals were ever created — the unit gates mock the insert and never hit
-- the constraint.
--
-- This is the schema half of the Phase 5 family addition (the code half shipped
-- in f8b57a1; this constraint extension makes the queue path actually work).

ALTER TABLE action_proposals
    DROP CONSTRAINT IF EXISTS action_proposals_family_check;

ALTER TABLE action_proposals
    ADD CONSTRAINT action_proposals_family_check
        CHECK (family IN ('capital', 'substrate', 'external-write'));

COMMENT ON COLUMN action_proposals.family IS
    'ADR-307: queue family discriminator (capital | substrate | external-write). The cockpit renderer dispatches on it (capital → order-ticket; substrate → diff; external-write → effect preview). decision_context is family-shaped.';
COMMENT ON COLUMN action_proposals.decision_context IS
    'ADR-307: family-shaped operator decision context. capital: {rationale, expected_effect, reversibility, risk_warnings}. substrate: {diff, message}. external-write: {effect:{channel|to|page,...,preview}, gate_reason}.';
