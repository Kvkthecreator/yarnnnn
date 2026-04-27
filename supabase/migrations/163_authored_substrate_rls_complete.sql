-- ============================================================================
-- Migration 163 — complete authored-substrate RLS for authenticated writes
-- ============================================================================
--
-- Migration 162 added INSERT to workspace_blobs but the gap was wider:
--
-- (1) workspace_blobs UPDATE policy missing — `_upsert_blob` in
--     services.authored_substrate uses INSERT ... ON CONFLICT (sha256)
--     DO UPDATE. When the blob already exists (sha collision — same
--     content authored by anyone before), the UPDATE branch fires and
--     fails with code 42501 + "(USING expression)" annotation. Auth
--     users could not update the dedup'd blob row, breaking the
--     content-addressed write path.
--
-- (2) workspace_file_versions INSERT policy missing — every revision
--     write through the API path failed at the version-row insert,
--     same symptom as (1) but a different table.
--
-- Together, migration 162 alone wasn't sufficient — the full
-- authored-substrate write chain (blob upsert → version insert →
-- workspace_files upsert) needs all three layers permissive for
-- authenticated users with appropriate scoping.
--
-- This migration completes the chain. Combined with migration 162,
-- the full operator-attributed write path through API routes will
-- now succeed for any authenticated user.
--
-- Scoping rationale:
--
-- workspace_blobs:
--   INSERT: WITH CHECK true (already added in 162)
--   UPDATE: WITH CHECK true — same rationale as INSERT. Blobs are
--     content-addressed and immutable in practice (the only valid
--     "update" is metadata bookkeeping like updated_at; the content
--     itself never changes for a given sha). No per-row scoping
--     needed.
--
-- workspace_file_versions:
--   INSERT: WITH CHECK (user_id = auth.uid()) — versions ARE
--     user-scoped, unlike blobs. Authenticated user may insert a
--     revision row only with their own user_id.
--   UPDATE: not added — versions are immutable per ADR-209 (every
--     mutation produces a new revision; existing revisions never
--     change). Service-role ALL covers any admin-level edits.
--   DELETE: not added — same reason. Service-role only.
-- ============================================================================

-- workspace_blobs UPDATE for authenticated users
CREATE POLICY "Authenticated users can update workspace blobs"
ON public.workspace_blobs
FOR UPDATE
TO authenticated
USING (true)
WITH CHECK (true);

-- workspace_file_versions INSERT for authenticated users (user-scoped)
CREATE POLICY "Authenticated users can insert own workspace file versions"
ON public.workspace_file_versions
FOR INSERT
TO authenticated
WITH CHECK (user_id = auth.uid());
