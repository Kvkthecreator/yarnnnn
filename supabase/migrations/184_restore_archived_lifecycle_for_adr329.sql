-- =============================================================================
-- Migration 184 — Restore 'archived' to the workspace_files lifecycle constraint
-- =============================================================================
--
-- ADR-329 D4 (2026-06-08) reintroduced lifecycle='archived' as the operator
-- "Delete" mechanism (trash-semantics, ADR-209-retained, reversible):
-- `routes/documents.py::delete` writes a new revision with lifecycle='archived',
-- and the Files tree + uploads list filter it out via
-- `lifecycle.is.null OR lifecycle.neq.archived`.
--
-- But migration 159 (ADR-209 Phase 5, 2026-04-23) had DROPPED 'archived' from
-- the lifecycle CHECK constraint, on the reasoning that "the only code path
-- that ever wrote it was dead." ADR-329 re-made that path live WITHOUT a
-- migration to re-permit the value — so since 2026-06-08 the constraint has
-- been
--     CHECK (lifecycle IN ('ephemeral', 'active', 'delivered'))
-- and any operator "Delete" click 500s on a constraint violation. ADR-329 D4
-- has been non-functional against the live schema.
--
-- This migration re-adds 'archived' to the enum so ADR-329's delete=archive
-- actually works. It also unblocks the ADR-320 legacy-straggler cleanup
-- (archiving inert context/ duplicates that have current operation/ twins),
-- which uses the same lifecycle='archived' mechanism.
--
-- Idempotent: drops + re-adds the named constraint.
-- =============================================================================

ALTER TABLE workspace_files
  DROP CONSTRAINT IF EXISTS workspace_files_lifecycle_check;

ALTER TABLE workspace_files
  ADD CONSTRAINT workspace_files_lifecycle_check
  CHECK (lifecycle IN ('ephemeral', 'active', 'delivered', 'archived'));

-- =============================================================================
-- Verification (run manually after migration)
-- =============================================================================
--
-- -- Constraint now permits 'archived':
-- SELECT pg_get_constraintdef(oid) FROM pg_constraint
-- WHERE conname = 'workspace_files_lifecycle_check';
-- -- expect: CHECK ((lifecycle = ANY (ARRAY['ephemeral','active','delivered','archived'])))
