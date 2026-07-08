-- Migration 206 — ADR-416 Phase 1: per-principal spend attribution (the rollup)
--
-- The multi-principal re-key (ADR-373) made the balance a per-workspace commons
-- drawn by every principal, and migration 192 added `execution_events.principal_id`
-- to capture WHO caused each spend. But nothing ever CONSUMED that column for a
-- cost rollup — "who spent what" had no live answer (ADR-416 Layer ③, the audit's
-- capture-only finding). This migration adds the consumer.
--
-- `spend_by_principal(p_workspace_id)` returns, per principal, the spend that
-- principal drew from the workspace pool over the SAME window the balance gate
-- uses — so the rows sum to exactly the pool's spend-since-anchor (migration 200's
-- get_effective_balance). It is a legibility READ; it does NOT gate. The hard-stop
-- stays workspace-summed (one pool); this only attributes the draws within it.
--
-- Window/anchor MUST mirror get_effective_balance (migration 200) so the parts
-- reconcile to the whole:
--   WHERE workspace_id = p_workspace_id
--     AND created_at > COALESCE(allowance_granted_at, subscription_refill_at, created_at)
--
-- No new column, no gate change, no balance-mechanics change. Idempotent.

CREATE OR REPLACE FUNCTION public.spend_by_principal(p_workspace_id uuid)
RETURNS TABLE(principal_id text, spend_usd numeric, event_count bigint)
LANGUAGE sql
STABLE
AS $$
  SELECT
    COALESCE(ee.principal_id, 'unknown') AS principal_id,
    COALESCE(SUM(ee.cost_usd), 0)        AS spend_usd,
    COUNT(*)                             AS event_count
  FROM execution_events ee
  JOIN workspaces w ON w.id = p_workspace_id
  WHERE ee.workspace_id = p_workspace_id
    AND ee.created_at > COALESCE(
      w.allowance_granted_at,
      w.subscription_refill_at,
      w.created_at
    )
  GROUP BY COALESCE(ee.principal_id, 'unknown')
  ORDER BY spend_usd DESC;
$$;

COMMENT ON FUNCTION public.spend_by_principal(uuid) IS
  'ADR-416 Phase 1 — per-principal spend rollup over the workspace pool, same '
  'window as get_effective_balance (migration 200). Legibility read, never a gate. '
  'Rows sum to the pool spend-since-anchor.';
