-- Migration 179 — ADR-298 Phase 1: wake_queue table for single-lane
-- Reviewer execution + two-lane (paced + live) drain + cross-source dedup.
--
-- ADR: docs/adr/ADR-298-reviewer-wake-queue-and-pace.md
--
-- Per ADR-298 D2 (Critical classification per Axiom 1): the queue is
-- **transient compute + deterministic enforcement, not authoritative state**.
-- Modeled on the `tasks` scheduling-index precedent (ADR-231 D4). The
-- queue is mechanically reconstructable from filesystem state + DB
-- telemetry at every moment — no semantic truth lives in this table
-- that doesn't already exist in workspace_files + execution_events +
-- session_messages + action_proposals.
--
-- Per ADR-298 D3 (Two lanes): every row is in either the `paced` lane
-- (cron_tick judgment recurrences, drained at operator-declared pace rate)
-- or the `live` lane (addressed, substrate_event, manual_fire,
-- proposal_arrival — drained as fast as single-in-flight allows). Both
-- lanes share the single-in-flight-per-workspace constraint.
--
-- Per ADR-298 D6 (Cross-source dedup at queue layer): UNIQUE constraint
-- on (user_id, wake_source, dedup_key) replaces ADR-272's
-- execution_events.wake_dedup_key location. Per-source dedup-key derivation:
--   substrate_event  → revision_id (UUID)
--   cron_tick        → '<slug>:<scheduled_minute_iso>'
--   addressed        → message_id (UUID)
--   proposal_arrival → proposal_id (UUID)
--   manual_fire      → NULL (operator explicitly bypasses dedup)
--
-- Phase 1 scope (this migration): table + indexes + RLS. No production
-- callers yet — service helpers added in api/services/wake_queue.py.
-- Production cutover lands in Phase 3 per the ADR's implementation
-- plan.

CREATE TABLE IF NOT EXISTS wake_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    wake_source TEXT NOT NULL,
    lane TEXT NOT NULL,
    slug TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    dedup_key TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    enqueued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_at TIMESTAMPTZ,
    locked_by TEXT,
    completed_at TIMESTAMPTZ,
    execution_event_id UUID,

    CONSTRAINT wake_queue_wake_source_check
        CHECK (wake_source IN (
            'cron_tick', 'addressed', 'substrate_event',
            'proposal_arrival', 'manual_fire'
        )),
    CONSTRAINT wake_queue_lane_check
        CHECK (lane IN ('paced', 'live')),
    CONSTRAINT wake_queue_status_check
        CHECK (status IN (
            'pending', 'locked', 'completed', 'failed', 'dropped'
        )),
    -- ADR-298 D6: cross-source dedup. Partial unique — NULL dedup_key
    -- (manual_fire) bypasses idempotency by design.
    CONSTRAINT wake_queue_dedup_unique
        UNIQUE (user_id, wake_source, dedup_key)
);

COMMENT ON TABLE wake_queue IS
    'ADR-298 — Reviewer wake queue. Single-lane execution per workspace, '
    'two-lane drain (paced + live), cross-source dedup at insert time. '
    'Classified as transient compute per FOUNDATIONS Axiom 1: '
    'reconstructable from filesystem + DB substrate at every moment. '
    'See ADR-298 D2 + Scenario L.';

COMMENT ON COLUMN wake_queue.wake_source IS
    'One of cron_tick | addressed | substrate_event | proposal_arrival | '
    'manual_fire. Mirrors execution_events.wake_source taxonomy.';

COMMENT ON COLUMN wake_queue.lane IS
    'paced | live. paced = cron_tick judgment recurrences, drained at '
    'operator-declared pace rate. live = everything else, drained as '
    'fast as single-in-flight allows. Both lanes share the single-in-'
    'flight constraint per workspace.';

COMMENT ON COLUMN wake_queue.dedup_key IS
    'Per-source idempotency discriminator. substrate_event=revision_id; '
    'cron_tick=<slug>:<scheduled_minute_iso>; addressed=message_id; '
    'proposal_arrival=proposal_id; manual_fire=NULL (intentional bypass). '
    'UNIQUE (user_id, wake_source, dedup_key) enforces cross-source '
    'dedup at insert time. NULL allowed for manual_fire only.';

COMMENT ON COLUMN wake_queue.status IS
    'pending → locked → completed (happy path). Transitions on failure: '
    'pending|locked → failed (Reviewer execution failure). pending → '
    'dropped (pace-exhausted drop, manual GC, etc).';

COMMENT ON COLUMN wake_queue.locked_at IS
    'Set when scheduler instance acquires the row for execution. Pairs '
    'with locked_by (scheduler instance ID). Stale-lock reclaim: another '
    'scheduler instance can reclaim if locked_at < now() - threshold '
    '(threshold ≈ 2× p95 of execution_events.duration_ms per ADR-298 '
    '§8). Scenario J.';

COMMENT ON COLUMN wake_queue.execution_event_id IS
    'FK link to the execution_events row written when this wake actually '
    'ran. Populated by the drainer after Reviewer execution completes. '
    'Provides audit pairing: every queue entry that reaches completed '
    'has a matching execution_events row.';

-- Hot-path index for drainer "next pending wake to dispatch" query.
-- Partial index on pending rows only — completed/failed/dropped rows
-- accumulate but are not scanned by the drainer.
CREATE INDEX IF NOT EXISTS idx_wake_queue_pending_drain
    ON wake_queue (user_id, lane, enqueued_at)
    WHERE status = 'pending';

-- Index for stale-lock reclaim sweeps (drainer crash recovery, Scenario J).
CREATE INDEX IF NOT EXISTS idx_wake_queue_locked_reclaim
    ON wake_queue (locked_at)
    WHERE status = 'locked';

-- Index for GC sweep (completed rows older than 7d, per ADR-298 D2).
CREATE INDEX IF NOT EXISTS idx_wake_queue_completed_gc
    ON wake_queue (completed_at)
    WHERE status IN ('completed', 'failed', 'dropped');

-- RLS — service role only. The queue is transient compute, not operator-
-- readable substrate (per ADR-298 D2). Operators read configuration
-- (yaml files), outcomes (feed + execution_events), and watch-state
-- (standing_intent.md) — not the queue itself.
ALTER TABLE wake_queue ENABLE ROW LEVEL SECURITY;

CREATE POLICY wake_queue_service_role_only ON wake_queue
    FOR ALL
    TO public
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
