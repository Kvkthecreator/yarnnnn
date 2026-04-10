-- Migration 144: Usage-first billing (ADR-172)
-- Replaces tier-limit enforcement with balance-based gate
-- Adds: balance_usd + free_balance_granted + subscription_refill_at on workspaces
--       balance_transactions audit table
--       get_effective_balance() RPC

-- ── 1. Workspaces: balance columns ──────────────────────────────────────────

ALTER TABLE workspaces
  ADD COLUMN IF NOT EXISTS balance_usd numeric(10,4) NOT NULL DEFAULT 3.0,
  ADD COLUMN IF NOT EXISTS free_balance_granted boolean NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS subscription_refill_at timestamptz;

-- Existing workspaces already had their $3 implicitly — mark as granted
UPDATE workspaces SET free_balance_granted = true WHERE free_balance_granted IS NULL;

-- ── 2. balance_transactions: top-up / refill audit trail ────────────────────

CREATE TABLE IF NOT EXISTS balance_transactions (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id          uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    created_at            timestamptz NOT NULL DEFAULT now(),
    kind                  text NOT NULL CHECK (kind IN (
                            'signup_grant', 'topup', 'subscription_refill', 'admin_grant'
                          )),
    amount_usd            numeric(10,4) NOT NULL,
    lemon_order_id        text,
    lemon_subscription_id text,
    metadata              jsonb
);

CREATE INDEX IF NOT EXISTS balance_transactions_workspace
    ON balance_transactions (workspace_id, created_at);

-- RLS: users can read their own transactions; inserts via service key only
ALTER TABLE balance_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own balance transactions"
    ON balance_transactions FOR SELECT
    USING (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
        )
    );

-- Backfill signup_grant rows for all existing workspaces
INSERT INTO balance_transactions (workspace_id, kind, amount_usd, metadata)
SELECT id, 'signup_grant', 3.0, '{"note": "migration_144_backfill"}'::jsonb
FROM workspaces
ON CONFLICT DO NOTHING;

-- ── 3. get_effective_balance() RPC ──────────────────────────────────────────
-- Effective balance = workspace.balance_usd minus spend since last refill (or since creation)

CREATE OR REPLACE FUNCTION get_effective_balance(p_user_id uuid)
RETURNS numeric
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT COALESCE(
    (
      SELECT w.balance_usd - COALESCE(
        (
          SELECT SUM(tu.cost_usd)
          FROM token_usage tu
          WHERE tu.user_id = p_user_id
            AND tu.created_at > COALESCE(
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
$$;

GRANT EXECUTE ON FUNCTION get_effective_balance(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION get_effective_balance(uuid) TO service_role;
