-- Migration 108: Drop abandoned platform_connections.last_synced_at column
--
-- This column has not been written since ADR-073 moved to per-resource
-- freshness tracking via sync_registry. All code derives platform-level
-- freshness from MAX(sync_registry.last_synced_at) per platform.
-- Explicit comments in platform_worker.py, platform_sync_scheduler.py,
-- working_memory.py, and system_state.py confirm this column is dead.
--
-- Dropping to eliminate confusion (NULL values on new accounts look like
-- a data inconsistency bug when they're actually expected).

ALTER TABLE platform_connections DROP COLUMN IF EXISTS last_synced_at;
