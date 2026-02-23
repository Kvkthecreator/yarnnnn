# DECISION-001: Platform Sync Strategy

**Date**: 2026-02-11
**Status**: Decided
**Decision Makers**: Kevin, Claude

---

## Context

YARNNN connects to user platforms (Slack, Gmail, Notion) to gather context for deliverable generation. Two sync models are architecturally supported:

1. **Continuous Background Sync**: Scheduled jobs refresh platform data periodically
2. **On-Demand Sync**: Platform data fetched when needed for deliverable generation

This decision affects costs, UX, and monetization strategy.

---

## Decision

**Ship on-demand sync only for v1. Reserve continuous sync for future premium tier.**

### Rationale

| Factor | Continuous | On-Demand |
|--------|------------|-----------|
| Cost at scale | High (users × platforms × frequency) | Proportional to usage |
| Data freshness | Always warm | Fresh at generation time |
| Complexity | Requires sync scheduling UI | Simpler UX |
| Premium value | Clear enterprise feature | Baseline expectation |

### Implementation

The architecture already supports both:
- `unified_scheduler.py` - has scheduled sync capability (disabled for now)
- `execute.py` - handles `Execute(action="platform.sync")` on-demand
- `platform_content` table - stores cached data with `synced_at` timestamps

**No code changes needed.** This is a configuration/product decision.

---

## Frontend Implications

### Platform Settings (Missing Today)

Users need visibility into their connected platforms. Required UI:

```
┌─────────────────────────────────────────────────────────┐
│ Connected Platforms                                      │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 🔗 Slack                              [Connected ✓] │ │
│ │   Workspace: acme-corp                              │ │
│ │   Channels (3/5 max):                               │ │
│ │     • #engineering (last sync: 2h ago)              │ │
│ │     • #product (last sync: 2h ago)                  │ │
│ │     • #general (last sync: 1d ago)                  │ │
│ │   [+ Add Channel] [Manage]                          │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📧 Gmail                              [Connected ✓] │ │
│ │   Account: user@company.com                         │ │
│ │   Labels (2/3 max):                                 │ │
│ │     • INBOX (last sync: 30m ago)                    │ │
│ │     • Important (last sync: 30m ago)                │ │
│ │   [+ Add Label] [Manage]                            │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📝 Notion                             [Connect →]   │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Key UI Elements Needed

1. **Platform Connection Status**
   - Connected/disconnected state
   - Account/workspace identifier
   - OAuth re-auth prompt if token expired

2. **Channel/Source Selection**
   - List of available channels/labels/pages
   - Toggle to include/exclude from sync
   - **Cap enforcement** (see limits below)

3. **Sync Status Per Source**
   - Last sync timestamp
   - Sync health indicator
   - Manual "Refresh Now" button

4. **Deliverable → Platform Mapping**
   - When creating deliverable, show which platforms are sources
   - Indicate data freshness for each source

---

## Resource Limits (v1)

To control costs and complexity:

| Platform | Resource Type | Free Tier | Pro Tier (Future) |
|----------|--------------|-----------|-------------------|
| Slack | Channels | 5 | 20 |
| Gmail | Labels | 3 | 10 |
| Notion | Pages/DBs | 5 | 25 |
| Total platforms | - | 3 | Unlimited |

### Limit Enforcement

- Frontend: Disable "Add" button when at cap
- Backend: Reject `platform.sync` for sources beyond limit
- Schema: Store limits in `user_settings` or tier-based lookup

---

## Data Model Implications

### Current Schema (Sufficient)

```sql
-- platforms table
platforms (
  id, user_id, provider, credentials,
  config,  -- JSONB: selected channels, labels, etc.
  status, last_sync_at, created_at
)

-- platform_content table
platform_content (
  id, platform_id, content_type, content_id,
  raw_content, extracted_summary,
  synced_at, expires_at
)
```

### Needed Additions

```sql
-- Add to platforms.config JSONB:
{
  "selected_sources": [
    {"type": "channel", "id": "C123", "name": "#engineering"},
    {"type": "channel", "id": "C456", "name": "#product"}
  ],
  "source_limit": 5,  -- or look up from tier
  "sync_preferences": {
    "freshness_threshold_hours": 24
  }
}

-- Add to user tier/settings:
user_settings.platform_limits = {
  "slack_channels": 5,
  "gmail_labels": 3,
  "notion_pages": 5
}
```

---

## Future: Premium Continuous Sync

When enabled for premium users:

1. Add `sync_schedule` to `platforms.config`:
   ```json
   {
     "sync_schedule": {
       "enabled": true,
       "frequency": "hourly",
       "quiet_hours": {"start": "22:00", "end": "06:00"}
     }
   }
   ```

2. `unified_scheduler.py` picks up platforms with `sync_schedule.enabled = true`

3. Charge based on sync frequency × sources

---

## Action Items

### Immediate (v1)
- [ ] Frontend: Platform settings page with connection status
- [ ] Frontend: Source selection UI (channels, labels, pages)
- [ ] Frontend: Limit enforcement (cap display, disable add when full)
- [ ] Backend: Validate source limits on sync requests
- [ ] Backend: Store `selected_sources` in platforms.config

### Deferred (v2/Premium)
- [ ] Continuous sync toggle in UI
- [ ] Sync frequency selection
- [ ] Usage/cost dashboard
- [ ] Tier-based limit configuration

---

## Related

- ADR-035: Platform-First Type System
- ADR-038: Claude Code Architecture Mapping (platform as context)
- `api/services/platform_sync.py` - sync implementation
- `api/jobs/unified_scheduler.py` - scheduler infrastructure
