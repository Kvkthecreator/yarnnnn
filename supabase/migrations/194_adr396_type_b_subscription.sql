-- Migration 194: Type-B subscription over the metered balance (ADR-396)
--
-- Turns the pay-as-you-go balance (ADR-172) into the OVERAGE pool beneath a
-- plan tier that grants a monthly INCLUDED ALLOWANCE. The draw order (ADR-396
-- §3): allowance → balance → hard-stop at zero.
--
-- What changes:
--   * workspaces gains `subscription_tier` (the internal plan selector — distinct
--     from the LS-variant flag `subscription_plan`), plus `allowance_usd` +
--     `allowance_granted_at` (the monthly included allowance and its anchor).
--   * get_effective_balance is rewritten to draw spend against (allowance_usd +
--     balance_usd), anchored on allowance_granted_at → subscription_refill_at →
--     created_at. The allowance is spent first by construction; top-ups persist
--     across cycles (a monthly grant resets ALLOWANCE, never balance_usd).
--   * balance_transactions.kind gains 'allowance_grant'.
--
-- N=1 safety: every existing workspace defaults to tier 'free' with $0 allowance,
-- so (allowance_usd + balance_usd) == balance_usd and the effective balance is
-- BYTE-IDENTICAL to pre-migration behavior until a workspace subscribes. Nothing
-- charges differently on deploy.
--
-- Companion canon: ADR-396 (this), ADR-172 (amended — balance re-scoped as the
-- overage pool), ADR-291 (execution_events preserved as the sole meter),
-- ADR-392 (retention gate, now tier-clamped in code).

BEGIN;

-- ── 1. Workspaces: tier + allowance columns ─────────────────────────────────

ALTER TABLE workspaces
  ADD COLUMN IF NOT EXISTS subscription_tier text NOT NULL DEFAULT 'free',
  ADD COLUMN IF NOT EXISTS allowance_usd numeric(10,4) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS allowance_granted_at timestamptz;

-- Guard the tier to the known set (free | starter | pro). Unknown values would
-- read as free via the app's normalize_tier, but the DB constraint keeps the
-- column honest at the write boundary.
ALTER TABLE workspaces
  DROP CONSTRAINT IF EXISTS workspaces_subscription_tier_check;
ALTER TABLE workspaces
  ADD CONSTRAINT workspaces_subscription_tier_check
  CHECK (subscription_tier IN ('free', 'starter', 'pro'));

CREATE INDEX IF NOT EXISTS idx_workspaces_subscription_tier
  ON workspaces (subscription_tier);

-- ── 2. balance_transactions: allowance_grant kind ───────────────────────────
-- A monthly billing cycle records an 'allowance_grant' row (the included
-- allowance), distinct from 'subscription_refill' (the legacy balance reset,
-- retired in code by ADR-396 — the kind stays in the CHECK for historical rows).

ALTER TABLE balance_transactions
  DROP CONSTRAINT IF EXISTS balance_transactions_kind_check;
ALTER TABLE balance_transactions
  ADD CONSTRAINT balance_transactions_kind_check
  CHECK (kind IN (
    'signup_grant', 'topup', 'subscription_refill', 'admin_grant', 'allowance_grant'
  ));

-- ── 3. get_effective_balance() RPC — allowance-then-balance draw ─────────────
-- effective = (allowance_usd + balance_usd) − spend since the allowance anchor.
--
-- Anchor precedence: allowance_granted_at (moves each monthly grant) →
-- subscription_refill_at (legacy anchor, still honored for pre-ADR-396 rows) →
-- created_at (never-subscribed workspaces count spend over their lifetime, same
-- as today). The allowance is consumed FIRST purely by being summed into the
-- pool that spend draws down — no separate accounting needed; when the pool hits
-- zero the caller's hard-stop fires (check_balance, unchanged).

CREATE OR REPLACE FUNCTION public.get_effective_balance(p_user_id uuid)
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
          WHERE ee.user_id = p_user_id
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
      WHERE w.owner_id = p_user_id
      LIMIT 1
    ),
    0
  );
$function$;

GRANT EXECUTE ON FUNCTION get_effective_balance(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION get_effective_balance(uuid) TO service_role;

COMMIT;
