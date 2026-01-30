-- Migration: 013_fix_work_tickets_rls.sql
-- Fix RLS policy for work_tickets INSERT operations
-- Date: 2025-01-30
--
-- Problem: The 012_work_scheduling migration added a policy "Users can manage their own templates"
-- with WITH CHECK (user_id = auth.uid()). This policy applies to ALL operations (not just templates)
-- and blocks INSERTs when user_id is NULL.
--
-- Solution:
-- 1. Drop the overly broad template policy
-- 2. Create specific policies for templates (require user_id)
-- 3. Update the project-based policy to have explicit WITH CHECK for inserts

-- =============================================================================
-- 1. DROP PROBLEMATIC POLICY
-- =============================================================================

DROP POLICY IF EXISTS "Users can manage their own templates" ON work_tickets;


-- =============================================================================
-- 2. UPDATE PROJECT-BASED POLICY WITH EXPLICIT WITH CHECK
-- =============================================================================

-- Drop old policy
DROP POLICY IF EXISTS "Users can manage tickets in their projects" ON work_tickets;

-- Recreate with explicit WITH CHECK for inserts
-- This allows inserting tickets with project_id in user's projects (user_id optional)
CREATE POLICY "Users can manage tickets in their projects"
    ON work_tickets FOR ALL
    USING (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    )
    WITH CHECK (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );


-- =============================================================================
-- 3. CREATE SEPARATE TEMPLATE POLICIES (OPTIONAL - user_id based access)
-- =============================================================================

-- For templates, ALSO allow access via user_id (for global templates without project)
-- This is an OR condition with the project-based policy
CREATE POLICY "Users can access their templates by user_id"
    ON work_tickets FOR ALL
    USING (
        is_template = true AND user_id = auth.uid()
    )
    WITH CHECK (
        is_template = true AND user_id = auth.uid()
    );


-- =============================================================================
-- 4. ENSURE SELECT POLICY EXISTS
-- =============================================================================

-- The original select policy from 001 should still exist, but recreate if needed
DROP POLICY IF EXISTS "Users can view tickets in their projects" ON work_tickets;

CREATE POLICY "Users can view tickets in their projects"
    ON work_tickets FOR SELECT
    USING (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
        OR (is_template = true AND user_id = auth.uid())
    );
