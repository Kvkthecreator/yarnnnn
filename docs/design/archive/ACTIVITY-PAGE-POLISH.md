# Activity Page Polish — Date Grouping & Expandable Details

**Date:** 2026-03-05
**Status:** Implemented
**Related:**
- [ADR-063: Activity Log](../../adr/archive/ADR-063-activity-log-four-layer-model.md)
- [Activity Feature Doc](../../features/activity.md)

---

## Problem

The activity page rendered a flat list of up to 500 events with no temporal structure. Clicking any item navigated directly to a related page (agent workspace, context page, memory) with no preview of what happened — the redirect felt ambiguous because the user lost context of the activity that triggered it.

Rich metadata (strategy, error messages, item counts, tool usage) existed per event but was never surfaced.

---

## Changes

### 1. Date-grouped list with progressive loading

Activities are grouped by date ("Today", "Yesterday", "Mar 3") with sticky headers. Initial render shows 50 items; a "Load more" button reveals the next batch of 50.

Backend fetch unchanged (500 items, 30 days). Pagination is client-side via `visibleCount` state — appropriate given the volume (~20-40 events/day per user).

```
┌─────────────────────────────────────────────┐
│ TODAY                                       │
├─────────────────────────────────────────────┤
│ ▶ Weekly Digest v3 delivered        2h ago  │
│   Synced gmail: 12 items            3h ago  │
│   Chat turn complete                5h ago  │
├─────────────────────────────────────────────┤
│ YESTERDAY                                   │
├─────────────────────────────────────────────┤
│   Noted: prefers bullet points      1d ago  │
│   ...                                       │
└─────────────────────────────────────────────┘
         [ Load more (42 remaining) ]
```

### 2. Expandable detail rows

Click a row to expand inline detail panel showing:
- **Metadata details** per event type (strategy, type, version, status, error, items synced, tools used, etc.)
- **Absolute timestamp** ("Mar 3, 2026 9:15 AM")
- **Explicit navigation link** ("View agent", "View gmail context", etc.)

This replaces the previous click-to-navigate behavior. Navigation is now a deliberate second step inside the expanded panel.

```
┌─────────────────────────────────────────────┐
│ ▶ Weekly Digest v3 delivered    ▲   2h ago  │
├─────────────────────────────────────────────┤
│   Strategy    scheduled_recurring           │
│   Type        digest                        │
│   Version     v3                            │
│   Status      delivered                     │
│   Mar 3, 2026 9:15 AM                       │
│   View agent →                        │
└─────────────────────────────────────────────┘
```

The chevron icon rotates 180 degrees on expand (same pattern as `UserMemoryPanel`, `DocumentList`).

---

## What was deleted

| Item | Reason |
|------|--------|
| `handleActivityClick()` function | Navigation moved into expanded detail panel via `getNavigationTarget()` helper |
| Flat `filteredActivities.map()` render | Replaced by date-grouped render with `groupByDate()` |

---

## Implementation

Single file change: `web/app/(authenticated)/activity/page.tsx`

**New helpers** (pure functions, outside component):
- `groupByDate(items)` — groups `ActivityItem[]` into `{ label, items }[]` using `isToday`/`isYesterday`/`format` from date-fns
- `getNavigationTarget(item)` — returns `{ href, label }` for the expanded panel nav link (replaces `handleActivityClick`)

**New state**:
- `visibleCount` (number) — tracks how many items to render, incremented by `PAGE_SIZE` (50)
- `expandedIds` (Set\<string\>) — tracks which activity rows are expanded

**Both reset on filter change** via `handleFilterChange()`.

**Metadata detail renderer** (`renderMetadataDetails`): switch on `event_type` with type-specific field rendering. Unknown event types render all metadata keys generically.

---

## Patterns reused

- `Set<string>` expand toggle: `web/components/UserMemoryPanel.tsx`
- `ChevronDown` rotation: `UserMemoryPanel`, `DocumentList`, `system/page.tsx`
- `cn()` conditional classes: `web/lib/utils`
- date-fns (`format`, `isToday`, `isYesterday`, `startOfDay`): already a project dependency
