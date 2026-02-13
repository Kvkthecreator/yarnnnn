-- Migration 049: Fix document RPCs for ADR-058 schema
--
-- Updates get_document_with_stats to use filesystem_documents and filesystem_chunks
-- instead of the old documents and chunks tables.

-- Drop the old function first (return type changed)
DROP FUNCTION IF EXISTS get_document_with_stats(uuid);

-- Recreate the function for filesystem_documents
CREATE OR REPLACE FUNCTION get_document_with_stats(doc_id uuid)
RETURNS TABLE (
    id uuid,
    filename text,
    file_type text,
    file_size integer,
    storage_path text,
    user_id uuid,
    processing_status text,
    processed_at timestamptz,
    error_message text,
    page_count integer,
    word_count integer,
    created_at timestamptz,  -- Maps to uploaded_at for compatibility
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
        d.user_id,
        d.processing_status,
        d.processed_at,
        d.error_message,
        d.page_count,
        d.word_count,
        d.uploaded_at as created_at,  -- ADR-058: uploaded_at → created_at for API compatibility
        (SELECT COUNT(*) FROM filesystem_chunks c WHERE c.document_id = d.id) as chunk_count,
        (SELECT COUNT(*) FROM knowledge_entries m
         WHERE m.source_ref->>'document_id' = d.id::text
         AND m.is_active = true) as memory_count
    FROM filesystem_documents d
    WHERE d.id = doc_id
    AND d.user_id = auth.uid();
END;
$$;

GRANT EXECUTE ON FUNCTION get_document_with_stats TO authenticated;
