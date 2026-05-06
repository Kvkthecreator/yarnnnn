-- ADR-249: Two-Intent File Handling — drop filesystem_documents + filesystem_chunks.
--
-- Uploaded documents now live at /workspace/uploads/{slug}.md in workspace_files.
-- The filesystem_chunks embedding index is superseded by workspace_files.embedding
-- (file-level vector, written at upload time via process_document()).
-- Original binaries remain in Supabase Storage (documents bucket) — storage_path
-- is preserved in the workspace file's YAML frontmatter.
--
-- All readers have been migrated to workspace_files prior to this migration.
-- All writers (routes/documents.py, services/documents.py) write to workspace_files only.
-- Purge cascade updated in routes/account.py (workspace_files user-scoped delete).

-- Drop RPC that depended on filesystem_documents + filesystem_chunks
DROP FUNCTION IF EXISTS get_document_with_stats(uuid);

-- Drop chunks first (FK → documents)
DROP TABLE IF EXISTS filesystem_chunks CASCADE;

-- Drop documents
DROP TABLE IF EXISTS filesystem_documents CASCADE;
