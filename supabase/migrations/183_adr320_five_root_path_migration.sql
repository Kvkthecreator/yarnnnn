-- Migration 183 — ADR-320: five-root workspace permission topology (live data move)
--
-- Moves every live workspace_files + workspace_file_versions row from the legacy
-- roots into the five ADR-320 roots: governance/ constitution/ persona/ operation/
-- system/. The directory IS the permission policy (FOUNDATIONS Derived Principle 25).
--
-- Mapping (legacy -> new), applied to the segment after `/workspace/`:
--   context/_shared/{AUTONOMY.md,_autonomy.yaml,_token_budget.yaml,_pace.yaml,_preferences.yaml} -> governance/
--   context/_shared/{MANDATE.md,PRECEDENT.md}                                                     -> constitution/
--   context/_shared/IDENTITY.md  (operator-posture)  -> DISSOLVED (collapses into persona/IDENTITY.md; persona wins per Axiom 2)
--   context/_shared/{BRAND.md,CONVENTIONS.md}                                                     -> operation/
--   context/{domain}/...                                                                          -> operation/{domain}/...
--   review/...                                                                                    -> persona/...
--   review/decisions.md (legacy name)                                                             -> persona/judgment_log.md
--   memory/...                                                                                    -> system/...
--   specs/...                                                                                     -> operation/specs/...
--   reports/...                                                                                   -> operation/reports/...
--   operations/...                                                                                -> operation/operations/...
--   research/mandate.md (vestigial)                                                               -> DELETED
--
-- IDENTITY collision: every workspace has BOTH context/_shared/IDENTITY.md (operator
-- posture) AND review/IDENTITY.md (persona). Both would map to persona/IDENTITY.md,
-- violating UNIQUE(user_id, path). Resolution per ADR-320 D2b operator-identity
-- collapse: the persona file wins; the operator-posture file is DELETED first.
-- Its content is redundant with the persona (two embodiments of one principal, Axiom 2).
--
-- Revision chain (ADR-209): workspace_file_versions.path moves in lockstep so the
-- full authored history follows each file to its new root. parent_version_id is
-- untouched (the DAG is path-independent).
--
-- Idempotent: re-running is a no-op (no legacy-root rows remain after first run).
-- Transactional: all-or-nothing.

BEGIN;

-- ---------------------------------------------------------------------------
-- Step 0: resolve the IDENTITY collision BEFORE any move.
-- Delete the operator-posture IDENTITY (context/_shared/IDENTITY.md); the persona
-- (review/IDENTITY.md) survives and becomes persona/IDENTITY.md in Step 2.
--
-- ORDER: workspace_files first, THEN versions. workspace_files.head_version_id is
-- a FK into workspace_file_versions(id); deleting a version still referenced as a
-- head violates the FK. Removing the file row first drops that reference.
-- ---------------------------------------------------------------------------
DELETE FROM workspace_files          WHERE path LIKE '%/context/_shared/IDENTITY.md';
DELETE FROM workspace_file_versions  WHERE path LIKE '%/context/_shared/IDENTITY.md';

-- Delete the vestigial research/mandate.md (canonical MANDATE is constitution/).
DELETE FROM workspace_files          WHERE path LIKE '%/research/mandate.md';
DELETE FROM workspace_file_versions  WHERE path LIKE '%/research/mandate.md';

-- ---------------------------------------------------------------------------
-- Step 1: a reusable mapping function (segment-after-/workspace/ rewrite).
-- Applied to both tables. Order matters: most-specific first.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION _adr320_remap(p text) RETURNS text AS $$
DECLARE r text := p;
BEGIN
  -- governance/
  r := replace(r, '/workspace/context/_shared/AUTONOMY.md',       '/workspace/governance/AUTONOMY.md');
  r := replace(r, '/workspace/context/_shared/_autonomy.yaml',    '/workspace/governance/_autonomy.yaml');
  r := replace(r, '/workspace/context/_shared/_token_budget.yaml','/workspace/governance/_token_budget.yaml');
  r := replace(r, '/workspace/context/_shared/_pace.yaml',        '/workspace/governance/_pace.yaml');
  r := replace(r, '/workspace/context/_shared/_preferences.yaml', '/workspace/governance/_preferences.yaml');
  -- constitution/
  r := replace(r, '/workspace/context/_shared/MANDATE.md',        '/workspace/constitution/MANDATE.md');
  r := replace(r, '/workspace/context/_shared/PRECEDENT.md',      '/workspace/constitution/PRECEDENT.md');
  -- operation/ (brand + conventions)
  r := replace(r, '/workspace/context/_shared/BRAND.md',          '/workspace/operation/BRAND.md');
  r := replace(r, '/workspace/context/_shared/CONVENTIONS.md',    '/workspace/operation/CONVENTIONS.md');
  -- legacy decisions.md -> judgment_log.md (then review/ -> persona/ below)
  r := replace(r, '/workspace/review/decisions.md',              '/workspace/review/judgment_log.md');
  -- review/ -> persona/
  r := replace(r, '/workspace/review/',                          '/workspace/persona/');
  -- memory/ -> system/
  r := replace(r, '/workspace/memory/',                         '/workspace/system/');
  -- specs/ reports/ operations/ -> operation/...
  r := replace(r, '/workspace/specs/',                          '/workspace/operation/specs/');
  r := replace(r, '/workspace/reports/',                        '/workspace/operation/reports/');
  r := replace(r, '/workspace/operations/',                     '/workspace/operation/operations/');
  -- any remaining context/{domain}/ -> operation/{domain}/  (trading, authored, customers, revenue, audience, portfolio, ...)
  -- context/_shared/ is fully handled above; this catches all other domains.
  r := regexp_replace(r, '/workspace/context/([^/]+)/', '/workspace/operation/\1/');
  RETURN r;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ---------------------------------------------------------------------------
-- Step 2: apply the remap. workspace_files first (the head), then versions.
-- Only rows whose remap actually changes are touched (WHERE path <> remap).
-- ---------------------------------------------------------------------------
UPDATE workspace_files
   SET path = _adr320_remap(path)
 WHERE path <> _adr320_remap(path);

UPDATE workspace_file_versions
   SET path = _adr320_remap(path)
 WHERE path <> _adr320_remap(path);

-- ---------------------------------------------------------------------------
-- Step 3: verification — zero legacy-root rows must remain.
-- Raises (aborting the transaction) if any survive.
-- ---------------------------------------------------------------------------
DO $$
DECLARE leftover int;
BEGIN
  SELECT count(*) INTO leftover FROM workspace_files
   WHERE path ~ '/workspace/(context|review|memory|specs|reports|operations|research)/'
     AND path !~ '/workspace/operation/(specs|reports|operations)/';
  IF leftover > 0 THEN
    RAISE EXCEPTION 'ADR-320 migration left % legacy-root rows in workspace_files', leftover;
  END IF;
  SELECT count(*) INTO leftover FROM workspace_file_versions
   WHERE path ~ '/workspace/(context|review|memory|specs|reports|operations|research)/'
     AND path !~ '/workspace/operation/(specs|reports|operations)/';
  IF leftover > 0 THEN
    RAISE EXCEPTION 'ADR-320 migration left % legacy-root rows in workspace_file_versions', leftover;
  END IF;
END $$;

DROP FUNCTION _adr320_remap(text);

COMMIT;
