-- Behavioural probe for conversation RLS (migration 228 / ADR-495 D2).
--
-- WHY THIS EXISTS. `api/test_adr495_conversation_rls.py` is a STATIC gate — it
-- reads SQL and source text, so it proves the migration's SHAPE and nothing
-- about its BEHAVIOUR. A policy can be present, well-named, and wrong. This
-- probe impersonates real users via the same claim RLS reads
-- (`request.jwt.claim.sub`) under `SET LOCAL ROLE authenticated`, so the
-- policies are genuinely exercised.
--
-- It earned its keep on first run: it caught that the migration's original
-- cast-only policy would have made the steward rail (13 `thinking_partner`
-- sessions, zero cast rows) unreadable — a whole-feature blackout no static
-- check would have seen.
--
-- RUN IT (safe — every write rolls back):
--   CONN="…"  # docs/database/ACCESS.md
--   { echo "BEGIN;"; cat api/scripts/probes/probe_conversation_rls.sql; \
--     echo "ROLLBACK;"; } | psql "$CONN" -v ON_ERROR_STOP=1 -f -
--
-- Re-run after ANY change to the two policies, to `append_session_message`, or
-- to `conversation_members`. A green static gate is not evidence that a member
-- can still read the conversation they were invited to.
--
-- Every check RAISES on failure, so ON_ERROR_STOP makes the whole run fail
-- loudly rather than printing a NOTICE nobody reads.
\set ON_ERROR_STOP on
\pset pager off

-- Pick a live group conversation (2 humans) + its two members.
CREATE TEMP TABLE probe AS
SELECT m.conversation_id AS conv,
       min(m.principal_id::text) AS a,
       max(m.principal_id::text) AS b
FROM conversation_members m
WHERE m.member_kind = 'human'
GROUP BY m.conversation_id
HAVING count(*) = 2
LIMIT 1;

-- A third party: a user in NEITHER cast slot.
CREATE TEMP TABLE outsider AS
SELECT g.principal_id AS c
FROM principal_grants g, probe p
WHERE g.role IN ('owner','member') AND g.status='active'
  AND g.principal_id <> p.a AND g.principal_id <> p.b
LIMIT 1;

SELECT 'conv='||conv||' a='||a||' b='||b FROM probe;
SELECT 'outsider='||c FROM outsider;

-- A lane the outsider is NOT in, but whose workspace they DO belong to —
-- the case that separates "cast membership" from "workspace membership".
SELECT 'turns in conv = '||count(*) FROM session_messages
 WHERE session_id = (SELECT conv FROM probe);

-- ── TEST 1: a cast member reads the conversation + its turns ───────────────
DO $$
DECLARE v_a text; v_conv uuid; n_sess int; n_msg int;
BEGIN
  SELECT a, conv INTO v_a, v_conv FROM probe;
  PERFORM set_config('request.jwt.claim.sub', v_a, true);
  SET LOCAL ROLE authenticated;
  SELECT count(*) INTO n_sess FROM chat_sessions WHERE id = v_conv;
  SELECT count(*) INTO n_msg  FROM session_messages WHERE session_id = v_conv;
  RESET ROLE;
  RAISE NOTICE 'TEST1 cast member A: sessions=% messages=% (expect 1, >=0)', n_sess, n_msg;
  IF n_sess <> 1 THEN RAISE EXCEPTION 'FAIL: a cast member cannot read their own conversation'; END IF;
END $$;

-- ── TEST 2: the SECOND human reads it too (the N>1 case that was dead) ─────
DO $$
DECLARE v_b text; v_conv uuid; n_sess int;
BEGIN
  SELECT b, conv INTO v_b, v_conv FROM probe;
  PERFORM set_config('request.jwt.claim.sub', v_b, true);
  SET LOCAL ROLE authenticated;
  SELECT count(*) INTO n_sess FROM chat_sessions WHERE id = v_conv;
  RESET ROLE;
  RAISE NOTICE 'TEST2 cast member B: sessions=% (expect 1)', n_sess;
  IF n_sess <> 1 THEN RAISE EXCEPTION 'FAIL: the invited member still cannot read the shared conversation'; END IF;
END $$;

-- ── TEST 3: a NON-participant reads nothing, even as a workspace member ────
DO $$
DECLARE v_c text; v_conv uuid; n_sess int; n_msg int;
BEGIN
  SELECT c INTO v_c FROM outsider;
  SELECT conv INTO v_conv FROM probe;
  IF v_c IS NULL THEN RAISE NOTICE 'TEST3 SKIPPED (no third principal live)'; RETURN; END IF;
  PERFORM set_config('request.jwt.claim.sub', v_c, true);
  SET LOCAL ROLE authenticated;
  SELECT count(*) INTO n_sess FROM chat_sessions WHERE id = v_conv;
  SELECT count(*) INTO n_msg  FROM session_messages WHERE session_id = v_conv;
  RESET ROLE;
  RAISE NOTICE 'TEST3 non-participant: sessions=% messages=% (expect 0, 0)', n_sess, n_msg;
  IF n_sess <> 0 OR n_msg <> 0 THEN
    RAISE EXCEPTION 'FAIL: a non-participant can read a conversation (ADR-495 D2 breached)';
  END IF;
END $$;

-- ── TEST 4: the visibility WINDOW holds against a raw query ────────────────
-- Move member B to a from-now window and confirm earlier turns disappear.
DO $$
DECLARE v_b text; v_conv uuid; n_before int; n_after int; v_max int;
BEGIN
  SELECT b, conv INTO v_b, v_conv FROM probe;
  SELECT coalesce(max(sequence_number),0) INTO v_max FROM session_messages WHERE session_id=v_conv;
  IF v_max = 0 THEN RAISE NOTICE 'TEST4 SKIPPED (conversation has no turns)'; RETURN; END IF;

  PERFORM set_config('request.jwt.claim.sub', v_b, true);
  SET LOCAL ROLE authenticated;
  SELECT count(*) INTO n_before FROM session_messages WHERE session_id=v_conv;
  RESET ROLE;

  -- "From now" = max + 1 (the `default_window` rule): STRICTLY past the last
  -- turn. Setting it to `max` was the first version of this test and it
  -- correctly still showed turn `max` (max >= max) — the test's boundary was
  -- wrong, not the policy. Recorded because it is the same off-by-one a future
  -- reader will reach for.
  UPDATE conversation_members SET visible_from_sequence = v_max + 1
   WHERE conversation_id=v_conv AND member_kind='human' AND principal_id=v_b::uuid;

  PERFORM set_config('request.jwt.claim.sub', v_b, true);
  SET LOCAL ROLE authenticated;
  SELECT count(*) INTO n_after FROM session_messages WHERE session_id=v_conv;
  RESET ROLE;

  RAISE NOTICE 'TEST4 window: before=% after=% (max_seq=%) — from-now must show 0', n_before, n_after, v_max;
  IF n_after <> 0 THEN
    RAISE EXCEPTION 'FAIL: the visibility window is not enforced by RLS (from-now still reads % turns)', n_after;
  END IF;
  -- And the boundary itself: a floor AT the last turn still shows that turn.
  UPDATE conversation_members SET visible_from_sequence = v_max
   WHERE conversation_id=v_conv AND member_kind='human' AND principal_id=v_b::uuid;
  PERFORM set_config('request.jwt.claim.sub', v_b, true);
  SET LOCAL ROLE authenticated;
  SELECT count(*) INTO n_after FROM session_messages WHERE session_id=v_conv;
  RESET ROLE;
  RAISE NOTICE 'TEST4b boundary: floor=max shows % turn(s) (expect >=1 — the window is inclusive)', n_after;
  IF n_after < 1 THEN
    RAISE EXCEPTION 'FAIL: the window is exclusive at its own floor';
  END IF;
END $$;

-- ── TEST 5: the steward rail still works (thinking_partner, no cast) ───────
DO $$
DECLARE v_u text; n_sess int; n_msg int; v_sid uuid;
BEGIN
  SELECT user_id::text, id INTO v_u, v_sid FROM chat_sessions
   WHERE session_type='thinking_partner' ORDER BY created_at DESC LIMIT 1;
  IF v_u IS NULL THEN RAISE NOTICE 'TEST5 SKIPPED (no thinking_partner session)'; RETURN; END IF;
  PERFORM set_config('request.jwt.claim.sub', v_u, true);
  SET LOCAL ROLE authenticated;
  SELECT count(*) INTO n_sess FROM chat_sessions WHERE id=v_sid;
  SELECT count(*) INTO n_msg  FROM session_messages WHERE session_id=v_sid;
  RESET ROLE;
  RAISE NOTICE 'TEST5 steward own session: sessions=% messages=% (expect 1, >=0)', n_sess, n_msg;
  IF n_sess <> 1 THEN
    RAISE EXCEPTION 'FAIL: the steward rail is unreadable — cast policy leaked onto non-lane sessions';
  END IF;
END $$;

-- ── TEST 6: append_session_message refuses a non-participant ───────────────
DO $$
DECLARE v_c text; v_conv uuid; ok boolean := false;
BEGIN
  SELECT c INTO v_c FROM outsider;
  SELECT conv INTO v_conv FROM probe;
  IF v_c IS NULL THEN RAISE NOTICE 'TEST6 SKIPPED (no third principal live)'; RETURN; END IF;
  PERFORM set_config('request.jwt.claim.sub', v_c, true);
  SET LOCAL ROLE authenticated;
  BEGIN
    PERFORM append_session_message(v_conv, 'user', 'probe-intrusion', '{}'::jsonb);
  EXCEPTION WHEN insufficient_privilege THEN ok := true;
  END;
  RESET ROLE;
  RAISE NOTICE 'TEST6 definer-function refuses outsider: %', ok;
  IF NOT ok THEN
    RAISE EXCEPTION 'FAIL: append_session_message still lets a non-participant write';
  END IF;
END $$;

-- ── TEST 7: a participant CAN append (the function still works) ────────────
DO $$
DECLARE v_a text; v_conv uuid; before_n int; after_n int;
BEGIN
  SELECT a, conv INTO v_a, v_conv FROM probe;
  SELECT count(*) INTO before_n FROM session_messages WHERE session_id=v_conv;
  PERFORM set_config('request.jwt.claim.sub', v_a, true);
  SET LOCAL ROLE authenticated;
  PERFORM append_session_message(v_conv, 'user', 'probe-legit', '{}'::jsonb);
  RESET ROLE;
  SELECT count(*) INTO after_n FROM session_messages WHERE session_id=v_conv;
  RAISE NOTICE 'TEST7 participant append: before=% after=% (expect +1)', before_n, after_n;
  IF after_n <> before_n + 1 THEN
    RAISE EXCEPTION 'FAIL: a participant can no longer append to their own conversation';
  END IF;
END $$;

-- ── TEST 8: the service client (no JWT) is unaffected ──────────────────────
DO $$
DECLARE v_conv uuid; n int;
BEGIN
  SELECT conv INTO v_conv FROM probe;
  PERFORM set_config('request.jwt.claim.sub', '', true);
  PERFORM append_session_message(v_conv, 'assistant', 'probe-system', '{}'::jsonb);
  SELECT count(*) INTO n FROM session_messages WHERE session_id=v_conv AND content='probe-system';
  RAISE NOTICE 'TEST8 service-client write (no JWT): rows=% (expect 1)', n;
  IF n <> 1 THEN RAISE EXCEPTION 'FAIL: the system''s own writes were broken'; END IF;
END $$;

SELECT '=== ALL PROBES PASSED ===' AS result;
