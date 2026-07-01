-- 192_execution_events_principal_id.sql
--
-- Layer-1 capture (capture-first pricing arc, 2026-07-01): attribute every
-- execution_events row to the PRINCIPAL that caused it, not only the workspace
-- owner's user_id.
--
-- Today the ledger is keyed on user_id. When an external LLM writes to the
-- substrate over MCP and Freddie reviews it (the `mcp-foreign-write-review`
-- rows), the cost is charged to the OWNER's user_id and the ledger cannot say
-- which external principal caused it. This column closes that gap so the
-- Cost & Activity Surface can answer "who spent what" per principal.
--
-- Design: NULLABLE column. record_execution_event() attributes every NEW row —
-- an explicit principal_id (the interop path passes the FOREIGN provider host-id
-- via resolve_principal_id, ADR-373 D2) wins; otherwise it defaults to user_id,
-- which is the correct principal for every owner/reviewer/recurrence site
-- (resolve_principal_id maps reviewer→user_id). So no owner-attributed call site
-- changed, and new rows are always attributed. Only rows written BEFORE this
-- migration stay NULL (honest — not back-guessed). N=1 safe: for a solo
-- workspace every row's principal_id == the owner, so the per-principal rollup
-- is byte-identical to the per-user rollup; the split appears exactly when a
-- second principal (a foreign LLM over MCP, a persona-agent) acts.
--
-- This is CAPTURE, not pricing — recording who acted is a truth/completeness
-- fix (ADR-391 §5 item 2), independent of any commercial model.

ALTER TABLE execution_events
  ADD COLUMN IF NOT EXISTS principal_id text;

COMMENT ON COLUMN execution_events.principal_id IS
  'The principal that caused this invocation (ADR-373 resolve_principal_id: owner user_id | foreign-LLM provider host-id | agent slug). NULL = unattributed. Populated at record_execution_event; existing rows stay NULL. Capture-first Layer-1, migration 192.';

-- Index for the per-principal rollup the Cost & Activity Surface will query
-- (GROUP BY principal_id within a workspace + time window). Partial on NOT NULL
-- to skip the unattributed rows.
CREATE INDEX IF NOT EXISTS idx_execution_events_principal
  ON execution_events (user_id, principal_id, created_at DESC)
  WHERE principal_id IS NOT NULL;
