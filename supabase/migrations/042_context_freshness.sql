-- ADR-049: Context Freshness Model
-- Adds source snapshot tracking and sync metadata for context freshness management

-- =============================================================================
-- 1. Add source_snapshots to deliverable_versions
-- =============================================================================
-- Records what sources were used at generation time (immutable audit trail)

ALTER TABLE deliverable_versions
ADD COLUMN IF NOT EXISTS source_snapshots JSONB DEFAULT '[]';

COMMENT ON COLUMN deliverable_versions.source_snapshots IS
'ADR-049: Immutable record of source states at generation time. Structure: [{platform, resource_id, resource_name, synced_at, platform_cursor, item_count}]';

-- =============================================================================
-- 2. Add sync_metadata to ephemeral_context
-- =============================================================================
-- Tracks current sync state for freshness checks

ALTER TABLE ephemeral_context
ADD COLUMN IF NOT EXISTS sync_metadata JSONB DEFAULT '{}';

COMMENT ON COLUMN ephemeral_context.sync_metadata IS
'ADR-049: Current sync state for freshness checks. Structure: {synced_at, platform_cursor, item_count, source_latest_at}';

-- =============================================================================
-- 3. Create sync_registry table for source-level freshness tracking
-- =============================================================================
-- Enables freshness checks without scanning all ephemeral_context rows

CREATE TABLE IF NOT EXISTS sync_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_name TEXT,

    -- Sync state
    last_synced_at TIMESTAMPTZ,
    platform_cursor TEXT,  -- Platform-specific position marker (e.g., Slack message ts)
    item_count INTEGER DEFAULT 0,
    source_latest_at TIMESTAMPTZ,  -- Latest item timestamp from platform

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(user_id, platform, resource_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sync_registry_user_platform ON sync_registry(user_id, platform);
CREATE INDEX IF NOT EXISTS idx_sync_registry_staleness ON sync_registry(user_id, last_synced_at);

-- RLS
ALTER TABLE sync_registry ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own sync registry"
ON sync_registry FOR SELECT
USING (user_id = auth.uid());

CREATE POLICY "Users can manage their own sync registry"
ON sync_registry FOR ALL
USING (user_id = auth.uid());

COMMENT ON TABLE sync_registry IS
'ADR-049: Source-level sync tracking for context freshness. Enables efficient freshness checks without scanning ephemeral_context.';

-- =============================================================================
-- 4. Helper function to check source freshness
-- =============================================================================

CREATE OR REPLACE FUNCTION check_source_freshness(
    p_user_id UUID,
    p_platform TEXT,
    p_resource_id TEXT
) RETURNS JSONB AS $$
DECLARE
    v_sync_state RECORD;
BEGIN
    SELECT
        last_synced_at,
        platform_cursor,
        item_count,
        source_latest_at
    INTO v_sync_state
    FROM sync_registry
    WHERE user_id = p_user_id
      AND platform = p_platform
      AND resource_id = p_resource_id;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'synced', false,
            'message', 'Source not synced yet'
        );
    END IF;

    RETURN jsonb_build_object(
        'synced', true,
        'last_synced_at', v_sync_state.last_synced_at,
        'platform_cursor', v_sync_state.platform_cursor,
        'item_count', v_sync_state.item_count,
        'source_latest_at', v_sync_state.source_latest_at
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =============================================================================
-- 5. Helper function to update sync registry after sync
-- =============================================================================

CREATE OR REPLACE FUNCTION update_sync_registry(
    p_user_id UUID,
    p_platform TEXT,
    p_resource_id TEXT,
    p_resource_name TEXT,
    p_platform_cursor TEXT,
    p_item_count INTEGER,
    p_source_latest_at TIMESTAMPTZ
) RETURNS UUID AS $$
DECLARE
    v_id UUID;
BEGIN
    INSERT INTO sync_registry (
        user_id, platform, resource_id, resource_name,
        last_synced_at, platform_cursor, item_count, source_latest_at,
        updated_at
    ) VALUES (
        p_user_id, p_platform, p_resource_id, p_resource_name,
        now(), p_platform_cursor, p_item_count, p_source_latest_at,
        now()
    )
    ON CONFLICT (user_id, platform, resource_id) DO UPDATE SET
        resource_name = COALESCE(EXCLUDED.resource_name, sync_registry.resource_name),
        last_synced_at = now(),
        platform_cursor = EXCLUDED.platform_cursor,
        item_count = EXCLUDED.item_count,
        source_latest_at = EXCLUDED.source_latest_at,
        updated_at = now()
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
