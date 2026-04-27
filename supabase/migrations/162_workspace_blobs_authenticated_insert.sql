-- ============================================================================
-- Migration 162 — workspace_blobs: allow authenticated users to INSERT
-- ============================================================================
--
-- Surfaced 2026-04-27 during alpha-trader scaffolding (scaffold_trader.py via
-- POST /api/tasks). Operator-scoped JWT writes to substrate via the API
-- failed at the workspace_blobs upsert step in services.authored_substrate
-- write_revision() with code 42501 — "new row violates row-level security
-- policy for table workspace_blobs."
--
-- Root cause: migration 158 created workspace_blobs with RLS policies that
-- allow service-role ALL operations and authenticated SELECT, but no INSERT
-- policy for authenticated users. Every operator-attributed write through
-- the API path is rejected at the blob upsert step. This blocks:
--   - POST /api/tasks (scaffold_trader and any task-create flow)
--   - UpdateContext invocations from chat (operator MANDATE/IDENTITY edits)
--   - PATCH /api/workspace/file (operator file-edit affordance)
--   - ProposeAction (agents writing proposals via JWT-scoped routes)
-- and in general every operator-authored substrate write through the API.
--
-- Service-key writes (back-office tasks, scheduler, scaffold scripts using
-- get_service_client) work because the service-role bypass policy permits
-- ALL operations.
--
-- Fix: add an INSERT policy for authenticated users. Blobs are content-
-- addressed (sha256-keyed, immutable, globally-shared across all users by
-- design — one blob per unique content). No per-user attribution lives on
-- workspace_blobs itself; user attribution lives on workspace_file_versions
-- (which IS RLS-scoped per user_id) and references blobs by sha. The worst
-- case under permissive blob-INSERT is that a user inserts content nobody
-- ever references — harmless, the row is unreferenced bytes.
--
-- This restores the ADR-209 contract that "every mutation to the substrate
-- is attributed, purposeful, and retained" — without a write path through
-- API routes, ADR-209 attribution has no operator-attributed entries from
-- chat/UI, only from server-side service-key writes.
-- ============================================================================

CREATE POLICY "Authenticated users can insert workspace blobs"
ON public.workspace_blobs
FOR INSERT
TO authenticated
WITH CHECK (true);

-- The WITH CHECK is unconditionally true because blobs are content-addressed
-- and globally-deduped by sha256. There's no per-row scoping to enforce
-- here — the per-user authorization happens at workspace_file_versions
-- (which references the blob by sha). Adding any user-id check on blobs
-- would break the dedup property (multiple users with identical content
-- would each need their own blob row, defeating the content-addressed
-- design from ADR-209).
