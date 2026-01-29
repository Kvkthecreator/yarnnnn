-- Migration: 005_user_context_layer.sql
-- Implements ADR-004: Two-Layer Memory Architecture

-- ============================================
-- USER CONTEXT TABLE (User-scoped memory)
-- ============================================

CREATE TABLE IF NOT EXISTS user_context (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Classification (7 categories)
    -- preference, business_fact, work_pattern, communication_style, goal, constraint, relationship
    category TEXT NOT NULL,
    key TEXT NOT NULL,       -- Unique identifier within category (for upsert)

    -- Content
    content TEXT NOT NULL,

    -- Scoring
    importance FLOAT DEFAULT 0.5,      -- 0-1 for retrieval priority
    confidence FLOAT DEFAULT 0.8,      -- 0-1 how confident extraction is

    -- Source tracking
    source_type TEXT DEFAULT 'extracted',  -- extracted, explicit, inferred
    source_project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

    -- Lifecycle
    last_referenced_at TIMESTAMPTZ,    -- When last used in context assembly
    reference_count INTEGER DEFAULT 0,  -- How often referenced
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Upsert constraint: same user + category + key = update, not duplicate
    CONSTRAINT unique_user_context UNIQUE (user_id, category, key)
);

-- Indexes for efficient retrieval
CREATE INDEX IF NOT EXISTS idx_user_context_user ON user_context(user_id);
CREATE INDEX IF NOT EXISTS idx_user_context_category ON user_context(category);
CREATE INDEX IF NOT EXISTS idx_user_context_importance ON user_context(importance DESC);
CREATE INDEX IF NOT EXISTS idx_user_context_updated ON user_context(updated_at DESC);

-- RLS: Users can only access their own context
ALTER TABLE user_context ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own context"
    ON user_context FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can insert their own context"
    ON user_context FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update their own context"
    ON user_context FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete their own context"
    ON user_context FOR DELETE
    USING (user_id = auth.uid());

-- Auto-update updated_at timestamp
CREATE TRIGGER user_context_updated_at
    BEFORE UPDATE ON user_context
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================
-- EXTEND BLOCKS TABLE (add assumption type)
-- ============================================

-- The semantic_type column already exists from migration 004
-- Valid types are now: fact, guideline, requirement, insight, note, question, assumption
-- No schema change needed, just documentation

COMMENT ON COLUMN blocks.semantic_type IS
    'Semantic classification: fact, guideline, requirement, insight, note, question, assumption';


-- ============================================
-- USER CONTEXT EXTRACTION LOG
-- ============================================

-- Extend extraction_logs to track user context extraction
ALTER TABLE extraction_logs
ADD COLUMN IF NOT EXISTS user_items_extracted INTEGER DEFAULT 0;

COMMENT ON COLUMN extraction_logs.items_extracted IS 'Number of project blocks extracted';
COMMENT ON COLUMN extraction_logs.user_items_extracted IS 'Number of user context items extracted';
