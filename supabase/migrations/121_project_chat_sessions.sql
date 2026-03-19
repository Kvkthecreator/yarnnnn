-- ADR-119 P4b: Project-scoped chat sessions
--
-- Adds project_slug TEXT column to chat_sessions for project-scoped TP conversations.
-- Uses TEXT slug (not UUID) because ADR-119 projects live in workspace_files
-- (path-based), not the legacy projects table. The legacy project_id UUID FK
-- is preserved but unused.

ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS project_slug TEXT;

-- Index for project-scoped session lookup (matches agent_id scoping pattern)
CREATE INDEX IF NOT EXISTS idx_chat_sessions_project_slug
  ON chat_sessions(user_id, project_slug, session_type, status, updated_at DESC)
  WHERE project_slug IS NOT NULL;
