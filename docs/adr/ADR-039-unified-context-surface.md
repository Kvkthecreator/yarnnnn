# ADR-039: Unified Context Surface

> **Status**: Accepted
> **Date**: 2026-02-11
> **Deciders**: Kevin (solo founder)
> **Related**: ADR-037 (Chat-First), ADR-038 (Filesystem-as-Context)

---

## Context

ADR-038 established that YARNNN's context sources (platforms, documents, user-stated facts) are the "filesystem" that TP navigates. However, the current frontend separates these into distinct pages:

- `/integrations` — Platform connections
- `/docs` — Document uploads
- `/settings?tab=memory` — User facts (buried in settings)

This creates a false hierarchy where platforms feel primary and other sources feel secondary. Users without platform connections see an incomplete experience.

## Decision

**Unify all context sources into a single "Context" page** that feels like a file explorer (Finder/Explorer), not a settings panel.

### Navigation Change

**Before:**
```
Chat | Deliverables | Integrations | Activity | Docs | Settings
```

**After:**
```
Chat | Deliverables | Context | Activity | Settings
```

- **Chat** — Primary interaction (conversation with TP)
- **Deliverables** — Scheduled recurring outputs
- **Context** — Your "filesystem" (unified view of all sources)
- **Activity** — Execution history, job logs, recent actions
- **Settings** — Account, billing, preferences

### Context Page Design

Following Finder/Explorer mental model:

```
┌─────────────────────────────────────────────────────────────┐
│  Context                                    [+ Add Source]  │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│  SOURCES     │  All Context                    [Search...]  │
│              │  ─────────────────────────────────────────── │
│  ○ All       │                                              │
│              │  ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│  PLATFORMS   │  │ Slack   │ │ Gmail   │ │ Notion  │        │
│  ● Slack     │  │ #eng    │ │ Inbox   │ │ Specs   │        │
│  ○ Gmail     │  │ 142 msg │ │ 89 msgs │ │ 12 pgs  │        │
│  ○ Notion    │  │ 2d ago  │ │ 1d ago  │ │ 5d ago  │        │
│              │  └─────────┘ └─────────┘ └─────────┘        │
│  DOCUMENTS   │                                              │
│  ○ All Docs  │  ┌─────────┐ ┌─────────┐                    │
│              │  │ Q1.pdf  │ │ Brief   │                    │
│  FACTS       │  │ 12 pgs  │ │ .docx   │                    │
│  ○ All Facts │  │ Jan 15  │ │ Feb 2   │                    │
│              │  └─────────┘ └─────────┘                    │
│              │                                              │
│  [Connect    │  ┌─────────────────────────────────────┐    │
│   Platform]  │  │ "Prefers bullet points over prose"  │    │
│              │  │ fact • preference                    │    │
│  [Upload     │  └─────────────────────────────────────┘    │
│   Document]  │                                              │
│              │  ┌─────────────────────────────────────┐    │
│  [Add Fact]  │  │ "Reports due on Fridays"            │    │
│              │  │ fact • schedule                      │    │
│              │  └─────────────────────────────────────┘    │
│              │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

### Key Design Principles

1. **Sidebar = Source types** (like Finder's sidebar: Favorites, Locations, Tags)
2. **Main area = Content** (cards/tiles, not tables)
3. **Visual hierarchy by recency** (most recent first, with timestamps)
4. **Quick actions in sidebar** (Connect, Upload, Add — not buried)
5. **Search across all** (unified search bar)
6. **Empty states guide action** (not just "no data")

### Source Cards

Each source type has a card design:

**Platform card:**
```
┌───────────────┐
│ [Slack icon]  │
│ #engineering  │
│ 142 messages  │
│ Synced 2d ago │
│ [Sync] [View] │
└───────────────┘
```

**Document card:**
```
┌───────────────┐
│ [PDF icon]    │
│ Q1-Report.pdf │
│ 12 pages      │
│ Uploaded Jan  │
│ [View] [Del]  │
└───────────────┘
```

**Fact card:**
```
┌─────────────────────────────────────┐
│ "Prefers bullet points over prose"  │
│ preference • formatting             │
│ Added Feb 10                        │
│                              [Edit] │
└─────────────────────────────────────┘
```

### Empty State (Cold Start)

When user has no context:

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│              Your context is empty                          │
│                                                             │
│    TP works best when it knows about your work.            │
│    Add context from any of these sources:                   │
│                                                             │
│    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│    │ [Platform]  │  │ [Document]  │  │ [Keyboard]  │       │
│    │             │  │             │  │             │       │
│    │ Connect     │  │ Upload      │  │ Tell TP     │       │
│    │ Slack,      │  │ PDFs,       │  │ directly    │       │
│    │ Gmail,      │  │ docs,       │  │ in chat     │       │
│    │ Notion      │  │ notes       │  │             │       │
│    └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                             │
│    All three are equally valid — pick what fits your work. │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### What Gets Removed/Consolidated

| Old Page | Disposition |
|----------|-------------|
| `/integrations` | → `/context` (Platforms section) |
| `/integrations/[provider]` | → `/context?source=slack` (filtered view) |
| `/docs` | → `/context` (Documents section) |
| `/settings?tab=memory` | → `/context` (Facts section) |
| `/activity` | Kept as-is (execution history, job logs) |

### Routes

```
/context                    # All context (default)
/context?source=platforms   # Platforms only
/context?source=slack       # Specific platform
/context?source=documents   # Documents only
/context?source=facts       # Facts only
/context?search=quarterly   # Search results
```

## Consequences

### Positive

- **Single mental model** — "Context" is one thing, not three
- **Equal treatment** — Platforms don't feel privileged over docs/facts
- **Discoverable** — All add-context actions visible in one place
- **Familiar UX** — Finder/Explorer metaphor is well-understood
- **Cold start friendly** — Empty state guides all three paths equally

### Negative

- **Migration effort** — Need to refactor existing pages
- **URL changes** — `/integrations` and `/docs` become redirects
- **Learning curve** — Existing users need to find new location

### Neutral

- **Settings slimmed** — Settings becomes purely account/billing
- **Activity consolidated** — Moves to Deliverables as execution log

## Implementation

### Phase 1: Context Page MVP
1. Create `/context` route with sidebar + main area
2. Implement source filtering (all, platforms, documents, facts)
3. Design card components for each source type
4. Add empty state with three CTAs

### Phase 2: Migration
1. Redirect `/integrations` → `/context?source=platforms`
2. Redirect `/docs` → `/context?source=documents`
3. Remove old pages
4. Update nav component

### Phase 3: Polish
1. Add search across all sources
2. Add drag-drop for documents
3. Add inline fact editing
4. Add bulk actions (delete, sync)

---

## References

- [ADR-037: Chat-First Surface Architecture](ADR-037-chat-first-surface-architecture.md)
- [ADR-038: Filesystem-as-Context Architecture](ADR-038-filesystem-as-context.md)
- Apple Finder, Windows Explorer as UX reference
