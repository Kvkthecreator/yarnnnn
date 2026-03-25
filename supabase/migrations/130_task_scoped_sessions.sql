-- Migration 130: Task-scoped sessions
-- Adds task_slug column to chat_sessions for task-scoped TP conversations.

ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS task_slug TEXT;

CREATE INDEX IF NOT EXISTS idx_chat_sessions_task_slug
  ON chat_sessions(user_id, task_slug, session_type, status, updated_at DESC)
  WHERE task_slug IS NOT NULL;
