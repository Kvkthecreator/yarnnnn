# yarnnn Platform Resource Limits

> **Status**: Implemented (framework ready, not hardened)
> **Date**: 2026-02-11
> **Related**: ADR-043 (Platform Settings), ADR-046 (Google Calendar Integration)

---

## Overview

This document describes the resource limits that control platform usage based on subscription tier. These limits serve three purposes:

1. **Cost Control** - External API calls, storage, and sync operations have real costs
2. **Fair Usage** - Prevent abuse and ensure equitable resource distribution
3. **Monetization** - Create upgrade incentives aligned with value delivered

---

## Tier Limits

### Current Implementation

| Resource | Free | Pro | Enterprise |
|----------|------|-----|------------|
| Slack channels | 5 | 20 | 100 |
| Gmail labels | 3 | 10 | 50 |
| Notion pages | 5 | 25 | 100 |
| Calendar events | 3 | 10 | 50 |
| Total platforms | 3 | 10 | 50 |

### Rationale

- **Free tier**: Enough to try the product meaningfully, not enough to run a business on
- **Pro tier**: Sufficient for individual power users with multiple active projects
- **Enterprise tier**: High limits for organizations with complex workflows

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
    calendar_events: int
    total_platforms: int

TIER_LIMITS = {
    "free": PlatformLimits(
        slack_channels=5,
        gmail_labels=3,
        notion_pages=5,
        calendar_events=3,
        total_platforms=3,
    ),
    "pro": PlatformLimits(...),
    "enterprise": PlatformLimits(...),
}

# Provider to limit field mapping
PROVIDER_LIMIT_MAP = {
    "slack": "slack_channels",
    "gmail": "gmail_labels",
    "google": "gmail_labels",
    "notion": "notion_pages",
    "calendar": "calendar_events",
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

```typescript
interface TierLimits {
  tier: 'free' | 'pro' | 'enterprise';
  limits: {
    slack_channels: number;
    gmail_labels: number;
    notion_pages: number;
    calendar_events: number;
    total_platforms: number;
  };
  usage: { ... };
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
    "slack_channels": 5,
    "gmail_labels": 3,
    "notion_pages": 5,
    "calendar_events": 3,
    "total_platforms": 3
  },
  "usage": {
    "slack_channels": 2,
    "gmail_labels": 1,
    "notion_pages": 0,
    "calendar_events": 0,
    "platforms_connected": 2
  }
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

### At Limit State

```
┌────────────────────────────────────────────────────────────┐
│ ⚠️  Channel limit reached                                  │
│                                                            │
│ Your free plan allows 5 channels.                          │
│ [✨ Upgrade to Pro] for 20 channels.                       │
└────────────────────────────────────────────────────────────┘
```

### Near Limit Warning (80%)

```
Using 4 of 5 channels (80%)
```

### Upgrade Prompt

Shown inline on platform detail page, not as blocking modal:
- Clear value proposition
- One-click upgrade path
- Non-intrusive placement

---

## Future Enhancements

### Not Yet Implemented

1. **Usage Dashboard** - Show limits and usage across all resources
2. **Overage Alerts** - Email when approaching limits
3. **Grace Period** - Allow temporary overage for downgrade scenarios
4. **Usage History** - Track usage over time for analytics
5. **Admin Override** - Manual limit adjustments for special cases

### Potential Additional Limits

| Resource | Consideration |
|----------|---------------|
| Deliverables | Number of active scheduled deliverables |
| Executions/month | Monthly quota for deliverable runs |
| Context storage | Total stored memories/context size |
| API calls/day | Rate limit for external platform calls |

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

### Two Limit Systems

There are currently two separate limit systems:

1. **Platform Resource Limits** (`api/services/platform_limits.py`)
   - Slack channels, Gmail labels, Notion pages, Calendar events
   - Enforced at source selection time
   - Documented in this file

2. **Legacy App Limits** (`web/lib/subscription/limits.ts`)
   - Projects, memories per project, chat sessions per month, documents
   - Frontend-only, not fully enforced
   - May need consolidation in future

The platform resource limits are the primary monetization lever as they directly correlate with API usage and storage costs.
