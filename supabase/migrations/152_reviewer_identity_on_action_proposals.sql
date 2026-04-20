-- Migration 152 — ADR-194 v2 Phase 2a: reviewer audit trail on action_proposals
--
-- Adds two nullable columns to action_proposals so every approve / reject
-- carries attribution for who (or what AI) filled the Reviewer seat, plus
-- a short reasoning summary for the proposal card UX.
--
-- Full reasoning text always lands in /workspace/review/decisions.md per
-- FOUNDATIONS v5.1 Axiom 0 (filesystem is the substrate). These columns
-- are narrow metadata — not a parallel substrate.
--
-- reviewer_identity format (human-readable, not an FK):
--   human:<user_id>                          — user clicked approve in UX
--   ai:<model-slug-and-version>              — future AI Reviewer (Phase 3)
--   impersonated:<admin_user_id>-as-<persona> — future admin persona (Phase 2c)
--
-- reviewer_reasoning is optional; kept short (<1KB typical). The Reviewer
-- writes full reasoning + structured decision context to decisions.md.

ALTER TABLE action_proposals
    ADD COLUMN IF NOT EXISTS reviewer_identity text,
    ADD COLUMN IF NOT EXISTS reviewer_reasoning text;

COMMENT ON COLUMN action_proposals.reviewer_identity IS
    'ADR-194 v2 Phase 2a: who filled the Reviewer seat. Format: "human:<user_id>" | "ai:<model-slug>" | "impersonated:<admin-user_id>-as-<persona-slug>". NULL for legacy rows written before Phase 2a.';

COMMENT ON COLUMN action_proposals.reviewer_reasoning IS
    'ADR-194 v2 Phase 2a: brief reasoning for proposal-card UX. Full reasoning + decision context written to /workspace/review/decisions.md per Axiom 0.';
