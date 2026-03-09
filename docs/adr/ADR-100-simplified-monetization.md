# ADR-100: Simplified Monetization — 2-Tier Model with Early Bird Pricing

> **Status**: Accepted
> **Date**: 2026-03-09
> **Deciders**: Kevin (solo founder)
> **Supersedes**: ADR-053 3-tier structure (Free/Starter/Pro → Free/Pro)
> **Related**: ADR-053 (Platform Sync Monetization), ADR-072 (Accumulation Moat), ADR-077 (Sync Overhaul)

---

## Context

### Problem

ADR-053 established a 3-tier model (Free/$9 Starter/$19 Pro) with 6+ gating dimensions:
- Source limits per platform (Slack/Gmail/Notion)
- Sync frequency (1x/4x/hourly)
- Daily token budget (50k/250k/unlimited)
- Active deliverables (2/5/unlimited)

This creates several problems for MVP beta:

1. **User confusion** — Nobody thinks in "50k tokens/day." Users understand "messages" and "deliverables."
2. **Decision paralysis** — Two paid tiers means two decisions. At beta, you want one: "free or paid?"
3. **Compressed revenue** — $9 and $19 are too close. Most who'd pay $9 would pay $19.
4. **Over-engineering** — 6 dimensions of gating = 6 enforcement surfaces to maintain.

### Bootstrap Constraint

Must be net-positive (or near break-even) from day one of standard pricing. Willing to accept modest loss during Early Bird beta as customer acquisition cost.

### Pre-Seed Signal

Need 50–100 users with conversion data to demonstrate product-market fit. Early Bird pricing ($9) lowers conversion friction for beta users.

---

## Decision

### 1. Collapse to 2 Tiers (Free + Pro)

| | Free | Pro |
|---|------|-----|
| **TP messages** | 50/month | Unlimited |
| **Active deliverables** | 2 | 10 |
| **Platforms** | All 4 | All 4 |
| **Sources** | 5/5/10 (Slack/Gmail/Notion) | Unlimited |
| **Sync frequency** | 1x/day | Hourly |
| **Standard price** | $0 | **$19/mo** |

### 2. Early Bird Pricing

- **$9/mo** — same Pro features, promotional price during beta
- **Monthly only** — no yearly lock-in (limits exposure to prolonged loss on heavy users)
- **Separate Lemon Squeezy variant** — can stop selling anytime without affecting existing subscribers
- **Existing $9 subscribers continue** — Lemon Squeezy keeps billing them after variant removed from checkout
- **Sunset at our discretion** — post 100 users, post investment, or whenever ready

### 3. Replace Daily Token Budget with Monthly Messages

- Users understand "50 messages this month" — not "50,000 tokens today"
- Count user-sent messages in `session_messages` per calendar month
- Predictable cost ceiling per free user
- Clear upgrade trigger: "You've used 45 of 50 messages this month"

### 4. Remove Starter Tier Entirely

- Delete from backend constants, frontend types, Lemon Squeezy variant mapping
- Any existing "starter" subscribers in DB gracefully mapped to "pro"
- One tier to explain, one upgrade CTA, one decision

---

## Cost Analysis

### Free User (50 msgs/month, 2 deliverables)

| Component | Estimate |
|-----------|----------|
| TP messages (realistic ~30 msgs × $0.04) | $1.20/mo |
| Deliverables (2 active, ~1 run/day each = 60 runs × $0.08) | $4.80/mo |
| Sync infrastructure | $0.05/mo |
| **Active free user total** | **~$6/mo** |
| **Blended (40% active)** | **~$3/mo** |

### Pro User (unlimited msgs, 10 deliverables)

| Component | Estimate |
|-----------|----------|
| TP messages (power user ~240 msgs × $0.04) | $9.60/mo |
| Deliverables (~100 runs/mo × $0.08) | $8.00/mo |
| Sync infrastructure | $0.50/mo |
| **Heavy Pro user** | **~$18/mo** |
| **Moderate Pro user** | **~$7/mo** |
| **Blended Pro** | **~$10–12/mo** |

### Break-Even at Standard Pricing ($19/mo)

| Conversion Rate | Revenue per 10 users | Cost per 10 users | Net |
|----------------|---------------------|-------------------|-----|
| 10% | $19 | $27 + $11 = $38 | -$19 |
| 15% | $28.50 | $25.50 + $16.50 = $42 | -$13.50 |
| 20% | $38 | $24 + $22 = $46 | -$8 |
| 25% | $47.50 | $22.50 + $27.50 = $50 | -$2.50 |

At standard pricing, need ~25%+ conversion for true net-positive. Realistic with good activation.

### Early Bird Phase ($9/mo) — Accepted Loss

At 50 users, 20% conversion (10 paying):
- Revenue: $90/mo
- Cost: ~$230/mo
- Loss: ~$140/mo

**$140/mo for 2–3 months = $400–840 total CAC.** This is the cost of acquiring 50+ users with conversion data for pre-seed. Acceptable.

### Long-Term Cost Trajectory

LLM costs drop ~50–75% per year. Today's $3/mo free user becomes $1/mo within 12 months. Margins improve naturally without price changes.

---

## Early Bird Trust Model

The critical insight: **trust is preserved by only giving people MORE, never less.**

| Action | Trust Impact |
|--------|-------------|
| Raising price on existing users | Betrayal |
| Reducing free tier after reliance | Betrayal |
| Adding cheaper tier below Pro | Fine — more options |
| Lowering Pro price | Positive — "I got in early" |
| Grandfathering Early Bird users | Loyalty + word-of-mouth |

Early Bird users get exactly what was advertised: Pro at $9/mo while available. When we stop selling it, their subscriptions continue. They're our earliest believers and will become profitable as costs drop.

### Beta Shield

Early Bird framing gives social permission for rough edges:
- "$19/mo Pro" sets expectation of polish
- "$9/mo Early Bird" says "we're early, your feedback shapes the product"
- Different relationship: collaborators, not just customers

---

## Implementation

### Lemon Squeezy Variants

| Variant | Price | Env Var |
|---------|-------|---------|
| Pro Monthly (Standard) | $19/mo | `LEMONSQUEEZY_PRO_MONTHLY_VARIANT_ID` |
| Pro Yearly (Standard) | $190/yr | `LEMONSQUEEZY_PRO_YEARLY_VARIANT_ID` |
| Pro Monthly (Early Bird) | $9/mo | `LEMONSQUEEZY_PRO_EARLYBIRD_VARIANT_ID` |

Starter variants deprecated — stop referencing in code, can remove from Lemon Squeezy dashboard later.

### Migration Path

- Existing "starter" subscribers → treated as "pro" (graceful upgrade)
- Existing "pro" subscribers → unchanged
- Database `workspaces.subscription_status` still stores "free" or "pro"

### Key Files Changed

- `api/services/platform_limits.py` — 2-tier constants, monthly message enforcement
- `api/routes/subscription.py` — Early Bird variant, remove Starter
- `api/routes/chat.py` — Monthly message limit check
- `web/lib/subscription/limits.ts` — 2-tier frontend limits
- `web/app/pricing/page.tsx` — 2-column layout + Early Bird
- `web/components/subscription/SubscriptionCard.tsx` — 2-tier display
- `supabase/migrations/094_monthly_message_count.sql` — New RPC

---

## Consequences

### Positive

1. **Simpler for users** — One decision: free or paid
2. **Simpler for us** — Less enforcement code, fewer edge cases
3. **Better conversion** — $9 Early Bird is impulse-buy territory
4. **Future flexibility** — Can add tiers, adjust prices, only ever giving people more
5. **Investor narrative** — "Net positive at $19, $9 Early Bird for beta traction"

### Negative

1. **Early Bird loss** — ~$140/mo at 50 users. Acceptable as CAC.
2. **No middle tier** — Some users may want "more than free, less than $19." Can add Starter later if data shows demand.

### Mitigations

- Early Bird is time-limited — sunset when economics require
- Monthly-only Early Bird limits long-term exposure
- LLM cost trajectory naturally improves margins
