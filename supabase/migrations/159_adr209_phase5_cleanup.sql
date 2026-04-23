-- Migration 159: ADR-209 Phase 5 — schema cleanup
--
-- Closes the ADR-209 deprecation manifest. Three schema changes:
--
--   1. Drop workspace_files.version integer column.
--      Post-Phase 2 audit found zero live-code writers and zero meaningful
--      readers (code references search for the word "version" all resolve
--      to agent_runs, manifest.json, or platform registries — never the
--      workspace_files column). DB state confirms: 101 rows trivially
--      default to 1, one residual row at 2 from pre-Phase 2 legacy write
--      path. Revision chain (workspace_file_versions) is the authoritative
--      versioning substrate per ADR-209.
--
--   2. Delete the single pre-Phase 2 archived-history row at
--      /agents/trading-operator/history/AGENT.md/v1.md. It's the last
--      artifact of the deleted /history/{filename}/v{N}.md convention
--      (ADR-119 Phase 3, superseded).
--
--   3. Tighten the lifecycle check constraint to remove the 'archived'
--      enum value. Post-Phase 2 there are no live producers of
--      lifecycle='archived' — the only code path that ever wrote it was
--      _archive_to_history, deleted in Phase 2. The three remaining
--      values ('ephemeral', 'active', 'delivered') cover the live
--      lifecycle state machine per ADR-127 + workspace-conventions.md.
--
-- Kept intact:
--   - workspace_files.content column (denormalization retained).
--     Measured read-latency gap between denormalized read and three-table
--     JOIN is negligible (0.05ms vs 0.065ms), but the FTS index
--     (idx_ws_fts) + embedding index (idx_ws_embedding) are both defined
--     on workspace_files.content. Dropping the column would require
--     rebuilding both indexes on a joined view or on workspace_blobs —
--     materially invasive for zero measurable benefit. Decision documented
--     in ADR-209 Phase 5 + docs/architecture/authored-substrate.md §3.

-- =============================================================================
-- 1. Drop the one pre-Phase 2 /history/ artifact
-- =============================================================================

-- FK order: no revision chain for this legacy path, so a simple delete works.
-- (The legacy /history/ pattern created workspace_files rows but not
-- workspace_file_versions rows — the backfill in migration 158 gave it a
-- synthetic initial revision, so we clean both sides.)
DELETE FROM workspace_files
  WHERE path LIKE '%/history/%/v%.md'
    AND lifecycle = 'archived';

DELETE FROM workspace_file_versions
  WHERE path LIKE '%/history/%/v%.md';

-- =============================================================================
-- 2. Drop the version integer column
-- =============================================================================

ALTER TABLE workspace_files DROP COLUMN IF EXISTS version;

-- =============================================================================
-- 3. Tighten lifecycle check constraint (drop 'archived' enum value)
-- =============================================================================

ALTER TABLE workspace_files
  DROP CONSTRAINT IF EXISTS workspace_files_lifecycle_check;

ALTER TABLE workspace_files
  ADD CONSTRAINT workspace_files_lifecycle_check
  CHECK (lifecycle IN ('ephemeral', 'active', 'delivered'));

-- =============================================================================
-- Verification queries (run manually after migration)
-- =============================================================================
--
-- -- Column is gone:
-- SELECT column_name FROM information_schema.columns
-- WHERE table_name = 'workspace_files' AND column_name = 'version';
-- -- expect 0 rows
--
-- -- No archived rows remain:
-- SELECT COUNT(*) FROM workspace_files WHERE lifecycle = 'archived';
-- -- expect constraint-violation if attempted; pre-delete cleanup ensures 0
--
-- -- No /history/ artifact paths remain:
-- SELECT COUNT(*) FROM workspace_files WHERE path LIKE '%/history/%/v%.md';
-- -- expect 0
