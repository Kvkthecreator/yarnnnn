# yarnnn Platform Resource Limits

> **Status**: ARCHIVED — Superseded by ADR-172 (Usage-First Billing)
> **Date**: 2026-03-26 (revised). **Archived**: 2026-04-15.
> **Superseded by**: [ADR-172](../adr/ADR-172-usage-first-billing.md) — all tier limits, capability gates, message limits, source limits, and credit costs dissolved. Balance (`balance_usd`) is the single gate.
>
> This document describes enforcement infrastructure that no longer exists. `TIER_LIMITS`, `CREDIT_COSTS`, `PlatformLimits`, `check_agent_limit()`, `check_source_limit()`, `check_monthly_message_limit()`, `work_credits` table — all deleted. See [STRATEGY.md](./STRATEGY.md) for the current model.
>
> **Original content below preserved for historical reference.**

---

> ~~**Status**: Implemented — subscription + work credits model~~
> **Date**: 2026-03-26 (revised)
> **Related**: ADR-100, [UNIFIED-CREDITS.md](./UNIFIED-CREDITS.md), [STRATEGY.md](./STRATEGY.md)

---

## Overview

Two gates: subscription (chat access) and work credits (autonomous work).

- **Subscription** buys access + unlimited chat (Pro)
- **Work credits** meter autonomous agent work (task runs, renders)

---

## Tier Limits

| Resource | Free | Pro ($19/mo) |
|----------|------|--------------|
| **Chat messages** | 150/month | **Unlimited** |
| **Work credits** | 20/month | 500/month |
| **Active tasks** | 2 | 10 |
| **Slack sources** | 5 | Unlimited |
| **Notion pages** | 10 | Unlimited |
| **Platforms** | 2 (Slack + Notion) | 2 |
| **Sync frequency** | 1x/day | Hourly |

### Credit Costs

| Action | Credits |
|--------|---------|
| Task execution (scheduled or manual) | 3 |
| Render (PDF, chart, PPTX) | 1 |

All numbers configurable in `TIER_LIMITS` and `CREDIT_COSTS` dicts in `platform_limits.py`.

---

## Implementation

### Backend: `api/services/platform_limits.py`

```python
CREDIT_COSTS = {
    "task_execution": 3,
    "render": 1,
    "agent_run": 3,   # legacy alias
}

TIER_LIMITS = {
    "free": PlatformLimits(
        monthly_messages=150,
        monthly_credits=20,
        active_tasks=2,
        ...
    ),
    "pro": PlatformLimits(
        monthly_messages=-1,      # Unlimited
        monthly_credits=500,
        active_tasks=10,
        ...
    ),
}
```

### Key Functions

| Function | Purpose |
|----------|---------|
| `check_credits(client, user_id)` | Check remaining work credits |
| `record_credits(client, user_id, action_type)` | Record credit consumption |
| `check_monthly_message_limit(client, user_id)` | Check chat limit (Free only) |
| `check_task_limit(client, user_id)` | Check active task count |
| `get_usage_summary(client, user_id)` | Full limits + usage for API |

### Database

- `work_credits` table — unified ledger (replaces `work_units` + `render_usage`)
- `get_monthly_credits(p_user_id)` — RPC for monthly credit sum
- `get_monthly_message_count(p_user_id)` — RPC for chat messages (Free tier)

### Enforcement Points

| Point | File | Gate |
|-------|------|------|
| Chat message | `api/routes/chat.py` | `check_monthly_message_limit()` — Free only |
| Task execution | `api/services/task_pipeline.py` | `check_credits()` before pipeline |
| Render | `api/services/primitives/runtime_dispatch.py` | `check_credits()` before dispatch |
| Task creation | `api/routes/tasks.py` | `check_task_limit()` |

### Frontend

| Component | Location | Purpose |
|-----------|----------|---------|
| Credits in nav | `web/components/shell/UserMenu.tsx` | Shows remaining credits |
| Usage tab | `web/app/(authenticated)/settings/page.tsx` | Credits bar + chat bar (Free) + plan details |
| Upgrade prompt | `web/components/subscription/UpgradePrompt.tsx` | Modal/banner for messages, credits, tasks |
| Tier constants | `web/lib/subscription/limits.ts` | `TIER_LIMITS`, `CREDIT_COSTS` |

---

## API Endpoint

### GET `/api/user/limits`

```json
{
  "tier": "free",
  "limits": {
    "monthly_messages": 150,
    "monthly_credits": 20,
    "active_tasks": 2,
    "slack_channels": 5,
    "notion_pages": 10,
    "total_platforms": 2,
    "sync_frequency": "1x_daily"
  },
  "usage": {
    "monthly_messages_used": 12,
    "credits_used": 6,
    "active_tasks": 1,
    "slack_channels": 3,
    "notion_pages": 2,
    "platforms_connected": 1
  },
  "next_sync": "2026-03-27T08:00:00+09:00"
}
```

---

## See Also

- [UNIFIED-CREDITS.md](./UNIFIED-CREDITS.md) — subscription + credits pricing model
- [COST-MODEL.md](./COST-MODEL.md) — per-task economics
- [STRATEGY.md](./STRATEGY.md) — business strategy
