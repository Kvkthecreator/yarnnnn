-- 197_adr406_linear_chain_guard.sql
-- ADR-406 D3: the revision chain becomes STRUCTURALLY linear.
--
-- A partial UNIQUE index on workspace_file_versions.parent_version_id means
-- two truly concurrent writers that both read head H cannot both insert a
-- child of H — the loser gets a unique violation, which write_revision()
-- translates: precondition callers get StaleWriteError (their base is
-- gone), append callers retry on the fresh head. This closes the
-- read-then-insert TOCTOU window the Python-side CAS (ADR-406 D1) leaves
-- open.
--
-- Pre-verified clean in prod before ratification (2026-07-03): 0 duplicate
-- parent_version_id values across 284 revisions — the index builds without
-- repair.
--
-- The ADR-209 orphan-reconciliation property is preserved: an orphan
-- revision (insert succeeded, head-pointer upsert lost) IS the newest
-- revision, so the next write parents on it — still unique.
--
-- NULL parents (first revision of each path) are exempt (partial index).

CREATE UNIQUE INDEX IF NOT EXISTS uq_workspace_file_versions_parent
  ON workspace_file_versions (parent_version_id)
  WHERE parent_version_id IS NOT NULL;

COMMENT ON INDEX uq_workspace_file_versions_parent IS
  'ADR-406 D3: linearity guard — at most one child per parent revision. '
  'write_revision() translates violations (StaleWriteError for '
  'precondition callers, fresh-head retry for appenders).';
