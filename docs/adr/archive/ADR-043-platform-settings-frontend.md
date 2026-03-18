# ADR-043: Platform Settings Frontend

**Date**: 2026-02-11
**Status**: Proposed
**Relates to**: DECISION-001 (Platform Sync Strategy), ADR-035 (Platform-First Types)

---

## Context

Users connect platforms (Slack, Gmail, Notion) to provide context for agent generation. Currently, platform connections exist in the backend but lack frontend visibility and control. Users need to:

1. See which platforms are connected
2. Select which sources (channels, labels, pages) to sync
3. Understand sync status and data freshness
4. Stay within resource limits

---

## Decision

Implement a Platform Settings page with source selection, limit enforcement, and sync status visibility.

---

## Frontend Components

### 1. Platform Settings Page (`/settings/platforms`)

**Route**: `/settings/platforms` or `/platforms`

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ Platform Connections                                        │
│ Connect your tools to enable context-aware agents     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ [PlatformCard: Slack]                                       │
│ [PlatformCard: Gmail]                                       │
│ [PlatformCard: Notion]                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. PlatformCard Component

**States**: Disconnected | Connected | Error (token expired)

```
Disconnected:
┌─────────────────────────────────────────────────────────────┐
│ 💬 Slack                                                    │
│ Connect to sync channel messages for your agents      │
│                                          [Connect Slack →]  │
└─────────────────────────────────────────────────────────────┘

Connected:
┌─────────────────────────────────────────────────────────────┐
│ 💬 Slack                                    ● Connected     │
│ acme-corp.slack.com                                         │
│                                                             │
│ Selected Channels (3 of 5)                    [Manage →]    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ #engineering        Last sync: 2 hours ago    [Remove]  │ │
│ │ #product            Last sync: 2 hours ago    [Remove]  │ │
│ │ #general            Last sync: 1 day ago      [Remove]  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ [+ Add Channel]                           [Disconnect ⚠️]   │
└─────────────────────────────────────────────────────────────┘

Error:
┌─────────────────────────────────────────────────────────────┐
│ 💬 Slack                                    ⚠️ Reconnect    │
│ Connection expired. Please reconnect to continue syncing.   │
│                                        [Reconnect Slack →]  │
└─────────────────────────────────────────────────────────────┘
```

### 3. Source Selection Modal

Triggered by "Manage" or "+ Add Channel/Label/Page"

```
┌─────────────────────────────────────────────────────────────┐
│ Select Slack Channels                              [×]      │
├─────────────────────────────────────────────────────────────┤
│ 🔍 Search channels...                                       │
├─────────────────────────────────────────────────────────────┤
│ Selected (3 of 5 max)                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ☑ #engineering         1,234 members                    │ │
│ │ ☑ #product               456 members                    │ │
│ │ ☑ #general             2,100 members                    │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Available                                                   │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ☐ #design                 89 members                    │ │
│ │ ☐ #random                567 members                    │ │
│ │ ☐ #announcements         all members          (disabled)│ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ⚠️ You've reached the 5 channel limit.                      │
│    Upgrade to Pro for up to 20 channels.                    │
│                                                             │
│                              [Cancel]  [Save Changes]       │
└─────────────────────────────────────────────────────────────┘
```

### 4. Sync Status Indicator

Inline component showing freshness:

```
Recent (< 1 hour):    ● Synced 15 min ago
Stale (1-24 hours):   ○ Synced 6 hours ago
Old (> 24 hours):     ⚠️ Synced 2 days ago [Refresh]
```

### 5. Agent Source Preview

When creating/editing a agent, show platform sources:

```
┌─────────────────────────────────────────────────────────────┐
│ Data Sources                                                │
├─────────────────────────────────────────────────────────────┤
│ This agent will pull from:                            │
│                                                             │
│ 💬 Slack: #engineering, #product                            │
│    ● Last synced 2 hours ago                                │
│                                                             │
│ 📧 Gmail: INBOX, Important                                  │
│    ○ Last synced 8 hours ago                                │
│                                                             │
│ [Configure Sources]              [Refresh Now]              │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Requirements

### API Endpoints Needed

```
GET  /api/platforms
     → List user's platforms with connection status, selected sources

GET  /api/platforms/:id/available-sources
     → List available channels/labels/pages for selection

PUT  /api/platforms/:id/sources
     → Update selected sources (with limit validation)

POST /api/platforms/:id/sync
     → Trigger on-demand sync for platform

GET  /api/user/limits
     → Get user's tier limits (platform counts, source counts)
```

### Response Shapes

```typescript
// GET /api/platforms
interface PlatformResponse {
  id: string;
  provider: 'slack' | 'gmail' | 'notion';
  status: 'connected' | 'disconnected' | 'error';
  workspace_name?: string;  // "acme-corp" for Slack
  account_email?: string;   // for Gmail
  selected_sources: Source[];
  source_limit: number;
  last_sync_at: string | null;
  error_message?: string;   // if status === 'error'
}

interface Source {
  id: string;           // channel ID, label ID, page ID
  type: string;         // 'channel', 'label', 'page', 'database'
  name: string;         // "#engineering", "INBOX", "Q1 Planning"
  last_sync_at: string | null;
  metadata?: {
    member_count?: number;  // for Slack channels
    message_count?: number; // for Gmail labels
  };
}

// GET /api/platforms/:id/available-sources
interface AvailableSourcesResponse {
  sources: Source[];
  selected_ids: string[];
  limit: number;
  can_add_more: boolean;
}

// GET /api/user/limits
interface UserLimitsResponse {
  tier: 'free' | 'pro' | 'enterprise';
  limits: {
    slack_channels: number;
    gmail_labels: number;
    notion_pages: number;
    total_platforms: number;
  };
  usage: {
    slack_channels: number;
    gmail_labels: number;
    notion_pages: number;
    platforms_connected: number;
  };
}
```

---

## State Management

### Platform Store (Zustand/Context)

```typescript
interface PlatformStore {
  platforms: Platform[];
  userLimits: UserLimits | null;
  isLoading: boolean;

  // Actions
  fetchPlatforms: () => Promise<void>;
  fetchUserLimits: () => Promise<void>;
  updateSources: (platformId: string, sourceIds: string[]) => Promise<void>;
  triggerSync: (platformId: string) => Promise<void>;
  disconnectPlatform: (platformId: string) => Promise<void>;
}
```

---

## Component Hierarchy

```
PlatformSettingsPage
├── PageHeader
│   └── "Platform Connections" + description
├── PlatformList
│   ├── PlatformCard (Slack)
│   │   ├── PlatformHeader (icon, name, status badge)
│   │   ├── WorkspaceInfo (if connected)
│   │   ├── SourceList
│   │   │   └── SourceItem (name, sync status, remove button)
│   │   └── PlatformActions (add source, disconnect)
│   ├── PlatformCard (Gmail)
│   └── PlatformCard (Notion)
└── SourceSelectionModal
    ├── SearchInput
    ├── SelectedSourcesList
    ├── AvailableSourcesList
    ├── LimitWarning (if at cap)
    └── ActionButtons (cancel, save)
```

---

## Limit Enforcement UX

### At Limit
- "Add Channel" button disabled with tooltip: "Channel limit reached (5/5)"
- Modal shows warning banner with upgrade CTA
- Checkboxes for additional sources disabled

### Approaching Limit
- Show count: "3 of 5 channels"
- No warning unless at limit

### Over Limit (Edge Case)
If user downgrades and is over limit:
- Show all sources but mark excess as "inactive"
- Banner: "You're over your plan limit. Remove X sources or upgrade."
- Generation skips inactive sources

---

## Sync Status Logic

```typescript
function getSyncStatus(lastSyncAt: string | null): SyncStatus {
  if (!lastSyncAt) return { level: 'never', label: 'Never synced' };

  const hoursSince = differenceInHours(new Date(), new Date(lastSyncAt));

  if (hoursSince < 1) return { level: 'fresh', label: `${minutesSince}m ago` };
  if (hoursSince < 24) return { level: 'stale', label: `${hoursSince}h ago` };
  return { level: 'old', label: `${daysSince}d ago`, showRefresh: true };
}
```

---

## Error Handling

### OAuth Token Expired
- Platform card shows error state
- "Reconnect" button triggers OAuth flow
- After reconnect, refresh platform data

### Sync Failure
- Show toast: "Failed to sync Slack. Retrying..."
- Retry with exponential backoff (3 attempts)
- After final failure: "Sync failed. Try again later."

### Source Not Found
- If channel deleted/archived, show in list with warning
- "This channel is no longer available. [Remove]"

---

## Mobile Considerations

- Cards stack vertically
- Source selection modal becomes full-screen drawer
- Touch-friendly checkboxes and buttons
- Swipe to remove source (with confirmation)

---

## Implementation Phases

### Phase 1: Core Platform Settings
- [ ] Platform list page with connection status
- [ ] Basic source display (read-only from current config)
- [ ] Connect/disconnect flows (existing OAuth)

### Phase 2: Source Selection
- [ ] Source selection modal
- [ ] Available sources API endpoint
- [ ] Update sources API endpoint
- [ ] Limit enforcement (frontend + backend)

### Phase 3: Sync Status
- [ ] Last sync timestamps per source
- [ ] Manual refresh button
- [ ] Sync status indicators

### Phase 4: Agent Integration
- [ ] Source preview in agent creation
- [ ] Pre-generation freshness check UI
- [ ] "Refresh sources" before generate

---

## Files to Create/Modify

### Existing Structure (ADR-039)

The frontend uses a unified Context page (`/context`) that already shows platforms.
Platform settings should extend this pattern rather than create a new page.

```
web/app/(authenticated)/context/page.tsx  -- Existing unified context view
web/app/(authenticated)/integrations/page.tsx  -- Redirects to /context?source=platforms
web/app/(authenticated)/integrations/[provider]/page.tsx  -- Provider detail page
```

### New/Modified Files
```
web/app/(authenticated)/integrations/[provider]/page.tsx  -- Extend with source selection
web/components/platforms/SourceSelectionModal.tsx  -- New modal component
web/components/platforms/SyncStatusBadge.tsx  -- Sync freshness indicator
web/lib/api/client.ts  -- Add new API methods (limits, sources)
```

### Backend (Implemented)
```
api/routes/integrations.py  -- Source management endpoints added
api/services/platform_limits.py  -- Limit checking logic (created)
```

---

## Implementation Status

### Phase 1: Core Platform Settings ✅

**Backend (Complete)**:
- `api/services/platform_limits.py` - Tier-based limits (Free: 5 Slack, 3 Gmail, 5 Notion)
- `api/routes/integrations.py` - New endpoints:
  - `GET /api/user/limits` - Returns tier limits and current usage
  - `GET /api/integrations/{provider}/sources` - Get selected sources
  - `PUT /api/integrations/{provider}/sources` - Update selected sources
  - `POST /api/integrations/{provider}/sync` - Trigger on-demand sync

**Frontend (Complete)**:
- `web/lib/api/client.ts` - Added API methods:
  - `api.integrations.getLimits()` - Fetch user tier limits
  - `api.integrations.getSources(provider)` - Get selected sources
  - `api.integrations.updateSources(provider, sourceIds)` - Update sources
  - `api.integrations.triggerSync(provider)` - Trigger sync

- `web/components/platforms/SourceSelectionModal.tsx`:
  - Search/filter available sources
  - Checkbox selection with limit enforcement
  - Shows "X of Y" count with limit warnings
  - Upgrade CTA when at limit
  - Saves changes via API

- `web/components/platforms/SyncStatusBadge.tsx`:
  - `SyncStatusBadge` - Full badge with label and refresh button
  - `SyncStatusInline` - Compact inline variant
  - `SyncStatusDot` - Dot-only indicator
  - States: fresh (<1h), stale (1-24h), old (>24h), never

- `web/components/ui/PlatformDetailPanel.tsx`:
  - Added "Manage" button to resources section
  - Shows source count with limit (e.g., "3/5")
  - Opens SourceSelectionModal on click
  - Refreshes after source changes

### Phase 2: Source Selection ✅
See Phase 1 - implemented together.

### Phase 3: Sync Status (Partial)
- SyncStatusBadge component created
- Not yet integrated into PlatformCard/resource lists

### Phase 4: Agent Integration (Pending)
- [ ] Source preview in agent creation
- [ ] Pre-generation freshness check UI
- [ ] "Refresh sources" before generate

### Phase 5: First-Time Import for Cold Start ✅

**Problem**: Users connect a platform and select channels, but TP has no context until a agent runs. This creates a poor cold-start experience where users expect "I connected Slack, TP should know about my work."

**Solution**: After first source selection save, prompt user to import recent context.

**Flow**:
```
1. User connects Slack → sees channel list
2. User selects channels → clicks "Save changes"
3. Save succeeds → show import prompt:
   ┌─────────────────────────────────────────────────────────────┐
   │ ✓ Sources saved                                             │
   │                                                             │
   │ Import recent context from these channels?                  │
   │ This lets TP understand your work right away.               │
   │                                                             │
   │ • Last 7 days of messages                                   │
   │ • From 3 selected channels                                  │
   │ • ~30 seconds                                               │
   │                                                             │
   │                        [Skip]  [Import Now]                 │
   └─────────────────────────────────────────────────────────────┘
4. If "Import Now" → trigger import job → show progress
5. Import completes → channels show "Synced" badge
6. TP now has context for chat conversations
```

**When to show prompt**:
- First time saving sources for this platform (no previous selections)
- OR when adding new sources that have never been imported

**When NOT to show**:
- User is just removing sources
- All selected sources already have extracted context
- User previously dismissed the prompt (store preference)

**Limits consideration**:
- Import uses same tier limits as selection
- If user can select 5 channels, they can import from 5 channels
- Cost (API calls + LLM) already factored into tier pricing

**Implementation**:
- Frontend: `ImportPrompt` component shown after successful save
- Backend: Uses existing `POST /api/integrations/{provider}/import` endpoint
- Progress: Poll existing job status endpoint

---

## Related

- DECISION-001: Platform Sync Strategy
- ADR-035: Platform-First Type System
- ADR-038: Claude Code Architecture Mapping
- ADR-039: Unified Context Surface
