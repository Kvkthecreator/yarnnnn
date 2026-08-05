-- 236 — ADR-495 D1/D2 repair: the creator reads the conversation it creates.
--
-- THE DEFECT. Every lane creation failed in production with
--   postgrest 42501: new row violates row-level security policy
--                     for table "chat_sessions"
-- raised at routes/lanes.py:450 (the `.insert(row).execute()`), which broke
-- Studio's authoring lane ("Could not create the authoring lane."), the Docs
-- lane, and plain new chats alike — the whole lane surface, not one app.
--
-- The INSERT was never the thing denied. Proven by falsification against the
-- live database (2026-08-05): the SAME insert as the SAME principal succeeds
-- without RETURNING and fails with it. PostgREST always returns the created
-- row, so the write is followed by a SELECT-visibility check in the same
-- statement — and migration 228's SELECT policy answers, for a `lane` row,
-- `is_conversation_participant(id)`. The cast row that would satisfy it is
-- added AFTER the insert returns (routes/lanes.py:465, `add_participant`).
-- The creator therefore had to already be a participant in order to create the
-- conversation that makes them one: a genuine ordering deadlock, and one no
-- amount of application reordering fixes cleanly (the id does not exist to
-- attach a cast row to until the insert lands).
--
-- WHY THIS IS A REPAIR, NOT A NEW RULE. Migration 228 states the intent in its
-- own header (§2): "the cast reads; the creator still owns", and "the creator's
-- own reach is preserved below, as the N=1 case of the cast rule". Its
-- `session_messages` policies implement exactly that, ORing `s.user_id =
-- auth.uid()` into the lane arm in three places (the SELECT, the INSERT, and
-- the truncate gate). The `chat_sessions` SELECT policy is the ONE site where
-- that clause was omitted. This migration restores the omission; it does not
-- widen the model. ADR-495 D2's promise (participants, not workspace members at
-- large) is untouched — a non-creator non-participant still sees nothing.
--
-- FALSIFIED BEFORE SHIPPING (each run in a ROLLBACK-only transaction against
-- production, as the acting principal, with the candidate policy applied):
--   1. The creator's own lane INSERT ... RETURNING now succeeds, and migration
--      203's BEFORE INSERT trigger fills workspace_id as designed.
--   2. NO LEAK: a principal who is neither creator nor cast sees 0 of another
--      user's lane rows (the clause is `user_id = auth.uid()`, not a widening).
--   3. THE GRANT BOUND STILL BINDS: a lane the acting principal CREATED but
--      whose workspace they are not a member of returns 0 rows. The revocation
--      semantics migration 228 built (a revoked member loses reach on their
--      next statement even if their participant row lingers) survive intact —
--      the creator clause is ANDed under the same workspace-grant test, never
--      beside it.
--
-- Singular implementation: the 228 policy is REPLACED, not supplemented — two
-- policies answering "may I read this conversation" is the dual approach 228
-- itself deleted the migration-008 policy to avoid.

DROP POLICY IF EXISTS "Cast reads the conversation" ON public.chat_sessions;

CREATE POLICY "Cast reads the conversation"
  ON public.chat_sessions
  FOR SELECT
  TO authenticated
  USING (
    CASE WHEN session_type = 'lane' THEN
      -- ADR-495 D2: participants, full stop — plus the creator as the N=1 case
      -- of that rule (228's own framing). The creator clause is what lets the
      -- INSERT ... RETURNING that BIRTHS the conversation read its own row back,
      -- one statement before `add_participant` makes the cast membership true.
      (
        user_id = auth.uid()
        OR public.is_conversation_participant(id)
      )
      AND (
        -- Unchanged from 228: a workspace-bound conversation additionally
        -- requires the grant, so a revoked member loses reach on their next
        -- statement even if their participant row lingers. The IS NULL arm keeps
        -- a migration-203 trigger regression degrading to cast-only rather than
        -- locking out.
        workspace_id IS NULL
        OR public.is_workspace_member(workspace_id)
      )
    ELSE
      -- Every other session kind (thinking_partner, and whatever the wake /
      -- narrative machinery adds next) is the creator's own. Byte-identical to
      -- the migration-008 rule 228 replaced.
      user_id = auth.uid()
    END
  );

COMMENT ON POLICY "Cast reads the conversation" ON public.chat_sessions IS
  'ADR-495 D2 + migration 236: a lane row is readable by its cast OR its '
  'creator, bounded by the workspace grant. The creator clause is required for '
  'INSERT ... RETURNING to see the row it just created (the cast row is added '
  'immediately after, in routes/lanes.py::create_lane).';
