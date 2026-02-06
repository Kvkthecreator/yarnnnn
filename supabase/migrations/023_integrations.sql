-- Migration: 023_integrations.sql
-- ADR-026: Integration Architecture
--
-- Adds tables for third-party integrations (Slack, Notion, etc.) using MCP.
-- Supports encrypted OAuth token storage, export preferences, and audit logging.

-- =============================================================================
-- User Integrations (OAuth token storage)
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_integrations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Integration provider
    provider TEXT NOT NULL,  -- 'slack', 'notion', 'google', etc.

    -- Encrypted OAuth tokens (Fernet encryption at application layer)
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,

    -- Token metadata
    token_type TEXT DEFAULT 'Bearer',
    expires_at TIMESTAMPTZ,  -- When access token expires

    -- Provider-specific metadata
    -- Slack: { workspace_id, workspace_name, team_id, bot_user_id }
    -- Notion: { workspace_id, workspace_name }
    metadata JSONB DEFAULT '{}',

    -- Connection status
    status TEXT DEFAULT 'active',  -- 'active', 'expired', 'revoked', 'error'
    last_error TEXT,
    last_used_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- One integration per provider per user
    UNIQUE(user_id, provider)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_integrations_user
    ON user_integrations(user_id);
CREATE INDEX IF NOT EXISTS idx_user_integrations_provider
    ON user_integrations(provider);
CREATE INDEX IF NOT EXISTS idx_user_integrations_status
    ON user_integrations(status);

-- RLS
ALTER TABLE user_integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own integrations"
    ON user_integrations FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own integrations"
    ON user_integrations FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own integrations"
    ON user_integrations FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own integrations"
    ON user_integrations FOR DELETE
    USING (auth.uid() = user_id);

-- Service role for background jobs
CREATE POLICY "Service role can manage all integrations"
    ON user_integrations FOR ALL
    TO service_role
    USING (true);

-- =============================================================================
-- Deliverable Export Preferences
-- =============================================================================

CREATE TABLE IF NOT EXISTS deliverable_export_preferences (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    deliverable_id UUID NOT NULL REFERENCES deliverables(id) ON DELETE CASCADE,

    -- Export destination
    provider TEXT NOT NULL,  -- 'slack', 'notion', 'email', 'download'

    -- Provider-specific destination
    -- Slack: { channel_id, channel_name }
    -- Notion: { page_id, page_title, database_id }
    -- Email: { recipients: ["email@example.com"] }
    destination JSONB NOT NULL DEFAULT '{}',

    -- Auto-export settings
    auto_export BOOLEAN DEFAULT false,  -- Export automatically on approval

    -- Display order (for UI)
    sort_order INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- One preference per provider per deliverable
    UNIQUE(deliverable_id, provider)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_export_prefs_deliverable
    ON deliverable_export_preferences(deliverable_id);
CREATE INDEX IF NOT EXISTS idx_export_prefs_auto
    ON deliverable_export_preferences(auto_export) WHERE auto_export = true;

-- RLS (inherits from deliverable ownership)
ALTER TABLE deliverable_export_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view export prefs for own deliverables"
    ON deliverable_export_preferences FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM deliverables d
            WHERE d.id = deliverable_id
            AND d.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert export prefs for own deliverables"
    ON deliverable_export_preferences FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM deliverables d
            WHERE d.id = deliverable_id
            AND d.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update export prefs for own deliverables"
    ON deliverable_export_preferences FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM deliverables d
            WHERE d.id = deliverable_id
            AND d.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete export prefs for own deliverables"
    ON deliverable_export_preferences FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM deliverables d
            WHERE d.id = deliverable_id
            AND d.user_id = auth.uid()
        )
    );

-- Service role for background jobs
CREATE POLICY "Service role can manage all export prefs"
    ON deliverable_export_preferences FOR ALL
    TO service_role
    USING (true);

-- =============================================================================
-- Export Log (Audit Trail)
-- =============================================================================

CREATE TABLE IF NOT EXISTS export_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    -- What was exported
    deliverable_version_id UUID NOT NULL REFERENCES deliverable_versions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Export details
    provider TEXT NOT NULL,  -- 'slack', 'notion', 'email', 'download'
    destination JSONB,       -- Copy of destination at time of export

    -- Export result
    status TEXT NOT NULL,    -- 'pending', 'success', 'failed'
    error_message TEXT,

    -- External reference (for linking back)
    -- Slack: message timestamp (ts)
    -- Notion: page id
    -- Email: message id
    external_id TEXT,
    external_url TEXT,       -- Direct link to exported content

    -- Metadata
    content_hash TEXT,       -- Hash of exported content (for deduplication)
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_export_log_version
    ON export_log(deliverable_version_id);
CREATE INDEX IF NOT EXISTS idx_export_log_user
    ON export_log(user_id);
CREATE INDEX IF NOT EXISTS idx_export_log_status
    ON export_log(status);
CREATE INDEX IF NOT EXISTS idx_export_log_created
    ON export_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_export_log_provider
    ON export_log(provider);

-- RLS
ALTER TABLE export_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own export logs"
    ON export_log FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own export logs"
    ON export_log FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Updates allowed for status changes
CREATE POLICY "Users can update own export logs"
    ON export_log FOR UPDATE
    USING (auth.uid() = user_id);

-- Service role for background jobs
CREATE POLICY "Service role can manage all export logs"
    ON export_log FOR ALL
    TO service_role
    USING (true);

-- =============================================================================
-- Helper Functions
-- =============================================================================

-- Get user's active integrations
CREATE OR REPLACE FUNCTION get_user_integrations(p_user_id UUID)
RETURNS TABLE (
    id UUID,
    provider TEXT,
    status TEXT,
    metadata JSONB,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ui.id,
        ui.provider,
        ui.status,
        ui.metadata,
        ui.last_used_at,
        ui.created_at
    FROM user_integrations ui
    WHERE ui.user_id = p_user_id
    AND ui.status = 'active'
    ORDER BY ui.created_at;
END;
$$;

-- Get export history for a deliverable
CREATE OR REPLACE FUNCTION get_deliverable_export_history(
    p_deliverable_id UUID,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    version_number INTEGER,
    provider TEXT,
    status TEXT,
    external_url TEXT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        el.id,
        dv.version_number,
        el.provider,
        el.status,
        el.external_url,
        el.created_at
    FROM export_log el
    JOIN deliverable_versions dv ON dv.id = el.deliverable_version_id
    WHERE dv.deliverable_id = p_deliverable_id
    ORDER BY el.created_at DESC
    LIMIT p_limit;
END;
$$;

-- =============================================================================
-- Update Trigger for updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION update_integration_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_integrations_timestamp
    BEFORE UPDATE ON user_integrations
    FOR EACH ROW
    EXECUTE FUNCTION update_integration_timestamp();

CREATE TRIGGER update_export_preferences_timestamp
    BEFORE UPDATE ON deliverable_export_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_integration_timestamp();
