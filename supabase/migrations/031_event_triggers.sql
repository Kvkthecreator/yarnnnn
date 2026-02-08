-- ADR-031 Phase 4: Event Triggers
-- Migration 031: Schema changes for event-driven deliverable triggers
--
-- This migration adds support for:
-- 1. trigger_type column (schedule vs event)
-- 2. trigger_config column (event-specific configuration)
-- 3. last_triggered_at for cooldown tracking
-- 4. Index for event trigger queries

-- =============================================================================
-- 1. Trigger Type and Config on Deliverables
-- =============================================================================

-- Trigger type - schedule (default) or event
ALTER TABLE deliverables ADD COLUMN IF NOT EXISTS trigger_type TEXT DEFAULT 'schedule';

-- Check constraint for trigger_type
ALTER TABLE deliverables ADD CONSTRAINT deliverables_trigger_type_check
    CHECK (trigger_type = ANY (ARRAY['schedule', 'event', 'manual']));

-- Event trigger configuration (only used when trigger_type = 'event')
-- Schema:
-- {
--   "platform": "slack" | "gmail" | "notion",
--   "event_types": ["app_mention", "message_im"],
--   "resource_ids": ["C123ABC456", "D789DEF"],
--   "cooldown": {"type": "per_thread", "duration_minutes": 5},
--   "sender_filter": ["U123", "U456"],  -- optional
--   "keyword_filter": ["urgent", "help"]  -- optional
-- }
ALTER TABLE deliverables ADD COLUMN IF NOT EXISTS trigger_config JSONB;

-- Last triggered timestamp for cooldown management
ALTER TABLE deliverables ADD COLUMN IF NOT EXISTS last_triggered_at TIMESTAMPTZ;

-- Index for finding event-triggered deliverables
CREATE INDEX IF NOT EXISTS idx_deliverables_trigger_type ON deliverables(trigger_type) WHERE trigger_type = 'event';

-- Index for trigger config platform lookups (for event routing)
CREATE INDEX IF NOT EXISTS idx_deliverables_trigger_platform ON deliverables((trigger_config->>'platform')) WHERE trigger_type = 'event';


-- =============================================================================
-- 2. Helper Function: Get Event-Triggered Deliverables
-- =============================================================================

CREATE OR REPLACE FUNCTION get_event_triggered_deliverables(
    p_user_id UUID,
    p_platform TEXT,
    p_resource_id TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    trigger_config JSONB,
    governance TEXT,
    last_triggered_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.title,
        d.trigger_config,
        d.governance,
        d.last_triggered_at
    FROM deliverables d
    WHERE d.user_id = p_user_id
      AND d.status = 'active'
      AND d.trigger_type = 'event'
      AND d.trigger_config->>'platform' = p_platform
      AND (
          p_resource_id IS NULL
          OR d.trigger_config->'resource_ids' ? p_resource_id
          OR jsonb_array_length(d.trigger_config->'resource_ids') = 0
      );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- =============================================================================
-- 3. Trigger Event Log Table
-- =============================================================================
-- Tracks event triggers for analytics and debugging

CREATE TABLE IF NOT EXISTS trigger_event_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deliverable_id UUID REFERENCES deliverables(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Event details
    platform TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resource_id TEXT,
    event_data JSONB DEFAULT '{}',
    event_timestamp TIMESTAMPTZ NOT NULL,

    -- Trigger outcome
    triggered BOOLEAN NOT NULL DEFAULT false,
    skip_reason TEXT,  -- cooldown, filter, error
    version_id UUID REFERENCES deliverable_versions(id) ON DELETE SET NULL,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_trigger_log_deliverable ON trigger_event_log(deliverable_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trigger_log_user ON trigger_event_log(user_id, created_at DESC);

-- RLS
ALTER TABLE trigger_event_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own trigger logs" ON trigger_event_log
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Service role can manage all trigger logs" ON trigger_event_log
    FOR ALL TO service_role USING (true);


-- =============================================================================
-- 4. Update Trigger Timestamp Function
-- =============================================================================

CREATE OR REPLACE FUNCTION update_deliverable_triggered()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE deliverables
    SET last_triggered_at = now()
    WHERE id = NEW.deliverable_id
      AND NEW.triggered = true;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_trigger_event_logged
    AFTER INSERT ON trigger_event_log
    FOR EACH ROW
    EXECUTE FUNCTION update_deliverable_triggered();
