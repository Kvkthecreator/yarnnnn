# Cost Model — Per-Task Economics

> **Status**: Canonical — updated for ADR-138 (agents + tasks) and prompt caching
> **Date**: 2026-03-26 (revised)
> **Related**: ADR-100 (tier model), ADR-138 (agents as work units), ADR-141 (task pipeline), [UNIFIED-CREDITS.md](./UNIFIED-CREDITS.md)

---

## Per-Task Cost Breakdown

With prompt caching (deployed 2026-03-26) and mechanical task pipeline (ADR-141), each task's cost is predictable.

### Daily Task (e.g., Slack briefer)

| Step | Model | Calls/Week | Cost/Call | Weekly |
|------|-------|-----------|----------|--------|
| Task execution (weekdays) | Sonnet (cached) | 5 | $0.02-0.03 | $0.125 |
| Delivery (email/Slack) | Internal | 5 | ~$0 | $0 |
| **Total** | | | | **~$0.13/week** |

**Monthly: ~$0.50 per daily task**

### Weekly Task (e.g., research report)

| Step | Model | Calls/Week | Cost/Call | Weekly |
|------|-------|-----------|----------|--------|
| Task execution | Sonnet (cached) | 1 | $0.03-0.05 | $0.04 |
| Render (if PDF/chart) | Internal | 0-1 | $0.005 | $0.003 |
| **Total** | | | | **~$0.04/week** |

**Monthly: ~$0.17 per weekly task**

### Monthly Task (e.g., competitor analysis)

| Step | Model | Calls/Month | Cost/Call | Monthly |
|------|-------|------------|----------|---------|
| Task execution | Sonnet (cached) | 1 | $0.04-0.06 | $0.05 |
| Render (if needed) | Internal | 0-1 | $0.005 | $0.005 |
| **Total** | | | | **~$0.06/month** |

---

## User Cost Profiles

### Casual Pro ($19/mo) — 3 tasks

- 2 weekly tasks + 1 monthly task
- Task cost: (2 × $0.17) + $0.06 = **$0.40/month**
- Chat cost (est. 200 messages): **$2.00/month**
- **Total: ~$2.40/month → 87% margin**

### Active Pro ($19/mo) — 6 tasks

- 2 daily tasks + 3 weekly tasks + 1 monthly task
- Task cost: (2 × $0.50) + (3 × $0.17) + $0.06 = **$1.57/month**
- Chat cost (est. 500 messages): **$4.00/month**
- **Total: ~$5.57/month → 71% margin**

### Power Pro ($19/mo) — 10 tasks

- 4 daily tasks + 4 weekly tasks + 2 monthly tasks
- Task cost: (4 × $0.50) + (4 × $0.17) + (2 × $0.06) = **$2.80/month**
- Chat cost (est. 800 messages): **$6.00/month**
- **Total: ~$8.80/month → 54% margin**

---

## Cost Optimization — Implemented

1. **Prompt caching** (2026-03-26) — 90% savings on stable system prompt + tool definitions. Cached Sonnet calls drop from ~$0.05 to ~$0.02-0.03.
2. **Mechanical scheduling** (ADR-141) — zero LLM cost for scheduling decisions. SQL-only: `next_run_at <= now()`.
3. **Execution lock** (2026-03-26) — optimistic `next_run_at` bump prevents duplicate runs. Eliminated 6x duplicate execution bug.
4. **Context scoping** — task pipeline reads only TASK.md + AGENT.md + relevant workspace context. No unbounded platform dumps.

## Cost Optimization — Future

5. **Batch API** — Anthropic Batch API (50% off, non-real-time). Task executions are non-interactive — route through batch to cut per-task cost further.
6. **Output diffing** — if output is <10% different from last run, skip delivery. Saves Sonnet call.
7. **Haiku pre-screen** — cheap check before expensive generation (is there new content since last run?). Saves Sonnet calls on no-change cycles.

---

## Token Usage per Task Execution

| Component | Tokens | Source |
|-----------|--------|--------|
| System prompt (cached) | ~2000 | Role prompt + TASK.md context |
| AGENT.md context (cached) | ~1000 | Agent identity + instructions |
| Workspace context | ~2000-5000 | Platform content, memory files |
| Tool results | ~1000-3000 | Search/Read results per tool round |
| Output | ~500-2000 | Generated content |
| **Total per call** | **~6500-13000** | |

With caching: system prompt + AGENT.md = ~3000 tokens cached (90% discount on input cost).

---

## Pricing Alignment

| Plan | Tasks | Est. Monthly LLM Cost | Subscription | Gross Margin |
|------|-------|----------------------|-------------|-------------|
| **Free** | 2 | ~$0.50-1.50 | $0 | Loss leader |
| **Pro** | 10 | ~$3-9 | $19/mo | 53-84% |

Work credits (500/mo Pro) provide a secondary bound: even if all 10 tasks run daily (10 × 3 × 30 = 900 credits), the user hits the credit limit before LLM cost becomes unsustainable. Overage packs ($5/100) have ~80% margin.

---

## See Also

- [UNIFIED-CREDITS.md](./UNIFIED-CREDITS.md) — subscription + credits pricing model
- [STRATEGY.md](./STRATEGY.md) — business strategy and Lemon Squeezy setup
- [LIMITS.md](./LIMITS.md) — enforcement framework
