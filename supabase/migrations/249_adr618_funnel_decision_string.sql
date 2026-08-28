-- Migration 249 — ADR-618: 'string' joins the funnel_decision vocabulary.
--
-- THE SAME DEFECT AS MIGRATION 222, REPEATED VERBATIM. The strings lane
-- (ADR-569) meters each run as two execution_events rows
-- (string-sweep:{topic} mechanical + string-write:{topic} judgment), both
-- stamped funnel_decision='string' — the lane marker, exactly as capture
-- stamps 'capture' (migration 196) and radar stamped 'radar' (222). The
-- value was never added, so the check constraint DROPPED BOTH ROWS.
--
-- Observed live 2026-08-28 01:45Z, on the first production string run ever
-- executed: the run reached GitHub through the connector, landed
--   /workspace/inbound/github/kvkthecreator-yarnnnn/2026-08-28T01:45:25Z.md
--     (system:capture-github, revision_kind='observation')
-- and wrote the derivation
--   /workspace/operation/fundraising/application-copy-bank.md
--     (system:strings, revision_kind='derivation', derived_from=[the above])
-- — and recorded ZERO execution_events. Byte-for-byte the failure 222
-- describes: "the first standing sweep's derive landed its brief but lost
-- its ledger row".
--
-- Why it stayed invisible for both lanes: record_execution_event() never
-- raises (by design — telemetry must not fail a run), so the insert failure
-- is a log line, not an error the run can see. It logs [LEDGER-DROP] with
-- "UNRECORDED spend", which is exactly right and exactly unread until
-- someone greps for it. The lane's own output looks perfect: the file
-- updated, the schedule advanced, the desk said "Ran — the file was updated."
--
-- ⭐ The lesson worth carrying past this fix: a lane's ledger marker is part
-- of standing it up, not part of its telemetry polish. A new funnel_decision
-- value must ship WITH the lane that stamps it, or the lane spends silently.
-- Three lanes have now needed this migration; the vocabulary is a coupling
-- point between code and schema that nothing gates.
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
      'string'::text
    ])
  );

COMMENT ON CONSTRAINT execution_events_funnel_decision_check ON execution_events IS
  'Funnel outcome vocabulary: wake-funnel decisions (skip/tier_2_wait/tier_2_observe/escalate/mechanical) + lane markers (capture per ADR-393, radar per ADR-486, string per ADR-569/618). radar is retained: the lane is deleted (ADR-592) but its historical rows are not.';
