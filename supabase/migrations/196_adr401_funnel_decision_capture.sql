-- 196: ADR-401 live-eval fix — admit 'capture' into the funnel_decision CHECK.
--
-- ADR-393 gave the capture lane its own execution_events stamp
-- (funnel_decision='capture', services/capture/lane.py) but the CHECK
-- constraint never gained the value, so EVERY capture-lane telemetry INSERT
-- has been silently rejected since the lane shipped (record_execution_event
-- swallows insert errors by design). Observed live 2026-07-03: capture-slack
-- fired, wrote raw, proposed its derive wake — and left zero execution_events
-- rows. This admits the value the code already writes.

ALTER TABLE execution_events
  DROP CONSTRAINT IF EXISTS execution_events_funnel_decision_check;

ALTER TABLE execution_events
  ADD CONSTRAINT execution_events_funnel_decision_check
  CHECK (
    funnel_decision IS NULL
    OR funnel_decision = ANY (ARRAY[
      'skip'::text,
      'tier_2_wait'::text,
      'tier_2_observe'::text,
      'escalate'::text,
      'mechanical'::text,
      'capture'::text
    ])
  );
