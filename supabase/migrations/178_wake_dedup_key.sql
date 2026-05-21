-- Migration 178 — Add wake_dedup_key column + partial unique index for
-- wake-proposal idempotency.
--
-- Closes the architectural gap surfaced by docs/observations/2026-05-21-
-- 005856-wake-duplication-audit/: the substrate_event walker's 30-minute
-- lookback re-discovered the same transition revision on every scheduler
-- tick (*/1 * * * *), producing up to 30 redundant Reviewer wakes per
-- single matched hook. The transition guard in _field_change_matches
-- correctly prevented re-firing on PRESERVING writes but did NOT dedupe
-- the same revision across multiple WALKER INVOCATIONS.
--
-- Fix shape per the observation folder: add an idempotency column on
-- execution_events that callers populate with a wake-source-specific
-- discriminator. The partial unique index makes the dedup contract
-- DB-enforced rather than application-enforced.
--
-- Semantics per wake source:
--
--   substrate_event   → revision_id (UUID of the workspace_file_versions
--                       row that triggered the hook match)
--   proposal_arrival  → proposal_id (UUID of the action_proposals row)
--   cron_tick         → NULL (idempotency lives at the tasks-table CAS
--                       layer per services/scheduling.py::claim_task_run;
--                       this column is unused for cron_tick)
--   addressed         → NULL (operator-initiated; the operator's HTTP
--                       request is the idempotency boundary)
--   manual_fire       → NULL (admin tool; audit-only; intentionally
--                       allows repeated fires)
--
-- The column is TEXT NULL — same shape as wake_source + funnel_decision
-- per migration 177. The partial unique index (WHERE wake_dedup_key
-- IS NOT NULL) lets NULL-carrying rows accumulate without conflict
-- while enforcing single-fire semantics on populated rows.
--
-- Population path: services/telemetry.py::record_execution_event gains
-- a wake_dedup_key kwarg; services/wake.py call sites pass the
-- discriminator on substrate_event + proposal_arrival final records.
-- Walkers consult this column via SELECT before submit_wake_proposal —
-- skip if a row with the same tuple already exists.
--
-- Race-window note: there is a theoretical race between the walker's
-- SELECT check and the wake's INSERT (the Reviewer's full LLM duration,
-- ~20-75s). In practice scheduler ticks at */1 cadence are well-
-- separated; this window is acknowledged in the walker code comment.
-- If observed races occur, the next iteration tightens with INSERT-on-
-- claim (a "claimed" sentinel row written before the Reviewer fires,
-- updated to final status afterward). This migration's partial unique
-- index supports either approach.
--
-- No new RLS policy needed — inherits from existing execution_events policy.

ALTER TABLE execution_events
    ADD COLUMN IF NOT EXISTS wake_dedup_key TEXT;

COMMENT ON COLUMN execution_events.wake_dedup_key IS
    'Wake-source-specific idempotency discriminator. For substrate_event '
    'this is the workspace_file_versions.id (UUID); for proposal_arrival '
    'this is the action_proposals.id (UUID); NULL for cron_tick / '
    'addressed / manual_fire which idempotency-gate at other layers. '
    'Partial unique index enforces single-fire semantics on populated '
    'rows. See docs/observations/2026-05-21-005856-wake-duplication-audit/.';

-- Partial unique index: enforce single-fire only for rows that carry
-- a dedup key. NULL-carrying rows (cron_tick / addressed / manual_fire)
-- accumulate freely.
CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_events_wake_dedup
    ON execution_events (user_id, wake_source, wake_dedup_key)
    WHERE wake_dedup_key IS NOT NULL;
