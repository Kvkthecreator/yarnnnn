-- Migration 170: Add session_messages to supabase_realtime publication.
--
-- FOUNDATIONS v8.4 Axiom 1 fourth sub-clause + ADR-260 real-time-visible-
-- handoffs commitment: the operator-in-real-time embodiment must SEE
-- substrate writes that the operator-as-Reviewer made during cron-fired
-- Loop wake-ups. Pre-2026-05-11, the FE only re-fetched session_messages
-- on chat-turn (sendMessage); cron-fired Reviewer narrations landed in
-- substrate but were invisible to the operator until they typed a message.
--
-- The new useSessionMessagesRealtime hook (web/lib/realtime/) subscribes
-- via Supabase Realtime to INSERT events on session_messages filtered to
-- the operator's active session. The subscription requires the table to
-- be in the supabase_realtime publication.
--
-- RLS is preserved as-is — the existing "Users can access messages in
-- their sessions" SELECT policy gates which rows the realtime channel
-- emits to each subscribing client.
--
-- Idempotency: ALTER PUBLICATION ADD TABLE errors if the table is
-- already in the publication. Wrapping in a DO block + EXCEPTION
-- handler to make the migration safe to re-run.

DO $$
BEGIN
  ALTER PUBLICATION supabase_realtime ADD TABLE public.session_messages;
EXCEPTION
  WHEN duplicate_object THEN
    RAISE NOTICE 'session_messages already in supabase_realtime publication — skipping';
END $$;

-- Verify
DO $$
DECLARE
  in_pub boolean;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE schemaname = 'public'
      AND tablename = 'session_messages'
      AND pubname = 'supabase_realtime'
  ) INTO in_pub;
  IF NOT in_pub THEN
    RAISE EXCEPTION 'Migration 170 failed: session_messages not in supabase_realtime publication after ALTER';
  END IF;
END $$;
