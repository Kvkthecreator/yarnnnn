# yarnnn Platform Resource Limits

> **Status**: Revised (ADR-100)
> **Date**: 2026-03-09
> **Related**: ADR-100 (Simplified Monetization), ADR-053 (Platform Sync Monetization)

---

## Overview

This document describes the resource limits that control platform usage based on subscription tier. These limits serve three purposes:

1. **Cost Control** — Monthly messages and deliverables are the primary LLM cost drivers
2. **Fair Usage** — Prevent abuse and ensure equitable resource distribution
3. **Monetization** — Create upgrade incentives aligned with value delivered

**Key Insight (ADR-100)**: Gate on what costs money (LLM usage). Users understand "50 messages/month" — not "50k tokens/day."

---

## Tier Limits (ADR-100)

| Resource | Free | Pro ($19/mo) |
|----------|------|--------------|
| **Platforms** | All 4 | All 4 |
| **Slack sources** | 5 | Unlimited |
| **Gmail labels** | 5 | Unlimited |
| **Notion pages** | 10 | Unlimited |
| **Calendars** | Unlimited | Unlimited |
| **Sync frequency** | 1x/day | Hourly |
| **Monthly messages** | 50 | Unlimited |
| **Active deliverables** | 2 | 10 |

### Early Bird Pricing

- **$9/mo** — Same Pro features at promotional price during beta
- Monthly only, no yearly
- Separate Lemon Squeezy variant, sunset at our discretion

### Sync Frequency Schedule

| Tier | Frequency | Schedule |
|------|-----------|----------|
| Free | 1x/day | 8am (user's timezone) |
| Pro | Hourly | Every hour |

---

## Implementation

### Backend: `api/services/platform_limits.py`

```python
@dataclass
class PlatformLimits:
    slack_channels: int
    gmail_labels: int
    notion_pages: int
    calendars: int
    total_platforms: int
    sync_frequency: str
    monthly_messages: int     # -1 for unlimited
    active_deliverables: int  # -1 for unlimited

TIER_LIMITS = {
    "free": PlatformLimits(
        slack_channels=5,
        gmail_labels=5,
        notion_pages=10,
        calendars=-1,
        total_platforms=4,
        sync_frequency="1x_daily",
        monthly_messages=50,
        active_deliverables=2,
    ),
    "pro": PlatformLimits(
        slack_channels=-1,
        gmail_labels=-1,
        notion_pages=-1,
        calendars=-1,
        total_platforms=4,
        sync_frequency="hourly",
        monthly_messages=-1,
        active_deliverables=10,
    ),
}
```

### Key Functions

| Function | Purpose |
|----------|---------|
| `get_user_tier(client, user_id)` | Returns user's subscription tier ("free" or "pro") |
| `get_limits_for_user(client, user_id)` | Returns PlatformLimits for tier |
| `check_source_limit(client, user_id, provider, count)` | Check if can add sources |
| `check_monthly_message_limit(client, user_id)` | Check monthly message budget |
| `check_deliverable_limit(client, user_id)` | Check active deliverable count |
| `get_usage_summary(client, user_id)` | Full limits + usage report |

---

## Enforcement Points

### 1. Monthly Message Limit (ADR-100)

When user sends a chat message:
- Calls `get_monthly_message_count()` RPC to count user messages this month
- Returns 429 if at limit with upgrade prompt
- Resets on 1st of each month (calendar month)

**Files**: `api/services/platform_limits.py`, `api/routes/chat.py`

### 2. Deliverable Limit

When user creates a deliverable:
- Check `active_deliverables` limit (Free: 2, Pro: 10)
- Returns 429 error with upgrade prompt if at limit

**Files**: `api/routes/deliverables.py`

### 3. Source Selection

When user selects sources to sync:
- Frontend disables checkbox when at limit
- Backend truncates to limit if exceeded
- Shows upgrade prompt

**Files**: `api/services/platform_limits.py`

### 4. Sync Operations (Background)

During scheduled syncs:
- Only sync selected sources (within limits)
- Tier-based frequency: Free=1x/day, Pro=hourly

**Files**: `api/jobs/platform_sync_scheduler.py`

---

## API Endpoints

### GET `/api/user/limits`

Returns current tier, limits, and usage.

```json
{
  "tier": "free",
  "limits": {
    "slack_channels": 5,
    "gmail_labels": 5,
    "notion_pages": 10,
    "calendars": -1,
    "total_platforms": 4,
    "sync_frequency": "1x_daily",
    "monthly_messages": 50,
    "active_deliverables": 2
  },
  "usage": {
    "slack_channels": 3,
    "gmail_labels": 1,
    "notion_pages": 2,
    "calendars": 1,
    "platforms_connected": 3,
    "monthly_messages_used": 12,
    "active_deliverables": 1
  },
  "next_sync": "2026-03-10T08:00:00+09:00"
}
```

---

## Legacy

### Deprecated Tier: Starter

ADR-053 defined a $9/mo Starter tier between Free and Pro. ADR-100 removed it:
- `get_user_tier()` maps any existing "starter" status to "pro"
- Starter Lemon Squeezy variants no longer referenced in code
- No migration needed — database values handled gracefully

### Deprecated Gate: Daily Token Budget

ADR-053 used `daily_token_budget` (50k/250k/unlimited tokens per day). ADR-100 replaced with `monthly_messages` (50/unlimited per month):
- More user-understandable
- Predictable cost ceiling
- `get_daily_token_usage()` RPC kept for analytics, not enforcement

---

## Related Files

| File | Purpose |
|------|---------|
| `api/services/platform_limits.py` | Backend limit enforcement |
| `api/routes/chat.py` | Monthly message limit check |
| `api/routes/deliverables.py` | Deliverable limit check |
| `web/lib/subscription/limits.ts` | Frontend limit constants |
| `web/lib/api/client.ts` | Frontend API client (getLimits) |
| `supabase/migrations/094_monthly_message_count.sql` | Monthly message count RPC |

---

## See Also

- [ADR-100: Simplified Monetization](../adr/ADR-100-simplified-monetization.md)
- [STRATEGY.md](./STRATEGY.md) - Pricing and billing strategy
