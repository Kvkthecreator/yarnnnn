-- Migration 180 — ADR-298 Phase 5 cleanup: drop execution_events.wake_dedup_key
-- column + partial unique index.
--
-- ADR: docs/adr/ADR-298-reviewer-wake-queue-and-pace.md (Phase 5)
--
-- Background. Migration 178 added wake_dedup_key + the partial unique index
-- (user_id, wake_source, wake_dedup_key) WHERE wake_dedup_key IS NOT NULL
-- on execution_events as an idempotency gate for the substrate_event walker's
-- 30-minute lookback re-discovering the same matched transition revision
-- across scheduler ticks.
--
-- ADR-298 cutover (migration 179 + commit 2dfdb98, 2026-05-22) replaced
-- that gate with the wake_queue table's UNIQUE (user_id, wake_source,
-- dedup_key) constraint enforced at INSERT time per ADR-298 D6. Cross-
-- source dedup now lives at the queue layer; execution_events is no
-- longer the dedup surface for wakes.
--
-- Phase 5 cleanup (this migration + commits in services/wake.py +
-- services/telemetry.py + services/wake_sources/substrate_event.py):
--   1. Walker stops doing the pre-SELECT against execution_events
--      (substrate_event.py: _already_fired_for helper DELETED, caller
--      simplified to unconditional submit_wake_proposal).
--   2. Reviewer-invocation bodies stop stamping wake_dedup_key on
--      execution_events rows (wake.py: 4 record_execution_event call
--      sites cleaned).
--   3. record_execution_event drops the kwarg (telemetry.py).
--   4. Drop the column + its partial unique index (this migration).
--
-- Per ADR-298 §"Singular Implementation": no parallel dedup path. The
-- wake_queue layer is the singular dedup gate post-cutover.
--
-- Idempotent: IF EXISTS guards on both the index drop and column drop
-- so this migration can re-run safely against a database that already
-- had migration 180 applied.

DROP INDEX IF EXISTS idx_execution_events_wake_dedup;

ALTER TABLE execution_events
    DROP COLUMN IF EXISTS wake_dedup_key;
