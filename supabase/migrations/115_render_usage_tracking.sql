-- Migration 115: Render usage tracking (ADR-118 D.2)
--
-- Adds render_usage table for per-user monthly render counting.
-- Used by RuntimeDispatch to enforce tier-based render limits.

CREATE TABLE IF NOT EXISTS render_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    skill_type TEXT NOT NULL,          -- document, presentation, spreadsheet, chart
    output_format TEXT NOT NULL,       -- pdf, pptx, xlsx, png, svg
    size_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for monthly count queries
CREATE INDEX idx_render_usage_user_month
    ON render_usage (user_id, created_at);

-- RLS: users can only see their own usage
ALTER TABLE render_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY render_usage_select ON render_usage
    FOR SELECT USING (auth.uid() = user_id);

-- Service key can insert (used by API during RuntimeDispatch)
CREATE POLICY render_usage_insert ON render_usage
    FOR INSERT WITH CHECK (true);

-- RPC to get monthly render count for a user
CREATE OR REPLACE FUNCTION get_monthly_render_count(p_user_id UUID)
RETURNS INT AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM render_usage
        WHERE user_id = p_user_id
          AND created_at >= date_trunc('month', now())
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
