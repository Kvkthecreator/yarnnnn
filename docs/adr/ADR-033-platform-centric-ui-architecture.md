# ADR-033: Platform-Centric UI Architecture

> **Status**: Accepted
> **Created**: 2026-02-09
> **Decision**: Option C (Hybrid) - Platform-aware Dashboard with progressive drill-down
> **Related**: ADR-032 (Platform-Native Frontend Architecture), ADR-031 (Platform-Native Deliverables)

---

## Context

ADR-032 established the platform-first mental model:

> "Users think in platforms, not synthesis engines. The frontend should match this mental model."

The backend now implements:
- Platform-centric draft delivery (Gmail Drafts, Slack DMs, Notion DB)
- Cross-platform synthesis with deduplication
- Project-to-resource mapping
- Multi-destination delivery

**The open question**: How should the UI surface this platform-first model?

### Current State

```
Navigation:
├── Dashboard (empty desk)
├── Context (memories browser with platform badges)
├── Docs (documents list)
└── Settings

Deliverables: Flat list, filterable by status (active/paused)
Projects: Implicit grouping (deliverables belong to projects)
Platforms: Shown as badges, no dedicated views
```

**Gap**: Users can see platform badges on memories, but cannot:
- View all context from a specific platform
- See all deliverables targeting a specific platform
- Manage platform resources in one place
- Understand "what does YARNNN know from my Slack?"

---

## The Core Question

**Where should users see platform-specific context and manage platform-specific deliverables?**

Two approaches under consideration:

| Aspect | Option A: Dashboard Revamp | Option B: Per-Platform Surfaces |
|--------|---------------------------|--------------------------------|
| **Entry point** | Dashboard with platform cards | New nav items per platform |
| **Forest view** | Dashboard shows all platforms | Context page shows all platforms |
| **Tree view** | Click card → platform detail | `/context/slack`, `/context/gmail` |
| **Deliverables** | Stay separate, filter by platform | Nested under target platform |
| **Mental model** | "My workspace has these platforms" | "I work in Slack, Gmail, Notion" |

---

## Option A: Dashboard Revamp

### Concept

Dashboard becomes the "forest view" - a unified workspace showing all connected platforms.

```
┌─────────────────────────────────────────────────────────────────┐
│  Dashboard                                              [+ Add] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ 🔷 Slack    │  │ 📧 Gmail    │  │ 📝 Notion   │             │
│  │             │  │             │  │             │             │
│  │ 3 channels  │  │ 2 labels    │  │ 5 pages     │             │
│  │ 142 msgs/7d │  │ 23 emails   │  │ shared      │             │
│  │             │  │             │  │             │             │
│  │ 2 scheduled │  │ 1 scheduled │  │ 0 scheduled │             │
│  │ deliveries  │  │ delivery    │  │ deliveries  │             │
│  │             │  │             │  │             │             │
│  │ [View →]    │  │ [View →]    │  │ [View →]    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┤
│  │ ⏰ Upcoming Deliveries                                      │
│  ├─────────────────────────────────────────────────────────────┤
│  │ • Weekly Status → #leadership (Slack)      Tomorrow 4pm    │
│  │ • Project Digest → sarah@co.com (Gmail)    Friday 9am      │
│  │ • Sprint Notes → /Engineering (Notion)     Monday 10am     │
│  └─────────────────────────────────────────────────────────────┘
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┤
│  │ 📋 Attention (3 drafts ready)                    [Review →] │
│  └─────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

### Click Platform Card → Platform Detail View

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Dashboard  /  🔷 Slack                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Connected Workspace: Acme Corp (T1234567)                     │
│  Status: ✅ Active                                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┤
│  │ Resources (Channels)                             [Refresh] │
│  ├─────────────────────────────────────────────────────────────┤
│  │ #engineering        │ 89 members │ ████████ 142 msgs/7d   │
│  │ #leadership-updates │ 12 members │ ██░░░░░░  18 msgs/7d   │
│  │ #random             │ 45 members │ ██████░░  67 msgs/7d   │
│  └─────────────────────────────────────────────────────────────┘
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┤
│  │ Deliverables Targeting Slack                                │
│  ├─────────────────────────────────────────────────────────────┤
│  │ Weekly Status Update → #leadership-updates    Fridays 4pm  │
│  │ Engineering Digest   → #engineering           Daily 9am    │
│  └─────────────────────────────────────────────────────────────┘
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┤
│  │ Recent Context (from Slack)                      [View All] │
│  ├─────────────────────────────────────────────────────────────┤
│  │ "Decided to use PostgreSQL for the new service" - #eng     │
│  │ "Alice is taking over the API migration" - #engineering    │
│  │ "Launch date moved to March 15" - #leadership-updates      │
│  └─────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

### Pros

1. **Single entry point**: Dashboard is the home, platforms are sections
2. **Holistic view**: See all platforms at once, compare activity
3. **Familiar pattern**: Similar to "workspace overview" UX
4. **Minimal nav change**: Keep existing Context/Docs/Settings, enhance Dashboard

### Cons

1. **Dashboard overload**: Could become cluttered with many platforms
2. **Two-level deep**: Dashboard → Platform → Resource → Deliverable
3. **Deliverables fragmented**: Still need separate deliverables list view
4. **Project relationship unclear**: Where do projects fit?

---

## Option B: Per-Platform Surface Layers

### Concept

Each platform gets its own first-class surface in navigation. The platform surface shows everything related to that platform: resources, context, and deliverables.

```
Navigation:
├── Dashboard (attention queue + cross-platform summary)
├── Slack (Slack-specific context + deliverables)
├── Gmail (Gmail-specific context + deliverables)
├── Notion (Notion-specific context + deliverables)
├── Docs (user documents, not platform imports)
└── Settings
```

### Platform Surface Example (Slack)

```
┌─────────────────────────────────────────────────────────────────┐
│  🔷 Slack                                          [⚙️ Manage] │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┬──────────────────────────────────────────┤
│  │ Channels         │ #engineering                             │
│  │                  ├──────────────────────────────────────────┤
│  │ #engineering  ●  │ 142 messages in last 7 days              │
│  │ #leadership      │                                          │
│  │ #random          │ Key Context:                             │
│  │                  │ • "Decided to use PostgreSQL..."         │
│  │ ─────────────    │ • "Alice taking over API migration"      │
│  │ + Add channel    │ • "Sprint demo Thursday 2pm"             │
│  │                  │                                          │
│  │                  ├──────────────────────────────────────────┤
│  │                  │ Deliverables → #engineering              │
│  │                  │                                          │
│  │                  │ • Engineering Daily Digest   [Edit]      │
│  │                  │   Daily at 9am                           │
│  │                  │                                          │
│  │                  │ [+ New deliverable to #engineering]      │
│  │                  │                                          │
│  └──────────────────┴──────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

### Navigation Structure

```
Slack (platform surface)
├── Resources (channels)
│   ├── #engineering
│   │   ├── Context (messages extracted)
│   │   └── Deliverables targeting this channel
│   ├── #leadership-updates
│   │   ├── Context
│   │   └── Deliverables
│   └── + Add channel
└── All Slack Deliverables (cross-channel view)

Gmail (platform surface)
├── Resources (labels)
│   ├── Work/Important
│   │   ├── Context
│   │   └── Deliverables
│   └── + Add label
└── All Gmail Deliverables

Notion (platform surface)
├── Resources (pages/databases)
│   ├── /Engineering
│   │   ├── Context
│   │   └── Deliverables
│   └── + Add page
└── All Notion Deliverables
```

### Pros

1. **Deep platform focus**: Everything about Slack in one place
2. **Deliverables co-located**: See deliverable right next to its target
3. **Clear ownership**: "These are my Slack workflows"
4. **Matches user mental model**: "I'm working in Slack mode"

### Cons

1. **Navigation explosion**: 3+ platform items in nav (grows with platforms)
2. **Cross-platform orphaned**: Where does cross-platform synthesis live?
3. **Projects unclear**: Project grouping becomes secondary
4. **Cognitive load**: User must switch between platform views

---

## First-Principles Analysis

### What is the user's primary mental model?

| User Thinking | Implication |
|---------------|-------------|
| "What's happening in my Slack?" | Platform-centric (Option B) |
| "What deliverables do I have?" | Deliverable-centric (current) |
| "What's YARNNN doing for me?" | Dashboard overview (Option A) |
| "Show me this project's context" | Project-centric |

**Reality**: Users likely oscillate between these modes. The question is which to prioritize.

### ADR-032 says "Platform-First"

> "Users don't live in YARNNN. They live in Slack, Gmail, Notion."

This suggests **Option B** (per-platform surfaces) more closely matches the stated philosophy.

**However**, ADR-032 also says:

> "Synthesis becomes invisible over time"

This suggests the UI shouldn't over-emphasize platforms once they're set up. The "where does this go" question is answered at setup time, then the user just reviews/approves.

### Data Model Implications

```
Current relationships:

User
├── user_integrations (1 per platform)
├── projects
│   ├── project_resources (maps project → platform resources)
│   └── deliverables (many per project)
└── deliverables.destinations (each deliverable → 1+ platforms)
```

**Key insight**: There's a many-to-many relationship:
- One project can have resources from multiple platforms
- One platform resource can be used by multiple projects
- One deliverable can target multiple platforms

This suggests **neither pure Option A nor B** fully captures the model.

---

## Option C: Hybrid - Platform-Aware Dashboard + Platform Drill-Down

### Concept

Dashboard remains the forest view with platform cards. Clicking a platform shows a detail panel (not a full navigation change). Deliverables stay organized by project but filterable by platform.

```
┌─────────────────────────────────────────────────────────────────┐
│  Dashboard                                                      │
├───────────────────────────────────────┬─────────────────────────┤
│                                       │                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ │  🔷 Slack Details       │
│  │ Slack ● │ │ Gmail   │ │ Notion  │ │                         │
│  │ 3 ch    │ │ 2 lbl   │ │ 5 pg    │ │  Workspace: Acme Corp   │
│  └─────────┘ └─────────┘ └─────────┘ │                         │
│                                       │  Channels:              │
│  Projects                             │  • #engineering (142)   │
│  ┌─────────────────────────────────┐ │  • #leadership (18)     │
│  │ Q1 Launch                       │ │                         │
│  │ • Weekly Status → Slack        │ │  Deliverables:          │
│  │ • Stakeholder Email → Gmail    │ │  • 2 targeting Slack    │
│  └─────────────────────────────────┘ │                         │
│  ┌─────────────────────────────────┐ │  Recent Context:        │
│  │ API Migration                   │ │  • "PostgreSQL..."      │
│  │ • Sprint Notes → Notion        │ │  • "Alice taking..."    │
│  └─────────────────────────────────┘ │                         │
│                                       │  [Full View →]          │
└───────────────────────────────────────┴─────────────────────────┘
```

### Key Features

1. **Dashboard is home**: Platform cards + project list coexist
2. **Platform detail panel**: Click card → side panel with details
3. **Project-organized deliverables**: Deliverables grouped by project (their owner)
4. **Platform filter**: Can filter deliverables list by target platform
5. **Full platform view**: "Full View" goes to dedicated platform page (Option B style) for deep exploration

### Navigation

```
Dashboard (home - shows platforms + projects + attention)
├── [Platform Detail Panel] (expandable side view)
└── [Full Platform View] (deep dive when needed)

Context (memories browser, current behavior)
├── Platform filter (show only Slack memories)
└── Project filter (show only Q1 Launch memories)

Deliverables (organized by project)
├── Platform filter (show only Slack-targeting)
└── Status filter (active/paused)

Settings
└── Integrations management
```

---

## Decision

**Option C (Hybrid)** is accepted.

### Rationale

1. **ADR-032 Platform-First**: Platforms are visible and prominent on Dashboard
2. **Data Model**: Respects project ownership while showing platform relationships
3. **Progressive Disclosure**: Overview → Side Panel → Full View (user controls depth)
4. **Scalability**: Doesn't add nav items per platform
5. **Supports Both Models**: Platform-specific deliverables AND cross-platform synthesizers coexist

### Key Insight: Two Types of Deliverables

The architecture must support both:

| Type | Example | Context Source | Target |
|------|---------|----------------|--------|
| **Platform-specific** | "Daily #engineering digest" | Single Slack channel | Same platform (Slack) |
| **Cross-platform synthesizer** | "Weekly status report" | Slack + Gmail + Notion | Any platform (often email) |

**Platform-specific deliverables** live naturally under their platform view.
**Cross-platform synthesizers** live under projects (their logical owner) and show in Dashboard with multi-platform badges.

### Context Boundaries via Projects

Projects serve as **context boundaries**:
- A project defines which resources are relevant together
- Cross-platform synthesis happens within project boundaries
- This prevents "everything everywhere" noise
- Recursive context building accumulates within project scope

```
Project: Q1 Product Launch
├── Slack: #product-launch, #engineering
├── Gmail: label:product-launch
├── Notion: /Q1-Launch-Planning
└── Deliverables:
    ├── Weekly Status (synthesizer) → Leadership email
    ├── Daily Slack Digest → #product-launch
    └── Sprint Notes → Notion /Q1-Launch-Planning
```

---

## Implementation Phases

### Phase 1: Dashboard Platform Cards

**Goal**: Show the forest - what platforms are connected, what's happening.

**Components**:
- `PlatformCardGrid` - Grid of connected platform cards
- `PlatformCard` - Individual card showing:
  - Platform icon + name
  - Connection status (connected/error/expired)
  - Resource count (3 channels, 2 labels, 5 pages)
  - Activity indicator (142 msgs/7d)
  - Deliverable count targeting this platform
- Click → opens `PlatformDetailPanel` (side drawer)

**Data Requirements**:
- `GET /api/integrations/summary` - Returns all integrations with:
  - Connection status
  - Resource counts from landscape
  - Deliverable counts (query by destination.platform)
  - Recent activity stats (from ephemeral_context)

**UI Location**: Dashboard surface, above or alongside project list

### Phase 2: Platform Detail Panel

**Goal**: Show the trees without leaving Dashboard context.

**Components**:
- `PlatformDetailPanel` - Slide-out drawer showing:
  - Connection info (workspace name, connected date)
  - Resources list (channels/labels/pages)
  - Per-resource activity sparkline
  - Deliverables targeting this platform
  - Recent context snippets
  - "Full View →" link

**Interactions**:
- Click resource → filter context to that resource
- Click deliverable → navigate to deliverable detail
- "Full View" → navigate to full platform surface

### Phase 3: Platform Filters

**Goal**: Let users slice existing views by platform.

**Changes**:
- `ContextBrowserSurface` - Add platform filter dropdown
  - Filter memories by `source_ref.platform`
  - Show platform badge on each memory
- `DeliverableListSurface` - Add platform filter
  - Filter by `destination.platform` OR `destinations[].platform`
  - Show "multi-platform" badge for synthesizers
- URL params: `?platform=slack` persists filter

### Phase 4: Full Platform View

**Goal**: Deep platform management for power users.

**Surface**: `platform-detail` with `?platform=slack`

**Features**:
- Full resource list with detailed stats
- Import history per resource
- Coverage state visualization (covered/partial/stale)
- All deliverables targeting this platform
- All context from this platform
- Manage: refresh landscape, disconnect, re-auth

### Phase 5: Project-Resource Mapping UI

**Goal**: Show and edit which resources feed which projects.

**Components**:
- `ProjectResourcesSection` in ProjectDetailSurface
  - Shows linked resources grouped by platform
  - Coverage indicator per resource
  - Add/remove resource controls
- `ResourceSuggestions` - Auto-suggest based on name matching
- Cross-platform context summary:
  - "142 Slack messages + 23 emails + 5 Notion updates"
  - Overlap score (deduplication efficiency)
  - Freshness score (data recency)

### Phase 6: Cross-Platform Synthesizer UI

**Goal**: First-class creation flow for synthesizers.

**Flow**:
1. "New Deliverable" → Type selector includes "Cross-Platform Summary"
2. Select project (defines context boundary)
3. Review auto-suggested resources (from project_resources)
4. Add/remove sources
5. Select destination(s) - can target multiple platforms
6. Set schedule

**Display**:
- Synthesizers show multi-platform badge in lists
- Show in Dashboard "Upcoming" section
- Show context coverage stats on version detail

---

## Open Questions

1. **Projects vs Platforms as primary organizer**: Should deliverables be listed under projects (current) or under their target platform?
   - **Recommendation**: Keep project-organized, add platform filter

2. **Where does cross-platform synthesis show?**: A deliverable that synthesizes Slack+Gmail belongs to... which platform view?
   - **Recommendation**: Show in both, with "cross-platform" badge

3. **Attention queue**: Should platform detail show only that platform's staged items?
   - **Recommendation**: Yes, filter attention queue by platform when in platform view

4. **Mobile considerations**: Platform cards work on mobile, but side panels don't
   - **Recommendation**: On mobile, card click goes to full platform view

---

## Appendix: Component Changes by Option

### Option A (Dashboard Revamp)

| Component | Change |
|-----------|--------|
| `Dashboard` page | Add platform cards, upcoming deliveries |
| New: `PlatformCard` | Platform summary card |
| New: `PlatformDetailSurface` | Full platform view |
| `DeliverableListSurface` | Add platform filter |
| `DeskContext` | Add `selectedPlatform` state |

### Option B (Per-Platform Surfaces)

| Component | Change |
|-----------|--------|
| `AuthenticatedLayout` | Add platform nav items |
| New: `SlackSurface` | Full Slack management |
| New: `GmailSurface` | Full Gmail management |
| New: `NotionSurface` | Full Notion management |
| `SurfaceRouter` | Add platform surface types |
| Remove separate Deliverables list? | Nested under platforms |

### Option C (Hybrid)

| Component | Change |
|-----------|--------|
| `Dashboard` page | Add platform cards |
| New: `PlatformCard` | Platform summary card |
| New: `PlatformDetailPanel` | Side panel for platform |
| New: `PlatformDetailSurface` | Full view (optional drill-down) |
| `ContextBrowserSurface` | Add platform filter |
| `DeliverableListSurface` | Add platform filter |
| `DeskContext` | Add `platformFilter` state |

---

## References

- [ADR-032: Platform-Native Frontend Architecture](./ADR-032-platform-native-frontend-architecture.md)
- [ADR-031: Platform-Native Deliverables](./ADR-031-platform-native-deliverables.md)
- [ADR-028: Destination-First Deliverables](./ADR-028-destination-first-deliverables.md)
