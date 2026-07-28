-- 224 — ADR-490: the pay-as-you-go platform margin lands on the ledger.
--
-- The pool is debited at provider cost × USAGE_BILLING_MULTIPLIER (1.30,
-- billing_tiers.py). The margin lives in a NEW `billed_usd` column stamped at
-- the single write site (telemetry.record_execution_event); `cost_usd` stays
-- ACTUAL provider cost (2026-07-06 ruling + the ADR-408 D4 router cost-mirror
-- depend on it). One ledger, two numbers: cost-truth and billed-draw.
--
-- Backfill: historical rows bill at cost (billed_usd = cost_usd) — the margin
-- is NEVER retroactive; every pool sum is byte-identical at the flip, and only
-- rows written after the code deploy carry the 1.30 draw.
--
-- RPC updates are additive (no signature change → CREATE OR REPLACE, no
-- deploy-window hazard): both pool reads switch to COALESCE(billed_usd,
-- cost_usd) so pre-column rows (or a write path that ever omits billed_usd)
-- degrade to at-cost, never to $0 (fail-safe: an omission UNDER-charges, it
-- cannot over-charge or free-ride the hard-stop).

BEGIN;

-- ── 1. The billed-draw column ────────────────────────────────────────────────

ALTER TABLE execution_events
  ADD COLUMN IF NOT EXISTS billed_usd numeric;

COMMENT ON COLUMN execution_events.billed_usd IS
  'ADR-490: the pool debit — cost_usd × the platform margin '
  '(billing_tiers.USAGE_BILLING_MULTIPLIER), stamped at the single telemetry '
  'write site. cost_usd stays actual provider cost. Pool reads use '
  'COALESCE(billed_usd, cost_usd). Historical rows backfilled at cost '
  '(margin never retroactive).';

-- Backfill history at cost (idempotent).
UPDATE execution_events
SET billed_usd = cost_usd
WHERE billed_usd IS NULL
  AND cost_usd IS NOT NULL;

-- ── 2. get_effective_balance draws billed ────────────────────────────────────
-- Same signature, same anchor precedence (migration 200); only the summed
-- column changes.

CREATE OR REPLACE FUNCTION public.get_effective_balance(p_workspace_id uuid)
  RETURNS numeric
  LANGUAGE sql
  STABLE SECURITY DEFINER
  SET search_path TO 'public'
AS $function$
  SELECT COALESCE(
    (
      SELECT (w.allowance_usd + w.balance_usd) - COALESCE(
        (
          SELECT SUM(COALESCE(ee.billed_usd, ee.cost_usd))
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

-- ── 3. spend_by_principal reports the billed draw ───────────────────────────
-- Same window as get_effective_balance; rows still sum to the pool
-- spend-since-anchor (both sides now billed — reconciliation preserved).

CREATE OR REPLACE FUNCTION public.spend_by_principal(p_workspace_id uuid)
RETURNS TABLE(principal_id text, spend_usd numeric, event_count bigint)
LANGUAGE sql
STABLE
AS $$
  SELECT
    COALESCE(ee.principal_id, 'unknown')                 AS principal_id,
    COALESCE(SUM(COALESCE(ee.billed_usd, ee.cost_usd)), 0) AS spend_usd,
    COUNT(*)                                             AS event_count
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
  'ADR-416 Phase 1 / ADR-490 — per-principal BILLED spend over the workspace '
  'pool (COALESCE(billed_usd, cost_usd)), same window as get_effective_balance. '
  'Legibility read + the member-cap gate''s source. Rows sum to the pool '
  'spend-since-anchor.';

COMMIT;
