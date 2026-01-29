-- Migration: 009_document_pipeline.sql
-- ADR-008: Document Pipeline Architecture
-- Date: 2026-01-29
--
-- This migration:
-- 1. Creates storage bucket for documents
-- 2. Adds user_id and storage_path to documents table
-- 3. Makes project_id nullable (allows user-scoped documents)
-- 4. Updates RLS policies for new ownership model
-- 5. Adds storage_path to work_outputs for future use

-- =============================================================================
-- 1. CREATE STORAGE BUCKET
-- =============================================================================

-- Create the documents bucket (private)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'documents',
    'documents',
    false,
    26214400,  -- 25MB limit
    ARRAY['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain', 'text/markdown']
)
ON CONFLICT (id) DO NOTHING;

-- Storage RLS: Users can only access their own folder
CREATE POLICY "Users can upload to their folder"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY "Users can read from their folder"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY "Users can delete from their folder"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );


-- =============================================================================
-- 2. EXTEND DOCUMENTS TABLE
-- =============================================================================

-- Add user_id for direct ownership (bypasses project->workspace chain for simpler RLS)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

-- Add storage_path to track bucket location (separate from file_url)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS storage_path TEXT;

-- Make project_id nullable to allow user-scoped documents
ALTER TABLE documents ALTER COLUMN project_id DROP NOT NULL;

-- Backfill user_id from existing documents (via project->workspace->owner)
UPDATE documents d
SET user_id = (
    SELECT w.owner_id
    FROM projects p
    JOIN workspaces w ON p.workspace_id = w.id
    WHERE p.id = d.project_id
)
WHERE d.user_id IS NULL AND d.project_id IS NOT NULL;


-- =============================================================================
-- 3. UPDATE RLS POLICIES
-- =============================================================================

-- Drop old policies
DROP POLICY IF EXISTS "Users can view documents in their projects" ON documents;
DROP POLICY IF EXISTS "Users can manage documents in their projects" ON documents;

-- New unified policy: users can manage their own documents
CREATE POLICY "Users can manage their own documents"
    ON documents FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());


-- =============================================================================
-- 4. EXTEND WORK_OUTPUTS TABLE (for future agent outputs)
-- =============================================================================

ALTER TABLE work_outputs ADD COLUMN IF NOT EXISTS storage_path TEXT;
ALTER TABLE work_outputs ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);


-- =============================================================================
-- 5. ADD INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);


-- =============================================================================
-- 6. HELPER FUNCTION: Get document with stats
-- =============================================================================

CREATE OR REPLACE FUNCTION get_document_with_stats(doc_id uuid)
RETURNS TABLE (
    id uuid,
    filename text,
    file_type text,
    file_size integer,
    storage_path text,
    project_id uuid,
    user_id uuid,
    processing_status text,
    processed_at timestamptz,
    error_message text,
    page_count integer,
    word_count integer,
    created_at timestamptz,
    chunk_count bigint,
    memory_count bigint
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.filename,
        d.file_type,
        d.file_size,
        d.storage_path,
        d.project_id,
        d.user_id,
        d.processing_status,
        d.processed_at,
        d.error_message,
        d.page_count,
        d.word_count,
        d.created_at,
        (SELECT COUNT(*) FROM chunks c WHERE c.document_id = d.id) AS chunk_count,
        (SELECT COUNT(*) FROM memories m WHERE m.source_ref->>'document_id' = d.id::text) AS memory_count
    FROM documents d
    WHERE d.id = doc_id
      AND d.user_id = auth.uid();
END;
$$;

GRANT EXECUTE ON FUNCTION get_document_with_stats TO authenticated;
