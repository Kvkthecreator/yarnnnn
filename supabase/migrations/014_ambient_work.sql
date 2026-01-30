-- Migration: 014_ambient_work.sql
-- ADR-015: Unified Context Model - Enable Ambient Work
-- Date: 2025-01-30
--
-- Allows work_tickets to exist without a project (ambient/personal work).
-- User can request work without selecting a project first.
-- TP routes intelligently or keeps as ambient.

-- =============================================================================
-- 1. MAKE PROJECT_ID NULLABLE
-- =============================================================================

-- Allow work tickets without a project
ALTER TABLE work_tickets ALTER COLUMN project_id DROP NOT NULL;

-- Add comment explaining the change
COMMENT ON COLUMN work_tickets.project_id IS
'Project this work belongs to. NULL = ambient work (user-level, no project).';


-- =============================================================================
-- 2. UPDATE RLS POLICIES FOR AMBIENT WORK
-- =============================================================================

-- Drop existing policies to recreate with ambient support
DROP POLICY IF EXISTS "Users can view tickets in their projects" ON work_tickets;
DROP POLICY IF EXISTS "Users can manage tickets in their projects" ON work_tickets;
DROP POLICY IF EXISTS "Users can access their templates by user_id" ON work_tickets;

-- New SELECT policy: project-based OR ambient (user_id based)
CREATE POLICY "Users can view their work tickets"
    ON work_tickets FOR SELECT
    USING (
        -- Project-based access
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
        OR
        -- Ambient work (no project, owned by user)
        (project_id IS NULL AND user_id = auth.uid())
        OR
        -- Templates owned by user
        (is_template = true AND user_id = auth.uid())
    );

-- New ALL policy: project-based OR ambient
CREATE POLICY "Users can manage their work tickets"
    ON work_tickets FOR ALL
    USING (
        -- Project-based access
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
        OR
        -- Ambient work
        (project_id IS NULL AND user_id = auth.uid())
        OR
        -- Templates owned by user
        (is_template = true AND user_id = auth.uid())
    )
    WITH CHECK (
        -- Can insert into own projects
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
        OR
        -- Can insert ambient work (must set user_id)
        (project_id IS NULL AND user_id = auth.uid())
        OR
        -- Can insert templates (must set user_id)
        (is_template = true AND user_id = auth.uid())
    );


-- =============================================================================
-- 3. INDEX FOR AMBIENT WORK QUERIES
-- =============================================================================

-- Efficient lookup of user's ambient work
CREATE INDEX IF NOT EXISTS idx_tickets_user_ambient
    ON work_tickets(user_id)
    WHERE project_id IS NULL AND is_template = false;
