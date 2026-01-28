-- YARNNN v5 - Phase 2: Scheduling Tables
-- Enables weekly digest emails and future notification types

-----------------------------------------------------------
-- 1. WORKSPACE DIGEST PREFERENCES
-----------------------------------------------------------
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS owner_email TEXT;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS digest_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS digest_day INTEGER DEFAULT 1; -- 0=Sun, 1=Mon, 2=Tue, etc.
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS digest_hour INTEGER DEFAULT 9; -- 0-23 in user's timezone
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS digest_timezone TEXT DEFAULT 'UTC';

-- Constraint: digest_day must be 0-6
ALTER TABLE workspaces ADD CONSTRAINT valid_digest_day
    CHECK (digest_day >= 0 AND digest_day <= 6);

-- Constraint: digest_hour must be 0-23
ALTER TABLE workspaces ADD CONSTRAINT valid_digest_hour
    CHECK (digest_hour >= 0 AND digest_hour <= 23);

-----------------------------------------------------------
-- 2. SCHEDULED MESSAGES
-----------------------------------------------------------
CREATE TABLE IF NOT EXISTS scheduled_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,

    -- Scheduling
    scheduled_for TIMESTAMPTZ NOT NULL,
    message_type TEXT NOT NULL, -- weekly_digest, work_complete, etc.

    -- Content
    subject TEXT,
    content JSONB NOT NULL, -- Flexible structure per message_type

    -- Delivery
    recipient_email TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, sent, failed, skipped
    sent_at TIMESTAMPTZ,
    failure_reason TEXT,

    -- Tracking
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scheduled_messages_workspace ON scheduled_messages(workspace_id);
CREATE INDEX idx_scheduled_messages_status ON scheduled_messages(status);
CREATE INDEX idx_scheduled_messages_scheduled ON scheduled_messages(scheduled_for)
    WHERE status = 'pending';

-- RLS
ALTER TABLE scheduled_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their workspace messages"
    ON scheduled_messages FOR SELECT
    USING (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
        )
    );

-----------------------------------------------------------
-- 3. WORK OUTPUT STATUS (for supervision light)
-----------------------------------------------------------
ALTER TABLE work_outputs ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'delivered';
-- Values: delivered, approved, dismissed

CREATE INDEX IF NOT EXISTS idx_outputs_status ON work_outputs(status);

-----------------------------------------------------------
-- 4. EMAIL DELIVERY LOG (optional, for debugging)
-----------------------------------------------------------
CREATE TABLE IF NOT EXISTS email_delivery_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scheduled_message_id UUID REFERENCES scheduled_messages(id) ON DELETE SET NULL,

    -- Email details
    recipient TEXT NOT NULL,
    subject TEXT,

    -- Provider response
    provider TEXT DEFAULT 'resend', -- resend, sendgrid, etc.
    provider_message_id TEXT,

    -- Status
    status TEXT NOT NULL, -- sent, bounced, delivered, opened, clicked
    status_updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_email_log_message ON email_delivery_log(scheduled_message_id);
CREATE INDEX idx_email_log_recipient ON email_delivery_log(recipient);

-- RLS (admin only, or inherit from scheduled_messages)
ALTER TABLE email_delivery_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view logs for their messages"
    ON email_delivery_log FOR SELECT
    USING (
        scheduled_message_id IN (
            SELECT sm.id FROM scheduled_messages sm
            JOIN workspaces w ON sm.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );

-----------------------------------------------------------
-- 5. HELPER FUNCTION: Get workspaces due for digest
-----------------------------------------------------------
CREATE OR REPLACE FUNCTION get_workspaces_due_for_digest(check_time TIMESTAMPTZ)
RETURNS TABLE (
    workspace_id UUID,
    owner_email TEXT,
    workspace_name TEXT,
    digest_timezone TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        w.id as workspace_id,
        COALESCE(w.owner_email, u.email) as owner_email,
        w.name as workspace_name,
        w.digest_timezone
    FROM workspaces w
    JOIN auth.users u ON w.owner_id = u.id
    WHERE w.digest_enabled = TRUE
      AND EXTRACT(DOW FROM check_time AT TIME ZONE w.digest_timezone) = w.digest_day
      AND EXTRACT(HOUR FROM check_time AT TIME ZONE w.digest_timezone) = w.digest_hour
      -- Prevent duplicate sends: no pending/sent message for this week
      AND NOT EXISTS (
          SELECT 1 FROM scheduled_messages sm
          WHERE sm.workspace_id = w.id
            AND sm.message_type = 'weekly_digest'
            AND sm.status IN ('pending', 'sent')
            AND sm.scheduled_for > check_time - INTERVAL '6 days'
      );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
