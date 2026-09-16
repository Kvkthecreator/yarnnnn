-- 255 — ADR-652: restore the missing SELECT policy on balance_transactions
--
-- THE DEFECT. `balance_transactions` has RLS **ENABLED WITH ZERO POLICIES** on
-- live. Migration 144 declared both:
--
--     ALTER TABLE balance_transactions ENABLE ROW LEVEL SECURITY;
--     CREATE POLICY "Users can read own balance transactions" ... FOR SELECT
--       USING (workspace_id IN (SELECT id FROM workspaces WHERE owner_id = auth.uid()));
--
-- but only the ALTER survives on the live table. No tracked migration drops the
-- policy, so it was dropped out-of-band. Its sibling `subscription_events` still
-- carries `subscription_events_select_own`, which is what the shape below mirrors.
--
-- RLS-on + no-policy is DENY-ALL to any non-service role. The table was written
-- for four months and read by nothing, so nothing noticed — until ADR-652 served
-- it to the Billing pane and the endpoint returned HTTP 200 / `entries: 0` to the
-- workspace's own owner, against 6 real rows (persona yarnnn-author,
-- ws e58ecdec, probed on prod 2026-09-16).
--
-- This is a FAIL-CLOSED defect, not an exposure: the missing policy denied reads
-- rather than permitting them. Restoring it OPENS exactly the access migration 144
-- specified and nothing wider — owner-only SELECT, no INSERT/UPDATE/DELETE policy
-- (writes stay service-key-only, as 144 intended: "inserts via service key only").
--
-- Receipt after apply: `SELECT count(*) FROM pg_policy WHERE polrelid =
-- 'balance_transactions'::regclass` goes 0 → 1, and the endpoint serves the
-- owner's real rows.

-- Idempotent: safe to re-run, and safe if the original policy is ever restored
-- under its migration-144 name.
DROP POLICY IF EXISTS "Users can read own balance transactions" ON balance_transactions;
DROP POLICY IF EXISTS balance_transactions_select_own ON balance_transactions;

-- Owner-only SELECT, mirroring `subscription_events_select_own` exactly.
-- Scoped through `workspaces.owner_id` rather than `principal_grants`: the
-- balance is the OWNER's fact (ADR-416 D1 — a plain member draws the pool but
-- does not fund it, and `/subscription/status` 403s them), so widening this to
-- grant-holders would be a new authorization decision, not a repair. The route's
-- `_resolve_billing_workspace` remains the authorization gate; this policy is the
-- second gate behind it.
CREATE POLICY balance_transactions_select_own
    ON balance_transactions FOR SELECT
    USING (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
        )
    );
