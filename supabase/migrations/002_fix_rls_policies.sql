-- YARNNN v5 - RLS Policy Fixes
-- Fixes missing policies and broken queries from 001_initial_schema.sql

-----------------------------------------------------------
-- GRANTS: Ensure roles can access tables
-----------------------------------------------------------

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO anon, authenticated;

-- Grant table permissions to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Anon users get read-only (for public data if any)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;

-----------------------------------------------------------
-- 1. WORKSPACES - Add UPDATE and DELETE policies
-----------------------------------------------------------

CREATE POLICY "Users can update own workspaces"
    ON workspaces FOR UPDATE
    USING (owner_id = auth.uid())
    WITH CHECK (owner_id = auth.uid());

CREATE POLICY "Users can delete own workspaces"
    ON workspaces FOR DELETE
    USING (owner_id = auth.uid());

-----------------------------------------------------------
-- 2. PROJECTS - Add UPDATE and DELETE policies
-----------------------------------------------------------

CREATE POLICY "Users can update projects in their workspaces"
    ON projects FOR UPDATE
    USING (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
        )
    )
    WITH CHECK (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete projects in their workspaces"
    ON projects FOR DELETE
    USING (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
        )
    );

-----------------------------------------------------------
-- 5. BLOCK_RELATIONS - Fix broken policy and add missing ones
-----------------------------------------------------------

-- Drop the broken SELECT policy
DROP POLICY IF EXISTS "Users can view relations for their blocks" ON block_relations;

-- Create proper SELECT policy that checks ownership
CREATE POLICY "Users can view relations for their blocks"
    ON block_relations FOR SELECT
    USING (
        source_id IN (
            SELECT b.id FROM blocks b
            JOIN projects p ON b.project_id = p.id
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );

-- Add INSERT policy
CREATE POLICY "Users can create relations for their blocks"
    ON block_relations FOR INSERT
    WITH CHECK (
        source_id IN (
            SELECT b.id FROM blocks b
            JOIN projects p ON b.project_id = p.id
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
        AND target_id IN (
            SELECT b.id FROM blocks b
            JOIN projects p ON b.project_id = p.id
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );

-- Add DELETE policy
CREATE POLICY "Users can delete relations for their blocks"
    ON block_relations FOR DELETE
    USING (
        source_id IN (
            SELECT b.id FROM blocks b
            JOIN projects p ON b.project_id = p.id
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );

-----------------------------------------------------------
-- 7. WORK_OUTPUTS - Add INSERT policy for agents/service
-----------------------------------------------------------

CREATE POLICY "Users can create outputs for their tickets"
    ON work_outputs FOR INSERT
    WITH CHECK (
        ticket_id IN (
            SELECT wt.id FROM work_tickets wt
            JOIN projects p ON wt.project_id = p.id
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );

-----------------------------------------------------------
-- 8. AGENT_SESSIONS - Add INSERT policy
-----------------------------------------------------------

CREATE POLICY "Users can create sessions in their projects"
    ON agent_sessions FOR INSERT
    WITH CHECK (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );