-- Migration 151 — Drop legacy semantic-content tables under FOUNDATIONS v6.0 Axiom 1 (Substrate).
-- ADR-195 v2: drop action_outcomes (superseded by /workspace/context/{domain}/_performance.md).
-- ADR-196:   drop user_memory     (superseded by /workspace/*.md since ADR-156).
--
-- Both tables held semantic content in DB rows, which Axiom 1 (Substrate) forbids:
-- "semantic content lives in the filesystem; DB rows are scheduling indexes,
-- audit ledgers, credentials, or ephemeral queues — nothing else."
-- (Originally framed under v5.1 Axiom 0; v6.0 renumbers the filesystem principle as Axiom 1.)
--
-- Safety:
-- * action_outcomes: zero rows in production (v1 reconciler only shipped 2026-04-19
--   and Commit 2 of this cycle redirected writes to _performance.md before the
--   daily back-office cycle completed). No data loss.
-- * user_memory: dead-write since ADR-156 (2026-04-01). Migration 102 backfilled
--   existing rows into workspace_files. No data loss.
--
-- CASCADE on both drops — any orphaned FK references (proposals, purge cascades)
-- are removed alongside the tables. The FKs that existed (action_outcomes ->
-- action_proposals, action_outcomes -> auth.users, user_memory -> auth.users)
-- are one-way references INTO these tables; dropping the tables cannot orphan
-- anything upstream.

DROP TABLE IF EXISTS action_outcomes CASCADE;
DROP TABLE IF EXISTS user_memory CASCADE;
