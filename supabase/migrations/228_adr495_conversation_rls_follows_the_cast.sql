-- 228 — A conversation is readable by its CAST (ADR-495 D2), enforced in the DB.
--
-- THE HOLE THIS CLOSES. `chat_sessions` / `session_messages` RLS has said
-- `user_id = auth.uid()` since migration 008 — the row belongs to its CREATOR.
-- That policy predates conversations having a cast (ADR-495, migration 226), so
-- a member correctly cast into a conversation could not see it: their list came
-- back empty, the transcript 404'd, and every application-level check passed.
--
-- ADR-502 §6a shipped the unblock in the APPLICATION layer — conversation reads
-- route through `_cast_read_client` (the service client, RLS bypassed) with the
-- cast + acting-workspace checks done in Python first. That works and is
-- honestly documented, but it leaves the database unable to answer the question
-- itself: 20 of `routes/lanes.py`'s 24 queries run with RLS off, so the ENTIRE
-- read binding is application code. One forgotten `.eq("workspace_id", ws)` and
-- there is nothing underneath.
--
-- Migration 227 already argued this exact call and chose the policy over the
-- callers ("make the table tell the truth to any authorized reader"), as did 221
-- before it. Same call here.
--
-- WHY NOT `is_workspace_member` — THE ONE PLACE THIS DIVERGES FROM 227.
-- 227's ledgers (execution_events, activity_log, tasks) are workspace-wide
-- facts: any member may read them. A CONVERSATION IS NOT. ADR-495 D2 is
-- explicit — "readable by its participants. Full stop. Not by workspace
-- grant-holders at large." A workspace member who is not in the cast must see
-- nothing. So this migration introduces its own predicate, `is_conversation_
-- participant`, and the workspace grant is an ADDITIONAL bound, not the test.
--
-- SPECIES-BLIND (ADR-495 D3 / ADR-405 §5). The predicate asks one question —
-- "is this principal in the cast, and from which turn?" — and asks it of a
-- `principal_id`, which only humans carry as an auth identity. It does NOT
-- branch on `member_kind` to decide access: the human filter is a JOIN KEY
-- (an Agent has no `auth.uid()` to match; Agents reach substrate through the
-- service client, never through a JWT), not a class test. There is no code path
-- here where being an Agent grants or denies anything.
--
-- THE WINDOW IS ENFORCED HERE TOO (ADR-495 D2). `session_messages` filters on
-- `sequence_number >= visible_from_sequence`, so a participant invited at "from
-- now" cannot read earlier turns even with a raw JWT and a hand-written query.
-- Until now that was an application promise at four call sites (and it leaked at
-- four more — see commit 68b12a5); now it is the table's own answer.
--
-- WRITES. Two policies, both narrow: a participant may INSERT a turn into a
-- conversation they are in, and the creator keeps full control of the session
-- row. No UPDATE/DELETE for participants on `session_messages` — a transcript is
-- append-only (ADR-406's appender rule), and the edit-and-resend truncate is a
-- service-client act gated by the author check in `routes/lanes.py`.

BEGIN;

-- ── 0. Heal the castless conversations BEFORE the policy binds ──────────────
-- Live read 2026-07-30: 7 `lane` rows have ZERO cast rows — all created
-- 2026-07-29 (the ADR-495 rollout day, before ADR-500's create-path rollback
-- landed) and all with 0 turns: abandoned shells. Under a cast-based policy a
-- castless conversation is invisible TO EVERYONE, so leaving them would silently
-- strand rows the application currently self-heals (`_get_lane`'s creator
-- fallback). Heal them here instead of deleting: the creator is always a
-- participant, which is the same rule the application applies, and healing is
-- reversible in a way that DELETE is not.
INSERT INTO conversation_members
  (conversation_id, workspace_id, member_kind, principal_id, visible_from_sequence, invited_by)
SELECT s.id, s.workspace_id, 'human', s.user_id, 0, s.user_id
FROM chat_sessions s
WHERE s.session_type = 'lane'
  AND NOT EXISTS (
    SELECT 1 FROM conversation_members m WHERE m.conversation_id = s.id
  )
ON CONFLICT DO NOTHING;

-- ── 1. The predicate: is the caller in this conversation's cast? ────────────
-- SECURITY DEFINER so a policy on `session_messages` may consult
-- `conversation_members` (which is service-role-only) without the caller
-- needing reach into it, and so it cannot recurse through another policy.
--
-- NOTE the cast: `conversation_members.principal_id` is `uuid` while
-- `principal_grants.principal_id` is `text` (the ADR-373 open-principal-set
-- shape — an Agent slug is not a uuid). `auth.uid()` is uuid, so this one
-- compares uuid-to-uuid directly; `is_workspace_member` does the ::text cast on
-- its own side. Getting this backwards silently matches nothing.
CREATE OR REPLACE FUNCTION public.is_conversation_participant(p_conversation_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.conversation_members m
    WHERE m.conversation_id = p_conversation_id
      AND m.member_kind = 'human'
      AND m.principal_id = auth.uid()
  );
$$;

COMMENT ON FUNCTION public.is_conversation_participant(uuid) IS
  'ADR-495 D2 — true if the calling user holds a participant row in this '
  'conversation. Membership IS read permission; this is the authorization '
  'primitive, mirrored from services/conversation_cast.py::visibility_floor. '
  'The member_kind filter is a JOIN KEY (an Agent has no auth.uid()), never a '
  'species test — ADR-405 §5. SECURITY DEFINER because conversation_members is '
  'service-role-only. Migration 228.';

-- The window: from which turn ordinal may the caller read? NULL = not in the
-- cast (so a NULL comparison in a policy is false, which fails CLOSED).
CREATE OR REPLACE FUNCTION public.conversation_visibility_floor(p_conversation_id uuid)
RETURNS integer
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT m.visible_from_sequence
  FROM public.conversation_members m
  WHERE m.conversation_id = p_conversation_id
    AND m.member_kind = 'human'
    AND m.principal_id = auth.uid()
  LIMIT 1;
$$;

COMMENT ON FUNCTION public.conversation_visibility_floor(uuid) IS
  'ADR-495 D2 — the caller''s visibility window in this conversation, or NULL '
  'when they are not in the cast. Enforced by the session_messages SELECT '
  'policy so the window holds against a raw JWT, not only at the four '
  'application read sites. Migration 228.';

REVOKE ALL ON FUNCTION public.is_conversation_participant(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.conversation_visibility_floor(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_conversation_participant(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.conversation_visibility_floor(uuid) TO authenticated;

-- ── 2. chat_sessions — the cast reads; the creator still owns ───────────────
-- SINGULAR IMPLEMENTATION: the migration-008 `FOR ALL` policy is REPLACED, not
-- supplemented. Leaving it would mean two policies answering "may I read this
-- conversation" with different rules — exactly the dual approach that let the
-- creator-scoped assumption survive ADR-495. The creator's own reach is
-- preserved below, as the N=1 case of the cast rule (migration 226 backfilled a
-- participant row for every pre-existing conversation, and §0 above healed the
-- stragglers), plus an explicit clause on the write policies so a session row
-- is never orphaned from its owner.
DROP POLICY IF EXISTS "Users own their chat sessions" ON public.chat_sessions;

-- READ: the cast, bounded by the workspace grant. Both clauses are required —
-- cast membership is the ADR-495 rule, and the grant bound means a revoked
-- member loses reach on their next statement even if their participant row
-- lingers (the same revocation semantics workspace_files has).
-- ONLY `lane` rows carry a cast. `chat_sessions` is a workspace-wide substrate
-- object that CHAT HAPPENS TO USE (ADR-495 D4 chose it for exactly that reason:
-- 87 references across 25 non-test files — narrative, working memory, session
-- continuity, wake queue, MCP, purge). The steward rail's `thinking_partner`
-- sessions are the live proof: 13 rows, ZERO cast rows, read through the USER
-- client on `user_id = auth.uid()` (routes/feed.py:1382). A cast-only policy
-- would have made the steward conversation unreadable — a whole-feature
-- blackout, caught by reading the table before trusting the ADR's noun.
--
-- So the rule is scoped to the object that actually has a cast, and the creator
-- rule survives for everything else. This is not two competing answers to one
-- question (the thing §2 deletes the 008 policy to avoid) — it is one answer per
-- KIND of session row, with `session_type` as the discriminator.
CREATE POLICY "Cast reads the conversation"
  ON public.chat_sessions
  FOR SELECT
  TO authenticated
  USING (
    CASE WHEN session_type = 'lane' THEN
      -- ADR-495 D2: participants, full stop. Not workspace members at large.
      public.is_conversation_participant(id)
      AND (
        -- A workspace-bound conversation additionally requires the grant, so a
        -- revoked member loses reach on their next statement even if their
        -- participant row lingers. `workspace_id` is NOT NULL on every live row
        -- (verified 2026-07-30: 64 lane + 13 thinking_partner, zero NULLs) and
        -- migration 203's trigger fills it on insert; the IS NULL arm keeps a
        -- trigger regression degrading to cast-only rather than locking out.
        workspace_id IS NULL
        OR public.is_workspace_member(workspace_id)
      )
    ELSE
      -- Every other session kind (thinking_partner, and whatever the wake /
      -- narrative machinery adds next) is the creator's own. Byte-identical to
      -- the migration-008 rule it replaces.
      user_id = auth.uid()
    END
  );

-- WRITE: the creator owns the session row — they create it, rename it, archive
-- it. A participant who did not create it does not mutate it (adding people is
-- an API act through the service client, gated by ADR-495 D3).
CREATE POLICY "Creator writes the conversation"
  ON public.chat_sessions
  FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "Creator updates the conversation"
  ON public.chat_sessions
  FOR UPDATE
  TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "Creator deletes the conversation"
  ON public.chat_sessions
  FOR DELETE
  TO authenticated
  USING (user_id = auth.uid());

-- ── 3. session_messages — the cast reads its WINDOW; participants append ───
DROP POLICY IF EXISTS "Users can access messages in their sessions" ON public.session_messages;

-- READ: in the cast AND at or after your window. This is the ADR-495 D2
-- promise made structural. `>=` against a NULL floor (not in the cast) is NULL
-- → not true → no rows: fails closed.
-- Same discriminator as §2: a lane's turns follow the cast + its window; every
-- other session kind's turns follow the creator. Expressed via EXISTS against
-- the parent row so one subquery answers both arms (and so a message whose
-- parent vanished is unreadable rather than orphaned-but-visible).
CREATE POLICY "Cast reads its window of the transcript"
  ON public.session_messages
  FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.chat_sessions s
      WHERE s.id = session_messages.session_id
        AND CASE WHEN s.session_type = 'lane' THEN
              -- ADR-495 D2 made structural: in the cast AND at or after your
              -- window. `>=` against a NULL floor (not in the cast) is NULL →
              -- not true → no rows, so this fails CLOSED.
              session_messages.sequence_number
                >= public.conversation_visibility_floor(s.id)
            ELSE
              s.user_id = auth.uid()
            END
    )
  );

-- WRITE: a participant may append a turn to a conversation they are in. Not
-- creator-only — that was the assumption that made shared conversations dead at
-- N>1 (and the reason `append_session_message` had to be SECURITY DEFINER with
-- no check at all to let a member's turn land).
CREATE POLICY "Participants append to the transcript"
  ON public.session_messages
  FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.chat_sessions s
      WHERE s.id = session_messages.session_id
        AND CASE WHEN s.session_type = 'lane' THEN
              public.is_conversation_participant(s.id)
            ELSE
              s.user_id = auth.uid()
            END
    )
  );

-- No UPDATE / DELETE policy: the transcript is append-only for participants
-- (ADR-406's appender rule). Edit-and-resend truncates via the service client,
-- gated by the author check in routes/lanes.py.

-- ── 4. append_session_message — a definer function must check what it bypasses ──
-- It has been SECURITY DEFINER with NO membership check since migration 008:
-- any authenticated caller who could name a session id could append a turn to
-- it. That was invisible while RLS was creator-only (the API never passed a
-- foreign id), and it becomes the way around §3's INSERT policy the moment
-- conversations are shared. A definer function is a hole exactly the size of
-- the check it forgot to make.
CREATE OR REPLACE FUNCTION append_session_message(
    p_session_id UUID,
    p_role TEXT,
    p_content TEXT,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS session_messages
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_next_seq INTEGER;
    v_message session_messages;
BEGIN
    -- The check this function never had. `auth.uid()` is NULL for the service
    -- client (no JWT), which is how the system's own writes — the scheduler,
    -- the wake drainer, the narrative writer — stay unaffected: they are not
    -- pretending to be a member, so there is no membership to verify.
    --
    -- Same discriminator as the policies: a lane's appender must be in the cast;
    -- any other session kind's must be its creator.
    IF auth.uid() IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM chat_sessions s
        WHERE s.id = p_session_id
          AND CASE WHEN s.session_type = 'lane' THEN
                public.is_conversation_participant(s.id)
              ELSE
                s.user_id = auth.uid()
              END
    ) THEN
        RAISE EXCEPTION 'not a participant in conversation %', p_session_id
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    -- Lock the session row to prevent race conditions
    PERFORM id FROM chat_sessions WHERE id = p_session_id FOR UPDATE;

    -- Get next sequence number
    SELECT COALESCE(MAX(sequence_number), 0) + 1 INTO v_next_seq
    FROM session_messages
    WHERE session_id = p_session_id;

    -- Insert message
    INSERT INTO session_messages (session_id, role, content, sequence_number, metadata)
    VALUES (p_session_id, p_role, p_content, v_next_seq, p_metadata)
    RETURNING * INTO v_message;

    -- Update session updated_at
    UPDATE chat_sessions SET updated_at = NOW() WHERE id = p_session_id;

    RETURN v_message;
END;
$$;

-- ── 5. conversation_members.workspace_id — from dead column to used one ─────
-- It was written on every insert and NEVER read as a filter, so the ADR-495
-- authorization primitive was workspace-blind and the binding lived entirely in
-- callers (the ADR-501 finding-4 shape). Two choices: drop it, or make it
-- honest. Make it honest — it is the natural home for the workspace bound, it is
-- fully populated (97/97 verified 2026-07-30), and dropping it would push the
-- workspace question back into application code permanently.
--
-- NOT NULL + FK, so it cannot drift from its parent conversation again. The
-- write-side asymmetry that allowed drift (routes/lanes.py stamping the
-- INVITER's acting workspace via `lane.get("workspace_id") or
-- _acting_workspace(auth)`) is fixed in the same commit as this migration.
UPDATE conversation_members m
SET workspace_id = s.workspace_id
FROM chat_sessions s
WHERE m.conversation_id = s.id
  AND (m.workspace_id IS DISTINCT FROM s.workspace_id);

ALTER TABLE conversation_members
  ALTER COLUMN workspace_id SET NOT NULL;

ALTER TABLE conversation_members
  DROP CONSTRAINT IF EXISTS conversation_members_workspace_id_fkey;
ALTER TABLE conversation_members
  ADD CONSTRAINT conversation_members_workspace_id_fkey
  FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;

-- The authorization lookup this column now serves.
CREATE INDEX IF NOT EXISTS idx_conversation_members_workspace
  ON conversation_members(workspace_id, principal_id) WHERE member_kind = 'human';

COMMENT ON COLUMN conversation_members.workspace_id IS
  'ADR-495 — the commons this conversation belongs to. NOT NULL + FK since '
  'migration 228: it was written-but-never-read (a dead column), which left '
  'the cast primitive workspace-blind. Kept in sync with the parent '
  'chat_sessions row; never derived from the inviter''s acting workspace.';

COMMIT;
