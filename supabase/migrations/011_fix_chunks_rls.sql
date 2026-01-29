-- Migration: 011_fix_chunks_rls.sql
-- Fix: Chunks RLS policy fails for user-scoped documents (project_id = NULL)
-- Date: 2026-01-29
--
-- The chunks table RLS policy from 006_unified_memory.sql requires:
--   documents -> projects -> workspaces -> owner_id
-- But ADR-008 allows documents without project_id (user-scoped).
-- This migration updates the policy to check document.user_id directly.

-- =============================================================================
-- FIX CHUNKS RLS POLICY
-- =============================================================================

-- Drop the old policy
DROP POLICY IF EXISTS "Users can access chunks from their documents" ON chunks;

-- Create new policy that checks document ownership directly
CREATE POLICY "Users can access chunks from their documents"
    ON chunks FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM documents d
            WHERE d.id = chunks.document_id
            AND d.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM documents d
            WHERE d.id = chunks.document_id
            AND d.user_id = auth.uid()
        )
    );
