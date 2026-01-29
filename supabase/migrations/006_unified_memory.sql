-- Migration: 006_unified_memory.sql
-- ADR-005: Unified Memory Architecture with Embeddings
-- Date: 2026-01-29
--
-- This migration:
-- 1. Enables pgvector extension (if not already)
-- 2. Creates unified 'memories' table with embeddings
-- 3. Creates 'chunks' table for document segments
-- 4. Extends 'documents' table with processing columns
-- 5. Drops deprecated tables (user_context, blocks, block_relations, extraction_logs)

-- =============================================================================
-- 1. ENABLE PGVECTOR EXTENSION
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- 2. CREATE MEMORIES TABLE (Unified memory storage)
-- =============================================================================
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,  -- NULL = user-scoped

    -- Content
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI ada-002 dimension

    -- Emergent structure (not forced categories)
    tags TEXT[] DEFAULT '{}',
    entities JSONB DEFAULT '{}',  -- {people: [], companies: [], concepts: []}

    -- Retrieval signals
    importance FLOAT DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),

    -- Provenance
    source_type TEXT NOT NULL,  -- 'chat', 'document', 'manual', 'import'
    source_ref JSONB,  -- {session_id, chunk_id, document_id, etc.}

    -- Lifecycle (soft-delete pattern)
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for retrieval
CREATE INDEX idx_memories_user ON memories(user_id) WHERE is_active = true;
CREATE INDEX idx_memories_project ON memories(project_id) WHERE is_active = true;
CREATE INDEX idx_memories_importance ON memories(importance DESC) WHERE is_active = true;
CREATE INDEX idx_memories_tags ON memories USING gin(tags) WHERE is_active = true;
CREATE INDEX idx_memories_source ON memories(source_type) WHERE is_active = true;

-- Vector index (ivfflat for approximate nearest neighbor search)
-- Note: Lists = 100 is good for up to ~100k rows. Adjust if needed.
CREATE INDEX idx_memories_embedding ON memories
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100)
    WHERE is_active = true AND embedding IS NOT NULL;

-- RLS
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own memories"
    ON memories FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_memories_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER memories_updated_at
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_memories_updated_at();


-- =============================================================================
-- 3. CREATE CHUNKS TABLE (Document segments)
-- =============================================================================
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Content
    content TEXT NOT NULL,
    embedding vector(1536),

    -- Position in document
    chunk_index INTEGER NOT NULL,  -- 0-based order
    page_number INTEGER,  -- For PDFs

    -- Metadata
    metadata JSONB DEFAULT '{}',  -- {section_title, heading_level, etc.}
    token_count INTEGER,

    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_chunks_document ON chunks(document_id);
CREATE INDEX idx_chunks_order ON chunks(document_id, chunk_index);
CREATE INDEX idx_chunks_embedding ON chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100)
    WHERE embedding IS NOT NULL;

-- RLS (inherits from documents via project ownership)
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access chunks from their documents"
    ON chunks FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM documents d
            JOIN projects p ON d.project_id = p.id
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE d.id = chunks.document_id
            AND w.owner_id = auth.uid()
        )
    );


-- =============================================================================
-- 4. EXTEND DOCUMENTS TABLE
-- =============================================================================
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'pending';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processed_at TIMESTAMPTZ;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS page_count INTEGER;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS word_count INTEGER;


-- =============================================================================
-- 5. DROP DEPRECATED TABLES
-- =============================================================================
-- These are replaced by the unified 'memories' table

DROP TABLE IF EXISTS block_relations CASCADE;
DROP TABLE IF EXISTS blocks CASCADE;
DROP TABLE IF EXISTS user_context CASCADE;
DROP TABLE IF EXISTS extraction_logs CASCADE;


-- =============================================================================
-- 6. GRANT PERMISSIONS
-- =============================================================================
GRANT ALL ON memories TO authenticated;
GRANT ALL ON chunks TO authenticated;
GRANT SELECT ON memories TO anon;
GRANT SELECT ON chunks TO anon;
