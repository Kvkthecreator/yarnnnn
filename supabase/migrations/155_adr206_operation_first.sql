-- Migration 155: ADR-206 Operation-First Scaffolding
--
-- Backend Phase 1:
--   1. Relocate workspace root files to ADR-206 paths:
--      /workspace/IDENTITY.md    → /workspace/context/_shared/IDENTITY.md
--      /workspace/BRAND.md       → /workspace/context/_shared/BRAND.md
--      /workspace/CONVENTIONS.md → /workspace/context/_shared/CONVENTIONS.md
--      /workspace/AWARENESS.md   → /workspace/memory/awareness.md
--      /workspace/_playbook.md   → /workspace/memory/_playbook.md
--      /workspace/style.md       → /workspace/memory/style.md
--      /workspace/notes.md       → /workspace/memory/notes.md
--   2. Drop `essential` flag on daily-update task rows
--      (ADR-206: daily-update is opt-in post-operation-declared, not signup-essential)
--   3. Drop the maintain-overview task rows + TASK.md/DELIVERABLE.md files
--      (ADR-204 cockpit synthesis dissolves into /work BriefingStrip per ADR-205 F2 + ADR-206)
--
-- Not touched by this migration:
--   - `back-office-*` task rows in existing workspaces (they continue to function; new signups
--     per workspace_init.py no longer scaffold them; they auto-materialize on trigger going
--     forward)
--   - User-authored tasks (origin != system_bootstrap)
--   - `agents` table (ADR-205 migration 154 already handled that collapse)
--
-- Apply with:
--   psql <ACCESS.md URL> -f supabase/migrations/155_adr206_operation_first.sql

BEGIN;

-- Step 1: File relocations
-- -------------------------
-- UPDATE workspace_files SET path = <new> WHERE path = <old>
-- Atomic per-file; UNIQUE constraint on (user_id, path) would block collisions,
-- but target paths are new under ADR-206 so no collisions expected. Rollback on
-- error via transaction.

UPDATE public.workspace_files
SET path = '/workspace/context/_shared/IDENTITY.md',
    updated_at = now()
WHERE path = '/workspace/IDENTITY.md';

UPDATE public.workspace_files
SET path = '/workspace/context/_shared/BRAND.md',
    updated_at = now()
WHERE path = '/workspace/BRAND.md';

UPDATE public.workspace_files
SET path = '/workspace/context/_shared/CONVENTIONS.md',
    updated_at = now()
WHERE path = '/workspace/CONVENTIONS.md';

UPDATE public.workspace_files
SET path = '/workspace/memory/awareness.md',
    updated_at = now()
WHERE path = '/workspace/AWARENESS.md';

UPDATE public.workspace_files
SET path = '/workspace/memory/_playbook.md',
    updated_at = now()
WHERE path = '/workspace/_playbook.md';

UPDATE public.workspace_files
SET path = '/workspace/memory/style.md',
    updated_at = now()
WHERE path = '/workspace/style.md';

UPDATE public.workspace_files
SET path = '/workspace/memory/notes.md',
    updated_at = now()
WHERE path = '/workspace/notes.md';

-- Step 2: daily-update loses essential flag (ADR-206)
-- ---------------------------------------------------
UPDATE public.tasks
SET essential = false,
    updated_at = now()
WHERE slug = 'daily-update';

-- Step 3: maintain-overview rows + workspace files dissolve
-- ----------------------------------------------------------
-- (cockpit synthesis moved into /work BriefingStrip per ADR-205 F2)

DELETE FROM public.workspace_files
WHERE path LIKE '/tasks/maintain-overview/%';

DELETE FROM public.tasks
WHERE slug = 'maintain-overview';

COMMIT;

-- Sanity checks (informational)
DO $$
DECLARE
  legacy_root_files INT;
  daily_essential_count INT;
  maintain_overview_count INT;
BEGIN
  SELECT COUNT(*) INTO legacy_root_files
    FROM public.workspace_files
    WHERE path IN (
      '/workspace/IDENTITY.md',
      '/workspace/BRAND.md',
      '/workspace/CONVENTIONS.md',
      '/workspace/AWARENESS.md',
      '/workspace/_playbook.md',
      '/workspace/style.md',
      '/workspace/notes.md'
    );

  SELECT COUNT(*) INTO daily_essential_count
    FROM public.tasks
    WHERE slug = 'daily-update' AND essential = true;

  SELECT COUNT(*) INTO maintain_overview_count
    FROM public.tasks
    WHERE slug = 'maintain-overview';

  RAISE NOTICE '[ADR-206] legacy root files remaining: % (expect 0)', legacy_root_files;
  RAISE NOTICE '[ADR-206] daily-update rows still flagged essential: % (expect 0)', daily_essential_count;
  RAISE NOTICE '[ADR-206] maintain-overview rows remaining: % (expect 0)', maintain_overview_count;
END $$;
