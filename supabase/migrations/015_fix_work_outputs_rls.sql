-- Migration: 015_fix_work_outputs_rls.sql
-- ADR-015: Fix work_outputs RLS for Ambient Work
-- Date: 2025-01-30
--
-- Problem: work_outputs RLS policies JOIN work_tickets to projects,
-- which fails when work_tickets.project_id is NULL (ambient work).
--
-- Solution: Update policies to check for:
-- 1. Project-based access (existing path)
-- 2. User-based access for ambient work (work_tickets.user_id)

-- =============================================================================
-- 1. FIX SELECT POLICY ON WORK_OUTPUTS
-- =============================================================================

-- Drop existing SELECT policy
DROP POLICY IF EXISTS "Users can view outputs for their tickets" ON work_outputs;

-- Create new SELECT policy that supports ambient work
CREATE POLICY "Users can view outputs for their tickets"
    ON work_outputs FOR SELECT
    USING (
        ticket_id IN (
            SELECT wt.id FROM work_tickets wt
            WHERE
                -- Project-based access
                wt.project_id IN (
                    SELECT p.id FROM projects p
                    JOIN workspaces w ON p.workspace_id = w.id
                    WHERE w.owner_id = auth.uid()
                )
                OR
                -- Ambient work access (no project, user owns ticket)
                (wt.project_id IS NULL AND wt.user_id = auth.uid())
        )
    );


-- =============================================================================
-- 2. FIX INSERT POLICY ON WORK_OUTPUTS
-- =============================================================================

-- Drop existing INSERT policy
DROP POLICY IF EXISTS "Users can create outputs for their tickets" ON work_outputs;

-- Create new INSERT policy that supports ambient work
CREATE POLICY "Users can create outputs for their tickets"
    ON work_outputs FOR INSERT
    WITH CHECK (
        ticket_id IN (
            SELECT wt.id FROM work_tickets wt
            WHERE
                -- Project-based access
                wt.project_id IN (
                    SELECT p.id FROM projects p
                    JOIN workspaces w ON p.workspace_id = w.id
                    WHERE w.owner_id = auth.uid()
                )
                OR
                -- Ambient work access (no project, user owns ticket)
                (wt.project_id IS NULL AND wt.user_id = auth.uid())
        )
    );


-- =============================================================================
-- 3. ADD UPDATE/DELETE POLICIES (for completeness)
-- =============================================================================

-- Drop if exists to ensure clean state
DROP POLICY IF EXISTS "Users can update outputs for their tickets" ON work_outputs;
DROP POLICY IF EXISTS "Users can delete outputs for their tickets" ON work_outputs;

-- UPDATE policy
CREATE POLICY "Users can update outputs for their tickets"
    ON work_outputs FOR UPDATE
    USING (
        ticket_id IN (
            SELECT wt.id FROM work_tickets wt
            WHERE
                wt.project_id IN (
                    SELECT p.id FROM projects p
                    JOIN workspaces w ON p.workspace_id = w.id
                    WHERE w.owner_id = auth.uid()
                )
                OR
                (wt.project_id IS NULL AND wt.user_id = auth.uid())
        )
    )
    WITH CHECK (
        ticket_id IN (
            SELECT wt.id FROM work_tickets wt
            WHERE
                wt.project_id IN (
                    SELECT p.id FROM projects p
                    JOIN workspaces w ON p.workspace_id = w.id
                    WHERE w.owner_id = auth.uid()
                )
                OR
                (wt.project_id IS NULL AND wt.user_id = auth.uid())
        )
    );

-- DELETE policy
CREATE POLICY "Users can delete outputs for their tickets"
    ON work_outputs FOR DELETE
    USING (
        ticket_id IN (
            SELECT wt.id FROM work_tickets wt
            WHERE
                wt.project_id IN (
                    SELECT p.id FROM projects p
                    JOIN workspaces w ON p.workspace_id = w.id
                    WHERE w.owner_id = auth.uid()
                )
                OR
                (wt.project_id IS NULL AND wt.user_id = auth.uid())
        )
    );


-- =============================================================================
-- 4. VERIFY: Add comment for documentation
-- =============================================================================

COMMENT ON TABLE work_outputs IS
'Agent work outputs. Access controlled via ticket ownership:
- Project-based: ticket belongs to a project in user workspace
- Ambient: ticket has no project but user_id matches current user';
