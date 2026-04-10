-- Migration 143: Token spend metering — ADR-171
--
-- Replaces work_credits with token_usage: universal meter across all LLM
-- call surfaces (chat, task_pipeline, web_search, inference, evaluation,
-- session_summary). cost_usd computed at write time from BILLING_RATES.
--
-- User-facing rates: 2x Anthropic API rates (Sonnet: $6/$30 per MTok in/out).
-- Cache discount not passed through — platform margin.
-- Overage model: hard stop at monthly limit.

-- Create token_usage table
CREATE TABLE IF NOT EXISTS token_usage (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at    timestamptz NOT NULL DEFAULT now(),
    caller        text NOT NULL,
    -- 'chat' | 'task_pipeline' | 'web_search' | 'inference' | 'evaluation' | 'session_summary'
    model         text NOT NULL,
    input_tokens  int NOT NULL DEFAULT 0,
    output_tokens int NOT NULL DEFAULT 0,
    cost_usd      numeric(10,6) NOT NULL,  -- at user-facing billing rates
    ref_id        uuid,        -- agent_runs.id or session_messages.id
    metadata      jsonb        -- task_slug, session_id, caller-specific context
);

-- Index for fast monthly rollup per user
CREATE INDEX token_usage_user_month ON token_usage (user_id, created_at);

-- RLS: users can read their own usage
ALTER TABLE token_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY token_usage_select ON token_usage
    FOR SELECT USING (auth.uid() = user_id);

-- Service key inserts (API + scheduler during execution)
CREATE POLICY token_usage_insert ON token_usage
    FOR INSERT WITH CHECK (true);

-- RPC: monthly spend in USD for a user (calendar month)
CREATE OR REPLACE FUNCTION get_monthly_spend_usd(p_user_id uuid)
RETURNS numeric AS $$
BEGIN
    RETURN COALESCE((
        SELECT SUM(cost_usd)
        FROM token_usage
        WHERE user_id = p_user_id
          AND created_at >= date_trunc('month', now())
    ), 0);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop work_credits infrastructure
DROP TABLE IF EXISTS work_credits CASCADE;
DROP FUNCTION IF EXISTS get_monthly_credits(uuid);
