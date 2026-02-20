-- Migration: 077_platform_content.sql
-- ADR-072: Unified Content Layer and TP Execution Pipeline
-- Date: 2026-02-20
--
-- SINGULAR IMPLEMENTATION: Replaces filesystem_items entirely.
-- No parallel phase. Legacy table dropped at end of migration.
--
-- Key changes from filesystem_items:
--   1. Retention-based accumulation (retained flag vs TTL-only)
--   2. Content versioning (version_of FK chain)
--   3. Semantic search via pgvector embeddings
--   4. Provenance tracking (retained_reason, retained_ref)

-- =============================================================================
-- PHASE 1: CREATE PLATFORM_CONTENT TABLE
-- =============================================================================

CREATE TABLE platform_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Platform identification
    platform TEXT NOT NULL,              -- slack, gmail, notion, calendar
    resource_id TEXT NOT NULL,           -- channel_id, label, page_id, calendar_id
    resource_name TEXT,                  -- human-readable (#engineering, Inbox, etc.)
    item_id TEXT NOT NULL,               -- message_id, thread_id, event_id

    -- Content
    content TEXT NOT NULL,
    content_type TEXT,                   -- message, email, page, event
    content_hash TEXT,                   -- SHA-256 for deduplication on re-fetch
    title TEXT,                          -- subject line, page title, event title

    -- Semantic search (pgvector)
    content_embedding vector(1536),

    -- Versioning
    version_of UUID REFERENCES platform_content(id) ON DELETE SET NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Retention policy (ADR-072)
    retained BOOLEAN NOT NULL DEFAULT false,
    retained_reason TEXT,                -- 'deliverable_execution', 'signal_processing', 'tp_session'
    retained_ref UUID,                   -- FK to deliverable_version, signal_action, or session
    retained_at TIMESTAMPTZ,             -- when it was marked retained
    expires_at TIMESTAMPTZ,              -- NULL if retained=true, otherwise TTL

    -- Authorship (for style inference)
    author TEXT,
    author_id TEXT,
    is_user_authored BOOLEAN DEFAULT false,

    -- Source timestamp
    source_timestamp TIMESTAMPTZ,        -- when it happened at source

    -- Metadata
    metadata JSONB DEFAULT '{}',
    sync_batch_id UUID,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),

    -- Constraints
    CONSTRAINT platform_content_logical_identity UNIQUE (user_id, platform, resource_id, item_id, content_hash)
);

COMMENT ON TABLE platform_content IS
'ADR-072: Unified content layer with retention-based accumulation. Replaces filesystem_items.
Content that proves significant (referenced by deliverables, signals, or TP) is retained indefinitely.
Unreferenced content expires after TTL.';

COMMENT ON COLUMN platform_content.retained IS
'When true, content never expires. Set when content is referenced by downstream systems.';

COMMENT ON COLUMN platform_content.retained_reason IS
'What marked this content as retained: deliverable_execution, signal_processing, or tp_session.';

COMMENT ON COLUMN platform_content.retained_ref IS
'FK to the record that marked this content retained (deliverable_version_id, session_id, etc.).';


-- =============================================================================
-- PHASE 2: MIGRATE DATA FROM FILESYSTEM_ITEMS
-- =============================================================================

-- Migrate existing content (all as ephemeral, none pre-retained)
INSERT INTO platform_content (
    user_id,
    platform,
    resource_id,
    resource_name,
    item_id,
    content,
    content_type,
    title,
    author,
    author_id,
    is_user_authored,
    source_timestamp,
    metadata,
    sync_batch_id,
    fetched_at,
    retained,
    expires_at,
    created_at
)
SELECT
    user_id,
    platform,
    resource_id,
    resource_name,
    item_id,
    content,
    content_type,
    title,
    author,
    author_id,
    is_user_authored,
    source_timestamp,
    metadata,
    sync_batch_id,
    synced_at,           -- maps to fetched_at
    false,               -- all migrated content starts as non-retained
    expires_at,
    synced_at            -- created_at = synced_at for migrated rows
FROM filesystem_items
WHERE expires_at IS NULL OR expires_at > now();  -- only migrate non-expired

-- Log migration count
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count FROM platform_content;
    RAISE NOTICE 'Migrated % rows from filesystem_items to platform_content', v_count;
END $$;


-- =============================================================================
-- PHASE 3: INDEXES
-- =============================================================================

-- User + recent (primary query pattern)
CREATE INDEX idx_platform_content_user_recent
    ON platform_content(user_id, fetched_at DESC);

-- Retained content (the accumulation query)
CREATE INDEX idx_platform_content_retained
    ON platform_content(user_id, retained, fetched_at DESC)
    WHERE retained = true;

-- Expiring content (cleanup query)
CREATE INDEX idx_platform_content_expires
    ON platform_content(expires_at)
    WHERE expires_at IS NOT NULL AND retained = false;

-- Platform + resource (sync and search patterns)
CREATE INDEX idx_platform_content_user_platform
    ON platform_content(user_id, platform);

CREATE INDEX idx_platform_content_user_resource
    ON platform_content(user_id, platform, resource_id);

-- User-authored content (style inference)
CREATE INDEX idx_platform_content_user_authored
    ON platform_content(user_id, platform)
    WHERE is_user_authored = true;

-- Source timestamp (recency queries)
CREATE INDEX idx_platform_content_source_timestamp
    ON platform_content(user_id, source_timestamp DESC)
    WHERE source_timestamp IS NOT NULL;

-- Semantic search via pgvector
CREATE INDEX idx_platform_content_embedding
    ON platform_content USING ivfflat (content_embedding vector_cosine_ops)
    WITH (lists = 100)
    WHERE content_embedding IS NOT NULL;

-- Full-text search fallback
CREATE INDEX idx_platform_content_search
    ON platform_content USING gin (to_tsvector('english', content));

-- Version chain
CREATE INDEX idx_platform_content_version_chain
    ON platform_content(version_of)
    WHERE version_of IS NOT NULL;


-- =============================================================================
-- PHASE 4: ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE platform_content ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own platform content" ON platform_content
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Service role manages platform content" ON platform_content
    FOR ALL TO service_role USING (true);


-- =============================================================================
-- PHASE 5: HELPER FUNCTIONS
-- =============================================================================

-- Mark content as retained
CREATE OR REPLACE FUNCTION mark_content_retained(
    p_content_ids UUID[],
    p_reason TEXT,
    p_ref UUID DEFAULT NULL
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    UPDATE platform_content
    SET
        retained = true,
        retained_reason = p_reason,
        retained_ref = p_ref,
        retained_at = now(),
        expires_at = NULL
    WHERE id = ANY(p_content_ids)
      AND retained = false;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$;

-- Cleanup expired content
CREATE OR REPLACE FUNCTION cleanup_expired_platform_content(
    p_batch_size INTEGER DEFAULT 1000
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM platform_content
        WHERE id IN (
            SELECT id FROM platform_content
            WHERE retained = false
              AND expires_at IS NOT NULL
              AND expires_at < now()
            LIMIT p_batch_size
        )
        RETURNING id
    )
    SELECT COUNT(*) INTO v_count FROM deleted;

    RETURN v_count;
END;
$$;

-- Search platform content
CREATE OR REPLACE FUNCTION search_platform_content(
    p_user_id UUID,
    p_query_embedding vector(1536) DEFAULT NULL,
    p_query_text TEXT DEFAULT NULL,
    p_platforms TEXT[] DEFAULT NULL,
    p_resource_ids TEXT[] DEFAULT NULL,
    p_retained_only BOOLEAN DEFAULT false,
    p_limit INTEGER DEFAULT 50,
    p_similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id UUID,
    platform TEXT,
    resource_id TEXT,
    resource_name TEXT,
    item_id TEXT,
    content TEXT,
    content_type TEXT,
    title TEXT,
    author TEXT,
    source_timestamp TIMESTAMPTZ,
    retained BOOLEAN,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    IF p_query_embedding IS NOT NULL THEN
        RETURN QUERY
        SELECT
            pc.id,
            pc.platform,
            pc.resource_id,
            pc.resource_name,
            pc.item_id,
            pc.content,
            pc.content_type,
            pc.title,
            pc.author,
            pc.source_timestamp,
            pc.retained,
            (1 - (pc.content_embedding <=> p_query_embedding))::FLOAT as similarity
        FROM platform_content pc
        WHERE pc.user_id = p_user_id
          AND pc.content_embedding IS NOT NULL
          AND (p_platforms IS NULL OR pc.platform = ANY(p_platforms))
          AND (p_resource_ids IS NULL OR pc.resource_id = ANY(p_resource_ids))
          AND (NOT p_retained_only OR pc.retained = true)
          AND (pc.retained = true OR pc.expires_at IS NULL OR pc.expires_at > now())
          AND (1 - (pc.content_embedding <=> p_query_embedding)) >= p_similarity_threshold
        ORDER BY pc.content_embedding <=> p_query_embedding
        LIMIT p_limit;

    ELSIF p_query_text IS NOT NULL THEN
        RETURN QUERY
        SELECT
            pc.id,
            pc.platform,
            pc.resource_id,
            pc.resource_name,
            pc.item_id,
            pc.content,
            pc.content_type,
            pc.title,
            pc.author,
            pc.source_timestamp,
            pc.retained,
            ts_rank(to_tsvector('english', pc.content), plainto_tsquery('english', p_query_text))::FLOAT as similarity
        FROM platform_content pc
        WHERE pc.user_id = p_user_id
          AND to_tsvector('english', pc.content) @@ plainto_tsquery('english', p_query_text)
          AND (p_platforms IS NULL OR pc.platform = ANY(p_platforms))
          AND (p_resource_ids IS NULL OR pc.resource_id = ANY(p_resource_ids))
          AND (NOT p_retained_only OR pc.retained = true)
          AND (pc.retained = true OR pc.expires_at IS NULL OR pc.expires_at > now())
        ORDER BY similarity DESC
        LIMIT p_limit;

    ELSE
        RETURN QUERY
        SELECT
            pc.id,
            pc.platform,
            pc.resource_id,
            pc.resource_name,
            pc.item_id,
            pc.content,
            pc.content_type,
            pc.title,
            pc.author,
            pc.source_timestamp,
            pc.retained,
            1.0::FLOAT as similarity
        FROM platform_content pc
        WHERE pc.user_id = p_user_id
          AND (p_platforms IS NULL OR pc.platform = ANY(p_platforms))
          AND (p_resource_ids IS NULL OR pc.resource_id = ANY(p_resource_ids))
          AND (NOT p_retained_only OR pc.retained = true)
          AND (pc.retained = true OR pc.expires_at IS NULL OR pc.expires_at > now())
        ORDER BY pc.fetched_at DESC
        LIMIT p_limit;
    END IF;
END;
$$;


-- =============================================================================
-- PHASE 6: GRANTS
-- =============================================================================

GRANT ALL ON platform_content TO authenticated;
GRANT SELECT ON platform_content TO anon;

GRANT EXECUTE ON FUNCTION mark_content_retained TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_expired_platform_content TO service_role;
GRANT EXECUTE ON FUNCTION search_platform_content TO authenticated;


-- =============================================================================
-- PHASE 7: DROP LEGACY TABLE
-- =============================================================================

-- Drop filesystem_items indexes first
DROP INDEX IF EXISTS idx_filesystem_items_user_platform;
DROP INDEX IF EXISTS idx_filesystem_items_user_resource;
DROP INDEX IF EXISTS idx_filesystem_items_source_timestamp;
DROP INDEX IF EXISTS idx_filesystem_items_user_authored;
DROP INDEX IF EXISTS idx_filesystem_items_expires;

-- Drop filesystem_items RLS policies
DROP POLICY IF EXISTS "Users can view own filesystem items" ON filesystem_items;
DROP POLICY IF EXISTS "Service role can manage filesystem items" ON filesystem_items;

-- Drop the legacy table
DROP TABLE filesystem_items;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'ADR-072: filesystem_items dropped. platform_content is now the singular content layer.';
END $$;
