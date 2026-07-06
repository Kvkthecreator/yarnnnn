-- Migration 204: execution_events gains a model column (ADR-291 amendment,
-- surfaced by the ADR-408 D4 router spike, 2026-07-06).
--
-- The `model` kwarg to record_execution_event() previously fed ONLY the
-- rate lookup at write time — the ledger never recorded WHICH model ran an
-- invocation (the model_routing.py docstring claimed execution_events.model
-- existed; it did not). With seat-level routing (ADR-408 D4) and per-lane
-- model pinning (ADR-411), per-model spend legibility is load-bearing:
-- "what did the GPT-4o-mini lane cost this month" needs the column.
--
-- Additive + nullable: rows written before this migration stay NULL
-- (honest — the model that ran them was never recorded). No backfill.

ALTER TABLE execution_events ADD COLUMN IF NOT EXISTS model text;

COMMENT ON COLUMN execution_events.model IS
  'Model that ran the invocation (ledger_model form — bare model id, no provider prefix). NULL for rows predating migration 204. Feeds per-model spend legibility (ADR-408 D4 / ADR-411); cost_usd is computed from this + tokens at write time via compute_cost_usd_inclusive.';
