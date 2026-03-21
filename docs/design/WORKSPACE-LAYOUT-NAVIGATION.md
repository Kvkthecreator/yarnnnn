# Workspace Layout & Navigation Architecture

**Date:** 2026-03-04 (initial), 2026-03-11 (persistent panel migration)
**Status:** Implemented — persistent panel architecture (2026-03-11)
**Authors:** Kevin Kim, Claude

**References:**
- [ADR-037: Chat-First Surface Architecture](../adr/ADR-037-chat-first-surface-architecture.md) — dashboard model being evolved
- [ADR-080: Unified Agent Modes](../adr/ADR-080-unified-agent-modes.md) — chat vs headless modes
- [ADR-087: Agent Scoped Context](../adr/ADR-087-workspace-scoping-architecture.md) — per-agent instructions + memory
- [ADR-105: Instructions to Chat Surface](../adr/ADR-105-instructions-chat-surface-migration.md) — directives flow through chat
- [Surface-Action Mapping](SURFACE-ACTION-MAPPING.md) — directive vs configuration design principle
- [Phase 3 Surface Layout (history)](archive/SURFACE-LAYOUT-PHASE3-HISTORY.md) — tabbed detail page, superseded

---

## 1. Problem (v2 — March 2026)

The original drawer overlay model (implemented 2026-03-04) had a structural issue:

| Drawer overlay model | Problem |
|---------------------|---------|
| Versions pinned above chat (InlineVersionCard) | Eats vertical space, `max-h-96` truncates long content, fights with chat |
| Drawer hidden by default | Users must click to see versions, instructions, memory — primary artifacts buried |
| Two different patterns | Dashboard: inline type cards in chat. Agent: stacked version + chat. Inconsistent. |

Benchmark: **Claude Cowork** uses a persistent right panel (always visible, ~35% width) that shows context, progress, and artifacts. The panel transforms when an artifact is selected — same surface, two modes.

---

## 2. Decision: Persistent Right Panel

Replace the sliding drawer overlay with a **persistent inline panel** that is visible by default and transforms between tab mode and version preview mode.

### Desktop (≥ lg / 1024px):
```
┌──────────────────────────────────────────────────────────────┐
│ Header: ← Agents  |  📋 Title [Mode] · Active  | [≡] │
├────────────────────────────────┬─────────────────────────────┤
│                                │  PANEL (400px, persistent)  │
│   CHAT (flex-1)                │                             │
│                                │  [Versions] [Instructions]  │
│   Messages scroll              │  [Memory] [Sessions]        │
│                                │  [Settings]                 │
│                                │  ─────────────────          │
│                                │  Tab content (scrollable)   │
│   ┌──────────────────────┐     │                             │
│   │ + input bar          │     │                             │
│   └──────────────────────┘     │                             │
├────────────────────────────────┴─────────────────────────────┤
```

### Mobile/tablet (< lg):
Same overlay drawer behavior as before — fixed, `w-full sm:w-[480px]`, backdrop dismissal.

### Panel toggle
The header toggle button collapses/expands the panel. Default is **open**. On < lg, it opens/closes the overlay.

---

## 3. Key Changes from v1

| v1 (drawer overlay) | v2 (persistent panel) |
|---------------------|----------------------|
| Fixed overlay, `z-50`, backdrop, hidden by default | Inline flex child, part of layout, visible by default |
| InlineVersionCard pinned above chat (shrink-0) | Versions live in panel — list mode + preview mode |
| `max-h-96` truncation on version content | Full-height scrollable markdown in panel, no cap |
| Drawer overlays chat — can't read version + chat simultaneously | Side-by-side: read version in panel, chat alongside |
| `panelDefaultOpen: false` | `panelDefaultOpen: true` (both dashboard + agent) |

### Deleted components
- **InlineVersionCard** — replaced by VersionsPanel with preview mode in the panel
- **VersionPreview** (old drawer version preview) — replaced by VersionPreviewFull (panel-native)
- **selectedIdx / onSelectIdx** props on AgentChatArea — version selection is now panel-internal

---

## 4. Layout Specification

### 4.1 `WorkspaceLayout` component

**File:** `web/components/desk/WorkspaceLayout.tsx`

Props:
- `identity` — icon + label + badge for header
- `breadcrumb` — optional back nav
- `headerControls` — optional right-side controls
- `children` — chat area content
- `panelTabs` — array of `{ id, label, content }` tabs
- `panelDefaultOpen` — default `true`
- `activeTabId` / `onActiveTabChange` — optional controlled tab (parent can drive)

Behavior:
- **≥ lg**: chat (flex-1) | panel (`w-[400px]`, shrink-0, border-l, inline)
- **< lg**: chat (100%) + overlay panel (fixed, `w-full sm:w-[480px]`, z-50, backdrop)
- Panel toggle in header (PanelRight / PanelRightClose icon swap)
- Escape key closes overlay panel (< lg only)
- Tab bar shared between inline and overlay modes

### 4.2 `/dashboard` — Global TP

**Panel tabs:** Agents | Context

Panel defaults open. Shows agent list (compact entry cards linking to `/agents/[id]`) and platform sync status.

### 4.3 `/agents/[id]` — Agent Workspace

**Panel tabs:** Versions | Instructions | Memory | Sessions | Settings

Panel defaults open with Versions tab. VersionsPanel has two internal modes:
1. **List mode** — compact version list with Run Now bar. Click a version to enter preview mode.
2. **Preview mode** — full markdown render with back arrow, copy, external link, feedback strip. Auto-opens to latest version.

---

## 5. Version Display Architecture

Versions are now **panel-exclusive**. No inline display in the chat area.

### VersionsPanel modes

**List mode:**
```
┌─────────────────────────────┐
│ 3 versions          [Run Now] │
├─────────────────────────────┤
│ v3  Mar 9, 3:09 PM  ✓ Del  → │
│ v2  Mar 8, 2:15 PM  ✓ Del  → │
│ v1  Mar 7, 9:00 AM  ✗ Fail → │
└─────────────────────────────┘
```

**Preview mode (after clicking v3):**
```
┌─────────────────────────────┐
│ ← v3 ✓ Delivered Mar 9  [▶] │
├─────────────────────────────┤
│                             │
│ # This Week's Signals       │
│ Your technical infra...     │
│                             │
│ ## VC Research Timing...    │
│ ...                         │
│                             │
├─────────────────────────────┤
│ 1,234 words · 95.9k tokens │
│ 💬 #daily-work (1) · ...   │
├─────────────────────────────┤
│ 💬 Leave feedback           │
└─────────────────────────────┘
```

---

## 6. Surface-Action Mapping (unchanged)

The persistent panel doesn't change the surface-action principle:
- **Chat (left)** — directives, feedback, generation requests
- **Panel (right)** — reference (versions, memory, sessions), configuration (settings), read-only instructions

Instructions editing still flows through chat (ADR-105). The Instructions tab remains read-only with "Edit in chat" affordance.

---

## 7. Files Changed (v2 migration)

| File | Change |
|------|--------|
| `web/components/desk/WorkspaceLayout.tsx` | Rewritten: persistent inline panel (≥lg) + overlay fallback (<lg) |
| `web/components/agents/AgentVersionDisplay.tsx` | Rewritten: VersionsPanel with list/preview modes, deleted InlineVersionCard |
| `web/components/agents/AgentChatArea.tsx` | Simplified: removed InlineVersionCard, version props, selectedIdx |
| `web/app/(authenticated)/agents/[id]/page.tsx` | Simplified: removed selectedIdx state, panelDefaultOpen=true, new VersionsPanel props |
| `web/components/desk/ChatFirstDesk.tsx` | panelDefaultOpen=true |

---

---

## 8. Project Page: WorkfloorView Evolution (ADR-128 Phase 6)

The project page (`/projects/[slug]`) uses `WorkspaceLayout` with a Chat/Workfloor toggle on the main (left) area and Team/Context/Outputs/Settings tabs on the right panel.

### WorkfloorView

The Workfloor shows per-agent cards. Initially showed pulse state only (operational). ADR-128 Phase 6 evolves cards to include **cognitive state**:

- **Contributor cards**: 4-bar assessment (mandate, fitness, context, output) with level indicators + reason annotations for non-high dimensions. Collapses to "All dimensions healthy" when all 4 are high.
- **PM card**: 5-layer constraint indicator (commitment → structure → context → quality → readiness) with first-broken-layer summary.
- **Graceful degradation**: Cards without cognitive data show pulse-only layout (pre-ADR-128 agents, awaiting-first-run agents).

### InlineProfileCard (Team panel)

Profile card shows identity + developmental state + **cognitive state section** (between seniority and thesis):
- Self-assessment: latest 4 dimensions with level + reason
- Confidence trajectory: 5-square sparkline (last 5 runs)

See [COGNITIVE-DASHBOARD-DESIGN.md](COGNITIVE-DASHBOARD-DESIGN.md) for full design spec.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-04 | v1: Drawer overlay model — InlineVersionCard + overlay drawer |
| 2026-03-11 | v2: Persistent panel — inline panel (≥lg), versions in panel, InlineVersionCard deleted |
| 2026-03-21 | v3: WorkfloorView cognitive state evolution — 4-bar contributor cards, 5-layer PM card, InlineProfileCard self-assessment (ADR-128 Phase 6) |
