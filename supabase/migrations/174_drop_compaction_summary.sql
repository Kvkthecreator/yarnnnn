-- Migration 174 — ADR-221 Phase 2 follow-up: drop vestigial compaction_summary column.
--
-- ADR-067 Phase 3's in-session LLM compaction (40K-token threshold; Haiku
-- summary write) was replaced wholesale by filesystem-native conversation.md
-- (ADR-221 Commit C, 2026-04-26). The column has had zero live writers since
-- that commit landed.
--
-- Audit 2026-05-15 confirmed: zero live writers, zero live readers in
-- api/routes/, api/services/, api/agents/. Comment references in
-- api/routes/feed.py (lines 491, 720) explicitly called out the vestigial
-- state and named the column drop as the Phase 2 follow-up. This migration
-- ships that follow-up.
--
-- Singular Implementation discipline: filesystem-native conversation.md is the
-- single compaction substrate per ADR-221 Decision 3. This column drop closes
-- the residual dual-substrate possibility.

ALTER TABLE chat_sessions DROP COLUMN IF EXISTS compaction_summary;

COMMENT ON TABLE chat_sessions IS
    'Chat sessions. compaction_summary column dropped in migration 174 '
    '(ADR-221 Phase 2 follow-up) — filesystem-native conversation.md replaced '
    'in-session LLM compaction per ADR-067 Phase 3 sunset.';
