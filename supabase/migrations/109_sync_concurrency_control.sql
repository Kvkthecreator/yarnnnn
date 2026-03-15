-- Migration 109: Sync concurrency control (ADR-112)
--
-- Adds sync lock columns to platform_connections for atomic
-- per-platform per-user concurrency control across all sync paths
-- (scheduled, manual "Sync Now", TP RefreshPlatformContent).
--
-- Replaces the SCHEDULE_WINDOW_MINUTES timing hack.

ALTER TABLE platform_connections ADD COLUMN IF NOT EXISTS sync_in_progress boolean DEFAULT false;
ALTER TABLE platform_connections ADD COLUMN IF NOT EXISTS sync_started_at timestamptz;
