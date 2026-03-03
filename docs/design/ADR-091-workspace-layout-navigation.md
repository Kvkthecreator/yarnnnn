# ADR-091: Workspace Layout & Navigation Architecture

**Date:** 2026-03-04
**Status:** Design — awaiting approval before implementation
**Authors:** Kevin Kim, Claude

**References:**
- [ADR-037: Chat-First Surface Architecture](../adr/ADR-037-chat-first-surface-architecture.md) — dashboard model being evolved
- [ADR-080: Unified Agent Modes](../adr/ADR-080-unified-agent-modes.md) — chat vs headless modes
- [ADR-087: Deliverable Scoped Context](../adr/ADR-087-workspace-scoping-architecture.md) — per-deliverable instructions + memory
- [ADR-088: Unified Input Processing](../adr/ADR-088-input-gateway-work-serialization.md) — parked, builds on this
- [ADR-089: Agent Autonomy](../adr/ADR-089-agent-autonomy-context-aware-triggers.md) — parked, builds on this
- [ADR-087 Phase 3 Surface Layout](ADR-087-phase3-surface-layout.md) — current tabbed detail page, superseded by this

---

## 1. Problem

The current navigation model has a structural mismatch with where the product has evolved:

| Current | Reality |
|---------|---------|
| `/dashboard` is the singular chat entry point | Deliverables now have their own scoped chat sessions, memory, and instructions |
| `/deliverables/[id]` is a content viewer + tabs | A deliverable with instructions, memory, and session history is functionally a sub-agent |
| TP chat is "global" with implicit deliverable scoping | Scoping is invisible — user navigates from deliverable but can't see or act on it |
| "Thinking Partner" as the only named chat context | Multiple chat contexts now exist (global TP, deliverable-scoped), no UI distinction |

ADR-087 Phase 3 (tabs) shipped the data surfaces for the sub-agent model. The missing piece is the **interaction surface**: the ability to talk to a deliverable directly, from its own page, with visible scoping.

---

## 2. Benchmark: Claude Cowork

Cowork's layout established the right mental model:

```
┌───────────────────────────────┬─────────────────────┐
│  Chat (primary, ~65%)         │  Panels (30%)        │
│                               │                      │
│  [conversation thread]        │  Progress            │
│                               │  Content (artifacts) │
│                               │  Context (sources)   │
│                               │  Skills              │
│                               │                      │
│  [input bar]                  │                      │
└───────────────────────────────┴─────────────────────┘
```

Key properties:
- **Chat is dominant** — the agent is the primary interface
- **Panels are informational** — they show agent state, not replace the agent
- **One layout** — same structure whether global or scoped

YARNNN maps cleanly to this:

| Cowork Panel | YARNNN (Global TP) | YARNNN (Deliverable) |
|-------------|-------------------|---------------------|
| Progress | Todos (existing) | Version status |
| Content | — | Delivery history (versions) |
| Context | Platform sync status | Deliverable memory |
| Skills | — | Deliverable instructions |

---

## 3. Decision

### 3.1 Direction: Bring chat to deliverables

Two directions were considered:

- **Direction A: Bring deliverables to chat** — refactor `/dashboard` so TP chat has a deliverable scope switcher. Chat stays central, deliverables become modes.
- **Direction B: Bring chat to deliverables** — each deliverable gets a full Cowork-style page. `/dashboard` becomes a launcher.

**Direction B is correct** for the following reasons:
- Data is deliverable-scoped (`chat_sessions.deliverable_id`, `deliverable_instructions`, `deliverable_memory`)
- URL encodes scope — deep links work, back button works
- Separation of concerns: global TP ≠ deliverable workspace
- Structurally maps to "sub-agent" mental model — each deliverable IS an agent with a home page

### 3.2 Route architecture

| Route | Purpose | Chat scope |
|-------|---------|------------|
| `/dashboard` | Global TP launcher + deliverable entry points | Global (no deliverable scope) |
| `/deliverables` | List of all deliverables | None (navigation only) |
| `/deliverables/[id]` | Deliverable workspace (Cowork-style) | Scoped to this deliverable |

### 3.3 Shared layout, distinct identity

Both `/dashboard` and `/deliverables/[id]` use the **same Cowork-style layout component**. The distinction is in the header identity chip:

**Global TP (`/dashboard`):**
```
┌─────────────────────────────────────────────────────┐
│  ◎ Thinking Partner           [platform status]      │
├──────────────────────────────────────────┬──────────┤
│  chat                                    │  panels  │
```

**Deliverable workspace (`/deliverables/[id]`):**
```
┌─────────────────────────────────────────────────────┐
│  ← Deliverables  │  📊 Weekly Status Report  [Rec]  │
├──────────────────────────────────────────┬──────────┤
│  chat (scoped)                           │  panels  │
```

The identity chip is the user's primary signal for "which agent am I talking to." It must be always visible, never ambiguous.

---

## 4. Layout Specification

### 4.1 Shared Cowork layout component

Both pages use a single `<WorkspaceLayout>` component:

```
┌─────────────────────────────────────────────────────┐
│  [HEADER — identity + breadcrumb + controls]         │
├──────────────────────────────────────────┬──────────┤
│  CHAT AREA (~65-70%)                     │ PANEL    │
│                                          │ (~30%)   │
│  [messages thread]                       │          │
│                                          │ [tab bar]│
│                                          │          │
│  [input bar]                             │ [tab     │
│                                          │  content]│
└──────────────────────────────────────────┴──────────┘
```

- Panel is **collapsible** — toggle button in header. Collapsed by default on mobile.
- Panel tabs differ per context (see §4.3).
- Input bar is identical in both contexts — same component, same UX.

### 4.2 `/dashboard` — Global TP

**Header:**
- Identity chip: `◎ Thinking Partner` (pill, no back nav)
- Right: platform sync status indicators (existing `PlatformSyncStatus`)

**Chat area:**
- Global TP (no deliverable scope)
- Idle/welcome state: deliverable cards as entry points + platform connect CTAs (existing `PlatformSyncStatus` idle content, refactored)
- On first message: transitions to chat thread

**Right panel tabs:**
- **Deliverables** — list of user's deliverables as entry cards (replaces current idle state inline cards)
- **Context** — platform sync status detail (existing coverage view)

**What changes from current dashboard:**
- Layout shifts from full-width single column → left chat + right panel
- Deliverable cards move from idle state inline → Deliverables panel tab
- Platform sync cards move from idle state inline → Context panel tab
- "Create a deliverable" and "What can you do?" CTAs move to input area suggestions

### 4.3 `/deliverables/[id]` — Deliverable Workspace

**Header:**
- Back nav: `← Deliverables` (links to `/deliverables`)
- Identity chip: `[icon] [Deliverable Title]  [Mode badge: Rec | Goal]`
- Right: `⏸ ▶ ⚙` (pause, run now, settings)

**Chat area:**
- TP chat scoped to this deliverable (`deliverable_id` set on session)
- Idle state: "You're talking to [Deliverable Title]. Ask me to generate, refine, or review."
- Scoped session continuity — resumes from last scoped session or starts new

**Right panel tabs:**
- **Versions** — delivery history (versions list, click to preview content in an overlay)
- **Memory** — `deliverable_memory` JSONB, read-only (observations + goal)
- **Instructions** — `deliverable_instructions`, editable textarea, auto-save
- **Sessions** — scoped chat session list, read-only

**What changes from current `/deliverables/[id]`:**
- Current page: content hero (version preview) is dominant, tabs are below
- New page: chat is dominant, version content accessible via Versions panel (click → overlay or panel expansion)
- Execution Details and Schedule sections fold into: Mode badge (header) + Schedule shown in Versions panel header
- Settings modal remains for destination, schedule, sources

---

## 5. Primitive Gap: Deliverable Instruction + Memory Writes

The current `Edit` primitive updates deliverable fields (status, schedule, title, etc.). It does **not** currently support writing to `deliverable_instructions` or `deliverable_memory`.

For chat on a deliverable page to be useful, TP must be able to:

1. **Update instructions** — user says "add a rule that outputs should always use bullet points" → TP calls `Edit` on `deliverable_instructions`
2. **Acknowledge observations** — user says "note that Q4 data is now finalized" → TP appends to `deliverable_memory.observations`

### Required primitive changes (separate commit, before UI work):

**`Edit` primitive additions:**
- Add `deliverable_instructions` to editable fields
- Add `deliverable_memory` write path: `append_observation(date, note)` and `set_goal(description, status, milestones)`
- These should be **scoped operations** (append, not replace) to avoid clobbering system-accumulated memory

**`Execute` primitive additions:**
- `deliverable.acknowledge` — lightweight action: extract an observation from conversation context and append to `deliverable_memory.observations` (Haiku-level, not a full generation). Un-parks part of ADR-089.

**No new primitives needed** — `Edit` and `Execute` cover both cases with field additions.

---

## 6. Identity Chip & Context Distinguisher

From the current screenshot, `/dashboard` shows "Thinking Partner" as a dropdown in the header. This needs to become a persistent, always-visible identity chip — not a dropdown.

**Design rule:** The identity chip is always visible in the top-left of the header, shows:
- For global TP: `◎ Thinking Partner`
- For deliverable workspace: `[deliverable icon] [Deliverable Title]`

This is the user's answer to "which agent am I talking to?" at all times.

The existing dropdown behavior (for switching skills or surfaces) moves to a different affordance — likely the input area `/` skill picker or a panel control — not the header identity.

---

## 7. `ChatFirstDesk` Refactor Strategy

The current `ChatFirstDesk` component is tightly coupled to the dashboard. The refactor extracts it into a reusable `WorkspaceLayout`:

```
ChatFirstDesk (current)
└── Monolithic component with:
    - Header with "Thinking Partner" title
    - Surface panel toggle
    - Messages area
    - Input bar
    - Platform sync status (idle)

WorkspaceLayout (new, shared)
├── props: identity, chatScope, panelTabs[], idleContent
├── Header (identity chip + controls)
├── ChatArea (messages + input, same component)
└── PanelArea (tabs + tab content)
```

`/dashboard` and `/deliverables/[id]` both render `<WorkspaceLayout>` with different props. The chat infrastructure (useTP, message rendering, streaming, tool results) is unchanged — it's just relocated inside the shared layout.

---

## 8. Navigation & URL Model

```
/dashboard                    → Global TP workspace
/deliverables                 → Deliverable list (unchanged)
/deliverables/[id]            → Deliverable workspace (replaces current detail page)
/deliverables/new             → New deliverable form (unchanged)
```

The `dashboard/deliverable/[id]` and `dashboard/deliverable/[id]/review` routes (legacy desk surfaces) are already redirects from ADR-037. These can be cleaned up in this pass.

**Deep links:** A scoped chat session at `/deliverables/[id]` is fully bookmarkable. The deliverable_id is encoded in the URL, not held in transient state.

---

## 9. What This Does NOT Include

- **Headless mode UI** — headless generation is scheduler/event-triggered, non-interactive. No UI surface needed. Separation is clean: headless = autonomous, chat = interactive.
- **Goal mode full UX** — mode badge + mode selector (already in settings modal). Full goal UX (milestones, progress, completion flow) is a separate design doc.
- **Multi-deliverable workspace** — one deliverable per workspace page. No tab bar for switching between deliverables in the same view.
- **Mobile layout** — panel collapses to hidden by default on mobile. Chat is full-width. Panel accessible via toggle.

---

## 10. Implementation Sequence

This is a multi-commit effort. Suggested order:

### Commit 1: Primitive additions (backend, no UI)
- `Edit` primitive: add `deliverable_instructions` + `deliverable_memory` write paths
- `Execute` primitive: add `deliverable.acknowledge` action
- Update `api/prompts/CHANGELOG.md`
- Update ADR-087 with primitive changes

### Commit 2: WorkspaceLayout component (frontend, no route changes)
- Extract `ChatFirstDesk` → `WorkspaceLayout` with props interface
- Wire `/dashboard` to `WorkspaceLayout` (identical behavior, refactor only)
- Build panel tab infrastructure (reusable tab component)
- No behavior change on dashboard — this is a structural refactor

### Commit 3: Deliverable workspace page
- Refactor `/deliverables/[id]` to use `WorkspaceLayout`
- Chat area wired to deliverable-scoped TP session
- Panel tabs: Versions, Memory, Instructions, Sessions (content from existing Phase 3 tabs)
- Header identity chip with deliverable title + mode badge

### Commit 4: Dashboard panel content + identity chip
- Identity chip distinguisher on `/dashboard`
- Deliverables panel tab (entry cards)
- Context panel tab (platform sync status)
- Remove inline idle state cards (moved to panel)

### Commit 5: ADR and doc updates
- Update ADR-087, ADR-088, ADR-089 status
- Update USER_FLOW_ONBOARDING_V2.md (dashboard is now launcher)
- Update ADR-087-phase3-surface-layout.md (superseded by this)

---

## 11. Files Changed (Estimated)

| File | Change | Scope |
|------|--------|-------|
| `api/services/primitives/edit.py` | Add deliverable_instructions + deliverable_memory fields | Small |
| `api/services/primitives/execute.py` | Add deliverable.acknowledge action | Small |
| `api/prompts/CHANGELOG.md` | Log primitive changes | Small |
| `web/components/desk/ChatFirstDesk.tsx` | Refactor → WorkspaceLayout (extract) | Major |
| `web/components/desk/WorkspaceLayout.tsx` | New shared layout component | Major (new) |
| `web/app/(authenticated)/dashboard/page.tsx` | Render WorkspaceLayout | Trivial |
| `web/app/(authenticated)/deliverables/[id]/page.tsx` | Full rewrite to WorkspaceLayout | Major |
| `docs/adr/ADR-087-workspace-scoping-architecture.md` | Update status + primitive additions | Small |
| `docs/design/USER_FLOW_ONBOARDING_V2.md` | Update dashboard description | Small |
| `docs/design/ADR-087-phase3-surface-layout.md` | Mark superseded | Trivial |
