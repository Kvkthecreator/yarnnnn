-- Migration 222 — ADR-486 R0: 'radar' joins the funnel_decision vocabulary.
--
-- The radar lane meters each sweep as two execution_events rows
-- (radar-sweep:{topic} mechanical + radar-brief:{topic} judgment), both
-- stamped funnel_decision='radar' — the lane marker, exactly as the capture
-- lane stamps 'capture' (migration 196). Without this value the check
-- constraint drops both rows (observed live 2026-07-24 05:31Z: the first
-- standing sweep's $0.019 derive landed its brief but lost its ledger row —
-- a one-ledger violation this migration closes).
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
      'radar'::text
    ])
  );

COMMENT ON CONSTRAINT execution_events_funnel_decision_check ON execution_events IS
  'Funnel outcome vocabulary: wake-funnel decisions (skip/tier_2_wait/tier_2_observe/escalate/mechanical) + lane markers (capture per ADR-393, radar per ADR-486).';
