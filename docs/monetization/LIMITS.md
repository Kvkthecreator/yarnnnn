# yarnnn Platform Resource Limits

> **Status**: Revised (ADR-053)
> **Date**: 2026-02-12
> **Related**: ADR-043 (Platform Settings), ADR-046 (Google Calendar), ADR-053 (Platform Sync Monetization)

---

## Overview

This document describes the resource limits that control platform usage based on subscription tier. These limits serve three purposes:

1. **Cost Control** - External API calls, storage, and sync operations have real costs
2. **Fair Usage** - Prevent abuse and ensure equitable resource distribution
3. **Monetization** - Create upgrade incentives aligned with value delivered

**Key Insight (ADR-053)**: Platform sync is the **base monetization layer**. Sync is cheap (~$0.003/user/day), highly profitable, and directly correlates with value delivered.

---

## Tier Limits

### Revised Structure (ADR-053)

| Resource | Free | Starter ($9/mo) | Pro ($19/mo) |
|----------|------|-----------------|--------------|
| **Platforms** | 2 | 4 | 4 |
| **Slack channels** | 1 | 5 | 20 |
| **Gmail labels** | 1 | 5 | 15 |
| **Notion pages** | 1 | 5 | 25 |
| **Calendars** | 1 | 3 | 10 |
| **Sync frequency** | 2x/day | 4x/day | Hourly |
| **TP conversations** | 20/mo | 100/mo | Unlimited |
| **Deliverables** | 3 active | 10 active | Unlimited |

### Sync Frequency Schedule

| Tier | Frequency | Schedule |
|------|-----------|----------|
| Free | 2x/day | 8am, 6pm (user's timezone) |
| Starter | 4x/day | Every 6 hours |
| Pro | Hourly | Every hour |

### Rationale (Revised)

- **Free tier**: "1 source per platform" - enough to experience value, fast onboarding, clear upgrade path
- **Starter tier**: Solo users who want "enough" - multiple sources per platform, $9/mo
- **Pro tier**: Power users with multiple active projects, near real-time sync, $19/mo

### Why Tighter Free Tier?

1. **Reduces decision paralysis** - "Pick 1 channel" vs "Pick up to 5 channels"
2. **Faster time-to-value** - Less config, quicker to first TP conversation
3. **Solves cold start** - Immediate sync of 1 source = context for first chat
4. **Clear upgrade path** - "Want more channels? Upgrade to Starter"

### Counting Model

**We count synced sources, not connections.**

A Slack "connection" without channels provides no context. Value = synced sources.

Example:
```
Free user:
- Connects Slack → selects 1 channel to sync
- Connects Gmail → selects 1 label (INBOX default)
- Platform limit is 2 → can only use 2 of the 4 platforms
```

### Legacy Limits (Deprecated)

Previous limits before ADR-053:

| Resource | Old Free | Old Pro | Old Enterprise |
|----------|----------|---------|----------------|
| Slack channels | 5 | 20 | 100 |
| Gmail labels | 3 | 10 | 50 |
| Notion pages | 5 | 25 | 100 |
| Calendar events | 3 | 10 | 50 |
| Total platforms | 3 | 10 | 50 |

These are superseded by the revised structure above.

---

## Implementation

### Backend: `api/services/platform_limits.py`

```python
@dataclass
class PlatformLimits:
    """Resource limits for a user tier."""
    slack_channels: int
    gmail_labels: int
    notion_pages: int
    calendars: int
    total_platforms: int
    sync_frequency: str  # "2x_daily", "4x_daily", "hourly"
    tp_conversations_per_month: int  # -1 for unlimited
    active_deliverables: int  # -1 for unlimited

TIER_LIMITS = {
    "free": PlatformLimits(
        slack_channels=1,
        gmail_labels=1,
        notion_pages=1,
        calendars=1,
        total_platforms=2,
        sync_frequency="2x_daily",
        tp_conversations_per_month=20,
        active_deliverables=3,
    ),
    "starter": PlatformLimits(
        slack_channels=5,
        gmail_labels=5,
        notion_pages=5,
        calendars=3,
        total_platforms=4,
        sync_frequency="4x_daily",
        tp_conversations_per_month=100,
        active_deliverables=10,
    ),
    "pro": PlatformLimits(
        slack_channels=20,
        gmail_labels=15,
        notion_pages=25,
        calendars=10,
        total_platforms=4,
        sync_frequency="hourly",
        tp_conversations_per_month=-1,  # unlimited
        active_deliverables=-1,  # unlimited
    ),
}

# Provider to limit field mapping
PROVIDER_LIMIT_MAP = {
    "slack": "slack_channels",
    "gmail": "gmail_labels",
    "google": "gmail_labels",
    "notion": "notion_pages",
    "calendar": "calendars",
}

# Sync frequency schedules
SYNC_SCHEDULES = {
    "2x_daily": ["08:00", "18:00"],  # User's timezone
    "4x_daily": ["00:00", "06:00", "12:00", "18:00"],
    "hourly": None,  # Every hour
}
```

### Key Functions

| Function | Purpose |
|----------|---------|
| `get_user_tier(client, user_id)` | Returns user's subscription tier |
| `get_limits_for_user(client, user_id)` | Returns PlatformLimits for tier |
| `check_source_limit(client, user_id, provider, count)` | Check if can add sources |
| `check_platform_limit(client, user_id)` | Check if can connect platform |
| `get_usage_summary(client, user_id)` | Full limits + usage report |
| `validate_sources_update(client, user_id, provider, ids)` | Validate source selection |

### Frontend: Platform Detail Page

The platform detail page (`/context/[platform]`) shows:

1. **Resource count**: "X selected • Y available • Z max (tier)"
2. **Inline selection**: Toggle checkboxes for each resource
3. **Limit warning**: Visual alert when at limit
4. **Upgrade prompt**: For free tier users who hit limits
5. **Sync status**: Last sync time, next sync time (ADR-052)

```typescript
interface TierLimits {
  tier: 'free' | 'starter' | 'pro';
  limits: {
    slack_channels: number;
    gmail_labels: number;
    notion_pages: number;
    calendars: number;
    total_platforms: number;
    sync_frequency: '2x_daily' | '4x_daily' | 'hourly';
    tp_conversations_per_month: number;
    active_deliverables: number;
  };
  usage: {
    slack_channels: number;
    gmail_labels: number;
    notion_pages: number;
    calendars: number;
    platforms_connected: number;
    tp_conversations_this_month: number;
    active_deliverables: number;
  };
  next_sync?: string;  // ISO timestamp
}
```

---

## API Endpoints

### GET `/api/user/limits`

Returns current tier, limits, and usage.

```json
{
  "tier": "free",
  "limits": {
    "slack_channels": 1,
    "gmail_labels": 1,
    "notion_pages": 1,
    "calendars": 1,
    "total_platforms": 2,
    "sync_frequency": "2x_daily",
    "tp_conversations_per_month": 20,
    "active_deliverables": 3
  },
  "usage": {
    "slack_channels": 1,
    "gmail_labels": 0,
    "notion_pages": 0,
    "calendars": 0,
    "platforms_connected": 1,
    "tp_conversations_this_month": 5,
    "active_deliverables": 1
  },
  "next_sync": "2026-02-12T18:00:00Z"
}
```

### PUT `/api/integrations/{provider}/sources`

Updates selected sources with limit enforcement.

**Request:**
```json
{
  "source_ids": ["C123", "C456", "C789"]
}
```

**Response (success):**
```json
{
  "success": true,
  "selected_count": 3,
  "limit": 5,
  "message": "OK: 3/5 sources"
}
```

**Response (over limit):**
```json
{
  "success": false,
  "selected_count": 5,
  "limit": 5,
  "message": "Requested 8 sources but limit is 5. Only first 5 saved.",
  "truncated": true
}
```

---

## Enforcement Points

### 1. Source Selection (Primary)

When user selects sources to sync:
- Frontend disables checkbox when at limit
- Backend truncates to limit if exceeded
- Shows "upgrade to Pro" prompt

### 2. Platform Connection (Secondary)

When user connects a new platform:
- Check `total_platforms` limit before OAuth flow
- Block connection with upgrade prompt if at limit

### 3. Sync Operations (Background)

During scheduled syncs:
- Only sync selected sources (within limits)
- Skip sources beyond limit
- Log skipped sources for admin visibility

---

## User Experience

### At Limit State (Free Tier)

```
┌────────────────────────────────────────────────────────────┐
│ ⚠️  Channel limit reached                                  │
│                                                            │
│ Your free plan allows 1 channel.                           │
│ [✨ Upgrade to Starter] for 5 channels ($9/mo)             │
└────────────────────────────────────────────────────────────┘
```

### Sync Frequency Indicator

```
#engineering
✅ Synced • 142 messages • Last sync: 2 hours ago
Next sync: 6:00 PM (Upgrade to Starter for 4x/day)
```

### Upgrade Prompt

Shown inline on platform detail page, not as blocking modal:
- Clear value proposition ("5 channels + 4x/day sync")
- One-click upgrade path
- Non-intrusive placement
- Tiered options: Starter ($9) vs Pro ($19)

---

## Future Enhancements

### Not Yet Implemented

1. **Usage Dashboard** - Show limits and usage across all resources
2. **Overage Alerts** - Email when approaching limits
3. **Grace Period** - Allow temporary overage for downgrade scenarios
4. **Usage History** - Track usage over time for analytics
5. **Admin Override** - Manual limit adjustments for special cases
6. **Stripe Integration** - Payment processing for Starter/Pro tiers

### Now Included in Tier Limits (ADR-053)

| Resource | Status |
|----------|--------|
| Deliverables | ✅ Included (3/10/unlimited) |
| TP conversations/month | ✅ Included (20/100/unlimited) |
| Sync frequency | ✅ Included (2x/4x/hourly) |

### Potential Future Limits

| Resource | Consideration |
|----------|---------------|
| Context storage | Total stored ephemeral_context size |
| API calls/day | Rate limit for platform tool calls |
| Deliverable executions | Monthly quota for scheduled runs |

---

## Security Considerations

1. **Server-side enforcement** - Never trust client-side limit checks alone
2. **Audit logging** - Log all limit checks and overrides
3. **Graceful degradation** - Don't break existing functionality when limits change
4. **Clear communication** - Always tell users why action was blocked

---

## Testing Checklist

- [ ] Free user cannot select more than limit
- [ ] At-limit state shows upgrade prompt
- [ ] Pro user has higher limits
- [ ] Downgrade handles over-limit sources gracefully
- [ ] API returns correct limits per tier
- [ ] Limit warning appears at 80%
- [ ] Source selection save is atomic (all or nothing)

---

## Related Files

| File | Purpose |
|------|---------|
| `api/services/platform_limits.py` | Backend limit enforcement (platform resources) |
| `web/lib/api/client.ts` | Frontend API client (getLimits) |
| `web/app/(authenticated)/context/[platform]/page.tsx` | Platform detail UI |
| `web/components/platforms/SourceSelectionModal.tsx` | Modal-based selection (legacy, prefer inline) |
| `web/lib/subscription/limits.ts` | Legacy limits (projects, memories, chat sessions) - not platform resources |

---

## Notes

### Consolidated Limit System (ADR-053)

As of ADR-053, platform resource limits are the **primary monetization lever**:

1. **Platform Resource Limits** (`api/services/platform_limits.py`)
   - Synced sources: Slack channels, Gmail labels, Notion pages, Calendars
   - Sync frequency: 2x/day → 4x/day → hourly
   - TP conversations per month
   - Active deliverables
   - Enforced at source selection + sync time

2. **Legacy App Limits** (`web/lib/subscription/limits.ts`)
   - Projects, memories per project - **deprecated**
   - Should be consolidated into platform limits

### Cost Analysis

| Tier | Sync Cost/Mo | LLM Cost/Mo (est) | Price | Margin |
|------|--------------|-------------------|-------|--------|
| Free | ~$0.05 | ~$0.50 | $0 | Loss leader |
| Starter | ~$0.15 | ~$2 | $9 | ~$6.85 (76%) |
| Pro | ~$0.50 | ~$5 | $19 | ~$13.50 (71%) |

Platform sync (no LLM) is extremely profitable. LLM usage is the variable cost controlled by conversation/deliverable limits.

---

## Changelog

### 2026-02-12: ADR-053 Revision

- **Tighter free tier**: 1 source per platform (was 3-5)
- **Added Starter tier**: $9/mo, middle ground for solo users
- **Sync frequency as tier lever**: 2x/4x/hourly
- **TP conversations limit**: 20/100/unlimited
- **Deliverables limit**: 3/10/unlimited
- **Counting model**: Synced sources, not connections
- **Removed Enterprise**: Deferred until demand

### 2026-02-11: Initial Implementation

- Framework for platform resource limits
- Free/Pro/Enterprise tiers (generous limits)
- Backend enforcement in `platform_limits.py`
