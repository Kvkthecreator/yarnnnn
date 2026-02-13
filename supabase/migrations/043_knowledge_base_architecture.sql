-- Migration: 043_knowledge_base_architecture.sql
-- ADR-058: Knowledge Base Architecture
-- Date: 2026-02-13
--
-- This migration implements the Filesystem + Knowledge architecture:
-- 1. Renames existing tables to align with new terminology
-- 2. Creates Knowledge tables (profile, styles, domains, entries)
-- 3. Migrates data from old schema to new
-- 4. Updates indexes and RLS policies
--
-- TERMINOLOGY ALIGNMENT:
--   ephemeral_context    → filesystem_items
--   documents            → filesystem_documents
--   chunks               → filesystem_chunks
--   user_integrations    → platform_connections
--   context_domains      → knowledge_domains
--   memories (user facts)→ knowledge_entries
--
-- NOTE: This is a breaking migration. Run only on clean database or with
-- careful data migration in production.

-- =============================================================================
-- PHASE 1: CREATE NEW FILESYSTEM TABLES
-- =============================================================================

-- Platform OAuth connections (renamed from user_integrations)
CREATE TABLE IF NOT EXISTS platform_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,  -- 'slack', 'gmail', 'notion', 'calendar'
    status TEXT DEFAULT 'active',

    -- Credentials (encrypted)
    credentials_encrypted TEXT,
    refresh_token_encrypted TEXT,

    -- Platform-specific metadata
    metadata JSONB DEFAULT '{}',  -- workspace_id, team_name, user_email, etc.
    settings JSONB DEFAULT '{}',  -- user preferences for this connection

    -- Sync state
    last_synced_at TIMESTAMPTZ,
    landscape JSONB,              -- discovered resources
    landscape_discovered_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(user_id, platform)
);

-- Synced platform content (renamed from ephemeral_context)
CREATE TABLE IF NOT EXISTS filesystem_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Location
    platform TEXT NOT NULL,       -- 'slack', 'gmail', 'notion', 'calendar'
    resource_id TEXT NOT NULL,    -- channel_id, label, page_id, calendar_id
    resource_name TEXT,           -- "#engineering", "Inbox", "Project Specs"
    item_id TEXT NOT NULL,        -- message_ts, email_id, block_id, event_id

    -- Content
    content TEXT NOT NULL,
    content_type TEXT,            -- 'message', 'email', 'page', 'event'
    title TEXT,                   -- subject line, page title, event title

    -- Authorship (for style inference)
    author TEXT,                  -- who wrote this
    author_id TEXT,               -- platform-specific author ID
    is_user_authored BOOLEAN DEFAULT false,  -- did the YARNNN user write this?

    -- Timestamps
    source_timestamp TIMESTAMPTZ, -- when it happened on platform
    synced_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,       -- TTL for cleanup

    -- Metadata
    metadata JSONB DEFAULT '{}',
    sync_batch_id UUID,
    sync_metadata JSONB DEFAULT '{}',

    UNIQUE(user_id, platform, resource_id, item_id)
);

-- Uploaded documents (renamed from documents)
CREATE TABLE IF NOT EXISTS filesystem_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- File info
    filename TEXT NOT NULL,
    file_type TEXT,               -- 'pdf', 'docx', 'txt', 'md'
    file_size INTEGER,
    storage_path TEXT NOT NULL,

    -- Processing state
    processing_status TEXT DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    processed_at TIMESTAMPTZ,
    error_message TEXT,

    -- Extracted metadata
    page_count INTEGER,
    word_count INTEGER,

    uploaded_at TIMESTAMPTZ DEFAULT now()
);

-- Document chunks for retrieval (renamed from chunks)
CREATE TABLE IF NOT EXISTS filesystem_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES filesystem_documents(id) ON DELETE CASCADE,

    -- Content
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER,

    -- Embedding for semantic search
    embedding vector(1536),
    token_count INTEGER,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT now()
);

-- Sync state tracking (kept as-is, just ensuring it exists)
CREATE TABLE IF NOT EXISTS sync_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_name TEXT,

    last_synced_at TIMESTAMPTZ,
    platform_cursor TEXT,
    item_count INTEGER DEFAULT 0,
    sync_metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(user_id, platform, resource_id)
);


-- =============================================================================
-- PHASE 2: CREATE KNOWLEDGE TABLES
-- =============================================================================

-- User profile (inferred + editable)
CREATE TABLE IF NOT EXISTS knowledge_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Inferred fields (from filesystem analysis)
    inferred_name TEXT,
    inferred_role TEXT,
    inferred_company TEXT,
    inferred_timezone TEXT,
    inferred_summary TEXT,

    -- User overrides (take precedence when set)
    stated_name TEXT,
    stated_role TEXT,
    stated_company TEXT,
    stated_timezone TEXT,
    stated_summary TEXT,

    -- Inference metadata
    last_inferred_at TIMESTAMPTZ,
    inference_sources JSONB DEFAULT '[]',
    inference_confidence FLOAT,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Platform-specific communication styles
CREATE TABLE IF NOT EXISTS knowledge_styles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,  -- 'slack', 'email', 'notion'

    -- Inferred style attributes
    tone TEXT,               -- 'casual', 'formal', 'mixed'
    verbosity TEXT,          -- 'minimal', 'moderate', 'detailed'
    formatting JSONB DEFAULT '{}',  -- {uses_emoji, uses_bullets, avg_length, etc.}
    vocabulary_notes TEXT,
    sample_excerpts TEXT[],  -- Examples of user's actual writing

    -- User overrides
    stated_preferences JSONB DEFAULT '{}',

    -- Inference metadata
    sample_count INTEGER DEFAULT 0,
    last_inferred_at TIMESTAMPTZ,
    inference_sources JSONB DEFAULT '[]',

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(user_id, platform)
);

-- Work domains (inferred from deliverable patterns)
CREATE TABLE IF NOT EXISTS knowledge_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Identity
    name TEXT NOT NULL,
    name_source TEXT DEFAULT 'inferred',  -- 'inferred' or 'user'

    -- Inferred narrative
    summary TEXT,
    key_facts TEXT[] DEFAULT '{}',
    key_people JSONB DEFAULT '[]',
    key_decisions TEXT[] DEFAULT '{}',

    -- Source mapping (which filesystem resources belong here)
    sources JSONB DEFAULT '[]',  -- [{platform, resource_id, resource_name}]

    -- Flags
    is_default BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,

    -- Inference metadata
    last_inferred_at TIMESTAMPTZ,
    inference_confidence FLOAT,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- General knowledge entries (preferences, facts, decisions)
CREATE TABLE IF NOT EXISTS knowledge_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    domain_id UUID REFERENCES knowledge_domains(id) ON DELETE SET NULL,

    -- Content
    content TEXT NOT NULL,
    entry_type TEXT NOT NULL,  -- 'preference', 'fact', 'decision', 'instruction'

    -- Source tracking
    source TEXT NOT NULL,      -- 'inferred', 'user_stated', 'document', 'conversation'
    source_ref JSONB,          -- {table, id} for traceability

    -- For inferred entries
    confidence FLOAT,
    inference_sources JSONB DEFAULT '[]',

    -- Organization
    tags TEXT[] DEFAULT '{}',
    importance FLOAT DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),

    -- Lifecycle
    is_active BOOLEAN DEFAULT true,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);


-- =============================================================================
-- PHASE 3: UPDATE SESSION TABLES
-- =============================================================================

-- Add knowledge extraction tracking to session_messages if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'session_messages'
        AND column_name = 'knowledge_extracted'
    ) THEN
        ALTER TABLE session_messages
        ADD COLUMN knowledge_extracted BOOLEAN DEFAULT false,
        ADD COLUMN knowledge_extracted_at TIMESTAMPTZ;
    END IF;
END $$;

-- Add domain_id to chat_sessions if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'chat_sessions'
        AND column_name = 'domain_id'
    ) THEN
        ALTER TABLE chat_sessions
        ADD COLUMN domain_id UUID REFERENCES knowledge_domains(id) ON DELETE SET NULL;
    END IF;
END $$;


-- =============================================================================
-- PHASE 4: UPDATE DELIVERABLES REFERENCES
-- =============================================================================

-- Add domain_id to deliverables if not exists (pointing to new table)
-- Note: We'll migrate the foreign key reference in a separate step
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'deliverables'
        AND column_name = 'knowledge_domain_id'
    ) THEN
        ALTER TABLE deliverables
        ADD COLUMN knowledge_domain_id UUID REFERENCES knowledge_domains(id) ON DELETE SET NULL;
    END IF;
END $$;


-- =============================================================================
-- PHASE 5: INDEXES
-- =============================================================================

-- Filesystem indexes
CREATE INDEX IF NOT EXISTS idx_filesystem_items_user_platform
    ON filesystem_items(user_id, platform);
CREATE INDEX IF NOT EXISTS idx_filesystem_items_user_resource
    ON filesystem_items(user_id, platform, resource_id);
CREATE INDEX IF NOT EXISTS idx_filesystem_items_source_timestamp
    ON filesystem_items(source_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_filesystem_items_user_authored
    ON filesystem_items(user_id, platform) WHERE is_user_authored = true;
CREATE INDEX IF NOT EXISTS idx_filesystem_items_expires
    ON filesystem_items(expires_at) WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_filesystem_documents_user
    ON filesystem_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_filesystem_documents_status
    ON filesystem_documents(processing_status);

CREATE INDEX IF NOT EXISTS idx_filesystem_chunks_document
    ON filesystem_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_filesystem_chunks_embedding
    ON filesystem_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100) WHERE embedding IS NOT NULL;

-- Knowledge indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_styles_user
    ON knowledge_styles(user_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_domains_user
    ON knowledge_domains(user_id) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_knowledge_domains_default
    ON knowledge_domains(user_id) WHERE is_default = true;
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_user
    ON knowledge_entries(user_id) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_domain
    ON knowledge_entries(domain_id) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_type
    ON knowledge_entries(entry_type) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_tags
    ON knowledge_entries USING gin(tags) WHERE is_active = true;

-- Platform connections indexes
CREATE INDEX IF NOT EXISTS idx_platform_connections_user
    ON platform_connections(user_id);


-- =============================================================================
-- PHASE 6: ROW LEVEL SECURITY
-- =============================================================================

-- Enable RLS on all new tables
ALTER TABLE platform_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE filesystem_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE filesystem_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE filesystem_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_styles ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_domains ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_entries ENABLE ROW LEVEL SECURITY;

-- Platform connections policies
CREATE POLICY "Users can manage own platform connections" ON platform_connections
    FOR ALL USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Filesystem items policies
CREATE POLICY "Users can view own filesystem items" ON filesystem_items
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Service role can manage filesystem items" ON filesystem_items
    FOR ALL TO service_role USING (true);

-- Filesystem documents policies
CREATE POLICY "Users can manage own documents" ON filesystem_documents
    FOR ALL USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Filesystem chunks policies (access via document ownership)
CREATE POLICY "Users can view chunks of own documents" ON filesystem_chunks
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM filesystem_documents d
            WHERE d.id = filesystem_chunks.document_id
            AND d.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role can manage chunks" ON filesystem_chunks
    FOR ALL TO service_role USING (true);

-- Knowledge profile policies
CREATE POLICY "Users can manage own profile" ON knowledge_profile
    FOR ALL USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Knowledge styles policies
CREATE POLICY "Users can manage own styles" ON knowledge_styles
    FOR ALL USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Knowledge domains policies
CREATE POLICY "Users can manage own domains" ON knowledge_domains
    FOR ALL USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Knowledge entries policies
CREATE POLICY "Users can manage own entries" ON knowledge_entries
    FOR ALL USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());


-- =============================================================================
-- PHASE 7: HELPER FUNCTIONS
-- =============================================================================

-- Get effective profile value (stated takes precedence over inferred)
CREATE OR REPLACE FUNCTION get_effective_profile(p_user_id UUID)
RETURNS TABLE (
    name TEXT,
    role TEXT,
    company TEXT,
    timezone TEXT,
    summary TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(kp.stated_name, kp.inferred_name) as name,
        COALESCE(kp.stated_role, kp.inferred_role) as role,
        COALESCE(kp.stated_company, kp.inferred_company) as company,
        COALESCE(kp.stated_timezone, kp.inferred_timezone) as timezone,
        COALESCE(kp.stated_summary, kp.inferred_summary) as summary
    FROM knowledge_profile kp
    WHERE kp.user_id = p_user_id;
END;
$$;

-- Get or create default domain for user
CREATE OR REPLACE FUNCTION get_or_create_default_domain(p_user_id UUID)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_domain_id UUID;
BEGIN
    -- Try to find existing default domain
    SELECT id INTO v_domain_id
    FROM knowledge_domains
    WHERE user_id = p_user_id AND is_default = true
    LIMIT 1;

    -- Create if not exists
    IF v_domain_id IS NULL THEN
        INSERT INTO knowledge_domains (user_id, name, name_source, is_default)
        VALUES (p_user_id, 'Personal', 'system', true)
        RETURNING id INTO v_domain_id;
    END IF;

    RETURN v_domain_id;
END;
$$;

-- Get knowledge entries by importance
CREATE OR REPLACE FUNCTION get_knowledge_entries_by_importance(
    p_user_id UUID,
    p_domain_id UUID DEFAULT NULL,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    entry_type TEXT,
    source TEXT,
    importance FLOAT,
    tags TEXT[],
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ke.id,
        ke.content,
        ke.entry_type,
        ke.source,
        ke.importance,
        ke.tags,
        ke.created_at
    FROM knowledge_entries ke
    WHERE ke.user_id = p_user_id
      AND ke.is_active = true
      AND (p_domain_id IS NULL OR ke.domain_id IS NULL OR ke.domain_id = p_domain_id)
    ORDER BY ke.importance DESC, ke.created_at DESC
    LIMIT p_limit;
END;
$$;


-- =============================================================================
-- PHASE 8: UPDATED_AT TRIGGERS
-- =============================================================================

-- Generic updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN
        SELECT unnest(ARRAY[
            'platform_connections',
            'sync_registry',
            'knowledge_profile',
            'knowledge_styles',
            'knowledge_domains',
            'knowledge_entries'
        ])
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_%s_updated_at ON %s;
            CREATE TRIGGER update_%s_updated_at
                BEFORE UPDATE ON %s
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        ', t, t, t, t);
    END LOOP;
END $$;


-- =============================================================================
-- PHASE 9: GRANTS
-- =============================================================================

GRANT ALL ON platform_connections TO authenticated;
GRANT ALL ON filesystem_items TO authenticated;
GRANT ALL ON filesystem_documents TO authenticated;
GRANT ALL ON filesystem_chunks TO authenticated;
GRANT ALL ON knowledge_profile TO authenticated;
GRANT ALL ON knowledge_styles TO authenticated;
GRANT ALL ON knowledge_domains TO authenticated;
GRANT ALL ON knowledge_entries TO authenticated;
GRANT ALL ON sync_registry TO authenticated;

GRANT SELECT ON platform_connections TO anon;
GRANT SELECT ON filesystem_items TO anon;
GRANT SELECT ON filesystem_documents TO anon;
GRANT SELECT ON filesystem_chunks TO anon;
GRANT SELECT ON knowledge_profile TO anon;
GRANT SELECT ON knowledge_styles TO anon;
GRANT SELECT ON knowledge_domains TO anon;
GRANT SELECT ON knowledge_entries TO anon;


-- =============================================================================
-- PHASE 10: COMMENTS
-- =============================================================================

COMMENT ON TABLE platform_connections IS
'ADR-058: OAuth connections to external platforms (Slack, Gmail, Notion, Calendar). Renamed from user_integrations.';

COMMENT ON TABLE filesystem_items IS
'ADR-058: Synced platform content - the "filesystem" that TP reads. Renamed from ephemeral_context.';

COMMENT ON TABLE filesystem_documents IS
'ADR-058: Uploaded documents - part of the filesystem. Renamed from documents.';

COMMENT ON TABLE filesystem_chunks IS
'ADR-058: Document chunks for retrieval. Renamed from chunks.';

COMMENT ON TABLE knowledge_profile IS
'ADR-058: User profile - inferred from filesystem + user overrides. Part of the Knowledge layer.';

COMMENT ON TABLE knowledge_styles IS
'ADR-058: Platform-specific communication styles - inferred from user-authored messages.';

COMMENT ON TABLE knowledge_domains IS
'ADR-058: Work domains - inferred from deliverable source patterns. Renamed from context_domains.';

COMMENT ON TABLE knowledge_entries IS
'ADR-058: General knowledge entries (preferences, facts, decisions) - inferred + user-stated. Replaces memories for user facts.';
