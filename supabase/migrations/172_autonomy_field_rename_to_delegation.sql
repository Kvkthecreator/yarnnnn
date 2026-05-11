-- Migration 172 — Commit F.1: rewrite all _autonomy.yaml files to canonical
-- {delegation, ceiling_cents} schema.
--
-- DEFECT BEING FIXED (audit 2026-05-11):
--   FE writes `level: bounded_autonomous` (4-value union); backend
--   `_validate_autonomy_block` reads `delegation` (3-value enum). The
--   field name and value space have been mismatched since ADR-254
--   landed. Result: `should_auto_execute_verdict()` falls through to
--   the default "manual" branch on EVERY production workspace, regardless
--   of what the operator picked on the FE chip. The autonomy mode UX
--   has been cosmetic — backend ignored every selection.
--
-- CANONICAL SCHEMA (post-migration):
--   default:
--     delegation: manual | bounded | autonomous   # 3 values, matches backend
--     ceiling_cents: <int>                        # required when delegation=bounded
--     never_auto:                                 # action_types that always route to operator
--       - <action_type>
--   domains:
--     <domain>:
--       delegation: ...
--       ceiling_cents: ...
--   paused_until: <ISO timestamp>                 # ADR-248 D3 — set by Reviewer / operator
--   pause_reason: <string>
--
-- VALUE MIGRATION RULES:
--   level: bounded_autonomous  →  delegation: bounded
--   level: autonomous          →  delegation: autonomous
--   level: manual              →  delegation: manual
--   level: assisted            →  delegation: manual    (was already silently treated as manual; assisted had no backend semantics)
--   (no level field)           →  delegation: manual    (safe default)
--
-- DROPPED FIELDS (ADR-263 D4 + cleanup):
--   heartbeat_triggers — explicitly deleted by ADR-263 D4 ("cron is part
--     of the environment that fires recurrences; recurrence.mode declares
--     wake intent"). Live data still carries these from pre-263 era.
--
-- ATTRIBUTION:
--   Rewrite is committed via the Authored Substrate (ADR-209) write path
--   from a one-shot Python script; this SQL migration is the manifest +
--   verification gate. The script lives in the same commit at
--   api/scripts/oneshot/rewrite_autonomy_yaml_to_delegation_schema.py.
--
-- IDEMPOTENCY: this SQL only verifies the post-state. The Python script
-- is the actual rewriter and is itself idempotent (skips files already
-- carrying `delegation:` and no `level:`).

DO $$
DECLARE
  bad_count int;
BEGIN
  -- Verification: every _autonomy.yaml file should now contain `delegation:`
  -- and NOT contain `level:` (the legacy field name).
  SELECT count(*) INTO bad_count
  FROM workspace_files
  WHERE path = '/workspace/context/_shared/_autonomy.yaml'
    AND (
      content NOT LIKE '%delegation:%'
      OR content LIKE '%
  level:%'  -- match `  level:` (indented under default/domains, not in a comment)
      OR content LIKE '%heartbeat_triggers:%'
    );

  IF bad_count > 0 THEN
    RAISE EXCEPTION 'Migration 172 verification failed: % _autonomy.yaml files still carry legacy schema (level: / heartbeat_triggers: / missing delegation:). Run api/scripts/oneshot/rewrite_autonomy_yaml_to_delegation_schema.py first.', bad_count;
  END IF;

  RAISE NOTICE 'Migration 172 verified: all _autonomy.yaml files use canonical {delegation, ceiling_cents} schema.';
END $$;
