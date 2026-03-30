# Token Economics Analysis — Full-Stack LLM Cost Audit

> **Status**: Live analysis — based on production data (2026-03-26 to 2026-03-30)
> **Date**: 2026-03-30
> **Purpose**: Comprehensive token usage audit across all LLM consumers, compared against monetization model
> **Related**: [COST-MODEL.md](./COST-MODEL.md), [STRATEGY.md](./STRATEGY.md), [UNIFIED-CREDITS.md](./UNIFIED-CREDITS.md)

---

## Executive Summary

COST-MODEL.md estimates task execution at $0.02-0.03/call with prompt caching. **This is approximately correct for the task itself**, but the model omits significant backend overhead that, pre-fix, doubled total LLM spend. The composer heartbeat spin loop consumed more tokens than all task runs combined on peak days.

**Key findings:**
1. Per-task Sonnet costs are **higher than documented** (~$0.04-0.08/run vs. $0.02-0.03) once cache tokens are properly counted
2. Backend overhead (composer heartbeat) was the **dominant cost driver** — now fixed
3. The cost model omits 4 headless LLM consumers that run regardless of user activity
4. Multi-step pipeline tasks cost **2-3x** single-step tasks (each step is a full Sonnet call)
5. TP chat costs are underestimated for active users (14 tools × ~500 tokens each = 7K tokens just for tool definitions)

---

## 1. All LLM Consumers — Complete Inventory

Every path in the system that calls the Anthropic API:

| Consumer | Model | Trigger | Frequency | Controllable? |
|----------|-------|---------|-----------|---------------|
| **Task execution (single-step)** | Sonnet | Scheduler cron (next_run_at) | Per task schedule | Yes — user sets cadence |
| **Task execution (multi-step)** | Sonnet | Scheduler cron | Per task schedule × N steps | Yes — type registry defines steps |
| **TP chat** | Sonnet | User message | Per user interaction | Yes — message limits |
| **ChatAgent (meeting room)** | Sonnet | User @-mention in project | Per user interaction | Yes — message limits |
| **Composer heartbeat** | Haiku | Scheduler cron (every 5 min, Pro) | Up to 288/day/user (Pro) | No — system overhead |
| **Memory extraction** | Haiku | Nightly cron (midnight UTC) | 1/day per active session | No — system overhead |
| **Agent generation (manual/MCP)** | Sonnet | User-initiated or MCP tool | On demand | Yes — credit-gated |

### Not LLM consumers (deterministic):
- Scheduler heartbeat — pure SQL, zero LLM
- Platform sync — direct API calls to Slack/Notion/GitHub
- Feedback distillation — pure string formatting
- Workspace cleanup — SQL TTL enforcement
- Delivery (email) — template rendering

---

## 2. Per-Consumer Token Economics

### 2.1 Task Execution — Single-Step (Primary Revenue Driver)

The core product loop. One Sonnet call per task run.

**Input token composition:**

| Component | Est. Tokens | Cached? |
|-----------|------------|---------|
| System prompt (role prompt + rules) | ~1,500 | Yes |
| Agent instructions (AGENT.md) | ~500-1,000 | Yes |
| Methodology playbooks | ~200-500 | Yes |
| Tool definitions (16 headless tools) | ~4,000-6,000 | Yes |
| Task objective + output spec | ~200-500 | Partially |
| Gathered context (workspace + knowledge, up to 10 results × 2000 chars) | ~2,000-8,000 | No |
| Tool round results (if tools used) | ~500-3,000/round | No |
| **Total input** | **~9,000-20,000** | **~6,000-8,000 cached** |

**Output tokens:** ~1,500-4,000 (observed range from production runs)

**Cost per single-step run (with caching):**

| Component | Tokens | Rate | Cost |
|-----------|--------|------|------|
| Cached input | ~7,000 | $0.30/MTok | $0.0021 |
| Uncached input | ~5,000-12,000 | $3.00/MTok | $0.015-0.036 |
| Output | ~2,500 | $15.00/MTok | $0.0375 |
| **Total** | | | **$0.05-0.08** |

> **vs. COST-MODEL.md estimate: $0.02-0.03** — The existing model underestimates by ~2-3x because:
> 1. Tool definitions alone are ~5K tokens (not counted in the "system prompt ~2000" estimate)
> 2. Output tokens at $15/MTok dominate cost (output is 2-3x more expensive than input)
> 3. The "~6500-13000 total" estimate in COST-MODEL.md is input-only and misses the output cost weight

### 2.2 Task Execution — Multi-Step Pipeline (ADR-145)

Each step is a full Sonnet call. Step N receives step N-1's output (up to 8K chars) as additional context.

**Cost per multi-step run:**

| Steps | Input (est.) | Output (est.) | Total Cost |
|-------|-------------|--------------|------------|
| 2 steps | ~30K (2 × 15K) | ~5K (2 × 2.5K) | ~$0.10-0.16 |
| 3 steps | ~50K (3 × ~17K, growing context) | ~7.5K | ~$0.16-0.24 |

**Production observation:** The `weekly-ai-agent-market-intel` task (2-step: Investigate → Compose) uses 2 Sonnet calls per run. At weekly cadence: **~$0.40-0.64/month**.

### 2.3 TP Chat (Orchestrator)

The conversational interface. Sonnet with 14 tools, streaming, up to 15 tool rounds per message.

**Per-message input composition:**

| Component | Est. Tokens | Cached? |
|-----------|------------|---------|
| System prompt | ~3,000-4,000 | Yes |
| Working memory injection | ~500-2,000 | No |
| Tool definitions (14 chat tools) | ~5,000-7,000 | Yes |
| Conversation history | ~500-5,000+ | Partially |
| Tool round results | ~500-3,000/round | No |
| **Total per message** | **~10,000-20,000** | **~8,000-11,000 cached** |

**Output:** ~500-2,000 tokens per response

**Cost per TP message:** ~$0.01-0.04 (heavily dependent on conversation length and tool usage)

**Monthly cost at scale:**

| Usage Level | Messages/mo | Est. Cost |
|------------|------------|-----------|
| Light (Free) | 50 | $0.50-1.00 |
| Moderate (Pro) | 200 | $2.00-4.00 |
| Heavy (Pro) | 500 | $5.00-10.00 |
| Power (Pro) | 1000+ | $10.00-20.00+ |

> **vs. COST-MODEL.md estimate: $2.00/month for 200 messages ($0.01 each)**
> Approximately correct for short conversations. Longer sessions with tool usage push closer to $0.02-0.04/message.

### 2.4 Composer Heartbeat (Backend Overhead)

Haiku call when `should_composer_act()` returns true AND workspace state has changed.

**Per-call cost:**

| Component | Tokens | Rate | Cost |
|-----------|--------|------|------|
| System prompt | ~500 | $0.80/MTok (Haiku) | $0.0004 |
| User message (assessment) | ~500-1,000 | $0.80/MTok | $0.0004-0.0008 |
| Output | ~200-500 | $4.00/MTok (Haiku) | $0.0008-0.002 |
| **Total per call** | | | **~$0.002-0.003** |

**Pre-fix frequency (observed 2026-03-29):**
- 819 LLM calls/day across 3 users → **~$1.60-2.50/day → ~$48-75/month**
- This exceeded all task execution costs combined

**Post-fix frequency (projected with state-change gate):**
- ~2-5 LLM calls/day per user (only on actual state changes)
- 3 users × 5 calls × $0.003 = **~$0.045/day → ~$1.35/month**
- **97% reduction**

**At scale (100 Pro users):**
- Pre-fix: 100 × 273 calls/day × $0.003 = **$81.90/day → $2,457/month** (unsustainable)
- Post-fix: 100 × 5 calls/day × $0.003 = **$1.50/day → $45/month** (negligible)

### 2.5 Memory Extraction (Backend Overhead)

Haiku nightly cron. Extracts durable facts from chat sessions.

**Per-session cost:** ~$0.001-0.003 (small prompt + conversation text)

**Note:** Currently not firing (zero events since March 20). When operational: ~1-3 sessions/user/day × $0.002 = **~$0.006/user/day → $0.18/user/month**. Negligible.

---

## 3. Observed vs. Modeled — Production Data (2026-03-29)

### 3.1 Token Usage Breakdown

The Anthropic dashboard showed ~4M tokens on 2026-03-29. Reconstructed:

| Consumer | Model | Est. Input Tokens | Est. Output Tokens | Est. Cost |
|----------|-------|------------------|-------------------|-----------|
| 12 task runs (single-step) | Sonnet | ~120K-180K | ~34K | $1.00-1.50 |
| 2 TP chat messages | Sonnet | ~20K-40K | ~2K | $0.10-0.15 |
| ~819 composer LLM calls | Haiku | ~800K-1.2M | ~200K-400K | $1.60-2.50 |
| Memory extraction | Haiku | 0 (not running) | 0 | $0 |
| **Total** | | **~1M-1.4M** | **~236K-436K** | **$2.70-4.15** |

**Sonnet/Haiku split on chart:** The dashboard shows ~2.5M Haiku + ~1.5M Sonnet, consistent with this breakdown. The Haiku bar (lighter color) is the composer loop; the Sonnet bar (darker) is task runs + chat.

### 3.2 Why 12 Runs in One Day?

The `test-quality-*` tasks were running on accelerated schedules for E2E quality testing (commit `d30ca54`). Normal operation: 2 weekly tasks + 1 reactive = ~2-3 runs/week. The 12-run day was a test artifact, not steady-state.

---

## 4. Revised Cost Model — All Consumers

### Per-User Monthly Cost (Steady State)

| Consumer | Free User | Casual Pro (3 tasks) | Active Pro (6 tasks) | Power Pro (10 tasks) |
|----------|-----------|---------------------|---------------------|---------------------|
| Task execution (single-step) | $0.30-0.60 | $0.70-1.20 | $1.50-2.50 | $2.50-4.00 |
| Task execution (multi-step) | — | $0.20-0.40 | $0.40-0.80 | $0.80-1.60 |
| TP chat | $0.50-1.00 | $2.00-4.00 | $4.00-8.00 | $6.00-12.00 |
| Composer heartbeat (post-fix) | ~$0.05 | ~$0.05 | ~$0.05 | ~$0.05 |
| Memory extraction | ~$0.10 | ~$0.18 | ~$0.18 | ~$0.18 |
| Platform sync | $0 | $0 | $0 | $0 |
| **Total** | **$0.95-1.75** | **$2.93-5.83** | **$6.13-11.53** | **$9.53-17.83** |

### Margin Analysis (Revised)

| Profile | Subscription | Est. LLM Cost | Margin |
|---------|-------------|---------------|--------|
| Free (2 tasks, 50 msgs) | $0 | $0.95-1.75 | **Loss leader** |
| Casual Pro (3 tasks, 200 msgs) | $19/mo | $2.93-5.83 | **69-85%** |
| Active Pro (6 tasks, 500 msgs) | $19/mo | $6.13-11.53 | **39-68%** |
| Power Pro (10 tasks, 800 msgs) | $19/mo | $9.53-17.83 | **6-50%** |
| Early Bird ($9/mo, 6 tasks) | $9/mo | $6.13-11.53 | **-28% to 32%** |

> **vs. COST-MODEL.md margins:**
> - Casual Pro: 87% → **69-85%** (closer but lower)
> - Active Pro: 71% → **39-68%** (significantly lower)
> - Power Pro: 54% → **6-50%** (dangerously thin)
> - Early Bird at Active usage: **potentially negative margin**

### Key Differences from COST-MODEL.md

1. **Task execution cost 2-3x higher** ($0.05-0.08 vs. $0.02-0.03) — output tokens at $15/MTok dominate
2. **Chat cost underestimated** for heavy users — tool definitions alone are ~6K cached tokens per message
3. **Backend overhead now included** — ~$0.23/user/month (negligible post-fix)
4. **Multi-step tasks not modeled** — each additional step roughly doubles the task cost

---

## 5. Backend Overhead — Pre vs. Post Production Fix

### What Changed (2026-03-30, commit a5a2246)

| Fix | Before | After | Impact |
|-----|--------|-------|--------|
| Token tracking | Reported 15-38 input tokens/run | Reports real ~10K-20K | Accurate cost visibility |
| Composer state gate | LLM called on every `should_act=true` (819/day) | LLM called only on state change (~5/day) | ~97% reduction in Haiku spend |

### Overhead Budget for Production

Post-fix, backend overhead per user:

| System Process | Model | Frequency | Monthly Cost |
|----------------|-------|-----------|-------------|
| Composer heartbeat (LLM calls) | Haiku | ~5/day | ~$0.05 |
| Composer heartbeat (DB queries) | None | 288/day (Pro) | $0 |
| Scheduler heartbeat | None | 288/day | $0 |
| Memory extraction | Haiku | ~1-3/day | ~$0.18 |
| Platform sync | None | Hourly (Pro) | $0 |
| Workspace cleanup | None | Daily | $0 |
| **Total backend overhead** | | | **~$0.23/user/month** |

This is <3% of total cost for any paying user. **Acceptable for production.**

---

## 6. Cost Optimization Opportunities

### Already Implemented
1. Prompt caching — ~90% savings on stable prompt components
2. Mechanical scheduling — zero LLM for schedule decisions
3. State-change gate — prevents composer spin loops
4. Execution lock — prevents duplicate runs

### High-Impact (Recommended Pre-Launch)
5. **Batch API for scheduled tasks** — Anthropic Batch API is 50% off for non-real-time. All scheduled task runs qualify. Would cut per-task cost from $0.05-0.08 to **$0.025-0.04**.
6. **Haiku pre-screen for tasks** — before each Sonnet run, a Haiku call checks "has anything changed since last run?" (~$0.002). Skips Sonnet ($0.05-0.08) when content is stale. Estimated 30-50% of daily task runs would skip.

### Medium-Impact (Post-Launch)
7. **Output diffing** — compare current run's output to last run. If <10% changed, skip delivery (saves render/email cost, not LLM cost).
8. **Context compression** — gathered workspace context (up to 20K chars) could be summarized by Haiku first, reducing Sonnet input by ~60%.
9. **Tool definition caching** — currently all 14-16 tool schemas are sent every call (~5-7K tokens). With prompt caching these are cheap, but moving to a smaller tool set for simple tasks would help.

### Low-Impact
10. **Haiku for simple tasks** — briefer/monitor roles produce short-form outputs. Could use Haiku ($0.001-0.003) instead of Sonnet ($0.05-0.08) for 95% cost reduction on these task types.

---

## 7. Monetization Model Stress Test

### Worst Case: Power Pro with Heavy Chat

- 10 daily tasks (all single-step): 10 × 30 × $0.08 = **$24.00/month**
- 1000 messages (long conversations): 1000 × $0.03 = **$30.00/month**
- Backend overhead: **$0.23/month**
- **Total: ~$54.23/month on $19 subscription = -185% margin**

This is unsustainable but unlikely — bounded by:
- Credit limit: 10 tasks × 3 credits × 30 days = 900 credits vs. 500 limit → **credit gate fires at day ~17**
- Message limit: Pro is unlimited → **no gate** (potential problem)

### Realistic Worst Case with Credit Gate

- 500 credits ÷ 3 credits/run = 166 task runs/month
- 166 runs × $0.08 = **$13.28/month** (task cost, credit-bounded)
- 500 messages × $0.02 = **$10.00/month** (chat, moderate)
- **Total: ~$23.28 → -22% margin**

Still negative. The credit gate helps but **chat is unbounded**.

### Recommendations for Monetization Model

1. **Update COST-MODEL.md** — per-task estimate should be $0.05-0.08, not $0.02-0.03
2. **Consider chat cost gate** — Pro "unlimited" chat could add a soft cap (e.g., 1000 msgs) with graceful degradation or overage pricing
3. **Early Bird is underwater** — at $9/mo, any user with >3 tasks and moderate chat loses money. Consider sunsetting sooner or limiting Early Bird to 5 tasks (not 10)
4. **Multi-step tasks should cost more credits** — currently 3 credits regardless of steps. A 3-step task costs 3x the LLM but same credits. Consider: `credits = 3 × num_steps`
5. **Batch API is the single highest-ROI optimization** — 50% off all scheduled task runs with zero UX impact

---

## 8. Batch API — Feasibility Assessment

The Anthropic Batch API accepts the same `messages.create()` requests but queues them for processing within a **24-hour window** (usually completes in minutes to a few hours). In return: **50% off** both input and output tokens. The trade-off is latency, not capability — same models, same tools, same outputs.

### Which calls qualify?

| Call Type | Real-time needed? | Batch candidate? |
|-----------|-------------------|-----------------|
| Scheduled task runs (cron) | No — user isn't waiting | **Yes** |
| Composer heartbeat (Haiku) | No — background system | **Yes** |
| Memory extraction (Haiku) | No — nightly cron | **Yes** |
| TP chat (user typing) | Yes — streaming response | No |
| Manual "Run Now" (from UI) | Yes — user clicked and waiting | No |
| MCP-triggered runs | Depends — usually yes | Maybe |

### How it would work

A routing decision at the top of `_generate()` in `task_pipeline.py`:

```
if trigger == "scheduled":
    → Batch API (50% off, response within minutes-hours)
elif trigger in ("manual", "reactive"):
    → Standard API (real-time, full price)
```

Implementation requires: batch submission function (new), polling/webhook handler for completed batches (new), routing decision (small change), failure/timeout handling (new). **Estimated: 2-3 days of work.**

### When it's worth implementing

At current scale (3 users, ~5 runs/week): saves ~$0.45/week. Not worth the complexity.

**Trigger point: ~50+ Pro users with daily tasks.** At that scale: 50 users × 4 daily tasks × 30 days × $0.06 × 50% = **~$180/month saved**. Justifies the 2-3 day investment.

### Decision (2026-03-30)

**Defer Batch API until user scale justifies it.** The composer fix (commit a5a2246) saves more at current scale than Batch API would. Revisit when monthly task execution cost exceeds ~$300.

---

## 9. Deferred Decisions — Revisit Post-Launch with Real Data

### Chat Cost Cap (Pro Unlimited)

Pro "unlimited" chat is an unbounded cost risk. However, setting a cap without usage data risks either:
- Cap too low → frustrates best users (destructive)
- Cap too high → nobody hits it (useless)

**Decision**: Ship unlimited. Monitor actual per-user message volumes for first 30 days. Set cap based on P95 usage + 2x headroom. If no user exceeds 500 msgs/month, a 1000-msg cap is safe.

### Multi-Step Credit Scaling

Currently: 3 credits per task run regardless of process steps. A 3-step pipeline costs 3x the LLM but consumes the same credits.

**Decision**: Defer. Only 1 of 3 active tasks uses multi-step. Revisit when multi-step adoption warrants the added credit complexity. Simple fix when needed: `credits = 3 × num_steps`.

### Early Bird Margin Risk

At $9/mo with active usage (6+ tasks, 500+ messages), Early Bird users are margin-negative. However, Early Bird is explicitly designed as an acquisition tool with planned sunset.

**Decision**: Keep as-is for launch. Track Early Bird users' actual cost. Sunset trigger: when paid user base reaches ~100 users OR when aggregate Early Bird margin drops below -20%.

---

## 10. Production Readiness Checklist

| Item | Status | Impact |
|------|--------|--------|
| Token tracking accuracy | **Fixed** (commit a5a2246) | Accurate cost monitoring |
| Composer spin loop | **Fixed** (commit a5a2246) | ~97% Haiku savings |
| Credit enforcement | Implemented | Bounds task execution cost |
| Message limit (Free) | Implemented (150/mo) | Bounds Free chat cost |
| Message limit (Pro) | **Unlimited — no gate** | Unbounded chat cost risk |
| Batch API | Not implemented | Would save ~50% on tasks |
| Multi-step credit scaling | Not implemented | Credit undercount for pipeline tasks |
| Memory extraction | **Not firing** (needs investigation) | No impact on cost, may affect quality |
| Duplicate agents | Exists (2× "Google Workspace Briefer") | Minor — cleanup task |
| Stuck run | Research Agent stuck in "generating" since 03-30 01:44 | Needs cleanup |

---

## See Also

- [COST-MODEL.md](./COST-MODEL.md) — per-task economics (needs update per this analysis)
- [STRATEGY.md](./STRATEGY.md) — business strategy and pricing tiers
- [UNIFIED-CREDITS.md](./UNIFIED-CREDITS.md) — credit model design
- [LIMITS.md](./LIMITS.md) — enforcement framework
