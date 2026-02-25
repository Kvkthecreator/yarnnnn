-- Migration 083: Add error tracking to sync_registry
-- ADR-077 follow-up: Per-resource sync error surfacing
--
-- Adds last_error and last_error_at columns so the frontend can display
-- why a specific resource failed to sync (e.g., rate limit, auth revoked).
-- Errors are cleared on next successful sync.

ALTER TABLE sync_registry
    ADD COLUMN IF NOT EXISTS last_error TEXT,
    ADD COLUMN IF NOT EXISTS last_error_at TIMESTAMPTZ;

COMMENT ON COLUMN sync_registry.last_error IS 'Most recent sync error message for this resource. Cleared on successful sync.';
COMMENT ON COLUMN sync_registry.last_error_at IS 'Timestamp of the most recent sync error.';
