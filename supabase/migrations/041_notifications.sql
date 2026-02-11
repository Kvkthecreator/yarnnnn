-- Migration: 041_notifications.sql
-- ADR-040: Proactive Notification Architecture
--
-- Streamlined notifications table for email and audit logging.
-- In-session TP notifications are handled in-memory (not persisted).

-- =============================================================================
-- Notifications Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS notifications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Content
    message TEXT NOT NULL,
    context JSONB DEFAULT '{}',

    -- Delivery (streamlined: email only, in-app handled by TP session)
    channel TEXT NOT NULL DEFAULT 'email' CHECK (channel IN ('email', 'in_app')),
    urgency TEXT DEFAULT 'normal' CHECK (urgency IN ('low', 'normal', 'high')),

    -- Source: what triggered this notification
    source_type TEXT NOT NULL CHECK (source_type IN ('system', 'monitor', 'tp', 'deliverable', 'event_trigger')),
    source_id UUID,  -- deliverable_id, monitor_id, etc.

    -- State
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_notifications_user_status ON notifications(user_id, status);
CREATE INDEX IF NOT EXISTS idx_notifications_user_created ON notifications(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_source ON notifications(source_type, source_id);

-- RLS
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Users can view their own notifications
CREATE POLICY "Users can view own notifications"
    ON notifications
    FOR SELECT
    USING (auth.uid() = user_id);

-- Service role can manage all notifications
CREATE POLICY "Service role full access to notifications"
    ON notifications
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- Event Trigger Log Table
-- =============================================================================
-- Replaces in-memory cooldown cache with database tracking

CREATE TABLE IF NOT EXISTS event_trigger_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- What was triggered
    deliverable_id UUID REFERENCES deliverables(id) ON DELETE SET NULL,
    monitor_id UUID,  -- Future: when monitors table exists

    -- Event details
    platform TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resource_id TEXT,
    event_data JSONB,

    -- Cooldown tracking
    cooldown_key TEXT NOT NULL,

    -- Result
    result TEXT CHECK (result IN ('executed', 'skipped', 'failed')),
    skip_reason TEXT,

    -- Timestamp
    triggered_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for cooldown queries and audit
CREATE INDEX IF NOT EXISTS idx_trigger_log_cooldown ON event_trigger_log(cooldown_key, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_trigger_log_user ON event_trigger_log(user_id, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_trigger_log_deliverable ON event_trigger_log(deliverable_id, triggered_at DESC);

-- RLS
ALTER TABLE event_trigger_log ENABLE ROW LEVEL SECURITY;

-- Users can view their own trigger logs
CREATE POLICY "Users can view own trigger logs"
    ON event_trigger_log
    FOR SELECT
    USING (auth.uid() = user_id);

-- Service role can manage all trigger logs
CREATE POLICY "Service role full access to trigger logs"
    ON event_trigger_log
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- Cleanup function for old trigger logs (called by scheduler)
-- =============================================================================

CREATE OR REPLACE FUNCTION cleanup_old_trigger_logs(retention_days INTEGER DEFAULT 30)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM event_trigger_log
    WHERE triggered_at < NOW() - (retention_days || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;
