# Surface Architecture — Chat + Work + Agents + Context

**Version:** v9.5 (2026-04-09)
**Status:** Canonical
**Governed by:** [ADR-163](../adr/ADR-163-surface-restructure.md) — Surface Restructure
**Active decisions:**
- [ADR-165 v5](../adr/ADR-165-workspace-state-surface.md) — `/chat` workspace state surface (TP-directed, single component, four lead views)
- [ADR-166](../adr/ADR-166-registry-coherence-pass.md) — task `output_kind` enum (4 values)
- [ADR-167](../adr/ADR-167-list-detail-surfaces.md) — `/work` and `/agents` collapse from master-detail into list/detail mode with kind-aware detail. **v2 amendment**: breadcrumb collapses into in-page `<PageHeader />`, replacing the floating bar AND the per-page title bands inside `WorkDetail`/`AgentContentView`.
- [AGENT-AND-TASK-SURFACE-PATTERNS](./AGENT-AND-TASK-SURFACE-PATTERNS.md) — broader shell and no-task-state rules layered on top of ADR-167

**Supersedes:**
- v9 (2026-04-08) — list/detail collapse with separate `<GlobalBreadcrumb />` floating bar
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
| **Agents** | `/agents` | "Who's on my team?" | Roster + agent detail with class-aware context and work-shape summaries |
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
/agents?agent={slug} → Agents DETAIL mode. Class-aware context + task-shape summaries.
/agents/{id}         → Compatibility entry. Redirects to `/agents?agent={slug}`.
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
│ yarnnn                   [Chat | Work | Agents | Context]     Avatar │ ← global header (logo / toggle / avatar)
└──────────────────────────────────────────────────────────────────────┘
```

The global header is **just** logo + toggle bar + avatar. There is no separate breadcrumb bar below it. The breadcrumb lives **inside each surface** as a `<PageHeader />` component (ADR-167 v2) — see "Page header" below.

**Toggle bar** (`web/components/shell/ToggleBar.tsx`): four-segment pill `Chat | Work | Agents | Context`. Icons: `MessageCircle`, `Briefcase`, `Users`, `FolderOpen`. `HOME_ROUTE` is `/chat` — both new and returning users land there.

### Page header (ADR-167 v5)

Every surface renders `<PageHeader />` as the first row of its center content area. It is **pure navigation chrome** — the breadcrumb and nothing else. No title, no metadata, no actions. Those all live inside the surface content as a separate `<SurfaceIdentityHeader />` block where they belong alongside the content they describe.

```
┌──────────────────────────────────────────────────────────────────────┐
│ Work › reporting's work › Daily Update                               │ ← PageHeader: breadcrumb chrome
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ Daily Update                                 [Run] [Pause] [Edit]    │ ← SurfaceIdentityHeader: the real H1
│ Recurring · Active · Reporting · daily · Next: 9h                    │    metadata strip under title
│                                                                      │
│ ─────────                                                            │
│ OBJECTIVE                                                            │
│ · Deliverable: Daily workspace update                                │
│ · Audience: You — quick morning scan                                 │
│                                                                      │
│ ─────────                                                            │
│ LATEST OUTPUT · 2026-04-08                                           │
│ ┌─────────────────────────────────────────────────────────┐          │
│ │                                                         │          │ ← nested card: bordered,
│ │   Daily Workspace Update — April 8, 2026                │          │    visually inset, muted
│ │                                                         │          │    background. The output's
│ │   System Status                                         │          │    own H1 is clearly scoped
│ │   ✅ All systems operational                             │          │    as "content inside the
│ │   …                                                     │          │    task," not as the page.
│ │                                                         │          │
│ └─────────────────────────────────────────────────────────┘          │
│                                                                      │
│ → Assigned to Reporting                                              │
└──────────────────────────────────────────────────────────────────────┘
```

**Two components, two responsibilities.** `<PageHeader />` answers "where am I?" It is chrome, always present with the same muted tone across every state (list and detail). `<SurfaceIdentityHeader />` answers "what is this page ABOUT?" It is content — rendered inside the surface's scroll area as a proper `h1.text-2xl` with metadata directly under it and optional actions inline on the right. WorkDetail and AgentContentView both render their own `<SurfaceIdentityHeader />` at the top of their content stream. No more plumbing task-shaped data through the chrome layer.

**Nested document pattern.** Any task-produced content (output iframes, CHANGELOG markdown, hygiene logs, AGENT.md) is wrapped in a bordered, visually inset card (`rounded-lg border border-border bg-muted/5`). This tells the user "this is a document the task produced." The card frame makes whatever H1s live inside that content clearly subordinate to the surface's own H1 above. Applied consistently across `DeliverableMiddle`, `TrackingMiddle`, `MaintenanceMiddle`, and `InstructionsBlock` (AGENT.md in AgentContentView).

**List-mode behavior.** `<PageHeader />` falls back to `defaultLabel` and renders a single-segment breadcrumb (`Work`, `Agents`, `Context`) with the exact same muted treatment — uniform tone across all states. List-mode pages don't render `<SurfaceIdentityHeader />` at all since there's no single "page subject" to introduce; the list surface itself owns the visual hierarchy (filter chips on /work, grouped roster on /agents, file tree on /context).

| Surface state | Breadcrumb / page title |
|---|---|
| Chat | `Chat` (breadcrumb chrome) + `Thinking Partner` surface identity header with workspace-state toggle action |
| Work (list) | `Work` |
| Work (task selected) | `Work › reporting's work › Daily Update` (with metadata subtitle and inline actions) |
| Work (filtered by agent) | `Work › Competitive Intelligence's work` |
| Agents (list) | `Agents` |
| Agents (selected) | `Agents › Competitive Intelligence` (with class · domain · task count · last run subtitle) |
| Context (no selection) | `Context` |
| Context (domain selected) | `Context › Competitors` |
| Context (deep file) | `Context › Competitors › cursor › profile.md` |

Pages set the breadcrumb segments via `setBreadcrumb()` in a `useEffect` (unchanged contract from b033513). PageHeader reads from the same context. List-mode pages clear the breadcrumb and PageHeader falls back to the surface label via `defaultLabel`.

---

## 1. Chat (`/chat`, HOME_ROUTE)

### Purpose
Dedicated TP (Thinking Partner) chat surface. The conversation column is the full surface — there is no always-on briefing side panel. Structured views (onboarding, daily briefing, recent work, context gaps) render as a TP-directed MODAL (ADR-165 v7) opened either by TP emitting a `<!-- workspace-state: ... -->` marker or by the user clicking the workspace-state button in the surface header. Four peer lens tabs: `context | briefing | recent | gaps`.

For new users with an empty workspace, the daily-update task still runs (deterministic empty-state template from ADR-161) and TP's first response opens the workspace-state modal to the `context` lens (soft-gated — switcher hidden while `isEmpty`).

### Layout (ADR-167 v5)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Chat                                                                 │ ← PageHeader (breadcrumb chrome)
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ Thinking Partner                            [⊞ Workspace state]      │ ← SurfaceIdentityHeader
│                                                                      │    h1 + action button
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│                    (conversation thread)                             │
│                                                                      │
│                    [ input row ──────── → ]                          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

Chat picks up the same two-component header pattern as /work and /agents: `<PageHeader />` as breadcrumb chrome, `<SurfaceIdentityHeader />` as the real H1 with inline actions. The surface identity H1 is "Thinking Partner" (the agent you're chatting with). The workspace-state toggle (formerly an `inputRowAddon` crammed between the + menu and the textarea inside the chat input row) moves UP into `SurfaceIdentityHeader.actions` — it sits alongside the page identity where it belongs, matching the Run/Pause/Edit pattern on /work detail.

The conversation column stays centered at `max-w-3xl` beneath the headers. Both headers are surface-wide (flush to the viewport edge) so the chrome tone is uniform with the other surfaces.

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
│  │ ● Daily Update       Recurring · Reporting · daily   Next: 9h │  │
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

**Filter chips** key on `output_kind` (ADR-166): `All | Tracking | Reports | Actions | System`. **Group-by dropdown** defaults to "Output kind" and supports Agent / Status / Schedule. **Search box** indexes title, assigned agent, task type, delivery target, objective fields, and context domains. **Status filter** defaults to active + paused, with an explicit "Include completed and archived" toggle. **Agent filter chip** appears when `?agent={slug}` is in the URL or applied via the UI; click X to clear.

The list is **sorted within each group** by lifecycle urgency: active first, then paused, then completed/archived; upcoming runs sort ahead of older work, and historical items sort by most recent run. Clicking a row uses browser-history-friendly navigation (`push`, not `replace`) so Back returns to the prior list state.

### Detail Mode (`/work?task={slug}`) — Kind-Aware (ADR-167)

In detail mode the page renders `<PageHeader />` as breadcrumb chrome, then `<WorkDetail />` as the identity + content surface. The selected task is fetched through `GET /api/tasks/{slug}` rather than inferred from the task list payload, so stale deep links now render an explicit "Task not found" state and fetch failures render an explicit retry state instead of silently dropping back to list mode. `WorkDetail` owns the real H1, metadata strip, and Run/Pause/Edit-via-chat actions; the middle band dispatches on `task.output_kind` because the four kinds need fundamentally different data:

| `output_kind` | Middle component | Renders |
|---|---|---|
| `accumulates_context` | `<TrackingMiddle>` | Domain folder link (`/context?domain={key}`) + last-run CHANGELOG (markdown summary of what was added) |
| `produces_deliverable` | `<DeliverableMiddle>` | The latest rendered HTML output in an iframe (or markdown) — this was the original `OutputPreview` |
| `external_action` | `<ActionMiddle>` | Action target (channel/page) + fire history with link-out to platform message |
| `system_maintenance` | `<MaintenanceMiddle>` | Hygiene log markdown + run history table. Objective block is suppressed (TP owns the contract, not the user). |

```
┌──────────────────────────────────────────────────────────────────────┐
│  Work › reporting's work › Daily Update                              │ ← PageHeader (chrome)
├──────────────────────────────────────────────────────────────────────┤
│  Daily Update                           [Run] [Pause] [Edit]         │ ← SurfaceIdentityHeader h1
│  Recurring · active · Reporting · daily · Next: 9h                   │    metadata under title
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
│  → Assigned to Reporting                                             │
└──────────────────────────────────────────────────────────────────────┘
```

### Filtering and deep-links

- `/work` — list mode, no filter
- `/work?agent={slug}` — list mode with the agent filter chip pre-applied (used by the breadcrumb's "Competitive Intelligence's work" segment and by AgentContentView's "See this agent's work" link)
- `/work?task={slug}` — detail mode for that task
- The breadcrumb (commit b033513) is the navigation between modes; clicking the `Work` segment from a detail returns you to list mode
- Invalid or stale `/work?task={slug}` links stay in detail mode and render an explicit not-found state with a "Back to work" action

### What Used to Live Here

- The left sidebar `WorkList` with auto-select-first → DELETED. Replaced by `WorkListSurface` (full-width list with filter chips, search, group-by). Landing on `/work` no longer shows you someone else's task by accident.
- The single one-shape `OutputPreview` inside `WorkDetail` → DELETED. Replaced by four kind-specific middle components in `web/components/work/details/`. The dispatch lives in `WorkDetail`.
- `ThreePanelLayout`'s left panel on `/work` → DELETED. The page no longer passes `leftPanel`. The layout is effectively two-panel (full-width center + FAB-overlay chat), which is what the page actually wanted all along.
- `WorkDetail`'s internal `<WorkHeader>` band (title + mode badge + status row + Next/Last run row) → DELETED in v2. The title moves to `<PageHeader />`'s breadcrumb (last segment). The metadata moves to PageHeader's `subtitle` slot. One row instead of four.
- `WorkDetail`'s internal `<ActionsRow>` (Run/Pause/Edit-via-chat at the bottom) → DELETED in v2. Actions move up to `<PageHeader />`'s `actions` slot, inline with the breadcrumb. One cluster of buttons instead of split top/bottom.
- The `★ Essential` badge next to the title → REMOVED in v2 (visual treatment only). The `essential` flag stays in the schema and DB and continues to gate archive in `routes/tasks.py`. Users discover it functionally — try to archive a daily-update and the API rejects it. No upfront badge needed.

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

In detail mode the page renders `<PageHeader />` followed by `<AgentContentView />`. `<SurfaceIdentityHeader />` inside AgentContentView is the real H1. The metadata strip stays compact (`Class · domain · N tasks · Ran Xh ago`); the detail body does the actual explanatory work.

The detail body follows two routing keys:

- **`agent.agent_class` chooses the top shell block**. Domain stewards foreground owned context, synthesizers foreground cross-domain synthesis, platform bots foreground platform connection plus source selection plus observation/write-back task mix, and Thinking Partner foregrounds orchestration/back-office posture.
- **`task.output_kind` chooses the assigned-work card shape**. Tracking tasks summarize context reads/writes, deliverable tasks summarize audience/deliverable, external-action tasks summarize target/delivery, and maintenance tasks summarize system purpose. `type_key` is allowed to specialize labels, but it does not fork the page architecture.

This keeps the surface scalable: new agent types usually fit an existing class shell, and new task types usually fit an existing `output_kind` card.

No-task states also vary by `agent_class`, not just copy:

- specialists explain missing domain-tracking work
- reporting explains upstream dependency on specialists
- integration bots surface actual connection state first, then explain observation vs write-back task mix
- Thinking Partner explains missing orchestration/back-office work

For platform bots specifically, `/agents?agent={slug}` is also the canonical management surface for source selection. Legacy `/context/slack` and `/context/notion` routes are compatibility redirects into the corresponding bot detail pages so `/context` stays the single filesystem browser.

### What Used to Live Here

- The left sidebar `AgentTreeNav` with auto-select-first → DELETED. Replaced by `AgentRosterSurface` (full-width grouped roster with health glances). Landing on `/agents` no longer shows you someone else's identity card by accident.
- `ThreePanelLayout`'s left panel on `/agents` → DELETED. Same as `/work`.
- `AgentContentView`'s internal `<AgentHeader>` band (avatar + name + mandate + class · domain · task count · last run) → DELETED in v2. The name moves to `<PageHeader />`'s breadcrumb (last segment). The metadata moves to PageHeader's `subtitle` slot. The "first sentence as mandate" tagline is dropped — the breadcrumb already declares the current agent.
- `meta-cognitive` (Thinking Partner class) was missing from `CLASS_LABELS` in v8/v9 — added in v2 so TP renders as "Thinking Partner" in the metadata strip instead of the raw key.

### What Moved Out Of Agents (v7.2) — And Where
| Old Tab | Content | Moved to |
|---|---|---|
| **Report** | Latest synthesis task outputs | `/work?task={slug}` → `DeliverableMiddle` (ADR-167) |
| **Data** | Domain entity dashboard | `/context?domain={key}` |
| **Pipeline** | Task config, schedule, actions | `/work` surface |
| **Agent** | Identity, instructions, work mix, feedback | Stayed here (`AgentContentView`, now the only thing on the page) |

---

## 4. Context (`/context`)

### Purpose
The only filesystem browser. Shows the workspace tree with domains, output folders, uploads, and IDENTITY/BRAND files. Unchanged from v7.2 structurally. ADR-163 adds one enhancement: inference-meta rendering.

Platform connection management and source selection do not live here anymore. Those belong to Settings > Connectors for connection lifecycle and the platform-bot agent detail surface for source scope.

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
- `web/components/shell/AuthenticatedLayout.tsx` — shell wrapper + TP provider. ADR-167 v2: no longer renders any breadcrumb chrome itself.
- `web/components/shell/ThreePanelLayout.tsx` — layout primitive. `leftPanel` is OPTIONAL (ADR-167) — pages omit it for the list/detail pattern; `/context` keeps it for filesystem tree nav.
- `web/components/shell/PageHeader.tsx` — in-page breadcrumb + title row (ADR-167 v2). Consumes `BreadcrumbContext`. Optional `subtitle` slot for metadata strip and `actions` slot for inline buttons. Falls back to `defaultLabel` when no segments are set. Replaces the deleted `GlobalBreadcrumb.tsx`.
- `web/contexts/BreadcrumbContext.tsx` — breadcrumb segment state with `kind`-tagged segments (commit b033513). Contract unchanged; only the renderer location moved.

### Chat
- `web/app/(authenticated)/chat/page.tsx` — Chat page (home). Loads scoped history, supplies first-party plus-menu actions, delegates everything else to `ChatSurface`.
- `web/components/chat-surface/ChatSurface.tsx` — page-level controller (ADR-165 v7, ADR-167 v5). Owns surface open state, parses TP workspace-state markers, renders `WorkspaceStateView` as a sibling modal; workspace-state toggle lives in `SurfaceIdentityHeader.actions`. Plus-menu "Update my context" action deleted in v7 — the `context` peer lens is the only re-entry path.
- `web/components/chat-surface/WorkspaceStateView.tsx` — single workspace-state component with four peer lens views (`context | briefing | recent | gaps`) as internal state branches (ADR-165 v7). Replaces the four sibling artifact files from v4.
- `web/components/chat-surface/ContextSetup.tsx` — identity capture atom (URL inputs + file uploads + free-text). Sole consumer: `WorkspaceStateView` `context` peer lens.
- `web/lib/workspace-state-meta.ts` — parser + stripper for TP's workspace-state HTML-comment marker (same pattern as ADR-162 inference-meta). Valid leads: `context | briefing | recent | gaps`.
- `docs/design/WORKSPACE-STATE-SURFACE.md` — design doc for `/chat` workspace state surface (ADR-165 v7)

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
- `web/components/agents/AgentContentView.tsx` — class-aware shell + output-kind-aware assigned-work cards (detail mode)

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
| 2026-04-09 | v9.5 | Agent detail consolidation amendment. `/agents?agent={slug}` is the single canonical detail surface; `/agents/{id}` now resolves and redirects there. `AgentContentView` no longer behaves like a generic identity card. Its top shell dispatches on `agent.agent_class`, and its assigned-work cards dispatch on task `output_kind` with optional `type_key` label specialization. This mirrors WorkDetail's kind-aware pattern and prevents bespoke per-agent page branches. |
| 2026-04-09 | v9.4 | ADR-167 v5 amendment — Page header split into two responsibilities. `<PageHeader />` becomes pure breadcrumb chrome (no title, no metadata, no actions — deleted `subtitle` and `actions` props). New `<SurfaceIdentityHeader />` primitive lives inside the surface content and renders the real H1 + metadata + optional actions. WorkDetail and AgentContentView each render their own SurfaceIdentityHeader at the top of their content stream. Additionally introduces the **nested document pattern**: any task-produced markdown/HTML content (output iframes in DeliverableMiddle, CHANGELOG in TrackingMiddle, hygiene log in MaintenanceMiddle, AGENT.md in InstructionsBlock) is wrapped in a bordered, visually inset card (`rounded-lg border border-border bg-muted/5`) so its internal H1s are unambiguously scoped as "content inside the task/agent" rather than competing with the surface's own H1. Uniform across all four `output_kind` middles. |
| 2026-04-09 | v9.3 | ADR-167 v4 amendment — `<PageHeader />` rewritten as pure chrome. v3 had promoted the last breadcrumb segment to a bold `h1.text-xl`, which duplicated against content that already had its own H1 (daily-update's rendered output renders `<h1>Daily Workspace Update — April 8, 2026</h1>` immediately inside the iframe). v3 also suppressed the breadcrumb entirely in list mode, making the header tone conditional. v4: (1) breadcrumb is ALWAYS present with the same muted tone across all states — list pages render the `defaultLabel` as a single-segment breadcrumb instead of suppressing the strip; (2) no bold title promotion anywhere — the last segment reads as chrome; (3) metadata + actions row stays as an optional second row but collapses when both are absent. Content's own H1 is now unambiguously the visual page title. |
| 2026-04-09 | v9.2 | ADR-167 v3 amendment — `<PageHeader />` restructured into two visually separated bands: Band 1 is a compact nav strip (breadcrumb path, muted), Band 2 is the title header (title + metadata subtitle + inline actions), with a divider between them. Previous v2 crammed breadcrumb + metadata + actions above one divider, which made the actual page title ambiguous against the content's own H1. v3 cleanly separates navigation (Band 1) from content-anchored header (Band 2). List-mode pages suppress Band 1 when there's only one segment. Applied uniformly across `/work`, `/agents`, `/context`. |
| 2026-04-08 | v9.1 | ADR-167 v2 amendment — Breadcrumb collapses into in-page `<PageHeader />`. `<GlobalBreadcrumb />` floating bar DELETED. `WorkDetail`'s internal `<WorkHeader>` and `<ActionsRow>` DELETED — title moves to PageHeader breadcrumb (last segment), metadata moves to PageHeader `subtitle`, Run/Pause/Edit-via-chat moves to PageHeader `actions`. `AgentContentView`'s internal `<AgentHeader>` band DELETED for the same reason. `★ Essential` visual badge removed (the flag stays — it's load-bearing for archive guard). `meta-cognitive` class label added (TP was rendering as raw key). |
| 2026-04-08 | v9 | ADR-167 — `/work` and `/agents` collapse from master-detail (left list + center detail + chat) into single surfaces with two URL-driven modes: list mode (full-width filterable list / roster) and detail mode (kind-aware detail dispatched on `task.output_kind`). `WorkList` and `AgentTreeNav` deleted. Auto-select-first deleted. `ThreePanelLayout.leftPanel` now optional. Four kind-aware middle components in `web/components/work/details/`. |
| 2026-04-08 | v8.1 | ADR-165 accepted: `/chat` remains the Chat surface, but changes internally from two-panel layout to a single TP console layer with artifact tabs for onboarding, briefing, recent work, and context gaps. |
| 2026-04-08 | v8 | ADR-163 — Four-surface restructure: Chat \| Work \| Agents \| Context. Activity absorbed. Agents page shrunk to identity. New /work surface. Mode collapse (surface only). Inference visibility via InferenceContentView. |
| 2026-04-06 | v7.2 | Task-class-aware tabs on Agents (superseded) |
| 2026-04-06 | v7.1 | Tabs restored (superseded) |
| 2026-04-06 | v7 | Unified shell, flat center panel (superseded) |
| 2026-04-06 | v6.1 | Global breadcrumb added |
| 2026-04-05 | v6 | Dashboard + TP chat two-panel (superseded) |
