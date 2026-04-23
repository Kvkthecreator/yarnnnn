-- Migration 158: ADR-209 — Authored Substrate (Phase 1 foundation)
--
-- Adds the substrate-level commitment that every mutation to `workspace_files`
-- is attributed, purposeful, and retained. Three of git's five capabilities
-- implemented natively in Postgres (content-addressed retention,
-- parent-pointer history, authored-by attribution); branching + distributed
-- replication deferred. See ADR-209 + docs/architecture/authored-substrate.md.
--
-- This migration is PHASE 1 ONLY: additive foundation.
-- - Creates workspace_blobs (CAS) + workspace_file_versions (revision chain)
-- - Adds workspace_files.head_version_id pointer column
-- - Backfills every existing workspace_files row with one synthetic
--   initial revision (authored_by='system:backfill-158')
--
-- Phase 2 (next PR) routes all write call sites through write_revision()
-- and deletes /history/ subfolder methods. Phase 1 is fully additive —
-- no code paths change, no writes break.
--
-- Scoping note: workspace_files uses `user_id` (not `workspace_id`) as the
-- scoping column per ADR-106 migration 100. We match that convention here.
-- The architectural term "workspace" in docs refers to the user-scoped file
-- store; the DB column is `user_id`.

-- pgcrypto provides digest() used by the backfill's sha256 computation.
-- Standard Supabase extension; idempotent create.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =============================================================================
-- 1. workspace_blobs — content-addressed store
-- =============================================================================

CREATE TABLE workspace_blobs (
    sha256 TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    size_bytes INTEGER GENERATED ALWAYS AS (octet_length(content)) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE workspace_blobs IS
    'ADR-209 Authored Substrate: content-addressed immutable store. Keyed by sha256 of content. Shared across all workspaces — identical content reuses the same blob. Referenced by workspace_file_versions.blob_sha.';

-- No user-level index needed — PK lookup is the only access pattern.
-- Blobs are shared content; scoping lives at the revision layer.

-- =============================================================================
-- 2. workspace_file_versions — revision chain per (user_id, path)
-- =============================================================================

CREATE TABLE workspace_file_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    blob_sha TEXT NOT NULL REFERENCES workspace_blobs(sha256),
    parent_version_id UUID REFERENCES workspace_file_versions(id),
    authored_by TEXT NOT NULL CHECK (length(authored_by) > 0),
    author_identity_uuid UUID,
    message TEXT NOT NULL CHECK (length(message) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE workspace_file_versions IS
    'ADR-209 Authored Substrate: parent-pointered revision chain per (user_id, path). Every mutation to workspace_files produces exactly one row here. authored_by carries the cognitive-layer prefix (operator | yarnnn:<model> | agent:<slug> | specialist:<role> | reviewer:<identity> | system:<actor>). message is a short human-readable summary. parent_version_id is NULL on the first revision for a path.';

-- Query path: "list revisions for (user, path) newest-first"
CREATE INDEX idx_wfv_path_created
    ON workspace_file_versions(user_id, path, created_at DESC);

-- Query path: "what has <authored_by> written lately?" (meta-awareness reads)
CREATE INDEX idx_wfv_authored_by_created
    ON workspace_file_versions(user_id, authored_by, created_at DESC);

-- Query path: "walk the parent chain backward"
CREATE INDEX idx_wfv_parent
    ON workspace_file_versions(parent_version_id)
    WHERE parent_version_id IS NOT NULL;

-- =============================================================================
-- 3. workspace_files.head_version_id — current-revision pointer
-- =============================================================================
--
-- The head pointer is what makes reads work. workspace_files continues to
-- hold the current content (denormalized for read performance — Phase 5
-- audits whether this stays); head_version_id tells you which revision
-- that content corresponds to.
--
-- Nullable during backfill (the column exists before the rows are populated);
-- Phase 2 adds a NOT NULL constraint after the backfill completes and after
-- call-site migration ensures every write sets it.

ALTER TABLE workspace_files
    ADD COLUMN head_version_id UUID REFERENCES workspace_file_versions(id);

COMMENT ON COLUMN workspace_files.head_version_id IS
    'ADR-209 Authored Substrate: points at the current (most recent) revision in workspace_file_versions for this (user_id, path). Reads default to this revision unless a specific historical revision is named. Set by write_revision() on every mutation.';

-- =============================================================================
-- 4. RLS — service role manages (same pattern as workspace_files)
-- =============================================================================

ALTER TABLE workspace_blobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_file_versions ENABLE ROW LEVEL SECURITY;

-- Users can SELECT their own revisions (blobs are SELECTed via join through revisions).
CREATE POLICY "Users can view own workspace file versions"
    ON workspace_file_versions
    FOR SELECT
    USING (user_id = auth.uid());

-- Service role (agents, pipelines, backfill) manages both tables.
CREATE POLICY "Service role manages workspace file versions"
    ON workspace_file_versions
    TO service_role
    USING (true);

-- Blobs are read-only to users (only accessible via joined queries from
-- workspace_file_versions, which already enforces user_id scoping).
-- Service role manages writes.
CREATE POLICY "Service role manages workspace blobs"
    ON workspace_blobs
    TO service_role
    USING (true);

-- Authenticated users can read blobs (they're content-addressed and shared;
-- the scoping happens at the revision layer which references them).
CREATE POLICY "Authenticated users can read workspace blobs"
    ON workspace_blobs
    FOR SELECT
    TO authenticated
    USING (true);

-- =============================================================================
-- 5. Backfill — every existing workspace_files row gets a synthetic revision
-- =============================================================================
--
-- One-shot. Runs once, at migration time. Every existing workspace_files
-- row produces:
--   - one workspace_blobs row for its content (dedup'd by sha256)
--   - one workspace_file_versions row with:
--       authored_by = 'system:backfill-158'
--       message    = 'initial backfill — pre-ADR-209 content'
--       parent_version_id = NULL (first revision in the chain)
--   - head_version_id updated to the new revision id
--
-- After this migration, every workspace_files row has exactly one revision
-- in its chain. Subsequent mutations (Phase 2+) extend the chain normally.

-- Step 5a: insert blobs (dedup by sha256 via ON CONFLICT DO NOTHING).
INSERT INTO workspace_blobs (sha256, content)
SELECT DISTINCT
    encode(digest(content, 'sha256'), 'hex') AS sha256,
    content
FROM workspace_files
ON CONFLICT (sha256) DO NOTHING;

-- Step 5b: insert one revision per workspace_files row.
-- Using a CTE so we can capture the inserted revision id and use it to
-- update head_version_id in the same transaction.
WITH inserted_revisions AS (
    INSERT INTO workspace_file_versions (
        user_id,
        path,
        blob_sha,
        parent_version_id,
        authored_by,
        message,
        created_at
    )
    SELECT
        wf.user_id,
        wf.path,
        encode(digest(wf.content, 'sha256'), 'hex'),
        NULL,  -- first revision in chain
        'system:backfill-158',
        'initial backfill — pre-ADR-209 content',
        wf.created_at  -- preserve original creation time on the synthetic revision
    FROM workspace_files wf
    WHERE wf.head_version_id IS NULL  -- idempotent: skip if already backfilled
    RETURNING id, user_id, path
)
-- Step 5c: point workspace_files.head_version_id at the new revision.
UPDATE workspace_files wf
SET head_version_id = ir.id
FROM inserted_revisions ir
WHERE wf.user_id = ir.user_id
  AND wf.path = ir.path;

-- =============================================================================
-- 6. Verification queries (run manually after migration)
-- =============================================================================
--
-- SELECT
--     (SELECT COUNT(*) FROM workspace_files)                AS files,
--     (SELECT COUNT(*) FROM workspace_file_versions)        AS revisions,
--     (SELECT COUNT(*) FROM workspace_files
--      WHERE head_version_id IS NOT NULL)                   AS files_with_head,
--     (SELECT COUNT(*) FROM workspace_blobs)                AS blobs;
--
-- Expected after backfill:
--   files = files_with_head  (every row has a head)
--   revisions >= files       (one revision per file; could be more on re-run)
--   blobs <= files           (dedup — identical content shares a blob)
