-- Migration 177 — Add ADR-296 v2 wake-source + funnel-decision columns to
-- execution_events.
--
-- ADR-296 v2 reframes the Reviewer's invocation surface around two
-- architectural commitments:
--
--   D1 — Wake is event-driven and evaluation-gated. Multiple wake sources
--        (cron_tick, addressed, proposal_arrival, substrate_event,
--        manual_fire) contribute proposals to one evaluation gate (Tier 1
--        deterministic / Tier 2 cheap Haiku). The Reviewer fires only on
--        escalation.
--
--   D2 — The funnel produces one of five outcomes per wake proposal:
--        skip (Tier 1 declines), tier_2_wait / tier_2_observe (Tier 2
--        defers without escalating), escalate (full Reviewer cycle fires),
--        mechanical (mechanical-mode recurrence bypass — no Reviewer wake).
--
-- This migration adds the columns that will carry that taxonomy on every
-- execution_events row. Columns are TEXT NULL with CHECK constraints
-- enumerating the allowed values; NULL is permitted so rows predating this
-- migration remain valid and Session B can ship telemetry-additive without
-- forcing call-site population.
--
-- Session B (this migration + telemetry signature extension) ships the
-- substrate. Session C/D wires callers (services/wake.py becomes the
-- singular invocation gateway; services/wake_evaluation.py produces the
-- funnel decision; both populate these columns at write time).
--
-- See docs/adr/ADR-296-continuous-judgment-cycle.md and
-- docs/architecture/adr296-implementation-scope.md.
--
-- NULL semantics:
--   - rows predating this migration → both columns NULL
--   - Session B → telemetry accepts the kwargs but no caller populates yet,
--     so both columns remain NULL post-deploy until Session C/D
--   - Session C+D → every execution_events row carries wake_source +
--     funnel_decision (NULL becomes a regression signal)
--
-- No new RLS policy needed — inherits from existing execution_events policy.

ALTER TABLE execution_events
    ADD COLUMN IF NOT EXISTS wake_source TEXT,
    ADD COLUMN IF NOT EXISTS funnel_decision TEXT;

-- CHECK constraints enumerate the taxonomies. NULL allowed so pre-migration
-- rows + Session B rows (no caller populates yet) remain valid.

ALTER TABLE execution_events
    ADD CONSTRAINT execution_events_wake_source_check
    CHECK (
        wake_source IS NULL
        OR wake_source IN (
            'cron_tick',
            'addressed',
            'proposal_arrival',
            'substrate_event',
            'manual_fire'
        )
    );

ALTER TABLE execution_events
    ADD CONSTRAINT execution_events_funnel_decision_check
    CHECK (
        funnel_decision IS NULL
        OR funnel_decision IN (
            'skip',
            'tier_2_wait',
            'tier_2_observe',
            'escalate',
            'mechanical'
        )
    );

COMMENT ON COLUMN execution_events.wake_source IS
    'ADR-296 v2 D1 wake-source taxonomy. One of cron_tick | addressed | '
    'proposal_arrival | substrate_event | manual_fire. NULL for rows '
    'predating migration 177 and for Session B rows (telemetry accepts '
    'the kwarg as no-op; Session C/D wires services/wake.py to populate).';

COMMENT ON COLUMN execution_events.funnel_decision IS
    'ADR-296 v2 D2 funnel decision taxonomy. One of skip | tier_2_wait | '
    'tier_2_observe | escalate | mechanical. NULL for rows predating '
    'migration 177 and for Session B rows. Session C/D wires '
    'services/wake_evaluation.evaluate() to populate.';
