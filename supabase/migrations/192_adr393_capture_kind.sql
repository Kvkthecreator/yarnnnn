-- Migration 192 — ADR-393: capture-lane scheduling kind on the tasks index.
--
-- The `tasks` table is the thin, reconstructable scheduling index (ADR-231 D4).
-- ADR-393 gives the capture lane its own declarations (_captures.yaml) but
-- REUSES this one index (the decision: one index, one CAS-claim mechanism, one
-- market-context resolver — a sibling table would duplicate all of it). A
-- `kind` discriminator routes rows:
--
--   kind = 'judgment'  →  a recurrence (wake funnel serves it; services.wake)
--   kind = 'capture'   →  a capture declaration (capture lane runs it; services.capture)
--
-- The wake path queries kind IN ('judgment', NULL); the capture drainer queries
-- kind = 'capture'. NULL is treated as 'judgment' for backward compatibility
-- with rows materialized before this migration (there are no capture rows yet,
-- so every existing row is a recurrence).
--
-- Fully reconstructable per Axiom 1: materialize_scheduling_index (recurrences)
-- and materialize_capture_index (captures) rebuild the correct kind from the
-- YAML source at any tick. This column is a projection convenience, not truth.

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS kind text NOT NULL DEFAULT 'judgment';

-- Partial index for the capture drainer's due-query hot path.
CREATE INDEX IF NOT EXISTS idx_tasks_capture_due
    ON tasks (next_run_at)
    WHERE kind = 'capture' AND status = 'active';

COMMENT ON COLUMN tasks.kind IS
    'ADR-393: judgment (recurrence → wake funnel) | capture (declaration → capture lane). NULL/absent treated as judgment.';
