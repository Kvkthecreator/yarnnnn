-- Migration 116: Add version + lifecycle columns to workspace_files (ADR-119 Phase 1)
--
-- version: tracks overwrite count for evolving files (thesis.md, memory/*.md, AGENT.md)
-- lifecycle: governs visibility and cleanup
--   'ephemeral' — scratch files in /working/, auto-cleaned after 24h
--   'active'    — current, live files (default)
--   'delivered'  — output sent to user, kept for feedback window
--   'archived'  — superseded, excluded from default queries

ALTER TABLE workspace_files
    ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS lifecycle TEXT NOT NULL DEFAULT 'active';

-- Constraint for valid lifecycle values
ALTER TABLE workspace_files
    ADD CONSTRAINT workspace_files_lifecycle_check
    CHECK (lifecycle IN ('ephemeral', 'active', 'delivered', 'archived'));

-- Index for lifecycle-filtered queries (most queries exclude ephemeral/archived)
CREATE INDEX IF NOT EXISTS idx_workspace_files_lifecycle
    ON workspace_files (user_id, lifecycle)
    WHERE lifecycle IN ('active', 'delivered');

-- Index for ephemeral cleanup job (find expired scratch files)
CREATE INDEX IF NOT EXISTS idx_workspace_files_ephemeral_cleanup
    ON workspace_files (lifecycle, updated_at)
    WHERE lifecycle = 'ephemeral';
