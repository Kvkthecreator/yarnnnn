# Surface Architecture — Chat + Work + Agents + Context

**Version:** v9 (2026-04-08)
**Status:** Canonical
**Governed by:** [ADR-163](../adr/ADR-163-surface-restructure.md) — Surface Restructure
**Active decisions:**
- [ADR-165](../adr/ADR-165-chat-artifact-surface.md) — `/chat` internal layout
- [ADR-166](../adr/ADR-166-registry-coherence-pass.md) — task `output_kind` enum (4 values)
- [ADR-167](../adr/ADR-167-list-detail-surfaces.md) — `/work` and `/agents` collapse from master-detail into list/detail mode with kind-aware detail

**Supersedes:**
- v8 (2026-04-08) — three-panel master-detail on Work and Agents
- v7.2 (2026-04-06) — task-class-aware tabs on Agents page
- v7.1 (2026-04-06) — tabs restored
- v7 (2026-04-06) — unified shell, flat center panel
- v6.1 (2026-04-06) — global breadcrumb
- v6 (2026-04-05) — dashboard + TP chat two-panel

---

## Design Thesis: Four Surfaces, One Question Each

Every previous version of this doc was trying to cram multiple jobs into the Agents page because Agents was the only top-level destination that touched work. The result: four tab layouts in ten commits. ADR-163 fixes the thrash by giving each question its own surface.

| Surface | Route | The question it answers | The answer |
|---|---|---|---|
| **Chat** | `/chat` | "What should I do? What's happening?" | TP chat + one active structured artifact |
| **Work** | `/work` | "What is my workforce doing?" | Task list + task detail (schedule, output, actions) |
| **Agents** | `/agents` | "Who's on my team?" | Roster + identity card + health |
| **Context** | `/context` | "What does my workspace know?" | Filesystem browser |

Four destinations. Each answers exactly one question. No overlap.

The old `/activity` page is **deleted**. Its content is absorbed into the surfaces that naturally own it: per-task activity to `/work`, per-agent activity to `/agents`, workspace-wide activity to the Chat briefing dashboard, diagnostic events to Settings → System Status.

---

## Route Map

```
/chat                → Chat (home). TP chat + one active artifact tab.
/work                → Work LIST mode. Full-width filterable list of tasks.
/work?agent={slug}   → Work LIST mode with the agent filter pre-applied.
/work?task={slug}    → Work DETAIL mode. Kind-aware detail dispatched on task.output_kind (ADR-167).
/agents              → Agents LIST mode. Full-width team roster grouped by class.
/agents?agent={id}   → Agents DETAIL mode. Identity + health card.
/context             → Context. Workspace filesystem browser. (Retains left tree nav.)
/context?domain={k}  → Context pre-filtered to a domain folder.
/settings            → Settings. Memory, brand, system status (absorbed from /activity).
```

**ADR-167 surface mode collapse:** `/work` and `/agents` no longer have a permanent left sidebar. Each is a single surface with two modes selected by URL state — list mode (no detail key) shows the full-width list/roster, detail mode (`?task=` or `?agent=`) shows kind-aware detail. The breadcrumb (commit b033513) drives navigation between modes. Auto-select-first on mount is GONE — landing on `/work` or `/agents` shows the list, never someone else's task or agent. `/context` retains its left sidebar (filesystem tree nav is the right pattern there).

**Legacy routes still live for bookmark preservation:**
- `/tasks` and `/tasks/{slug}` → redirect to `/work` (forwards slug as `?task=`)
- `/workfloor` → redirect to `HOME_ROUTE` (`/chat`)
- `/orchestrator` → redirect to `HOME_ROUTE` with query params preserved (OAuth callbacks)

**Deleted routes:**
- `/activity` — returns 404; content absorbed elsewhere

---

## Navigation

### Top Bar

```
┌──────────────────────────────────────────────────────────────────────┐
│ yarnnn                   [Chat | Work | Agents | Context]     Avatar │
│                          Work / Daily Update                         │
└──────────────────────────────────────────────────────────────────────┘
```

**Global breadcrumb** (`BreadcrumbContext`): pages set linkable breadcrumb segments into a shared context; the shell renders them as a centered scope path under the four-toggle nav. Prefer `href` for route-backed segments and reserve `onClick` for local state that has no URL. On narrow screens, the path scrolls horizontally rather than wrapping into the main surface.

| Surface state | Breadcrumb |
|---|---|
| Chat | _(empty — just logo)_ |
| Work (overview) | _(empty)_ |
| Work (task selected) | `Work / Daily Update` |
| Work (filtered by agent) | `Work / Competitive Intelligence's work` |
| Agents (overview) | _(empty)_ |
| Agents (selected) | `Agents / Competitive Intelligence` |
| Context (domain selected) | `Context / Competitors` |
| Context (deep file) | `Context / Competitors / cursor / profile.md` |

**Toggle bar** (`web/components/shell/ToggleBar.tsx`): four-segment pill `Chat | Work | Agents | Context`. Icons: `MessageCircle`, `Briefcase`, `Users`, `FolderOpen`. `HOME_ROUTE` is `/chat` — both new and returning users land there.

---

## 1. Chat (`/chat`, HOME_ROUTE)

### Purpose
Dedicated TP chat surface. Structured renderings such as onboarding, daily briefing, recent work, and context gaps render as one active artifact above the persistent TP console.

For new users with an empty workspace, the daily-update task still runs (deterministic empty-state template from ADR-161) and the briefing dashboard shows its honest "tell me what to track" message.

### Layout

```
┌──────────────────┬──────────────────────────────────┐
│  Briefing        │  TP Chat                         │
│                  │                                  │
│  Daily update    │  (conversation thread)           │
│  output (hero)   │                                  │
│                  │                                  │
│  Recent activity │                                  │
│  feed (last 72h) │                                  │
│                  │  [input ───────────────────────] │
└──────────────────┴──────────────────────────────────┘
```

The daily-update task is the intellectual center of the briefing. Its output is always fresh (recomputed daily), always honest (empty-state template for dormant workspaces), and always visible.

---

## 2. Work (`/work`)

### Purpose
Work is where the user looks at what their workforce is doing. First-class top-level destination (ADR-163). After ADR-167, `/work` is a single surface with **two modes** selected by URL state — list mode (no `?task=` param) and detail mode (`?task={slug}`).

### Task Modes on the Surface (ADR-163)

The schema has three modes (`recurring | goal | reactive`). The surface has **two labels**: `Recurring` and `One-time`. Mapping:

```
recurring  → Recurring
goal       → One-time
reactive   → One-time
```

The `WorkModeBadge` component is the only place modes are rendered. Every task row and task detail header uses it. The mapping is enforced by `taskModeLabel()` in `web/types/index.ts`.

The execution layer still distinguishes three modes because `goal` has the revision loop and `reactive` has dispatch-and-done semantics (see ADR-149). Users never see the third option — they pick "Recurring" or "One-time", and TP resolves "One-time" to `goal` or `reactive` behind the scenes based on task type.

### List Mode (default)

```
┌──────────────────────────────────────────────────────────────────────┐
│  [ All ][ Tracking ][ Reports ][ Actions ][ System ]                 │
│  Search: [____________]   Group by: ▾ [Output kind]  [include arch.] │
├──────────────────────────────────────────────────────────────────────┤
│  REPORTS · 5                                                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ ● ★ Daily Update     Recurring · Reporting · daily   Next: 9h │  │
│  │ ● Competitive Brief  Recurring · Comp Intel · weekly Next: 4d │  │
│  │ ● Market Report      Recurring · Mkt Rsch · monthly  Next: 12d│  │
│  └───────────────────────────────────────────────────────────────┘  │
│  TRACKING · 3                                                        │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ ● Track Competitors  Recurring · Comp Intel · weekly Next: 2d │  │
│  │ ● Slack Digest       Recurring · Slack Bot · daily   Next:18h │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  SYSTEM · 2                                                          │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ ● Agent Hygiene      Recurring · TP · daily          Next:22h │  │
│  │ ● Workspace Cleanup  Recurring · TP · daily          Next:22h │  │
│  └───────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

**Filter chips** key on `output_kind` (ADR-166): `All | Tracking | Reports | Actions | System`. **Group-by dropdown** defaults to "Output kind" and supports Agent / Status / Schedule. **Search box** filters by title substring. **Agent filter chip** appears when `?agent={slug}` is in the URL or applied via the UI; click X to clear.

The list is **sorted within each group** by status (active first) then `next_run_at` ascending. Click a row → URL transitions to `/work?task={slug}` → detail mode.

### Detail Mode (`/work?task={slug}`) — Kind-Aware (ADR-167)

`WorkDetail` is a thin shell that dispatches the middle band on `task.output_kind`. The chrome (header, objective, actions, assigned-to footer) is uniform; the middle band differs because the four kinds need fundamentally different data:

| `output_kind` | Middle component | Renders |
|---|---|---|
| `accumulates_context` | `<TrackingMiddle>` | Domain folder link (`/context?domain={key}`) + last-run CHANGELOG (markdown summary of what was added) |
| `produces_deliverable` | `<DeliverableMiddle>` | The latest rendered HTML output in an iframe (or markdown) — this was the original `OutputPreview` |
| `external_action` | `<ActionMiddle>` | Action target (channel/page) + fire history with link-out to platform message |
| `system_maintenance` | `<MaintenanceMiddle>` | Hygiene log markdown + run history table. Objective block is suppressed (TP owns the contract, not the user). |

```
┌──────────────────────────────────────────────────────────────────────┐
│  Daily Update              [Recurring]  [★ Essential]                │
│  active · Reporting · daily                                          │
│  Next: 9h  ·  Last: 16h ago                                          │
├──────────────────────────────────────────────────────────────────────┤
│  Objective                                                           │
│  · Deliverable: Daily workspace update                               │
│  · Audience: You — quick morning scan                                │
├──────────────────────────────────────────────────────────────────────┤
│  Latest output  ·  2026-04-08T09:00                                  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ [iframe with rendered HTML — DeliverableMiddle]                │  │
│  └───────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  [Run now]  [Pause]                                  [Edit via chat] │
├──────────────────────────────────────────────────────────────────────┤
│  → Assigned to Reporting                                             │
└──────────────────────────────────────────────────────────────────────┘
```

### Filtering and deep-links

- `/work` — list mode, no filter
- `/work?agent={slug}` — list mode with the agent filter chip pre-applied (used by the breadcrumb's "Competitive Intelligence's work" segment and by AgentContentView's "See this agent's work" link)
- `/work?task={slug}` — detail mode for that task
- The breadcrumb (commit b033513) is the navigation between modes; clicking the `Work` segment from a detail returns you to list mode

### What Used to Live Here

- The left sidebar `WorkList` with auto-select-first → DELETED. Replaced by `WorkListSurface` (full-width list with filter chips, search, group-by). Landing on `/work` no longer shows you someone else's task by accident.
- The single one-shape `OutputPreview` inside `WorkDetail` → DELETED. Replaced by four kind-specific middle components in `web/components/work/details/`. The dispatch lives in `WorkDetail`.
- `ThreePanelLayout`'s left panel on `/work` → DELETED. The page no longer passes `leftPanel`. The layout is effectively two-panel (full-width center + FAB-overlay chat), which is what the page actually wanted all along.

---

## 3. Agents (`/agents`)

### Purpose
Agents is where the user looks at **who** is on their team, not **what** they're doing. After ADR-167, `/agents` is a single surface with **two modes** selected by URL state — list mode (no `?agent=` param) and detail mode (`?agent={slug}`). Work observation lives on `/work`. Domain entity browsing lives on `/context`.

### List Mode (default) — `AgentRosterSurface`

```
┌──────────────────────────────────────────────────────────────────────┐
│  Domain Stewards · 5                                                 │
│  Each owns one context domain. They accumulate intelligence over time│
│  ┌──────────────────────────┐  ┌──────────────────────────┐         │
│  │ 🧠 Competitive Intel.    │  │ 🧠 Market Research       │         │
│  │ owns /context/competitors/│  │ owns /context/market/    │         │
│  │ 1 task · 2h ago · 100%   │  │ 1 task · 16h ago         │         │
│  └──────────────────────────┘  └──────────────────────────┘         │
│  ┌──────────────────────────┐  ┌──────────────────────────┐         │
│  │ 🧠 Business Development  │  │ 🧠 Operations            │         │
│  │ owns /context/relations/  │  │ owns /context/projects/  │         │
│  │ 0 tasks · never run      │  │ 0 tasks · never run      │         │
│  └──────────────────────────┘  └──────────────────────────┘         │
│  ┌──────────────────────────┐                                       │
│  │ 🧠 Marketing & Creative  │                                       │
│  │ owns /context/content/   │                                       │
│  │ 0 tasks · never run      │                                       │
│  └──────────────────────────┘                                       │
│                                                                      │
│  Synthesizer · 1                                                     │
│  Reads across all domains to compose cross-domain reports.           │
│  ┌──────────────────────────┐                                       │
│  │ 🪧 Reporting              │                                       │
│  │ reads all domains         │                                       │
│  │ 1 task · 16h ago          │                                       │
│  └──────────────────────────┘                                       │
│                                                                      │
│  Platform Bots · 3                                                   │
│  Tied to platform integrations. Bridge external surfaces.            │
│  ┌──────────────────────────┐  ┌──────────────────────────┐         │
│  │ 🔌 Slack Bot              │  │ 🔌 Notion Bot             │         │
│  └──────────────────────────┘  └──────────────────────────┘         │
│                                                                      │
│  Thinking Partner · 1                                                │
│  Orchestration and back office. Conversational by day, runs hygiene. │
│  ┌──────────────────────────┐                                       │
│  │ 💬 Thinking Partner       │                                       │
│  │ orchestration · back office│                                       │
│  │ 2 tasks · daily           │                                       │
│  └──────────────────────────┘                                       │
└──────────────────────────────────────────────────────────────────────┘
```

**Grouping** is by `agent_class` (ADR-140 v4 + ADR-164): Domain Stewards (5) / Synthesizer (1) / Platform Bots (3) / Thinking Partner (1). Each section has a one-line description of what that class does. Per-card health glance shows: status, owned domain (or class-specific subtitle), active task count, last run (color-coded by freshness), approval rate (only if `version_count >= 5`).

Click a card → URL transitions to `/agents?agent={slug}` → detail mode.

### Detail Mode (`/agents?agent={slug}`) — `AgentContentView`

The single identity card. Same as v8 — no tabs, no work observation, no domain browsing.

### Identity Card Sections
- **Identity block:** name, role + class, domain, origin, creation date
- **Instructions block:** rendered AGENT.md via MarkdownRenderer
- **Feedback block:** distilled feedback from `agent_memory.feedback` if present

### Health Card Sections
- **Tasks assigned:** count of active tasks
- **Total runs:** from `version_count`
- **Approval rate:** from `quality_score`, only shown if runs >= 5, with trend arrow
- **Last run:** relative time
- **Links out:** "See this agent's work" → `/work?agent={slug}`, "See this agent's context domain" → `/context?domain={domain}`, "Chat about this agent" → opens TP chat

### What Used to Live Here

- The left sidebar `AgentTreeNav` with auto-select-first → DELETED. Replaced by `AgentRosterSurface` (full-width grouped roster with health glances). Landing on `/agents` no longer shows you someone else's identity card by accident.
- `ThreePanelLayout`'s left panel on `/agents` → DELETED. Same as `/work`.

### What Moved Out Of Agents (v7.2) — And Where
| Old Tab | Content | Moved to |
|---|---|---|
| **Report** | Latest synthesis task outputs | `/work?task={slug}` → `DeliverableMiddle` (ADR-167) |
| **Data** | Domain entity dashboard | `/context?domain={key}` |
| **Pipeline** | Task config, schedule, actions | `/work` surface |
| **Agent** | Identity, instructions, history | Stayed here (`AgentContentView`, now the only thing on the page) |

---

## 4. Context (`/context`)

### Purpose
The only filesystem browser. Shows the workspace tree with domains, output folders, uploads, and IDENTITY/BRAND files. Unchanged from v7.2 structurally. ADR-163 adds one enhancement: inference-meta rendering.

### Inference Visibility (ADR-162 + ADR-163)

When the Context tab renders IDENTITY.md or BRAND.md, it uses `InferenceContentView` instead of the raw markdown renderer. The component:

1. Parses the `<!-- inference-meta: {...} -->` HTML comment embedded at the bottom of inference output (written by `_append_inference_meta()` in `api/services/context_inference.py`).
2. Strips the comment before rendering the markdown body.
3. Shows a source provenance caption above the body:
   - `Last updated from: pitch-deck.pdf · 2h ago`
   - `Last updated from: 2 documents, 1 URL · yesterday`
4. Shows a gap banner below the body when there's a high-severity unfilled gap from the deterministic gap detector (ADR-162 Sub-phase A):
   ```
   ⚠ Missing: company name
     What company or project are you building?
     [Chat to fill this in]
   ```

The gap banner's "Chat to fill this in" link navigates to `/chat?prompt=...` with a pre-filled message that drops the user into TP chat with a natural follow-up.

Currently wired for BrandSection in Settings (via `MemorySection.tsx`). A dedicated IdentitySection surface is a future addition — TP also consumes IDENTITY.md via working memory, so it's not invisible even without a UI surface.

---

## Component Map

### Shell
- `web/components/shell/ToggleBar.tsx` — top-level nav (4 segments)
- `web/components/shell/AuthenticatedLayout.tsx` — shell wrapper + TP provider
- `web/components/shell/ThreePanelLayout.tsx` — layout primitive. `leftPanel` is OPTIONAL (ADR-167) — pages omit it for the list/detail pattern; `/context` keeps it for filesystem tree nav.
- `web/components/shell/GlobalBreadcrumb.tsx` — centered scope path with linkable segments (commit b033513)
- `web/contexts/BreadcrumbContext.tsx` — breadcrumb segment state with `kind`-tagged segments

### Chat
- `web/app/(authenticated)/chat/page.tsx` — Chat page (home)
- `web/components/chat-surface/ChatSurface.tsx` — chat artifact surface (ADR-165)
- `docs/design/CHAT-ARTIFACT-SURFACE.md` — chat artifact surface plan for `/chat` (ADR-165)

### Work
- `web/app/(authenticated)/work/page.tsx` — Work page. List/detail mode switched on `?task=` URL state (ADR-167).
- `web/components/work/WorkListSurface.tsx` — full-width list with filter chips, search, group-by, agent filter (ADR-167; replaces deleted `WorkList.tsx`)
- `web/components/work/WorkDetail.tsx` — thin shell that dispatches the middle band on `task.output_kind` (ADR-167)
- `web/components/work/details/DeliverableMiddle.tsx` — middle band for `produces_deliverable` (the original iframe `OutputPreview`, extracted)
- `web/components/work/details/TrackingMiddle.tsx` — middle band for `accumulates_context` (domain folder + CHANGELOG)
- `web/components/work/details/ActionMiddle.tsx` — middle band for `external_action` (fire history + platform link-out)
- `web/components/work/details/MaintenanceMiddle.tsx` — middle band for `system_maintenance` (hygiene log + run history)
- `web/components/work/WorkModeBadge.tsx` — mode badge (the only mode renderer)

### Agents
- `web/app/(authenticated)/agents/page.tsx` — Agents page. List/detail mode switched on `?agent=` URL state (ADR-167).
- `web/components/agents/AgentRosterSurface.tsx` — full-width roster grouped by `agent_class` with health glance cards (ADR-167; replaces deleted `AgentTreeNav.tsx`)
- `web/components/agents/AgentContentView.tsx` — identity + health card (detail mode)

### Context
- `web/app/(authenticated)/context/page.tsx` — Context page. Retains left filesystem tree nav.
- `web/components/context/InferenceContentView.tsx` — meta-aware inferred content renderer (ADR-163)
- `web/lib/inference-meta.ts` — parse helper (ADR-163)

### Types
- `web/types/index.ts` — `TaskMode` type + `taskModeLabel()` helper for surface mapping

### Routes
- `web/lib/routes.ts` — `HOME_ROUTE`, `CHAT_ROUTE`, `WORK_ROUTE`, `AGENTS_ROUTE`, `CONTEXT_ROUTE`

---

## Migration Notes for Implementers

When adding a new surface, ask: "what question does this answer?" If the answer overlaps with an existing surface, the new thing probably belongs inside that surface, not as a new nav item. Four surfaces is the stopping point — five becomes thrash again.

When modifying task rendering, always use `WorkModeBadge` or the `taskModeLabel()` helper. Never render `task.mode` directly. The two-mode surface is load-bearing for avoiding user confusion.

When adding a new way to render a task in detail mode, **add it as a new middle component in `web/components/work/details/` and dispatch it from `WorkDetail`'s `KindMiddle` switch on `task.output_kind`**. Do not branch inside an existing middle component. Each middle component owns one `output_kind` and its own data fetch — this is the rule ADR-167 codified.

When adding per-entity activity surfaces, fold them into the entity's detail page (`/work?task=` or `/agents?agent=`). Don't build a new top-level activity destination — that's what ADR-163 deleted.

When adding a new detail-mode page, prefer the list/detail collapse pattern over master-detail (ADR-167). The breadcrumb already does the navigation work; a permanent left sidebar is no longer load-bearing.

---

## Revision History

| Date | Version | Change |
|---|---|---|
| 2026-04-08 | v9 | ADR-167 — `/work` and `/agents` collapse from master-detail (left list + center detail + chat) into single surfaces with two URL-driven modes: list mode (full-width filterable list / roster) and detail mode (kind-aware detail dispatched on `task.output_kind`). `WorkList` and `AgentTreeNav` deleted. Auto-select-first deleted. `ThreePanelLayout.leftPanel` now optional. Four kind-aware middle components in `web/components/work/details/`. |
| 2026-04-08 | v8.1 | ADR-165 accepted: `/chat` remains the Chat surface, but changes internally from two-panel layout to a single TP console layer with artifact tabs for onboarding, briefing, recent work, and context gaps. |
| 2026-04-08 | v8 | ADR-163 — Four-surface restructure: Chat \| Work \| Agents \| Context. Activity absorbed. Agents page shrunk to identity. New /work surface. Mode collapse (surface only). Inference visibility via InferenceContentView. |
| 2026-04-06 | v7.2 | Task-class-aware tabs on Agents (superseded) |
| 2026-04-06 | v7.1 | Tabs restored (superseded) |
| 2026-04-06 | v7 | Unified shell, flat center panel (superseded) |
| 2026-04-06 | v6.1 | Global breadcrumb added |
| 2026-04-05 | v6 | Dashboard + TP chat two-panel (superseded) |
