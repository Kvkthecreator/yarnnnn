-- Migration 117: Work budget tracking (ADR-120 Phase 3)
--
-- Adds work_units table for per-user monthly work budget enforcement.
-- Mirrors render_usage (migration 115) pattern.
-- Actions: agent_run (1 unit), assembly (2 units), render (1 unit), pm_heartbeat (1 unit).
-- Tier allocation: Free 60/month, Pro 1000/month.

CREATE TABLE IF NOT EXISTS work_units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,          -- agent_run, assembly, render, pm_heartbeat
    agent_id UUID,                      -- nullable, for project-level actions
    units_consumed INT NOT NULL DEFAULT 1,
    metadata JSONB,                     -- trigger_type, project_slug, skill_type, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for monthly rollup queries (same pattern as render_usage)
CREATE INDEX idx_work_units_user_month
    ON work_units (user_id, created_at);

-- RLS: users can see their own usage
ALTER TABLE work_units ENABLE ROW LEVEL SECURITY;

CREATE POLICY work_units_select ON work_units
    FOR SELECT USING (auth.uid() = user_id);

-- Service key can insert (used by API/scheduler during execution)
CREATE POLICY work_units_insert ON work_units
    FOR INSERT WITH CHECK (true);

-- RPC to get monthly work units consumed (SUM, not COUNT — assembly costs 2)
CREATE OR REPLACE FUNCTION get_monthly_work_units(p_user_id UUID)
RETURNS INT AS $$
BEGIN
    RETURN COALESCE((
        SELECT SUM(units_consumed)
        FROM work_units
        WHERE user_id = p_user_id
          AND created_at >= date_trunc('month', now())
    ), 0);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
