-- Migration 171 — ADR-265 D2: execution_events.shape → execution_events.mode
--
-- The `shape` column was added in migration 165 (ADR-250 Phase 2) as the 4-value
-- enum deliverable|accumulation|action|maintenance. Post-ADR-261 the output_kind
-- taxonomy dissolved; every dispatcher write since then has been the literal
-- constant "recurrence" with an explicit comment that shape is no longer a
-- discriminator. The post-ADR-263 cost discriminator is `recurrence.mode`
-- (judgment|mechanical) — judgment-mode wakes the Reviewer (LLM cost),
-- mechanical-mode runs deterministic Python (zero LLM cost).
--
-- This migration: add mode column, backfill historical rows to 'judgment'
-- (the pre-263 default; mechanical-mode dispatch postdates table creation),
-- then drop the dead shape column.

BEGIN;

-- Add mode column (nullable during backfill window inside this transaction).
ALTER TABLE execution_events
    ADD COLUMN mode text;

-- Backfill: every existing row predates ADR-263 mechanical-mode dispatch
-- (table created 2026-05-06, mechanical dispatch wired ~2026-05-08).
-- Treat all historical rows as judgment-mode.
UPDATE execution_events
SET mode = 'judgment'
WHERE mode IS NULL;

-- Tighten: make mode NOT NULL and constrain to the two valid values.
ALTER TABLE execution_events
    ALTER COLUMN mode SET NOT NULL,
    ADD CONSTRAINT execution_events_mode_check
        CHECK (mode IN ('judgment', 'mechanical'));

-- Drop the dead shape column. No live consumer reads it post-261; the
-- frontend's shapeLabel() mapping is being deleted in the same commit set.
ALTER TABLE execution_events
    DROP COLUMN shape;

COMMIT;
