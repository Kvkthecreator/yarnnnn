-- Migration: 026_fix_work_tickets_ambient_rls.sql
-- ADR-029: Fix work_tickets RLS for deliverable pipeline ambient work
-- Date: 2026-02-06
--
-- Problem: Deliverables created without a project_id fail when the pipeline
-- tries to create work_tickets because the RLS policy requires either:
-- 1. project_id in user's workspace projects, OR
-- 2. is_template = true AND user_id = auth.uid()
--
-- When a deliverable has no project_id and creates non-template work tickets,
-- the RLS policy blocks the INSERT.
--
-- Solution: Add a policy for "ambient work" - work tickets without a project
-- that are owned by the user (user_id = auth.uid()).

-- =============================================================================
-- 1. ADD AMBIENT WORK POLICY FOR WORK_TICKETS
-- =============================================================================

-- Policy for ambient work (no project, user-owned)
-- This allows users to create/manage work tickets that:
-- - Have no project_id (NULL)
-- - Have user_id matching the authenticated user
CREATE POLICY "Users can manage their ambient work tickets"
    ON work_tickets FOR ALL
    USING (
        project_id IS NULL AND user_id = auth.uid()
    )
    WITH CHECK (
        project_id IS NULL AND user_id = auth.uid()
    );


-- =============================================================================
-- 2. UPDATE SELECT POLICY TO INCLUDE AMBIENT WORK
-- =============================================================================

-- Drop and recreate the view policy to include ambient work access
DROP POLICY IF EXISTS "Users can view tickets in their projects" ON work_tickets;

CREATE POLICY "Users can view tickets in their projects"
    ON work_tickets FOR SELECT
    USING (
        -- Project-based access
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
        OR
        -- Template access
        (is_template = true AND user_id = auth.uid())
        OR
        -- Ambient work access (no project, user-owned)
        (project_id IS NULL AND user_id = auth.uid())
    );


-- =============================================================================
-- 3. DOCUMENTATION
-- =============================================================================

COMMENT ON TABLE work_tickets IS
'Work tickets for agent execution. Access controlled via:
- Project-based: ticket belongs to a project in user workspace
- Template: is_template=true and user_id matches
- Ambient: project_id IS NULL and user_id matches (deliverable pipeline, etc.)';
