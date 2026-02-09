-- Migration: 034_emergent_context_domains.sql
-- ADR-034: Emergent Context Domains
--
-- Context domains emerge from deliverable source patterns, not upfront definition.
-- This migration adds:
-- 1. context_domains table (system-managed, user-adjustable)
-- 2. domain_sources table (maps sources to domains)
-- 3. deliverable_domains table (links deliverables to computed domains)
-- 4. domain_id column on memories
-- 5. domain_style_profiles table (per-domain learned styles)
-- 6. Helper functions for domain operations

-- =============================================================================
-- 1. CONTEXT DOMAINS TABLE
-- =============================================================================
-- Domains are system-computed from deliverable source overlap.
-- Users can rename but generally don't manage these directly.

CREATE TABLE IF NOT EXISTS context_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Domain identity
    name TEXT NOT NULL,                      -- Auto-generated or user-set
    name_source TEXT DEFAULT 'auto',         -- 'auto' or 'user' (preserves user renames)
    description TEXT,                        -- Optional user description

    -- Domain metadata
    is_default BOOLEAN DEFAULT false,        -- For "Uncategorized" domain
    color TEXT,                              -- Optional UI color

    -- Lifecycle
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- One default domain per user
    CONSTRAINT unique_default_domain UNIQUE (user_id, is_default)
        DEFERRABLE INITIALLY DEFERRED
);

-- Note: The unique constraint on (user_id, is_default) needs special handling
-- since we only want uniqueness when is_default = true
DROP INDEX IF EXISTS idx_unique_default_domain;
CREATE UNIQUE INDEX idx_unique_default_domain
    ON context_domains(user_id)
    WHERE is_default = true;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_context_domains_user
    ON context_domains(user_id);

-- RLS
ALTER TABLE context_domains ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own domains"
    ON context_domains FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can insert own domains"
    ON context_domains FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own domains"
    ON context_domains FOR UPDATE
    USING (user_id = auth.uid());

CREATE POLICY "Users can delete own domains"
    ON context_domains FOR DELETE
    USING (user_id = auth.uid());

CREATE POLICY "Service role can manage all domains"
    ON context_domains FOR ALL
    TO service_role
    USING (true);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_context_domains_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER context_domains_updated_at
    BEFORE UPDATE ON context_domains
    FOR EACH ROW
    EXECUTE FUNCTION update_context_domains_timestamp();


-- =============================================================================
-- 2. DOMAIN SOURCES TABLE
-- =============================================================================
-- Maps platform resources (channels, labels, pages) to domains.
-- Computed from deliverable sources, not directly user-managed.

CREATE TABLE IF NOT EXISTS domain_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES context_domains(id) ON DELETE CASCADE,

    -- Source identification (matches deliverable source format)
    provider TEXT NOT NULL,                  -- slack, gmail, notion, calendar
    resource_id TEXT NOT NULL,               -- Channel ID, label name, page ID
    resource_name TEXT,                      -- Human-readable name for display

    -- How this mapping was established
    mapping_source TEXT DEFAULT 'inferred',  -- 'inferred' (from deliverables) or 'manual'

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),

    -- No duplicate source-to-domain mappings
    UNIQUE(domain_id, provider, resource_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_domain_sources_domain
    ON domain_sources(domain_id);
CREATE INDEX IF NOT EXISTS idx_domain_sources_lookup
    ON domain_sources(provider, resource_id);

-- RLS (inherits from domain ownership)
ALTER TABLE domain_sources ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view sources in own domains"
    ON domain_sources FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM context_domains cd
            WHERE cd.id = domain_id
            AND cd.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can manage sources in own domains"
    ON domain_sources FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM context_domains cd
            WHERE cd.id = domain_id
            AND cd.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role can manage all domain sources"
    ON domain_sources FOR ALL
    TO service_role
    USING (true);


-- =============================================================================
-- 3. DELIVERABLE DOMAINS TABLE
-- =============================================================================
-- Links deliverables to their computed domain(s).
-- A deliverable belongs to exactly one domain (determined by source overlap).

CREATE TABLE IF NOT EXISTS deliverable_domains (
    deliverable_id UUID NOT NULL REFERENCES deliverables(id) ON DELETE CASCADE,
    domain_id UUID NOT NULL REFERENCES context_domains(id) ON DELETE CASCADE,

    -- Metadata
    computed_at TIMESTAMPTZ DEFAULT now(),   -- When this link was computed

    PRIMARY KEY (deliverable_id)             -- One domain per deliverable
);

-- Index for domain lookups
CREATE INDEX IF NOT EXISTS idx_deliverable_domains_domain
    ON deliverable_domains(domain_id);

-- RLS (inherits from deliverable ownership)
ALTER TABLE deliverable_domains ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view deliverable domains for own deliverables"
    ON deliverable_domains FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM deliverables d
            WHERE d.id = deliverable_id
            AND d.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role can manage all deliverable domains"
    ON deliverable_domains FOR ALL
    TO service_role
    USING (true);


-- =============================================================================
-- 4. ADD DOMAIN_ID TO MEMORIES
-- =============================================================================
-- Memories are now scoped to domains instead of projects.

ALTER TABLE memories
    ADD COLUMN IF NOT EXISTS domain_id UUID REFERENCES context_domains(id);

-- Index for domain-scoped retrieval
CREATE INDEX IF NOT EXISTS idx_memories_domain
    ON memories(domain_id)
    WHERE is_active = true;

-- Comment explaining the relationship
COMMENT ON COLUMN memories.domain_id IS
    'Context domain this memory belongs to. NULL means uncategorized or pre-domain migration.';

-- Note: project_id is retained for backward compatibility during migration
-- It will be deprecated once domain migration is complete


-- =============================================================================
-- 5. DOMAIN STYLE PROFILES
-- =============================================================================
-- Learned communication styles per domain, per platform.

CREATE TABLE IF NOT EXISTS domain_style_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES context_domains(id) ON DELETE CASCADE,

    -- Platform-specific style
    platform TEXT NOT NULL,                  -- slack, gmail, notion

    -- Learned style characteristics
    style_attributes JSONB DEFAULT '{}',
    -- Example structure:
    -- {
    --   "tone": "casual" | "formal" | "mixed",
    --   "structure": "bullets" | "prose" | "mixed",
    --   "greeting_style": "Hey" | "Hi" | "Hello" | "none",
    --   "sign_off_style": "Thanks" | "Best" | "Cheers" | "none",
    --   "avg_length": "short" | "medium" | "long",
    --   "uses_emoji": true | false,
    --   "sample_phrases": ["..."]
    -- }

    -- Training metadata
    sample_count INTEGER DEFAULT 0,          -- Number of samples used for learning
    last_trained_at TIMESTAMPTZ,
    training_source_ref JSONB,               -- Reference to training data

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- One style profile per domain per platform
    UNIQUE(domain_id, platform)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_domain_style_profiles_domain
    ON domain_style_profiles(domain_id);

-- RLS
ALTER TABLE domain_style_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view style profiles for own domains"
    ON domain_style_profiles FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM context_domains cd
            WHERE cd.id = domain_id
            AND cd.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can manage style profiles for own domains"
    ON domain_style_profiles FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM context_domains cd
            WHERE cd.id = domain_id
            AND cd.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role can manage all style profiles"
    ON domain_style_profiles FOR ALL
    TO service_role
    USING (true);

-- Updated_at trigger
CREATE TRIGGER domain_style_profiles_updated_at
    BEFORE UPDATE ON domain_style_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_context_domains_timestamp();


-- =============================================================================
-- 6. HELPER FUNCTIONS
-- =============================================================================

-- Get or create default (uncategorized) domain for a user
CREATE OR REPLACE FUNCTION get_or_create_default_domain(p_user_id UUID)
RETURNS UUID AS $$
DECLARE
    v_domain_id UUID;
BEGIN
    -- Try to find existing default domain
    SELECT id INTO v_domain_id
    FROM context_domains
    WHERE user_id = p_user_id AND is_default = true;

    -- Create if doesn't exist
    IF v_domain_id IS NULL THEN
        INSERT INTO context_domains (user_id, name, name_source, is_default)
        VALUES (p_user_id, 'Uncategorized', 'auto', true)
        RETURNING id INTO v_domain_id;
    END IF;

    RETURN v_domain_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Find domain for a given source (returns NULL if source not in any domain)
CREATE OR REPLACE FUNCTION find_domain_for_source(
    p_user_id UUID,
    p_provider TEXT,
    p_resource_id TEXT
)
RETURNS UUID AS $$
DECLARE
    v_domain_id UUID;
BEGIN
    SELECT ds.domain_id INTO v_domain_id
    FROM domain_sources ds
    JOIN context_domains cd ON cd.id = ds.domain_id
    WHERE cd.user_id = p_user_id
      AND ds.provider = p_provider
      AND ds.resource_id = p_resource_id
    LIMIT 1;

    RETURN v_domain_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Get all sources for a domain
CREATE OR REPLACE FUNCTION get_domain_sources(p_domain_id UUID)
RETURNS TABLE (
    provider TEXT,
    resource_id TEXT,
    resource_name TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT ds.provider, ds.resource_id, ds.resource_name
    FROM domain_sources ds
    WHERE ds.domain_id = p_domain_id
    ORDER BY ds.provider, ds.resource_name;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Get domain for a deliverable
CREATE OR REPLACE FUNCTION get_deliverable_domain(p_deliverable_id UUID)
RETURNS UUID AS $$
DECLARE
    v_domain_id UUID;
BEGIN
    SELECT domain_id INTO v_domain_id
    FROM deliverable_domains
    WHERE deliverable_id = p_deliverable_id;

    RETURN v_domain_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Get user's domains with summary stats
CREATE OR REPLACE FUNCTION get_user_domains_summary(p_user_id UUID)
RETURNS TABLE (
    id UUID,
    name TEXT,
    name_source TEXT,
    is_default BOOLEAN,
    source_count BIGINT,
    deliverable_count BIGINT,
    memory_count BIGINT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cd.id,
        cd.name,
        cd.name_source,
        cd.is_default,
        (SELECT COUNT(*) FROM domain_sources ds WHERE ds.domain_id = cd.id) as source_count,
        (SELECT COUNT(*) FROM deliverable_domains dd WHERE dd.domain_id = cd.id) as deliverable_count,
        (SELECT COUNT(*) FROM memories m WHERE m.domain_id = cd.id AND m.is_active = true) as memory_count,
        cd.created_at
    FROM context_domains cd
    WHERE cd.user_id = p_user_id
    ORDER BY cd.is_default ASC, cd.name;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- =============================================================================
-- 7. DATA MIGRATION
-- =============================================================================
-- Migrate existing data to use domains

-- Step 1: Create default domain for each user who has memories or deliverables
INSERT INTO context_domains (user_id, name, name_source, is_default)
SELECT DISTINCT user_id, 'Uncategorized', 'auto', true
FROM (
    SELECT user_id FROM memories WHERE is_active = true
    UNION
    SELECT user_id FROM deliverables
) users
WHERE NOT EXISTS (
    SELECT 1 FROM context_domains cd
    WHERE cd.user_id = users.user_id AND cd.is_default = true
);

-- Step 2: Assign existing memories without domain_id to default domain
UPDATE memories m
SET domain_id = (
    SELECT id FROM context_domains cd
    WHERE cd.user_id = m.user_id AND cd.is_default = true
)
WHERE m.domain_id IS NULL AND m.is_active = true;

-- Step 3: Link existing deliverables to default domain
-- (Will be recomputed when domain inference runs)
INSERT INTO deliverable_domains (deliverable_id, domain_id)
SELECT d.id, cd.id
FROM deliverables d
JOIN context_domains cd ON cd.user_id = d.user_id AND cd.is_default = true
WHERE NOT EXISTS (
    SELECT 1 FROM deliverable_domains dd WHERE dd.deliverable_id = d.id
);


-- =============================================================================
-- 8. GRANTS
-- =============================================================================

GRANT ALL ON context_domains TO authenticated;
GRANT ALL ON domain_sources TO authenticated;
GRANT ALL ON deliverable_domains TO authenticated;
GRANT ALL ON domain_style_profiles TO authenticated;

GRANT SELECT ON context_domains TO anon;
GRANT SELECT ON domain_sources TO anon;
GRANT SELECT ON deliverable_domains TO anon;
GRANT SELECT ON domain_style_profiles TO anon;

GRANT EXECUTE ON FUNCTION get_or_create_default_domain TO authenticated;
GRANT EXECUTE ON FUNCTION find_domain_for_source TO authenticated;
GRANT EXECUTE ON FUNCTION get_domain_sources TO authenticated;
GRANT EXECUTE ON FUNCTION get_deliverable_domain TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_domains_summary TO authenticated;
