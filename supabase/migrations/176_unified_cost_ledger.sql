-- Migration 176: Unified Cost Ledger (ADR-291)
--
-- Collapses the dual-ledger architecture into a single canonical
-- substrate. Promotes `execution_events` to sole authoritative cost
-- record. Drops `token_usage` outright (no backfill — per ADR-291 D6,
-- Singular Implementation applies to data, not just code).
--
-- The structural finding (audit 2026-05-18): `get_effective_balance`
-- RPC reads only `token_usage.cost_usd` while Reviewer reflection
-- (heaviest cost driver, $4.41 of $7.14 historical billed) writes
-- only to `execution_events`. Reviewer spend never debited the balance.
-- This migration makes ADR-172's "balance as single gate" structurally
-- honest.
--
-- After this migration:
--   * All 7 LLM callers write `execution_events` rows only.
--   * `get_effective_balance(user_id)` reads `execution_events.cost_usd`.
--   * `compute_cost_usd_inclusive` (cache-aware, 2x markup) is the
--     sole cost function (lives in services/telemetry.py).
--
-- Companion canon: ADR-291, ADR-171 (amended), ADR-172 (amended),
-- ADR-250 (Phase 2 made load-bearing).

BEGIN;

-- ---------------------------------------------------------------
-- Step 1: Drop token_usage table.
--
-- No backfill. 55 historical rows (2026-05-10 → 2026-05-18) are
-- dropped with the table. Per ADR-291 D6: preserving rows under
-- derived slugs would create a second writer-shape semantics that
-- downstream readers would have to reconcile against, defeating the
-- Singular Implementation cleanup. `balance_transactions` preserves
-- the financial picture for accounting.
-- ---------------------------------------------------------------

DROP TABLE IF EXISTS public.token_usage CASCADE;

-- ---------------------------------------------------------------
-- Step 2: Rewrite get_effective_balance RPC to read execution_events.
--
-- Semantic preserved: balance = workspace.balance_usd − spend since
-- refill anchor. Substrate flipped from token_usage to execution_events.
-- ---------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.get_effective_balance(p_user_id uuid)
  RETURNS numeric
  LANGUAGE sql
  STABLE SECURITY DEFINER
  SET search_path TO 'public'
AS $function$
  SELECT COALESCE(
    (
      SELECT w.balance_usd - COALESCE(
        (
          SELECT SUM(ee.cost_usd)
          FROM execution_events ee
          WHERE ee.user_id = p_user_id
            AND ee.cost_usd IS NOT NULL
            AND ee.created_at > COALESCE(
              w.subscription_refill_at,
              w.created_at
            )
        ),
        0
      )
      FROM workspaces w
      WHERE w.owner_id = p_user_id
      LIMIT 1
    ),
    0
  );
$function$;

-- ---------------------------------------------------------------
-- Step 3: Drop the old get_monthly_spend_usd RPC if it exists.
--
-- It reads from token_usage which no longer exists. Callers (admin
-- dashboard analytics) should query execution_events directly.
-- ---------------------------------------------------------------

DROP FUNCTION IF EXISTS public.get_monthly_spend_usd(uuid);

COMMIT;
