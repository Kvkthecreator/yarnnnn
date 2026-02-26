# User Flow: Platform-First Onboarding (v3)

> **Status**: Current
> **Date**: 2026-02-26
> **Supersedes**: Onboarding V2 (2026-02-09)
> **Related ADRs**: ADR-053 (Tier Model), ADR-057 (Streamlined Onboarding), ADR-072 (Unified Content Layer), ADR-079 (Smart Source Auto-Selection)

---

## Overview

Users connect platforms (Slack, Gmail, Notion, Calendar) and select which sources to sync. Context accumulates over time through tier-based scheduled syncs. TP (Thinking Partner) uses this context in conversations and deliverable generation.

**Key design principle**: Context pages (`/context/{platform}`) are the **singular** source selection experience. No modals, no wizards — one place for everything.

---

## User Journey

```
OPEN  →  CONNECT  →  SELECT SOURCES  →  CONTEXT BUILDS  →  USE TP
 │          │              │                   │              │
 ▼          ▼              ▼                   ▼              ▼
Dashboard  OAuth       Context page       Scheduled       Chat +
welcome    redirect    with recommended   tier-based      Deliverables
screen     to context  grouping           syncs
           page
```

---

## Stage 1: First Open (Cold Start)

### User State
- Authenticated via Supabase Auth
- No connected platforms
- No synced content

### Experience

Dashboard shows `PlatformSyncStatus` component in `ChatFirstDesk`:
- 4 platform buttons (Slack, Gmail, Notion, Calendar) with connect CTAs
- Document upload option
- Tier info: "Free plan: 2 sources per platform, syncs 2x daily"

### Actions
1. **Connect Platform** → starts OAuth flow → redirects to `/context/{platform}?status=connected`
2. **Upload Document** → file picker → PDF/DOCX/TXT/MD
3. **Skip** → start chatting with TP (limited context)

---

## Stage 2: Connect Platform (OAuth)

### Flow
1. User clicks platform connect button (dashboard or context page)
2. OAuth redirect to provider (Slack/Google/Notion)
3. Provider grants access
4. Backend callback stores credentials in `platform_connections` (encrypted)
5. Redirect to `/context/{platform}?status=connected`

### Google OAuth Note
Google OAuth serves both Gmail and Calendar. Backend redirects to `/context/gmail?status=connected`. Calendar becomes available automatically.

---

## Stage 3: Source Selection (Context Page)

### First-Connect Experience

When landing on `/context/{platform}?status=connected`:

1. **Welcome banner** (green): "{Platform} Connected — Select sources to start building context"
2. **Landscape auto-discovery**: Backend fetches available resources (channels, labels, pages, calendars)
3. **Smart defaults** (ADR-079): `compute_smart_defaults()` pre-selects recommended sources based on activity heuristics
4. **Recommended grouping**: Resources split into "Recommended based on activity" (highlighted) and "All {resources}" sections

### Source Selection UI (`ResourceList`)

```
┌──────────────────────────────────────────────────────┐
│  ✅ Gmail Connected                                   │
│  Select sources below to start building context.      │
│  Recommended sources are highlighted based on activity.│
└──────────────────────────────────────────────────────┘

  Channels                         in Acme Corp
  Select which channels to include as context sources.
  3 of 5 selected

  ✦ RECOMMENDED BASED ON ACTIVITY
  ┌────────────────────────────────────────────────────┐
  │ ☑ #general          234 members    Synced 2h ago   │
  │ ☑ #engineering      89 members     Synced 2h ago   │
  │ ☑ #product          45 members     Not synced      │
  └────────────────────────────────────────────────────┘

  ALL CHANNELS
  ┌────────────────────────────────────────────────────┐
  │ ☐ #random           234 members                    │
  │ ☐ #social           178 members                    │
  │ ☐ #design           23 members                     │
  │ ...                                                │
  └────────────────────────────────────────────────────┘
```

### Save + Import Flow

1. User toggles sources → "Save changes" / "Discard" buttons appear
2. Save → backend persists to `platform_connections.landscape.selected_sources`
3. If newly-added sources have no synced content:
   - **Import prompt**: "Import now (last 7 days)" or "Wait for next scheduled sync"
   - Import runs foreground polling against `/integrations/{provider}/import`
   - Progress bar shows per-source import status

### Tier Limits

Source selection is gated by tier:

| Tier    | Slack Channels | Gmail Labels | Notion Pages | Calendars |
|---------|---------------|-------------|-------------|-----------|
| Free    | 5             | 5           | 10          | Unlimited |
| Starter | 15            | 10          | 25          | Unlimited |
| Pro     | Unlimited     | Unlimited   | Unlimited   | Unlimited |

When at limit:
- Amber warning: "{Resource} limit reached"
- Upgrade CTA: Free → "Upgrade to Starter", Starter → "Upgrade to Pro"
- Disabled checkboxes on unselected resources

### Smart Default Heuristics (ADR-079)

| Platform | Ranking Signal | Notes |
|----------|---------------|-------|
| Slack    | `num_members` desc | Busy channels = more context |
| Gmail    | INBOX > SENT > STARRED > user labels | Skip system noise (SPAM, TRASH, CATEGORY_*) |
| Notion   | `last_edited_time` desc | Recently active = most relevant |
| Calendar | Auto-select ALL | Tiny data volume, unlimited tier |

---

## Stage 4: Context Accumulates

### Scheduled Syncs

After source selection, tier-based scheduler runs automatically:

| Tier    | Sync Frequency |
|---------|---------------|
| Free    | 2x/day (8am, 6pm user timezone) |
| Starter | 4x/day (every 6 hours) |
| Pro     | Hourly |

Syncs are handled by `platform_sync_scheduler` cron job (every 5 min, checks who's due).

### Content Storage

Synced content stored in `platform_content` table (ADR-072):
- Retention-based: content has TTL (Slack 14d, Gmail 30d, Notion 90d, Calendar 2d)
- Retained content (referenced by TP) persists beyond TTL
- Content accumulates over time, building the "context moat"

### Coverage Visibility

Each resource in the context page shows:
- **Coverage badge**: Synced (green), Partial (yellow), Stale (orange), Not synced (gray), Error (red)
- **Item count**: "42 items synced 2 hours ago"
- **Error detail**: If sync failed, shows error message with timestamp
- **Expand**: Click chevron to preview synced content items inline

---

## Stage 5: Dashboard (Returning User)

### PlatformSyncStatus Component

Connected platforms show:
- Platform icon + workspace name
- Source count + last sync time
- Stale warning (amber) if sources are stale
- **"+" button** → navigates to `/context/{platform}` for source management

Unconnected platforms show:
- Connect button → starts OAuth → lands on context page

### Navigation Model

```
Dashboard (PlatformSyncStatus)
  ├─ [+] Slack    → /context/slack     (source selection)
  ├─ [+] Gmail    → /context/gmail     (source selection)
  ├─ [+] Notion   → /context/notion    (source selection)
  └─ [+] Calendar → /context/calendar  (calendar view + settings)
```

---

## Stage 6: Use TP

With accumulated context, TP can:
- Reference recent Slack messages, Gmail threads, Notion pages
- Prep for upcoming calendar meetings
- Generate deliverables (status reports, summaries, briefs)
- Answer questions about what happened across platforms

---

## Technical Components

### Frontend

| Component | Location | Purpose |
|-----------|----------|---------|
| `PlatformSyncStatus` | `components/desk/` | Dashboard platform cards + connect |
| `ResourceList` | `components/context/` | Source selection with grouping |
| `ResourceRow` | `components/context/` | Individual resource with coverage |
| `SyncStatusBanner` | `components/context/` | Tier + sync frequency display |
| `PlatformHeader` | `components/context/` | Back nav + connection details |
| `PlatformNotConnected` | `components/context/` | OAuth CTA for unconnected |

### Hooks

| Hook | Purpose |
|------|---------|
| `usePlatformData` | Loads integration, landscape, limits, sources, deliverables |
| `useSourceSelection` | Toggle, save, import workflow with tier enforcement |
| `useResourceExpansion` | On-demand content preview per resource |

### Backend

| Endpoint | Purpose |
|----------|---------|
| `GET /integrations/{provider}/landscape` | Discover resources + recommended flag |
| `PUT /integrations/{provider}/sources` | Save selected sources |
| `POST /integrations/{provider}/import` | Start foreground import job |
| `GET /integrations/limits` | Get tier limits for current user |

### Data Flow

```
OAuth → platform_connections (credentials)
     → landscape discovery → platform_connections.landscape
     → compute_smart_defaults() → landscape.selected_sources
     → platform_sync_scheduler → platform_content (accumulation)
     → TP prompt injection (working memory)
```

---

## Deleted Components (v3 cleanup)

These were removed as part of the singular selection UX:
- `components/onboarding/SourceSelectionModal.tsx` — replaced by context pages
- `components/platforms/SourceSelectionModal.tsx` — dead code
- `components/ui/PlatformDetailPanel.tsx` — dead code
- `components/platforms/SyncStatusBadge.tsx` — dead code

---

## References

- [ADR-053: Tier Model](../adr/ADR-053-tier-gated-monetization.md)
- [ADR-057: Streamlined Onboarding](../adr/ADR-057-streamlined-onboarding-gated-sync.md)
- [ADR-072: Unified Content Layer](../adr/ADR-072-unified-content-layer.md)
- [ADR-079: Smart Source Auto-Selection](../adr/ADR-079-smart-source-auto-selection.md)
- [Backend Orchestration v2.0](../architecture/backend-orchestration.md)
