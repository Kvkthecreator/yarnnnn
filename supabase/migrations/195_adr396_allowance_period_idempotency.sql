-- Migration 195: allowance-grant idempotency key (ADR-396 hardening)
--
-- A single Lemon Squeezy subscription action emits SEVERAL webhook events
-- (subscription_created + subscription_updated + subscription_payment_success all
-- fire on the first payment). Each previously called grant_allowance(), which
-- re-anchored allowance_granted_at — resetting the spend-since-anchor window and
-- silently handing back any allowance already consumed this cycle (a revenue leak
-- on a renewal with mid-cycle spend).
--
-- The fix records WHICH billing period the current allowance was granted for, so a
-- duplicate event for the same period is a no-op. `allowance_period` stores the LS
-- `renews_at` of the granted cycle. grant_allowance() compares its period_anchor
-- against this column: same period + same amount → skip (no re-anchor). A new
-- period (renews_at moved) or a tier change (amount differs) always re-grants.
--
-- N=1 safety: column is nullable and defaults NULL. Existing rows (incl. the one
-- live Starter subscription) get NULL, so the FIRST grant after deploy re-anchors
-- once (harmless — sets the period), and every duplicate thereafter is guarded.
-- Nothing charges differently; no backfill required.

BEGIN;

ALTER TABLE workspaces
  ADD COLUMN IF NOT EXISTS allowance_period timestamptz;

COMMENT ON COLUMN workspaces.allowance_period IS
  'ADR-396: the LS renews_at of the billing period the current allowance_usd was '
  'granted for. grant_allowance() dedup key — a repeat webhook event carrying the '
  'same period with an unchanged allowance amount is a no-op (no re-anchor).';

COMMIT;
