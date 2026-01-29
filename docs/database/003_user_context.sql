-- Migration: 003_user_context.sql
-- ADR-004: Two-Layer Memory Architecture
-- Creates user_context table for user-level memory (portable across projects)

-- =============================================================================
-- Table: user_context
-- =============================================================================
-- User-scoped memory that persists across all projects.
-- Stores preferences, business facts, goals, etc.

CREATE TABLE IF NOT EXISTS user_context (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Classification
    category TEXT NOT NULL,  -- preference, business_fact, work_pattern, communication_style, goal, constraint, relationship
    key TEXT NOT NULL,       -- Unique identifier within category (for upsert deduplication)

    -- Content
    content TEXT NOT NULL,

    -- Scoring
    importance FLOAT DEFAULT 0.5,      -- 0-1 for retrieval priority
    confidence FLOAT DEFAULT 0.8,      -- 0-1 how confident we are in this

    -- Source tracking
    source_type TEXT DEFAULT 'extracted',  -- extracted, explicit, inferred
    source_project_id UUID REFERENCES projects(id) ON DELETE SET NULL,  -- Where it came from (optional)

    -- Lifecycle
    last_referenced_at TIMESTAMPTZ,    -- When last used in context assembly
    reference_count INTEGER DEFAULT 0,  -- How often referenced
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Upsert constraint: (user_id, category, key) must be unique
    CONSTRAINT unique_user_context UNIQUE (user_id, category, key)
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_user_context_user ON user_context(user_id);
CREATE INDEX IF NOT EXISTS idx_user_context_category ON user_context(category);
CREATE INDEX IF NOT EXISTS idx_user_context_importance ON user_context(importance DESC);

-- =============================================================================
-- Row Level Security
-- =============================================================================

ALTER TABLE user_context ENABLE ROW LEVEL SECURITY;

-- Users can only see/manage their own context
CREATE POLICY "Users can view own context"
    ON user_context FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can insert own context"
    ON user_context FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own context"
    ON user_context FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete own context"
    ON user_context FOR DELETE
    USING (user_id = auth.uid());

-- =============================================================================
-- Grants (for authenticated users via Supabase)
-- =============================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON user_context TO authenticated;

-- =============================================================================
-- Update extraction_logs to support user-only extraction
-- =============================================================================
-- Add user_id column if not exists (for tracking global chat extractions)

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'extraction_logs' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE extraction_logs ADD COLUMN user_id UUID REFERENCES auth.users(id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'extraction_logs' AND column_name = 'user_items_extracted'
    ) THEN
        ALTER TABLE extraction_logs ADD COLUMN user_items_extracted INTEGER DEFAULT 0;
    END IF;
END $$;

-- Make project_id nullable for global chat extractions
ALTER TABLE extraction_logs ALTER COLUMN project_id DROP NOT NULL;

-- =============================================================================
-- Update blocks table with semantic_type and importance columns
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'blocks' AND column_name = 'semantic_type'
    ) THEN
        ALTER TABLE blocks ADD COLUMN semantic_type TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'blocks' AND column_name = 'importance'
    ) THEN
        ALTER TABLE blocks ADD COLUMN importance FLOAT DEFAULT 0.5;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'blocks' AND column_name = 'source_type'
    ) THEN
        ALTER TABLE blocks ADD COLUMN source_type TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'blocks' AND column_name = 'source_ref'
    ) THEN
        ALTER TABLE blocks ADD COLUMN source_ref TEXT;
    END IF;
END $$;

-- =============================================================================
-- Update agent_sessions to allow null project_id (for global chat)
-- =============================================================================

ALTER TABLE agent_sessions ALTER COLUMN project_id DROP NOT NULL;
