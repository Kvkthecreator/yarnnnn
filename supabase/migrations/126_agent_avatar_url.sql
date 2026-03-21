-- Migration 126: Add avatar_url to agents table
-- Nullable optional column for custom agent profile images.
-- Default: NULL (role-based initials rendered client-side).
ALTER TABLE agents ADD COLUMN IF NOT EXISTS avatar_url TEXT DEFAULT NULL;
