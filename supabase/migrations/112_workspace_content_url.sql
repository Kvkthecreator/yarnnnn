-- Migration 112: Add content_url to workspace_files (ADR-118 Phase B)
--
-- Stores a URL (Supabase Storage) pointing to a binary file (PDF, PPTX, XLSX, PNG).
-- The `content` column keeps the text/spec that generated it.
-- Path-based interface unchanged — agents resolve rendered outputs via content_url.

ALTER TABLE workspace_files ADD COLUMN content_url TEXT;

COMMENT ON COLUMN workspace_files.content_url IS 'URL to rendered binary file in Supabase Storage (PDF, PPTX, XLSX, PNG). NULL for text-only files.';
