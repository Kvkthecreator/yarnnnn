-- Migration: 081_signal_history_rls.sql
-- Enable RLS on signal_history (flagged by Supabase Security Advisor)
--
-- signal_history is written by service role (signal processing pipeline)
-- and read by service role + users viewing their own signal data.

ALTER TABLE signal_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own signal history"
    ON signal_history FOR SELECT
    USING (auth.uid() = user_id);

-- No INSERT/UPDATE/DELETE policies for users — service role only
