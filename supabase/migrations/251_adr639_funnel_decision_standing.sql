-- Migration 251 — ADR-639 D3: 'standing' joins the funnel_decision vocabulary.
--
-- The maintained-file lane is renamed from strings to STANDING WORK (ADR-639):
-- from the deploy that carries the rename, its two ledger rows per run
-- (standing-sweep:{topic} mechanical + standing-write:{topic} judgment) stamp
-- funnel_decision='standing'.
--
-- ⭐ THE VALUE SHIPS BEFORE THE CODE — migration 249's lesson, applied in the
-- order it teaches. record_execution_event() never raises (telemetry must not
-- fail a run), so a deploy that stamps a value this CHECK does not know loses
-- every ledger row SILENTLY ([LEDGER-DROP] in a log nobody greps, a run that
-- looks perfect from the surface). Three lanes have now needed this migration
-- (capture 196 · radar 222 · string 249); this one is applied first, then the
-- code deploys, so there is no window in which the lane spends unrecorded.
--
-- 'string' is RETAINED: 18 historical rows carry it (measured 2026-09-04) and
-- the ledger is never rewritten. 'radar' likewise (migration 249's own note).
--
-- No BEGIN/COMMIT wrapper (the migration-self-commits lesson): single
-- statement pair, atomic enough.

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
      'capture'::text,
      'radar'::text,
      'string'::text,
      'standing'::text
    ])
  );

COMMENT ON CONSTRAINT execution_events_funnel_decision_check ON execution_events IS
  'Funnel outcome vocabulary: wake-funnel decisions (skip/tier_2_wait/tier_2_observe/escalate/mechanical — the funnel is deleted, ADR-632; values retained for history) + lane markers (capture per ADR-393, radar per ADR-486, string per ADR-569/618, standing per ADR-639). radar and string are retained: their lanes are deleted/renamed but their historical rows are not.';
