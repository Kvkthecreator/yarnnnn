-- Migration 200: ADR-407 Phase 0 — the money gate re-keys to the workspace
--
-- ADR-391 D1 put the balance on the workspace row; migration 194 (ADR-396)
-- built the allowance-then-balance pool on top. But the GATE stayed
-- owner-keyed: get_effective_balance(p_user_id) resolved the workspace via
-- owner_id and summed spend via execution_events.user_id. Under ADR-373
-- multi-principal membership that breaks both ways — a member resolves NO
-- workspace (self-gates to $0) and a member's spend never debits the shared
-- pool (see docs/analysis/multi-user-workspace-scope-audit-2026-07-05.md §5.1).
--
-- This migration:
--   * execution_events gains `workspace_id` (the ledger's scope key per
--     ADR-407 D3/D4; `user_id` remains as attribution alongside principal_id).
--   * Backfill maps every historical row to its actor's owner workspace —
--     byte-identical to the old per-owner rollup in the N=1 world.
--   * get_effective_balance is re-keyed: takes p_workspace_id, sums spend by
--     workspace_id. Same pool, same anchor precedence (allowance_granted_at →
--     subscription_refill_at → created_at) — ONLY the scope key changes.
--
-- DEPLOY WINDOW NOTE: the RPC signature changes (p_user_id → p_workspace_id),
-- so between this migration and the code deploy the Python gate's RPC call
-- errors and get_effective_balance() returns 0.0 (fail-safe: judgment calls
-- block, nothing over-spends). Run this migration immediately around the
-- deploy of the same commit.
--
-- N=1 safety: after backfill, SUM(cost) grouped by workspace_id equals the old
-- SUM grouped by owner user_id for every owner — the gate's result is
-- byte-identical for the existing population (verified post-run).

BEGIN;

-- ── 1. execution_events: workspace scope key ────────────────────────────────

ALTER TABLE execution_events
  ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id);

COMMENT ON COLUMN execution_events.workspace_id IS
  'ADR-407 Phase 0: the workspace this invocation ran FOR (the ledger scope '
  'key — spend rolls up here). user_id + principal_id remain as attribution '
  '(WHO acted); workspace_id is WHERE it drew from. NULL only on rows whose '
  'actor had no owner workspace at backfill time.';

-- Backfill: every historical row was written in the N=1 world, where the
-- acting workspace is the actor''s owner workspace.
UPDATE execution_events ee
SET workspace_id = w.id
FROM workspaces w
WHERE w.owner_id = ee.user_id
  AND ee.workspace_id IS NULL;

-- Spend rollups filter by workspace + anchor window.
CREATE INDEX IF NOT EXISTS idx_execution_events_workspace_created
  ON execution_events (workspace_id, created_at DESC);

-- ── 2. get_effective_balance re-keyed to the workspace (ADR-407 D4) ─────────
-- Parameter rename requires DROP (CREATE OR REPLACE cannot rename an input
-- parameter). One function, one key: the workspace. Pool math and anchor
-- precedence are byte-identical to migration 194.

DROP FUNCTION IF EXISTS public.get_effective_balance(uuid);

CREATE FUNCTION public.get_effective_balance(p_workspace_id uuid)
  RETURNS numeric
  LANGUAGE sql
  STABLE SECURITY DEFINER
  SET search_path TO 'public'
AS $function$
  SELECT COALESCE(
    (
      SELECT (w.allowance_usd + w.balance_usd) - COALESCE(
        (
          SELECT SUM(ee.cost_usd)
          FROM execution_events ee
          WHERE ee.workspace_id = w.id
            AND ee.cost_usd IS NOT NULL
            AND ee.created_at > COALESCE(
              w.allowance_granted_at,
              w.subscription_refill_at,
              w.created_at
            )
        ),
        0
      )
      FROM workspaces w
      WHERE w.id = p_workspace_id
      LIMIT 1
    ),
    0
  );
$function$;

GRANT EXECUTE ON FUNCTION get_effective_balance(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION get_effective_balance(uuid) TO service_role;

COMMIT;
