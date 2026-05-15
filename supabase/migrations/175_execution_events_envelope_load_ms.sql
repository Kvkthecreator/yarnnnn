-- Migration 175 — Add envelope_load_ms observability column on execution_events.
--
-- ADR-276 + post-implementation hardening (2026-05-15):
-- `load_reviewer_governance_envelope` (services/reviewer_envelope.py) is the
-- single canonical pre-load helper for the Reviewer's governance + domain
-- substrate. Called at every reactive wake (services/invocation_dispatcher.py)
-- and every addressed turn (routes/feed.py). Internally it does 9 parallel
-- workspace_files reads via asyncio.gather + 1 signal_files compact summary.
--
-- This is the dominant DB-read pattern per Reviewer wake. Today's
-- execution_events.duration_ms captures wall-clock for the whole invocation
-- (envelope + LLM rounds + tool calls). Isolating envelope load gives us:
--   - empirical answer to "is envelope assembly a measurable fraction of
--     wake latency under production load?"
--   - early-warning when envelope cost grows (e.g. ADR-280 workspace guide
--     adds frontmatter reads)
--   - tuning input for future caching / batching decisions
--
-- NULL semantics:
--   - reactive Reviewer wakes (recurrence-fire) → column populated
--   - mechanical mode recurrences (no Reviewer) → column NULL
--   - addressed turns → don't record execution_events (chat path); envelope
--     timing for addressed turns is logged to structured logger only
--
-- No new RLS policy needed — inherits from existing execution_events policy.

ALTER TABLE execution_events
    ADD COLUMN IF NOT EXISTS envelope_load_ms int;

COMMENT ON COLUMN execution_events.envelope_load_ms IS
    'Wall-clock duration in ms for load_reviewer_governance_envelope() call '
    '(ADR-276). NULL for mechanical-mode recurrences (no Reviewer wake) and '
    'rows predating migration 175. Isolates the dominant Reviewer DB-read '
    'pattern from total duration_ms for capacity tuning.';
