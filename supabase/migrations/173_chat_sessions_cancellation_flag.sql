-- Migration 173 — Commit H.1: cancellation_requested flag on chat_sessions.
--
-- INTERRUPTION SURFACE — MODE 1 (Stop in-flight Loop)
-- Per FOUNDATIONS v8.4 + ADR-260, the Reviewer's Loop runs synchronously
-- and the operator-in-real-time embodiment may want to interrupt it
-- (Claude-Code-style: send button becomes stop button while running).
--
-- Two operator-trigger shapes need to halt:
--   (a) Operator's own sendMessage HTTP stream — abort the stream
--       client-side (already wired via NarrativeContext.abortControllerRef).
--   (b) Autonomous cron-fired Loop wake — operator sees System Agent
--       activity arriving via realtime, wants to stop it. NO HTTP stream
--       to abort because the operator's browser didn't trigger it.
--       Requires server-side cooperative cancellation: backend writes
--       a flag, Reviewer's tool-use loop checks between rounds and
--       exits early with stand_down verdict.
--
-- This migration adds the flag column. The endpoint that sets it +
-- the Reviewer's cooperative check land in the same commit.
--
-- SHAPE:
--   chat_sessions.cancellation_requested boolean NOT NULL DEFAULT false
--
-- LIFECYCLE:
--   - operator clicks Stop → POST /api/feed/cancel sets flag=true
--   - Reviewer's invoke_reviewer() checks the flag between rounds;
--     if true, exits the loop immediately with stand_down verdict +
--     "operator interrupted" reasoning
--   - on next addressed turn or Loop wake, flag is reset to false
--     (operator's intent applied to the in-flight session, not future ones)
--
-- ATTRIBUTION: this is a runtime-state flag, not authored content.
-- Lives on chat_sessions (the runtime container) not in the Authored
-- Substrate (ADR-209 is for content; this is a transient runtime signal).

ALTER TABLE chat_sessions
    ADD COLUMN IF NOT EXISTS cancellation_requested boolean NOT NULL DEFAULT false;

-- Add to supabase_realtime publication so the FE can observe its own
-- cancellation acknowledgement (and any future operator-side state
-- transitions on chat_sessions).
DO $$
BEGIN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.chat_sessions;
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'chat_sessions already in supabase_realtime publication — skipping';
END $$;

-- Verification
DO $$
DECLARE
    has_col boolean;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'chat_sessions'
          AND column_name = 'cancellation_requested'
    ) INTO has_col;
    IF NOT has_col THEN
        RAISE EXCEPTION 'Migration 173 failed: chat_sessions.cancellation_requested column missing';
    END IF;
    RAISE NOTICE 'Migration 173 verified: chat_sessions.cancellation_requested column exists.';
END $$;
