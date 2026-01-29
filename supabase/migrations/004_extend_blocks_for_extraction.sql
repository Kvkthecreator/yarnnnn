-- Migration: 004_extend_blocks_for_extraction.sql
-- Extends blocks table for extraction-first context system

-- Add semantic typing and source tracking to blocks
ALTER TABLE blocks
ADD COLUMN IF NOT EXISTS semantic_type TEXT,           -- fact, guideline, requirement, insight, note, question
ADD COLUMN IF NOT EXISTS source_type TEXT DEFAULT 'manual',  -- manual, chat, document, import
ADD COLUMN IF NOT EXISTS source_ref UUID,              -- reference to source (session_id, document_id, import_id)
ADD COLUMN IF NOT EXISTS importance FLOAT DEFAULT 0.5, -- 0-1 relevance score for retrieval priority
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;       -- optional TTL for time-bound context

-- Indexes for efficient retrieval
CREATE INDEX IF NOT EXISTS idx_blocks_semantic_type ON blocks(semantic_type);
CREATE INDEX IF NOT EXISTS idx_blocks_source_type ON blocks(source_type);
CREATE INDEX IF NOT EXISTS idx_blocks_importance ON blocks(importance DESC);

-- Extraction logs for observability
CREATE TABLE IF NOT EXISTS extraction_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,         -- chat, document, import, bulk
    source_ref UUID,                   -- optional reference to source
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    items_extracted INTEGER DEFAULT 0,
    error_message TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_extraction_logs_project ON extraction_logs(project_id);
CREATE INDEX IF NOT EXISTS idx_extraction_logs_status ON extraction_logs(status);

-- RLS for extraction_logs
ALTER TABLE extraction_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view extraction logs in their projects"
    ON extraction_logs FOR SELECT
    USING (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert extraction logs in their projects"
    ON extraction_logs FOR INSERT
    WITH CHECK (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );
