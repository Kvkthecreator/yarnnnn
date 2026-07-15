-- 216 — W0: the falsifier join key (ADR-457 D8, sequenced by ADR-460 §8)
--
-- THE GAP THIS CLOSES
-- D8 declares three falsifiers "all readable from execution_events + session
-- counts, no new telemetry system". Verified 2026-07-16: true for two, false
-- for one. Every chat turn AND every Studio bound-lane turn writes
-- slug="lane" (55 rows, identical shape) — the ledger cannot tell the two
-- surfaces apart, so falsifier 1 ("chat is used only as a command line") is
-- not measurable. The fact EXISTS one table over:
-- chat_sessions.context_metadata->'lane'->>'artifact_path' is the
-- discriminator (ADR-440 D3: a lane with a binding is a studio lane) — but
-- execution_events has no session/lane id, so the two cannot be joined.
-- (agent_run_id exists but lanes never write it; overloading it would make
-- two concepts share a column — the dilution ADR-460 just removed.)
--
-- WHAT THIS IS
-- The join key. Store the IDENTITY (which session), derive the CLASS (which
-- surface) at read time — DP29 derived-never-stored. A `surface` enum column
-- would store a derived fact and invite the two copies to disagree.
--
-- WHAT THIS IS NOT
-- Not a second ledger. ADR-396's DOUBLE-CHARGE INVARIANT holds byte-for-byte:
-- get_effective_balance still sums ONE ledger; this adds a nullable FK to the
-- existing row and touches no cost path.
--
-- BACKFILL: NONE, DELIBERATELY. The 55 pre-existing lane rows stay NULL and
-- are honestly unclassifiable — they predate the instrument. A backfilled
-- guess would fabricate the very baseline this instrument exists to protect
-- (falsifier 2 is only meaningful against a TRUE pre-settle baseline).
-- NULL reads as "recorded before W0", which is a true statement.
--
-- Spec: docs/analysis/w0-falsifier-instrumentation-spec-2026-07-16.md

ALTER TABLE execution_events
  ADD COLUMN IF NOT EXISTS session_id uuid NULL;

COMMENT ON COLUMN execution_events.session_id IS
  'W0/ADR-457 D8: the chat_sessions row this metered turn served, when the '
  'invocation came from a session-backed surface (lanes today). NULL for '
  'non-session invocations (recurrences, sweeps, capture) and for rows '
  'recorded before migration 216 — never backfilled, never guessed. The '
  'surface class (think / make / derive / steward) is DERIVED from the '
  'joined session''s lane binding at read time (DP29), never stored here.';

-- The falsifier read is a per-workspace window scan joining to sessions.
-- Partial: only session-backed rows are ever joined, and they are the
-- minority of the ledger.
CREATE INDEX IF NOT EXISTS idx_execution_events_session
  ON execution_events (workspace_id, session_id, created_at DESC)
  WHERE session_id IS NOT NULL;
