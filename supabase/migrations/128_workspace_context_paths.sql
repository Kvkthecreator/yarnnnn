-- Migration 128: ADR-133 — Workspace Context Architecture
--
-- Move user context files from /memory/ and /brand/ to /workspace/:
--   /memory/MEMORY.md      → /workspace/IDENTITY.md
--   /memory/preferences.md → dissolved (tone in BRAND.md, verbosity in IDENTITY.md)
--   /brand/default/BRAND.md → /workspace/BRAND.md
--
-- /memory/notes.md stays at /memory/notes.md (TP-accumulated knowledge)

-- Move profile to workspace identity
UPDATE workspace_files
SET path = '/workspace/IDENTITY.md',
    summary = 'User identity'
WHERE path = '/memory/MEMORY.md';

-- Move brand to workspace
UPDATE workspace_files
SET path = '/workspace/BRAND.md',
    summary = 'Brand identity'
WHERE path = '/brand/default/BRAND.md';

-- Delete preferences.md (dissolved — tone is in BRAND.md)
DELETE FROM workspace_files WHERE path = '/memory/preferences.md';
