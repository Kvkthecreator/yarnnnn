-- ADR-474 — Content inherits the file's scope
--
-- `workspace_blobs` was created ownerless (sha256 PK) so identical content
-- across workspaces would be stored once. The consequence: `workspace_purge`
-- cannot reach blobs — there is no column to scope on — so a member who
-- deletes their workspace leaves their file content in the table permanently.
--
-- This migration gives content the same scope the file above it already has:
-- the identity becomes (workspace_id, sha256), and the ledger's FK becomes
-- composite so a cross-workspace blob reference is structurally impossible
-- rather than merely discouraged.
--
-- Sharing is NOT this layer's job (ADR-474 D3). Two workspaces holding
-- identical bytes is a coincidence of content, never a relationship: sharing
-- is an explicit grant on the FILE (principal_grants · ADR-434 powerbox ·
-- ADR-437), resolved above this layer. Content-addressing is a storage
-- optimization; it must never be an authorization fact.
--
-- Pre-verified against live data (2026-07-21):
--   469 blobs · 461 referenced · 8 unreferenced (inside the 24h GC window)
--   718 revisions, ALL carrying a non-NULL workspace_id (no unresolvable row)
--   15 blobs cited by >1 workspace — every one a system:-authored kernel seed
--   0 blobs cited at more than one distinct path
--
-- Safe to re-run: each step is guarded.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. The owner column
-- ---------------------------------------------------------------------------

ALTER TABLE workspace_blobs
  ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE;

COMMENT ON COLUMN workspace_blobs.workspace_id IS
  'ADR-474 D1 — the owning workspace. A blob is the bytes of a file, and a '
  'file belongs to a workspace, so content inherits the file''s scope. '
  'ON DELETE CASCADE: dropping a workspace collects its content by '
  'construction. Sharing is a grant on the file (D3), never co-ownership here.';

-- ---------------------------------------------------------------------------
-- 2. Drop the old single-column PK FIRST
--
-- The split below writes one row per (sha, owning workspace). While `sha256`
-- alone is still the PK those rows all collide with the original — silently,
-- if the INSERT carries ON CONFLICT DO NOTHING. The key must be relaxed before
-- the split, and the composite PK is added after it (step 5).
--
-- The ledger's FK depends on this PK, so it goes first.
-- ---------------------------------------------------------------------------

ALTER TABLE workspace_file_versions
  DROP CONSTRAINT IF EXISTS workspace_file_versions_blob_sha_fkey;

ALTER TABLE workspace_blobs DROP CONSTRAINT IF EXISTS workspace_blobs_pkey;

-- ---------------------------------------------------------------------------
-- 3. Split blobs cited by more than one workspace
--
-- Each citing workspace beyond the first gets its own row carrying identical
-- content; the first claims the existing row (step 4).
--
-- Live: 15 rows, all kernel genesis seeds, ~87KB total.
-- ---------------------------------------------------------------------------

INSERT INTO workspace_blobs (sha256, content, storage_key, byte_size, created_at, workspace_id)
SELECT b.sha256, b.content, b.storage_key, b.byte_size, b.created_at, v.workspace_id
FROM workspace_blobs b
JOIN (
  SELECT DISTINCT blob_sha, workspace_id
  FROM workspace_file_versions
  WHERE workspace_id IS NOT NULL
) v ON v.blob_sha = b.sha256
WHERE b.workspace_id IS NULL
  AND v.workspace_id <> (
    SELECT MIN(v2.workspace_id::text)::uuid
    FROM workspace_file_versions v2
    WHERE v2.blob_sha = b.sha256 AND v2.workspace_id IS NOT NULL
  );

-- ---------------------------------------------------------------------------
-- 4. Backfill the original rows — owner = the first citing workspace
-- ---------------------------------------------------------------------------

UPDATE workspace_blobs b
SET workspace_id = (
  SELECT MIN(v.workspace_id::text)::uuid
  FROM workspace_file_versions v
  WHERE v.blob_sha = b.sha256 AND v.workspace_id IS NOT NULL
)
WHERE b.workspace_id IS NULL
  AND EXISTS (
    SELECT 1 FROM workspace_file_versions v
    WHERE v.blob_sha = b.sha256 AND v.workspace_id IS NOT NULL
  );

-- ---------------------------------------------------------------------------
-- 4b. Collect unreferenced blobs
--
-- A blob no revision cites has no derivable owner. These are exactly the rows
-- any GC would collect (the sweep's own rule: nothing references them), and
-- they cannot be carried into a NOT NULL column. The FK below is NO ACTION, so
-- the database itself refuses this delete if anything actually cites them.
-- ---------------------------------------------------------------------------

DELETE FROM workspace_blobs b
WHERE b.workspace_id IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM workspace_file_versions v WHERE v.blob_sha = b.sha256
  );

-- ---------------------------------------------------------------------------
-- 5. Fail loudly if anything is still unowned
--
-- Everything reachable must now have an owner. A surviving NULL means a
-- revision cites a blob with a NULL workspace_id — a case the pre-verification
-- says cannot exist. Abort rather than degrade the invariant.
-- ---------------------------------------------------------------------------

DO $$
DECLARE unowned INT;
BEGIN
  SELECT count(*) INTO unowned FROM workspace_blobs WHERE workspace_id IS NULL;
  IF unowned > 0 THEN
    RAISE EXCEPTION
      'ADR-474: % blob(s) still unowned after backfill — aborting', unowned;
  END IF;
END $$;

ALTER TABLE workspace_blobs ALTER COLUMN workspace_id SET NOT NULL;

-- ---------------------------------------------------------------------------
-- 6. The composite identity, and the FK that enforces it
--
-- The old PK and the ledger FK were dropped in step 2 (the split needs the
-- relaxed key). Here the composite identity is established and the FK
-- recreated against it.
-- ---------------------------------------------------------------------------

ALTER TABLE workspace_blobs ADD PRIMARY KEY (workspace_id, sha256);

-- The ledger already carries workspace_id (non-NULL on every live row), so the
-- composite FK needs no new column. This is what makes a cross-workspace blob
-- reference structurally impossible rather than merely discouraged.
ALTER TABLE workspace_file_versions
  ADD CONSTRAINT workspace_file_versions_blob_sha_fkey
  FOREIGN KEY (workspace_id, blob_sha)
  REFERENCES workspace_blobs (workspace_id, sha256);

-- Content-address lookups (dedup probes, content_ref resolution) still scan by
-- sha within a workspace; the PK covers (workspace_id, sha256). This index
-- serves the reverse order — "does this sha exist anywhere" — used by GC and
-- the reachability check.
CREATE INDEX IF NOT EXISTS idx_workspace_blobs_sha ON workspace_blobs (sha256);

COMMIT;
