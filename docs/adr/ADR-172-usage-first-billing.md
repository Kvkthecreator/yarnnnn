# ADR-172: Usage-First Billing — Balance Model

> **Status**: Implemented
> **Date**: 2026-04-10
> **Supersedes**: ADR-100 (2-tier subscription model), ADR-171 tier-limit enforcement (metering preserved, tier gates dissolved)

---

## Context

ADR-171 replaced work credits with a universal `cost_usd` token spend meter. The metering is correct. The enforcement model is not.

ADR-171 still enforced against tier limits ($3/mo for Free, $20/mo for Pro) — a subscription model with a spend meter bolted on. Three problems remain:

1. **Wrong gate**: a Free user who hits $3 and wants $5 more must commit to $19/mo. The only path is "upgrade." That's wrong — the right path is "add $5."
2. **Tier gates are fiction**: active_tasks (2 vs 10), sync frequency (daily vs hourly), source limits (5 vs unlimited) exist as capability gates but add zero value. Cost is already the gate. A user who can afford the token spend should not be blocked by an arbitrary task count.
3. **Early Bird is ambiguous**: $9/mo Early Bird pricing was useful for beta; it now creates a confusing third tier with no clear identity. Removed. Admin-granted balance (`kind='admin_grant'`) replaces it for rewarding early users.

---

## Decisions (all locked)

### 1. Balance is the single gate

Every workspace has a `balance_usd` (numeric). All LLM calls deduct `cost_usd` from the effective balance. Hard stop at zero. No tier limits, no capability gates.

**Effective balance** = `balance_usd − SUM(token_usage.cost_usd)` since last subscription refill (or since account creation for non-subscribers).

`balance_usd` is the top-up ledger. `token_usage` is the spend ledger. Both are authoritative — never duplicated.

### 2. Balance sources

| Kind | Amount | Trigger |
|---|---|---|
| `signup_grant` | $3.00 | Workspace creation (one-time) |
| `topup` | $10 / $25 / $50 | User purchases via Lemon Squeezy one-time order |
| `subscription_refill` | $20.00 | Pro subscription billing cycle (reset, not accumulate) |
| `admin_grant` | any | Admin manually credits balance (replaces Early Bird) |

All balance additions recorded in `balance_transactions` table.

### 3. Subscription is optional auto-refill

Pro subscription ($19/mo or $180/yr) = $20 balance reset each billing cycle. No capability difference vs. a top-up user. Subscription is a commitment discount + predictability, not an access tier.

**Removed**: `pro_early_bird` plan variant. `isEarlyBird` flag. Early Bird Lemon Squeezy variant. Existing early bird subscribers grandfathered at current rate via Lemon Squeezy (no code change needed — their webhook events map to `pro` plan going forward).

### 4. Operational gates dissolved entirely

Removed from enforcement:
- `active_tasks` limit (was 2 free / 10 pro)
- `monthly_messages` limit (was 150 free / unlimited pro)
- `sync_frequency` tier gate
- `slack_channels` / `notion_pages` / `total_platforms` source limits

These limits are deleted from `PlatformLimits`, `TIER_LIMITS`, `check_agent_limit()`, `check_source_limit()`, `validate_sources_update()`, `check_monthly_message_limit()`. All callers updated to remove gate checks.

Cost is the only gate. If a user can afford the token spend, they run.

**Exception preserved**: `max_sources` parameter in `compute_smart_defaults()` in `landscape.py` is retained as a UI convenience heuristic for auto-discovery (not enforcement) — it prevents overwhelming new users with 50 auto-selected channels. Set to a high value (50) to be non-restrictive.

### 5. Lemon Squeezy product structure

| Product | LS type | New env var |
|---|---|---|
| Pro Monthly ($19/mo) | Subscription | `LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID` (unchanged) |
| Pro Yearly ($180/yr) | Subscription | `LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID` (unchanged) |
| Top-up $10 | One-time | `LEMONSQUEEZY_TOPUP_10_VARIANT_ID` (new — fill after LS product creation) |
| Top-up $25 | One-time | `LEMONSQUEEZY_TOPUP_25_VARIANT_ID` (new) |
| Top-up $50 | One-time | `LEMONSQUEEZY_TOPUP_50_VARIANT_ID` (new) |

`LEMONSQUEEZY_PRO_EARLYBIRD_VARIANT_ID` — **deleted**.

Webhook: `subscription_payment_success` → `subscription_refill`. New handler: `order_created` → `topup` (for one-time purchases).

### 6. Subscriber vs non-subscriber distinction (UI only)

`subscription_status` on workspace is preserved — it drives:
- Whether the billing tab shows "Manage Billing" (subscriber) vs "Subscribe" CTA
- Auto-refill behavior in webhook handler
- No capability gating

Exposed as `is_subscriber: bool` in `/api/user/limits` response (not `tier`).

---

## Implementation

### New schema (migration 144)

```sql
-- Balance ledger on workspace
ALTER TABLE workspaces
  ADD COLUMN balance_usd numeric(10,4) NOT NULL DEFAULT 3.0,
  ADD COLUMN free_balance_granted boolean NOT NULL DEFAULT true,
  ADD COLUMN subscription_refill_at timestamptz;

-- Balance transaction audit trail
CREATE TABLE balance_transactions (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id  uuid NOT NULL REFERENCES workspaces(id),
    created_at    timestamptz NOT NULL DEFAULT now(),
    kind          text NOT NULL,  -- 'signup_grant' | 'topup' | 'subscription_refill' | 'admin_grant'
    amount_usd    numeric(10,4) NOT NULL,
    lemon_order_id       text,
    lemon_subscription_id text,
    metadata      jsonb
);

CREATE INDEX balance_transactions_workspace ON balance_transactions (workspace_id, created_at);

-- RPC: effective balance
CREATE OR REPLACE FUNCTION get_effective_balance(p_workspace_id uuid)
RETURNS numeric LANGUAGE sql STABLE AS $$
  SELECT COALESCE(
    (SELECT balance_usd FROM workspaces WHERE id = p_workspace_id),
    0
  ) - COALESCE(
    (SELECT SUM(cost_usd) FROM token_usage tu
     JOIN workspaces w ON tu.user_id = ANY(
       SELECT user_id FROM workspaces WHERE id = p_workspace_id LIMIT 1
     )
     WHERE tu.created_at > COALESCE(
       (SELECT subscription_refill_at FROM workspaces WHERE id = p_workspace_id),
       (SELECT created_at FROM workspaces WHERE id = p_workspace_id)
     )
    ),
    0
  );
$$;
```

### `platform_limits.py` changes

- `TIER_LIMITS` dict → deleted
- `PlatformLimits` dataclass → replaced by `WorkspaceBalance` (balance_usd, is_subscriber)
- `check_spend_budget()` → `check_balance(client, user_id) -> tuple[bool, float]` — queries effective balance
- Deleted: `check_agent_limit()`, `check_task_limit()`, `check_source_limit()`, `validate_sources_update()`, `check_monthly_message_limit()`, `get_active_task_count()`, `get_monthly_message_count()`
- `get_usage_summary()` → simplified to `balance_usd`, `spend_usd` (this period), `is_subscriber`

### Caller changes

| File | Change |
|---|---|
| `api/routes/agents.py` | Remove `check_agent_limit()` gate |
| `api/routes/chat.py` | Remove `check_monthly_message_limit()` gate; `check_credits()` → `check_balance()` |
| `api/routes/integrations.py` | Remove `validate_sources_update()` gate; `max_sources` → 50 (non-restrictive) |
| `api/services/primitives/runtime_dispatch.py` | `check_credits()` → `check_balance()` |
| `api/services/working_memory.py` | Remove `check_credits()` call from work_budget signal |
| `api/services/agent_execution.py` | Remove `record_credits()` call |
| `api/services/workspace_init.py` | Grant $3 signup balance, insert `balance_transactions` row |
| `api/routes/subscription.py` | Remove early_bird; add order_created topup handler; simplify plan variants |

### `/api/user/limits` response shape

```json
{
  "balance_usd": 12.50,
  "spend_usd": 1.23,
  "is_subscriber": true,
  "subscription_plan": "pro",
  "next_refill": "2026-05-01T00:00:00Z"
}
```

### Frontend changes

- `TIER_LIMITS` → deleted from `limits.ts`
- `useSubscriptionGate` → `useBalanceGate` (checks balance > 0, not tier)
- `SubscriptionCard` → balance display + top-up buttons + optional subscribe CTA
- `UpgradePrompt` → `AddBalancePrompt` (top-up) or `SubscribePrompt` (auto-refill)
- `UserMenu` → shows remaining balance (`$X remaining`)
- Pricing page → pay-as-you-go framing, subscription as optional

---

## What Does Not Change

- `token_usage` table — unchanged
- `BILLING_RATES` — unchanged (2x markup, Sonnet user-facing)
- `record_token_usage()` at all 7 call sites — unchanged
- `subscription_status` on workspaces — preserved (drives auto-refill)
- Lemon Squeezy core auth (API key, webhook secret, store ID) — unchanged

---

## Revision History

| Date | Change |
|---|---|
| 2026-04-10 | v1.0 — All decisions locked. Balance-first model, operational gates dissolved, early bird removed, top-up products added. |
