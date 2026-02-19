# ADR-066: Deliverable Detail Page Redesign — Output-First with Inline Review

**Status**: Proposed
**Date**: 2026-02-19
**Relates to**: ADR-063 (Four-Layer Model), ADR-042 (Deliverable Execution)

---

## Context

The current deliverable detail page (`/deliverables/[id]`) has accumulated features that fragment the user's workflow across multiple surfaces:

1. **Detail page** — Shows metadata, stats, version history
2. **Settings modal** — Configuration (title, schedule, sources, destination)
3. **Review page** (`/dashboard/deliverable/[id]/review/[versionId]`) — View and approve/reject output

This structure creates friction for the most common user action: **reviewing and approving generated output**.

### Current Problems

**High-frequency actions are buried:**
- Reviewing output requires 2 clicks (detail page → version → review page)
- Approve/reject buttons live on a separate route
- User must navigate away from the deliverable to see what it produced

**Low-frequency actions are prominent:**
- "Quality %" metric with unclear meaning
- "Run Now" as a giant button, even when versions are pending review
- Trend indicators (improving/declining) without actionable context

**Settings modal is overloaded:**
- Mixes identity (title) with operational config (schedule, sources)
- "Data Sources" only shows URL input — disconnected from connected platforms
- "Recipient Context" is vague and redundant with destination

**Information architecture mismatch:**
The UI treats a deliverable as a configuration object. Users think of it as "a thing YARNNN makes for me that I sometimes need to review."

---

## Decision: Output-First with Inline Review

Redesign the deliverable detail page around the **latest generated output**, with inline review actions. Merge the review functionality into the detail page.

### Core Principle

> The deliverable detail page answers: "What did YARNNN make, and is it good?"

Configuration and history are secondary.

---

## New Page Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ ← Back to Deliverables                            ⏸ Pause   ⚙   │
│                                                                 │
│ Competitive Research Brief                                      │
│ Weekly on Monday at 09:00 → Slack #research                     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─ Latest Output ───────────────────────────────────────────┐   │
│ │                                                           │   │
│ │  v2 · Feb 19, 8:49 AM · ● Pending Review                  │   │
│ │                                                           │   │
│ │  ┌───────────────────────────────────────────────────┐    │   │
│ │  │                                                   │    │   │
│ │  │  [Generated content rendered here - markdown]     │    │   │
│ │  │                                                   │    │   │
│ │  │  - Competitor A launched new feature...           │    │   │
│ │  │  - Market trend: 15% increase in...               │    │   │
│ │  │                                                   │    │   │
│ │  └───────────────────────────────────────────────────┘    │   │
│ │                                                           │   │
│ │  Sources: Slack #general (47 msgs) · Gmail (12 emails)    │   │
│ │                                                           │   │
│ │  ┌──────────────┐  ┌──────────────┐                       │   │
│ │  │  ✓ Approve   │  │  ✗ Reject    │                       │   │
│ │  └──────────────┘  └──────────────┘                       │   │
│ │                                                           │   │
│ │  [Optional feedback input on reject]                      │   │
│ │                                                           │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─ Previous Versions ───────────────────────────────────────┐   │
│ │  ▸ v1 · Feb 19, 8:48 AM · Staged                          │   │
│ │  ▸ v0 · Feb 12, 9:00 AM · Approved                        │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─ Schedule ────────────────────────────────────────────────┐   │
│ │  Next run: Wed, Feb 25 at 09:00 AM (6 days)               │   │
│ │  [Run Now]                                                │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Changes

### 1. Inline Latest Output

The most recent version's content is displayed directly on the page — no click-through required.

- Render `draft_content` or `final_content` as markdown
- Show version number, timestamp, status prominently
- If content is long (>500 words), show truncated with "Show full" expander

### 2. Inline Approve/Reject

Review actions move from the separate review page to the detail page.

- Approve: Progresses status to `approved`, triggers delivery
- Reject: Prompts for optional feedback, marks as `rejected`
- Both actions update the UI immediately

### 3. Source Attribution

Show what data fed the generation, pulled from `source_snapshots`:

```
Sources: Slack #general (47 msgs, synced 2h ago) · Gmail/Inbox (12 emails)
```

This gives users confidence in what informed the output.

### 4. Collapsible Previous Versions

Version history becomes an expandable list. Clicking a previous version shows its content inline (accordion-style), not a navigation.

### 5. Simplified Header

Remove:
- Quality % and trend indicators (unclear value)
- Status cards grid (Next Run / Quality / Status)

Keep:
- Title + subtitle (schedule + destination)
- Pause/Resume toggle
- Settings gear

### 6. "Run Now" Demoted

Move "Run Now" to a smaller button in the Schedule section, not a full-width CTA. The primary action is reviewing pending output, not generating more.

Show "Run Now" only when:
- No versions exist yet, OR
- No versions are pending review (all approved/rejected)

---

## Settings Modal Simplification

The modal becomes purely about configuration, not identity:

### Remove
- Title field (edit inline on page header, or keep in modal — low priority)
- "Recipient Context" section (redundant with destination)
- Quality-related fields (if any)

### Simplify
- **Destination**: Keep as-is (platform + format)
- **Schedule**: Keep as-is (frequency + day + time)
- **Data Sources**: Show connected platform sources (channels, labels, pages) instead of URL-only input
  - Dropdown: "Slack #channel", "Gmail label:X", "Notion page"
  - URL input as secondary option

### Keep
- Archive action (with confirmation)

---

## Routes

### Delete
- `/dashboard/deliverable/[id]/review/[versionId]` — functionality merged into detail page

### Modify
- `/deliverables/[id]` — becomes the output-first review page

---

## Implementation Phases

### Phase 1: Inline Output + Review Actions
1. Fetch latest version with content in `loadDeliverable()`
2. Render content as markdown in a new `LatestOutput` component
3. Add Approve/Reject buttons with API calls
4. Update version status in UI on action
5. Remove Quality/Status cards, simplify header

### Phase 2: Version History Accordion
1. Replace click-through version list with expandable rows
2. Lazy-load version content on expand
3. Show source_snapshots per version

### Phase 3: Settings Modal Cleanup
1. Remove Recipient Context section
2. Add platform source picker alongside URL input
3. Clean up layout

### Phase 4: Remove Review Route
1. Delete review page and route
2. Update all navigation references
3. Redirect old URLs to detail page

---

## What This Enables

- **Faster review cycle**: See output and approve in one view
- **Better context**: Source attribution visible alongside content
- **Cleaner mental model**: One page per deliverable, not three surfaces
- **Mobile-friendly**: Single scrollable page vs. multi-step navigation

---

## What This Removes

| Removed | Reason |
|---------|--------|
| Quality % metric | Unclear definition, no actionable insight |
| Trend indicators | Same — can reintroduce when meaningful |
| Separate review route | Merged into detail page |
| Recipient Context field | Redundant with destination |
| Giant "Run Now" button | Demoted — review is the primary action |

---

## Open Questions

### Resolved
- **Multiple staged versions**: Show the latest. Previous are in history.
- **Long content**: Truncate with "Show full" expander.

### Deferred
- **Edit before approve**: Keep as future feature. Users can reject with feedback, regenerate.
- **Diff view between versions**: Valuable but not in initial scope.
- **Inline title editing**: Nice-to-have, can keep in modal for now.

---

## Migration

No database changes required. This is purely a frontend restructure.

Existing review page URLs (`/dashboard/deliverable/[id]/review/[versionId]`) should redirect to `/deliverables/[id]` after Phase 4.

---

## Related

- [ADR-063](ADR-063-activity-log-four-layer-model.md) — Four-layer model (Work layer definition)
- [ADR-042](ADR-042-deliverable-execution-simplification.md) — Deliverable execution pipeline
- [docs/features/deliverables.md](../features/deliverables.md) — Deliverables layer documentation
- `web/app/(authenticated)/deliverables/[id]/page.tsx` — Current detail page
- `web/components/modals/DeliverableSettingsModal.tsx` — Current settings modal
