# Design Spec: Tab-Based Supervision UI

> **⚠️ LEGACY DOCUMENT**
> This design was superseded by [ADR-023: Supervisor Desk Architecture](../adr/ADR-023-supervisor-desk-architecture.md).
> The tab-based approach was abandoned in favor of a simpler single-surface "desk" model.
> Kept for historical reference only.

**Status:** Superseded
**Date:** 2026-02-02
**Superseded By:** ADR-023 (Supervisor Desk Architecture)
**Supersedes:** ADR-021 (Review-First Supervision UX) - extends and refines
**Inspired By:** Claude Code IDE patterns, legacy CHAT_FIRST_ARCHITECTURE

---

## Executive Summary

YARNNN's UI should function like an IDE where:
- **TP (Thinking Partner)** is the constant command interface (like Claude in Claude Code)
- **Tabs** are the documents/artifacts being supervised (like files in an IDE)
- **Content types** determine tab rendering (like file types determine syntax highlighting)
- **TP persists across tabs** - unlike IDE where AI is in sidebar, TP is always the interaction layer

---

## Part 1: Core Architecture

### 1.1 The Three Layers

```
┌─────────────────────────────────────────────────────────────────┐
│ CHROME: Tab bar, status indicators, user menu                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ CONTENT: The active tab's content (varies by tab type)          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ TP LAYER: Input, quick actions, contextual to active tab        │
└─────────────────────────────────────────────────────────────────┘
```

**Chrome** - Minimal, persistent navigation
**Content** - Tab-specific rendering based on content type
**TP Layer** - Always present, context-aware interaction

### 1.2 Tab Types (Content Types)

Every openable thing in YARNNN is a tab with a specific type:

| Tab Type | Icon | Content Rendering | TP Context |
|----------|------|-------------------|------------|
| `deliverable` | 📋 | Deliverable detail + version history | "This deliverable" |
| `version-review` | ✏️ | Editable draft content + refinement | "This draft" |
| `memory` | 🧠 | Memory content viewer/editor | "This memory" |
| `context` | 📚 | Context item detail | "This context" |
| `document` | 📄 | Uploaded document viewer | "This document" |
| `profile` | 👤 | User profile/preferences | "Your settings" |
| `home` | 🏠 | Dashboard/overview (special) | "Your deliverables" |

### 1.3 Tab Behavior

**Opening tabs:**
- TP mentions item inline → click opens tab
- Dock indicator click → opens relevant tab
- Deep link/URL → opens tab directly

**Tab management:**
- Reorderable (drag and drop)
- Closeable (× button)
- Maximum tabs (suggest 8, graceful handling beyond)
- Pinnable (home tab always first?)

**Tab state:**
- Unsaved changes indicator (dot)
- Loading state (spinner in tab)
- Error state (red indicator)
- Notification badge (needs attention)

---

## Part 2: TP Layer Design

### 2.1 TP Persistence Across Tabs

Unlike Claude Code where Claude is in a sidebar, TP is the **bottom layer** that persists:

```
┌─────────────────────────────────────────────────────────────────┐
│ [Home] [Weekly Status ×] [Memory: Preferences ×]                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Tab content changes based on active tab]                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ TP knows: "You're viewing Weekly Status Report"                 │
│ [Shorter] [Run now] [Show history]           [Custom input...]  │
└─────────────────────────────────────────────────────────────────┘
```

**Key difference from IDE:** TP input travels with you. You don't "switch to chat mode."

### 2.2 Context-Aware Quick Actions

Quick actions change based on active tab type:

| Tab Type | Quick Actions |
|----------|---------------|
| `home` | [Create new] [What's due] [Run all] |
| `deliverable` | [Run now] [Edit schedule] [Pause] |
| `version-review` | [Shorter] [More detail] [Approve] [Discard] |
| `memory` | [Edit] [Delete] [Link to deliverable] |
| `context` | [Summarize] [Extract key points] [Delete] |
| `document` | [Summarize] [Extract to memory] [Delete] |

### 2.3 TP Response Patterns

When TP responds, content appears **inline** with appropriate rendering:

**Short response:** Text only
```
TP: Done! I've updated the schedule to run on Tuesdays.
```

**Action result:** Collapsed card
```
TP: I've generated a new version.
┌─────────────────────────────────────────────────────────────┐
│ ✓ Version 13 generated                        [Open in tab] │
└─────────────────────────────────────────────────────────────┘
```

**Content preview:** Expandable card
```
TP: Here's the shortened version:
┌─────────────────────────────────────────────────────────────┐
│ Hi Sarah,                                                   │
│ Key updates this week:                                      │
│ • Sprint velocity up 10%                                    │
│ • Bug count down to 12                                      │
│ [Show full] [Apply to draft] [Open in tab]                  │
└─────────────────────────────────────────────────────────────┘
```

**Multi-item result:** Summary card
```
TP: Found 5 related memories.
┌─────────────────────────────────────────────────────────────┐
│ 📚 5 context items                            [View all →]  │
│ • Competitor Analysis (most relevant)                       │
│ • Q4 Goals                                                  │
│ • Team Structure                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 3: Claude Code Pattern Analysis

### 3.1 What Claude Code Does Well

| Pattern | How Claude Code Does It | YARNNN Adaptation |
|---------|------------------------|-------------------|
| **Inline progress** | "Reading file..." with spinner, collapses when done | "Generating..." with spinner, collapses to result card |
| **Tool results** | Brief summary, expandable details | Same - card with [Show details] |
| **Todo tracking** | Persistent todo list, real-time updates | Review queue as persistent indicator |
| **File references** | `filename:line` clickable links | `[Deliverable Name]` clickable → opens tab |
| **Error handling** | Inline error with context, retry option | Same pattern |
| **Loading states** | Skeleton → content transition | Same pattern |
| **Collapse long output** | Auto-collapse with "Show more" | Same - content preview with expand |

### 3.2 Information Density Levels

Claude Code uses three density levels:

**Inline (in message flow):**
- Brief status: "Done", "Failed", "3 files changed"
- No interaction needed for basic understanding

**Card (embedded but distinct):**
- Action results with details
- Preview content
- Clickable to expand or open

**Full view (tab/panel):**
- Complete content
- Full editing capability
- Deep inspection

**YARNNN should mirror this:**
```
Inline:     "Version 13 ready for review"
Card:       [Version preview with Approve/Open actions]
Full view:  [Tab with complete draft, editing, history]
```

### 3.3 State Indicators

Claude Code's visual language:

| State | Visual | YARNNN Equivalent |
|-------|--------|-------------------|
| Working | Spinner + description | Same |
| Success | ✓ checkmark, green | Same |
| Error | ✗ red, retry option | Same |
| Pending | Pulsing dot | Badge on tab/dock |
| Changed | Dot indicator | Unsaved dot on tab |

---

## Part 4: Tab Content Specifications

### 4.1 Home Tab (Dashboard)

The default/fallback tab when nothing specific is open.

```
┌─────────────────────────────────────────────────────────────────┐
│ [🏠 Home ×]                                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Good morning, Kevin                                            │
│                                                                 │
│  ┌─ Needs attention ─────────────────────────────────────────┐  │
│  │ 📋 Weekly Status Report - v12 ready for review            │  │
│  │    [Review now →]                                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Upcoming                                                       │
│  • Monthly Investor Update — Feb 15                             │
│  • Competitive Brief — Feb 10                                   │
│                                                                 │
│  Recent                                                         │
│  • Weekly Status v11 - approved yesterday                       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ [Create new] [What's due] [Run all]        [...              ]  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Deliverable Tab

View/manage a specific deliverable.

```
┌─────────────────────────────────────────────────────────────────┐
│ [🏠] [📋 Weekly Status ×]                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Weekly Status Report                          [Run now] [⏸]   │
│  📅 Weekly on Mondays at 9:00am                                 │
│  👤 Sarah (VP Marketing)                                        │
│                                                                 │
│  ┌─ Latest: v12 (staged) ────────────────────────────────────┐  │
│  │ Hi Sarah,                                                 │  │
│  │ Here's the weekly update...                               │  │
│  │ [Preview - 3 lines]                                       │  │
│  │                                         [Review draft →]  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Quality: 87% match (improving ↑)                               │
│                                                                 │
│  History                                                        │
│  ├─ v11 - approved Jan 27 - 85% match                          │
│  ├─ v10 - approved Jan 20 - 82% match                          │
│  └─ [Show all 12 versions]                                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ [Run now] [Edit schedule] [Pause]          [...              ]  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Version Review Tab

Edit/refine a specific version (the primary supervision action).

```
┌─────────────────────────────────────────────────────────────────┐
│ [🏠] [📋 Weekly Status] [✏️ Review v12 ×]                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Hi Sarah,                                                 │  │
│  │                                                           │  │
│  │ Here's the weekly update for Project Alpha:               │  │
│  │                                                           │  │
│  │ ## Key Metrics                                            │  │
│  │ - Sprint velocity: 42 points (↑ from 38)                  │  │
│  │ - Bug count: 12 open (↓ from 15)                          │  │
│  │ ...                                                       │  │
│  │                                                           │  │
│  │ [Editable content area]                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [Copy] [Download]                      [Discard] [✓ Approve]   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ [Shorter] [More detail] [More formal]  [Tell me what to fix...] │
└─────────────────────────────────────────────────────────────────┘
```

### 4.4 Memory Tab

View/edit a memory item.

```
┌─────────────────────────────────────────────────────────────────┐
│ [🏠] [🧠 Writing Preferences ×]                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Writing Preferences                                   [Edit]   │
│  🏷️ Type: User preference                                       │
│  📅 Created: Jan 15, 2026                                       │
│  🔗 Used by: Weekly Status, Investor Update                     │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ - Prefer bullet points over paragraphs                    │  │
│  │ - Executive tone, not casual                              │  │
│  │ - Always include metrics when available                   │  │
│  │ - Keep updates under 500 words                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Used in 8 deliverable generations                              │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ [Edit] [Delete] [Link to deliverable]  [...                  ]  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.5 Context Tab

View a context/knowledge item.

```
┌─────────────────────────────────────────────────────────────────┐
│ [🏠] [📚 Competitor Analysis ×]                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Competitor Analysis - Q1 2026                                  │
│  📄 Source: competitor_analysis.pdf                             │
│  📅 Added: Jan 10, 2026                                         │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ [Full extracted content from document]                    │  │
│  │                                                           │  │
│  │ Key competitors identified:                               │  │
│  │ 1. Company A - Market leader, $50M ARR                    │  │
│  │ 2. Company B - Fast-growing startup                       │  │
│  │ ...                                                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ [Summarize] [Extract key points] [Delete] [...               ]  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 5: Mobile Adaptation

### 5.1 Core Constraints

Mobile gets a **simplified but functional** version:

- **Single tab visible** (no tab bar, use navigation instead)
- **TP as bottom sheet** (collapsible)
- **Swipe gestures** for tab switching
- **Essential actions only** in quick actions

### 5.2 Mobile Layout

```
┌─────────────────────────────────────┐
│ ← Weekly Status Report      [···]   │  ← Header with back + menu
├─────────────────────────────────────┤
│                                     │
│  [Tab content, full width]          │
│                                     │
│                                     │
│                                     │
├─────────────────────────────────────┤
│ ▲ TP                        [Send]  │  ← Collapsed TP (tap to expand)
└─────────────────────────────────────┘

Expanded TP (bottom sheet):
┌─────────────────────────────────────┐
│ ═══════════════                     │  ← Drag handle
│                                     │
│ [Shorter] [More detail] [Approve]   │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Ask TP...                       │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Recent:                             │
│ "Make it shorter" - 2 min ago       │
│                                     │
└─────────────────────────────────────┘
```

### 5.3 Mobile Navigation

Instead of tabs, use a navigation stack:

```
Home → Deliverable → Review
  ←       ←           ←
```

Swipe right to go back. Menu (···) shows:
- Switch to other open items
- Close current
- Home

---

## Part 6: Implementation Phases

### Phase 1: Core Tab Infrastructure
- [ ] Tab bar component with open/close/reorder
- [ ] Tab state management (open tabs, active tab)
- [ ] URL routing for tabs (`/dashboard?tab=del_123`)
- [ ] Tab type registry and renderers

### Phase 2: TP Layer Refactor
- [ ] Move TP from embedded/floating to persistent bottom layer
- [ ] Context-aware quick actions based on active tab
- [ ] TP response card system (inline, card, full)
- [ ] Remove EmbeddedTPInput (replaced by unified TP layer)

### Phase 3: Content Type Renderers
- [ ] Home tab renderer
- [ ] Deliverable tab renderer
- [ ] Version review tab renderer
- [ ] Memory tab renderer
- [ ] Context tab renderer

### Phase 4: Mobile Adaptation
- [ ] Bottom sheet TP component
- [ ] Single-tab mobile layout
- [ ] Navigation stack instead of tabs
- [ ] Swipe gestures

### Phase 5: Polish
- [ ] Tab state indicators (unsaved, loading, error)
- [ ] Smooth transitions between tabs
- [ ] Keyboard shortcuts (Cmd+W close, Cmd+1-9 switch)
- [ ] Tab overflow handling

---

## Part 7: Open Questions

1. **Tab persistence:** Should open tabs persist across sessions? (Probably yes)
2. **Tab limits:** Hard limit on tabs, or graceful degradation?
3. **Split view:** Ever support side-by-side tabs? (Probably not for MVP)
4. **Tab groups:** Group related tabs? (Future consideration)
5. **Notifications:** How do notifications interact with tabs? (Badge + open?)

---

## Appendix: Comparison with Current Implementation

| Aspect | Current | Proposed |
|--------|---------|----------|
| Primary view | Dashboard page | Home tab |
| Deliverable view | Separate route | Deliverable tab |
| Review | Full-screen overlay | Review tab |
| TP location | Floating panel / embedded input | Persistent bottom layer |
| Navigation | Route-based pages | Tab-based with URL sync |
| Mobile | Same as desktop (problematic) | Dedicated mobile layout |

---

*This document should be reviewed and refined before implementation begins.*
