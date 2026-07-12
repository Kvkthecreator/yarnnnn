-- ADR-448: the reference edge — derived_from on the ledger.
-- A revision may carry the workspace paths it was made from (a JSON list of
-- absolute /workspace/... paths). Nullable, no default, written only when
-- non-empty (the revision_kind precedent — migration 208): ordinary authored
-- writes stay byte-identical. The GIN index serves the dependents containment
-- query ("which head revisions cite this path?").

ALTER TABLE workspace_file_versions ADD COLUMN IF NOT EXISTS derived_from JSONB;

CREATE INDEX IF NOT EXISTS idx_wfv_derived_from
  ON workspace_file_versions USING GIN (derived_from jsonb_path_ops);
