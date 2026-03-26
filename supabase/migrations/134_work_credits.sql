-- Migration 134: Work credits — unified metering for autonomous work
--
-- Consolidates work_units (migration 117) and render_usage (migration 115)
-- into a single work_credits table. Chat is NOT credited — covered by subscription.
--
-- Credit costs: task_execution=3, render=1
-- Tier allocation: Free 20/month, Pro 500/month
-- Overage: Pro only, $5/100 credits (future — Lemon Squeezy one-time purchase)

-- Create unified work_credits table
CREATE TABLE IF NOT EXISTS work_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,          -- task_execution, render, agent_run (legacy compat)
    credits_consumed INT NOT NULL DEFAULT 1,
    agent_id UUID,                      -- nullable, links to agent that triggered
    metadata JSONB,                     -- task_slug, skill_type, output_format, trigger_type, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for monthly rollup queries
CREATE INDEX idx_work_credits_user_month
    ON work_credits (user_id, created_at);

-- RLS: users can see their own usage
ALTER TABLE work_credits ENABLE ROW LEVEL SECURITY;

CREATE POLICY work_credits_select ON work_credits
    FOR SELECT USING (auth.uid() = user_id);

-- Service key can insert (used by API/scheduler during execution)
CREATE POLICY work_credits_insert ON work_credits
    FOR INSERT WITH CHECK (true);

-- RPC: get monthly credits consumed (SUM, not COUNT — task_execution costs 3)
CREATE OR REPLACE FUNCTION get_monthly_credits(p_user_id UUID)
RETURNS INT AS $$
BEGIN
    RETURN COALESCE((
        SELECT SUM(credits_consumed)
        FROM work_credits
        WHERE user_id = p_user_id
          AND created_at >= date_trunc('month', now())
    ), 0);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Migrate existing data from work_units and render_usage
-- work_units: each row was 1 unit → map to credits (task_execution=3, render=1)
INSERT INTO work_credits (user_id, action_type, credits_consumed, agent_id, metadata, created_at)
SELECT
    user_id,
    CASE
        WHEN action_type = 'render' THEN 'render'
        ELSE 'task_execution'
    END,
    CASE
        WHEN action_type = 'render' THEN 1
        ELSE 3  -- task executions now cost 3 credits
    END,
    agent_id,
    metadata,
    created_at
FROM work_units
ON CONFLICT DO NOTHING;

-- Migrate render_usage into work_credits
INSERT INTO work_credits (user_id, action_type, credits_consumed, metadata, created_at)
SELECT
    user_id,
    'render',
    1,
    jsonb_build_object('skill_type', skill_type, 'output_format', output_format, 'size_bytes', size_bytes),
    created_at
FROM render_usage
ON CONFLICT DO NOTHING;

-- Drop old tables
DROP TABLE IF EXISTS work_units CASCADE;
DROP TABLE IF EXISTS render_usage CASCADE;

-- Drop old RPCs
DROP FUNCTION IF EXISTS get_monthly_work_units(UUID);
DROP FUNCTION IF EXISTS get_monthly_render_count(UUID);
