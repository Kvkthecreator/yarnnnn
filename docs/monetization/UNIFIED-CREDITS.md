# Unified Credits — Chat-Inclusive Metered Pricing

> **Status**: Consideration — not yet decided
> **Date**: 2026-03-26
> **Context**: Duplicate task execution bug (6x runs) + unbounded chat costs exposed structural gap in current model
> **Related**: ADR-100 (current tier model), [COST-MODEL.md](COST-MODEL.md), [STRATEGY.md](STRATEGY.md)

---

## Problem Statement

The current model has two separate gates:

| Stream | Gate | Bounded? | Risk |
|--------|------|----------|------|
| Task runs | Work units (60 free / 1000 pro) | Yes | Scheduler bugs → runaway spend (observed: 6x duplicate) |
| Chat (TP) | Message count (50 free / unlimited pro) | **No (Pro)** | Heavy testing/usage → invisible API cost |
| Renders | Render count (10 free / 100 pro) | Yes | Low risk |

**The gap**: Pro chat is unlimited Sonnet at ~$0.02-0.15 per message (grows with context). A power user sending 30+ messages daily costs more in chat than in autonomous runs. The "unlimited" promise is a liability we can't see until the Anthropic invoice arrives.

**Additional friction**: Users track three different meters. The mental model is fragmented — "am I out of messages, work units, or renders?"

---

## Proposal: One Credit Pool

Everything draws from a single monthly credit balance.

### Credit Costs

| Action | Credits | Rationale |
|--------|---------|-----------|
| Chat message (TP) | 1 | Sonnet call, but lighter context than full generation |
| Task execution (scheduled) | 3 | Full pipeline: context gather → Sonnet → save → deliver |
| Manual agent run | 3 | Same pipeline as scheduled |
| Render (PDF/chart/PPTX) | 1 | Output gateway compute |
| Platform sync | 0 | Mechanical, no LLM cost |
| Composer heartbeat | 0 | Haiku, negligible |

**Why 1:3 chat-to-task?** A task execution costs ~$0.04-0.05 in API calls (multi-step Sonnet). A chat message costs ~$0.01-0.03 (single Sonnet turn, lower with caching). The 3:1 ratio roughly tracks actual cost difference while keeping chat feeling lightweight.

### Tier Structure

| | Free | Pro ($19/mo) |
|--|------|-------------|
| Monthly credits | 50 | 1,000 |
| Overage | Hard stop | Buy more ($5/100) |
| Sync frequency | 1x/day | Hourly |
| Active agents | 2 | 10 |

**What stays tier-gated (not credit-gated)**:
- Agent count (2 vs 10) — structural, not usage
- Sync frequency — cost is negligible, it's a product lever
- Source limits — same reasoning

### Usage Scenarios

**Casual Pro user (mostly chat)**:
- 600 chat messages + 30 weekly task runs (8 tasks × 4 weeks) + 10 renders
- = 600 + 90 + 10 = **700 credits/month** ✓

**Automation-heavy Pro user**:
- 100 chat messages + 80 task runs (daily briefers) + 20 renders
- = 100 + 240 + 20 = **360 credits/month** ✓

**Power user (needs overage)**:
- 500 chat messages + 100 task runs + 30 renders
- = 500 + 300 + 30 = **830 credits/month** ✓ (within 1000)

**Heavy tester (the scenario that burned us)**:
- 1000+ chat messages testing + 50 task runs
- = 1000 + 150 = **1,150 credits** → buys 1 pack ($5) or hits limit
- Under current model this is invisible and unbounded

---

## Unit Economics

With prompt caching enabled (deployed 2026-03-26):

| Action | Our API cost (cached) | Credit price at $19/1000 | Margin |
|--------|----------------------|--------------------------|--------|
| Chat message | ~$0.005-0.015 | $0.019 | 27-74% |
| Task execution | ~$0.02-0.03 | $0.057 (3 credits) | 47-65% |
| Render | ~$0.005 | $0.019 | 74% |

**Blended**: ~60% gross margin at Pro, improving as caching warms up.

**Overage packs** ($5/100 = $0.05/credit) are pure margin: ~75-90%.

**Free tier** (50 credits, no revenue): costs us ~$0.50-1.00/month in API calls. Acceptable for conversion funnel.

---

## Implementation Path

### Phase 1: Unified Credits Table
- New `credits_ledger` table (or evolve `work_units`): `user_id, action_type, credits_consumed, metadata, created_at`
- `check_credits(user_id)` replaces both `check_work_budget()` and `check_monthly_message_limit()`
- `record_credits(user_id, action, amount)` — single write path
- Delete `get_monthly_message_count()` RPC

### Phase 2: Enforcement Points
- `chat.py`: 1 credit per user message (before Sonnet call)
- `task_pipeline.py`: 3 credits per execution (replaces `record_work_units`)
- `runtime_dispatch.py`: 1 credit per render (replaces `check_render_limit`)
- Budget check at each point: `remaining = tier_limit - month_usage`

### Phase 3: Overage (Pro only)
- Lemon Squeezy one-time purchase for credit packs
- `credits_purchased` table or column on user profile
- Overage draws from purchased credits after monthly allowance exhausted
- Webhook: `order_created` → add credits

### Phase 4: Frontend
- Single credits meter in nav (replaces message count)
- Settings page: usage breakdown by type (chat vs runs vs renders)
- Low-credits warning at 10% remaining
- Buy-more CTA for Pro users at 0%

---

## Open Questions

1. **Should chat degrade to Haiku instead of hard-stopping?** Pro users hitting the limit mid-conversation is a bad experience. Haiku fallback preserves chat but signals "you're over budget." Trades user experience for cost control.

2. **Credit rollover?** Unused credits expire monthly (simpler) or roll over (more generous, complicates accounting). Leaning toward expire — it's the industry norm and prevents credit hoarding.

3. **Existing Pro subscribers**: Grandfather unlimited messages for 1-2 billing cycles with a "switching to credits" notice? Or migrate immediately with a generous first-month bonus (e.g., 2000 credits)?

4. **Should agent count stay tier-gated or become credit-gated?** Current: 2/10 hard limit. Alternative: each active agent costs N credits/month (makes scaling linear). Leaning toward keeping it tier-gated — it's simpler and agent count is a structural choice, not a usage metric.

5. **Batch API for tasks**: Anthropic's Batch API is 50% off but non-real-time. Task executions are non-interactive — could route through batch, cutting task credit cost further. Worth exploring after credits model is stable.

---

## What This Replaces

| Current | Unified Credits |
|---------|----------------|
| `work_units` table | `credits_ledger` (absorbed) |
| `get_monthly_message_count()` RPC | Deleted — credits check |
| `check_work_budget()` | `check_credits()` |
| `check_render_limit()` | `check_credits()` |
| `record_work_units()` | `record_credits()` |
| `record_render_usage()` | `record_credits()` |
| Three separate meters | One credit balance |

---

## Decision Criteria

Adopt this if:
- We're confident the 1:3 weighting reflects real cost ratios (validate with 2 weeks of cached usage data)
- Lemon Squeezy supports one-time credit pack purchases alongside subscriptions
- We're comfortable with the migration path for existing users

Don't adopt if:
- Users perceive credits as "nickel-and-diming" (survey needed)
- The weighting causes chat to feel expensive relative to value delivered
- Implementation complexity outweighs the cost control benefit (it shouldn't — the code paths are already isolated)
