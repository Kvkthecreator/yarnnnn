# Subscription + Work Credits — Hybrid Pricing Model

> **Status**: Decided — supersedes unified credits consideration
> **Date**: 2026-03-26 (revised)
> **Context**: Duplicate task execution bug (6x runs) + unbounded chat costs exposed structural gap. Unified credits model rejected — metering chat creates psychological friction that undermines engagement.
> **Related**: ADR-100 (current tier model), [COST-MODEL.md](COST-MODEL.md), [STRATEGY.md](STRATEGY.md)

---

## Problem Statement

The current model has three separate gates with different risk profiles:

| Stream | Gate | Bounded? | Risk |
|--------|------|----------|------|
| Task runs | Work units (60 free / 1000 pro) | Yes | Scheduler bugs → runaway spend (observed: 6x duplicate) |
| Chat (TP) | Message count (50 free / unlimited pro) | **No (Pro)** | Heavy usage → invisible API cost |
| Renders | Render count (10 free / 100 pro) | Yes | Low risk |

**The gap**: Pro chat is unlimited Sonnet at ~$0.005-0.15 per message (grows with context). Three separate meters fragment the mental model.

**Why unified credits was rejected**: Metering chat (even at 1 credit) makes every keystroke feel like a running meter. Users self-censor, send shorter messages, avoid follow-ups. Chat is the onramp to autonomous work — gating it punishes the behavior that leads to retention and task creation.

---

## Model: Subscription = Chat, Credits = Work

Two clean concepts users already understand:

1. **Subscription** buys access + unlimited chat (Pro)
2. **Work credits** meter autonomous agent work

### Tier Structure

| | Free | Pro ($19/mo) |
|--|------|-------------|
| **Chat (TP)** | 50 messages/mo | **Unlimited** |
| **Work credits** | 20/mo | 500/mo |
| **Overage** | Hard stop | Buy more ($5/100 credits) |
| **Sync frequency** | 1x/day | Hourly |
| **Active agents** | 6 (roster) | 6 (roster) |
| **Active tasks** | 2 | 10 |

### Work Credit Costs

| Action | Credits | Rationale |
|--------|---------|-----------|
| Task execution (scheduled) | 3 | Full pipeline: context gather → Sonnet → save → deliver |
| Manual task run (trigger) | 3 | Same pipeline as scheduled |
| Render (PDF/chart/PPTX) | 1 | Output gateway compute |
| Platform sync | 0 | Mechanical, no LLM cost |

**Chat is not credited.** It's covered by the subscription. Free tier uses message count (50/mo) as the conversion lever.

### Why This Works

- **Chat is the product experience.** Gating it punishes engagement. Unlimited chat for Pro is table stakes (ChatGPT, Cursor, etc.).
- **Autonomous work is the real cost center.** A user with 2 daily tasks costs predictably different from one with 15. Credits make this linear and visible.
- **No meter anxiety on chat.** Users talk freely. Credits only apply to agents doing work in the background — work users explicitly set up and can see coming.
- **Two concepts, not three.** "Talking is included, work costs extra" is intuitive. No mental math about whether to send a message.

---

## Usage Scenarios

**Casual Pro user (mostly chat + few tasks)**:
- Unlimited chat + 4 weekly tasks (4 × 3 × 4 weeks) + 5 renders
- = 48 + 5 = **53 credits/month** ✓ (well within 500)

**Automation-heavy Pro user (daily briefers)**:
- Unlimited chat + 3 daily tasks (3 × 3 × 22 weekdays) + 10 renders
- = 198 + 10 = **208 credits/month** ✓

**Power user (many tasks + renders)**:
- Unlimited chat + 8 tasks × various cadences (~120 runs) + 30 renders
- = 360 + 30 = **390 credits/month** ✓

**Heavy automation (needs overage)**:
- Unlimited chat + 200 task runs + 40 renders
- = 600 + 40 = **640 credits** → buys 2 packs ($10) or 140 over limit
- Under current model the task cost is visible; chat is unbounded

---

## Unit Economics

With prompt caching enabled (deployed 2026-03-26):

| Action | Our API cost (cached) | Credit price at $19/500 | Margin |
|--------|----------------------|--------------------------|--------|
| Chat message (Pro) | ~$0.005-0.015 | Included in $19 sub | Depends on volume |
| Task execution | ~$0.02-0.03 | $0.114 (3 credits × $0.038) | 62-74% |
| Render | ~$0.005 | $0.038 (1 credit) | 87% |

**Pro subscription margin analysis:**
- Moderate user: 300 messages ($4.50 chat) + 150 credits ($3.75 work) = $8.25 cost → **57% margin**
- Heavy chatter: 1000 messages ($10 chat) + 100 credits ($2.50 work) = $12.50 cost → **34% margin**
- Heavy automation: 100 messages ($1 chat) + 450 credits ($11.25 work) = $12.25 cost → **36% margin**

**Key insight**: prompt caching makes heavy chatters survivable. The $10 chat cost for 1000 messages was $30+ pre-caching.

**Overage packs** ($5/100 = $0.05/credit): ~75-85% margin on task runs, ~87% on renders.

**Free tier** (50 messages + 20 credits): costs us ~$0.50-1.50/month. Acceptable for conversion.

---

## Chat Cost Risk (Pro Unlimited)

The concern: unlimited Pro chat is an open liability.

**Mitigations:**
1. **Prompt caching** (shipped): 90% savings on repeated system prompt + tools context. Heavy sessions converge to ~$0.005/message.
2. **Session compaction** (existing): older messages summarized, preventing unbounded context growth.
3. **Natural ceiling**: even power users rarely exceed 50 messages/day (~1500/month). At $0.005-0.01 cached, that's $7.50-15/month — within the $19 subscription.
4. **Monitoring**: track `cost_per_user_month` for chat. If a user consistently costs >$15/month in chat alone, that's a signal to investigate (likely a script, not a human).

**If chat cost becomes a problem later**: add a soft daily message cap (e.g., 100/day) rather than crediting. This prevents scripting without making normal users feel metered.

---

## Resolved Questions

1. **Chat degradation at limit**: Not needed. Pro chat is unlimited. Free users at 50 messages get upgrade prompt. Clean.

2. **Credit rollover**: No. Credits expire monthly. Industry standard, prevents hoarding, simplifies accounting.

3. **Existing Pro subscribers**: Announce with 2 weeks notice. First month: 1000 credits (2× normal). Track actual usage and show users what they consumed — most will be well within 500.

4. **Agent count**: Not credit-gated. Agents are roster (pre-scaffolded per ADR-140). Tasks are the work units — task count is tier-gated (2 free / 10 pro).

5. **Batch API**: Defer. Design `record_credits()` with `action_type` so task runs can later split into `task_execution_realtime` vs `task_execution_batch` with different costs.

6. **Multi-turn tool cost**: 1 credit per user message regardless of internal tool rounds. Simpler for users, margin absorbs tool-heavy conversations.

---

## Implementation Path

### Phase 1: Work Credits Table
- New `work_credits` table: `user_id, action_type, credits_consumed, metadata, created_at`
- `check_work_credits(user_id)` replaces `check_work_budget()` and `check_render_limit()`
- `record_work_credits(user_id, action, amount)` — single write path for task runs + renders
- Delete `render_usage` table, `get_monthly_render_count()` RPC
- Evolve or replace `work_units` table

### Phase 2: Enforcement Points
- `task_pipeline.py`: 3 credits per execution (replaces `record_work_units`)
- `runtime_dispatch.py`: 1 credit per render (replaces render count check)
- `chat.py`: message count check unchanged for free tier, no check for Pro
- Budget check: `remaining = tier_credit_limit - month_credit_usage`

### Phase 3: Overage (Pro only)
- Lemon Squeezy one-time purchase for credit packs ($5/100)
- `purchased_credits` column or table
- Overage draws from purchased credits after monthly allowance exhausted
- Webhook: `order_created` → add credits

### Phase 4: Frontend
- Work credits meter in nav (task runs + renders only)
- Settings page: credit usage breakdown by type
- Low-credits warning at 10% remaining
- Buy-more CTA for Pro users at 0%
- Free tier: message count display (existing) + credit display

---

## What This Replaces

| Current | Subscription + Credits |
|---------|----------------------|
| `work_units` table | `work_credits` (evolved) |
| `render_usage` table | Absorbed into `work_credits` |
| `check_work_budget()` | `check_work_credits()` |
| `check_render_limit()` | `check_work_credits()` |
| `record_work_units()` | `record_work_credits()` |
| `record_render_usage()` | `record_work_credits()` |
| `get_monthly_message_count()` RPC | Kept for free tier only |
| Three meters (messages + work units + renders) | Two concepts (chat included + work credits) |

---

## Decision Criteria

**Adopt this model because:**
- Chat stays frictionless — no meter anxiety on the primary interaction surface
- Work credits bound the real cost variable (autonomous LLM calls)
- Two concepts map to how users think: "talking to my assistant" vs "agents doing work"
- Prompt caching makes unlimited Pro chat economically viable (~$0.005-0.01/cached message)
- Implementation is simpler than unified credits (no chat crediting logic, keep existing message count for free tier)

**Watch for:**
- Pro chat cost exceeding $15/user/month consistently → add soft daily cap
- Work credit pricing feeling expensive → adjust credit-per-action ratios
- Free→Pro conversion rate → tune free tier credits (20 may be tight, consider 30)
