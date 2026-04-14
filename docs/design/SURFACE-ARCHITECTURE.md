# Surface Architecture — Chat + Work + Context + Agents

**Version:** v11.0 (2026-04-14)
**Status:** Canonical
**Governed by:** [ADR-180](../adr/ADR-180-work-context-surface-split.md) — Work/Context Surface Split
**Active decisions:**
- [ADR-180](../adr/ADR-180-work-context-surface-split.md) — nav reorder, Work = operational, Context = knowledge (outputs + domains)
- [ADR-165 v5](../adr/ADR-165-workspace-state-surface.md) — `/chat` workspace state surface (TP-directed, single component, four lead views)
- [ADR-166](../adr/ADR-166-registry-coherence-pass.md) — task `output_kind` enum (4 values)
- [ADR-167](../adr/ADR-167-list-detail-surfaces.md) — `/work` and `/agents` list/detail collapse. **v2 amendment**: breadcrumb in `<PageHeader />`.
- [AGENT-AND-TASK-SURFACE-PATTERNS](./AGENT-AND-TASK-SURFACE-PATTERNS.md) — shell and no-task-state rules

**Supersedes:**
- v10.0 (2026-04-14) — Work hosted both outputs and operational detail; Agents at position 3
- v9.5 (2026-04-09) — kind-aware detail spec, run now removed, overflow menu for lifecycle
- v9 (2026-04-08) — list/detail collapse with separate GlobalBreadcrumb bar
- v8 (2026-04-08) — three-panel master-detail on Work and Agents

---

## Design Thesis: Four Surfaces, One Question Each

| Priority | Surface | Route | The question it answers | The answer |
|---|---|---|---|---|
| 1 | **Chat** | `/chat` | "What should I do? What's happening?" | TP chat + one active structured artifact |
| 2 | **Work** | `/work` | "Is my work configured, healthy, and running?" | Task list (operational) + task detail (schedule, health, config) |
| 3 | **Context** | `/context` | "What does my workspace know? What has it produced?" | Outputs + accumulated domains + uploads + settings |
| 4 | **Agents** | `/agents` | "Who's on my team?" | Roster + agent detail with class-aware identity and work-shape summaries |

**Priority order = navigation frequency.** Chat is where work is directed and results surface. Work is checked daily. Context is read when you want to consume what the system produced. Agents is a reference surface, visited rarely.

**Work is operational only** (ADR-180). Work answers: "is this task configured, healthy, and running correctly?" Work does NOT show task output documents or accumulated files — those live in Context. For `produces_deliverable` and `accumulates_context` tasks, Work shows a direct link to Context.

**Context is the knowledge surface** (ADR-180). Context hosts both accumulated domain knowledge (`/workspace/context/`) and task deliverable outputs (`/tasks/{slug}/outputs/latest/`). Four top-level sections: Context (domains), Outputs (task deliverables), Uploads, Settings.

**Agents is position 4.** Under ADR-176, agents serve work — they are the labor pool, not the organizing principle. The roster is a reference, not a daily destination.

Four destinations. Each answers exactly one question. No overlap.

The old `/activity` page is **deleted**. Its content is absorbed into the surfaces that naturally own it: per-task activity to `/work`, per-agent activity to `/agents`, workspace-wide activity to the Chat briefing dashboard, diagnostic events to Settings → System Status.

---

## Route Map

```
/chat                           → Chat (home). TP chat + one active artifact tab.
/work                           → Work LIST mode. Full-width filterable list of tasks.
/work?agent={slug}              → Work LIST mode with the agent filter pre-applied.
/work?task={slug}               → Work DETAIL mode. Operational detail (schedule, health, config).
/context                        → Context. Workspace knowledge browser. (Retains left tree nav.)
/context?domain={key}           → Context pre-filtered to a domain folder.
/context?path=/tasks/{slug}/outputs/latest → Context showing a task's latest output.
/agents                         → Agents LIST mode. Full-width team roster grouped by class.
/agents?agent={slug}            → Agents DETAIL mode. Class-aware identity + work-shape summaries.
/agents/{id}                    → Compatibility entry. Redirects to `/agents?agent={slug}`.
/settings                       → Settings. Memory, brand, system status.
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
│ yarnnn                   [Chat | Work | Context | Agents]     Avatar │ ← global header (logo / toggle / avatar)
└──────────────────────────────────────────────────────────────────────┘
```

The global header is **just** logo + toggle bar + avatar. There is no separate breadcrumb bar below it. The breadcrumb lives **inside each surface** as a `<PageHeader />` component (ADR-167 v2) — see "Page header" below.

**Toggle bar** (`web/components/shell/ToggleBar.tsx`): four-segment pill `Chat | Work | Context | Agents`. Icons: `MessageCircle`, `Briefcase`, `FolderOpen`, `Users`. `HOME_ROUTE` is `/chat` — both new and returning users land there.

### Page header (ADR-167 v5)

Every surface renders `<PageHeader />` as the first row of its center content area. It is **pure navigation chrome** — the breadcrumb and nothing else. No title, no metadata, no actions. Those all live inside the surface content as a separate `<SurfaceIdentityHeader />` block where they belong alongside the content they describe.

```
┌──────────────────────────────────────────────────────────────────────┐
│ Work › Daily Update                                                  │ ← PageHeader: breadcrumb chrome (ADR-180: task-first)
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

| Surface state | Breadcrumb (ADR-180) |
|---|---|
| Chat | `Chat` |
| Work (list) | `Work` |
| Work (task detail, from Work) | `Work › Daily Update` — task-first, no agent middle segment |
| Work (task detail, from Agents) | `Agents › Researcher › Daily Update` — traces navigation history |
| Work (filtered by agent) | `Work` — agent filter shown as chip in list UI, not breadcrumb |
| Agents (list) | `Agents` |
| Agents (agent selected) | `Agents › Researcher` |
| Context (no selection) | `Context` |
| Context (domain selected) | `Context › Competitors` |
| Context (deep file) | `Context › Competitors › cursor › profile.md` |
| Context (task output) | `Context › Daily Update` — output as first-class knowledge item |

Pages set the breadcrumb segments via `setBreadcrumb()` in a `useEffect` (unchanged contract from b033513). PageHeader reads from the same context. List-mode pages clear the breadcrumb and PageHeader falls back to the surface label via `defaultLabel`.

---

## 1. Chat (`/chat`, HOME_ROUTE)

### Purpose
Dedicated TP (Thinking Partner) chat surface. The conversation column is the full surface — no always-on briefing side panel. Two structured modals (ADR-165 v8) opened independently: the **Overview modal** (read-only diagnostic dashboard, four tabs: What I know / Heads up / Last time / Team activity) and the **Onboarding modal** (first-run identity capture). TP opens either via HTML-comment markers (`<!-- workspace-state: ... -->` or `<!-- onboarding -->`); the user opens the Overview modal via the "Overview" button in the surface header. Two markers, two modals, never conflated.

For new users with an empty workspace, TP's first response opens the Onboarding modal (identity capture form). The daily-update task still runs (deterministic empty-state template from ADR-161).

### Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│ Thinking Partner                                [⊞ Overview]         │ ← SurfaceIdentityHeader
│                                                                      │    h1 + action button
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│                    (conversation thread)                             │
│                                                                      │
│                    [ input row ──────── → ]                          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

`<SurfaceIdentityHeader />` with "Thinking Partner" as the real H1 and the "Overview" button in the actions slot. The conversation column is centered at `max-w-3xl`. The Overview toggle (icon: `LayoutDashboard`) sits alongside the page identity where it belongs, matching the Run/Pause/Edit pattern on /work detail.

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

### Detail Mode (`/work?task={slug}`) — Kind-Aware (v10, 2026-04-14)

In detail mode the page renders `<PageHeader />` as breadcrumb chrome, then `<WorkDetail />` as the identity + content surface. The selected task is fetched through `GET /api/tasks/{slug}`.

**Design principle: each output_kind answers a different question.** A single shared header/action bar is wrong because the four kinds have fundamentally different user mental models:

| `output_kind` | User question | Primary affordance |
|---|---|---|
| `produces_deliverable` | "What did it produce?" | Output artifact — full-width hero |
| `accumulates_context` | "Is it healthy? What's it collecting?" | Run health + compact receipts |
| `external_action` | "What did it last send? Fire it again?" | Fire button + send history |
| `system_maintenance` | "Is the system healthy?" | Log output, no user actions |

**Header strip is kind-aware** — each kind gets a purpose-fit metadata strip and action set:

| `output_kind` | Metadata strip | Actions |
|---|---|---|
| `produces_deliverable` | Mode badge · Schedule · `Last output: {date}` | `···` overflow (Pause/Resume, Archive) |
| `accumulates_context` | Mode badge · Schedule · `Next: {rel}` · `Last run: {date}` · domain link | `···` overflow (Pause/Resume, Archive) |
| `external_action` | Mode badge · `Target: {delivery}` · `Last fired: {date}` | **Fire** (primary) · `···` overflow (Archive) |
| `system_maintenance` | Mode badge · Schedule · `Last run: {date}` | *(none)* |

**Run now is removed.** Triggering a run is an intent expressed via TP ("run this now"), not a button on the detail page. The one exception is `external_action` tasks where firing IS the whole workflow — those get an explicit **Fire** primary action.

**Pause/Resume moved to overflow (`···`).** Lifecycle management is rare; it doesn't warrant a persistent visible button. An overflow menu keeps it accessible without cluttering the header.

**Objective block is kind-gated.** Only `produces_deliverable` tasks show the Objective block — deliverable/audience/purpose/format is meaningful for output tasks. `accumulates_context` instead shows an inline "Feeds →" summary in the header strip. `external_action` and `system_maintenance` suppress the objective block entirely.

**Agent footer removed.** The assigned agent is visible in the list row and the breadcrumb. It adds no value in the detail's own footer.

**Middle components by kind:**

| `output_kind` | Middle component | Shape |
|---|---|---|
| `accumulates_context` | `<TrackingMiddle>` | Domain folder link + compact run receipts (not a document card) |
| `produces_deliverable` | `<DeliverableMiddle>` | Latest rendered HTML/markdown as full hero (no change) |
| `external_action` | `<ActionMiddle>` | Latest payload card + fire history list |
| `system_maintenance` | `<MaintenanceMiddle>` | Hygiene log + run history (no change) |

**`TrackingMiddle` shape change**: was a rendered document card (CHANGELOG markdown). Now a compact health view — domain link + short run receipts (date, what changed). The domain folder is where the content lives; the task detail is just the health dashboard. `context_writes` registry fallback added: if TASK.md parsing fails to populate `task.context_writes`, `TrackingMiddle` infers the domain from `task.type_key` via a local map.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Work › Slack Bot › Slack Digest                                      │ ← PageHeader (chrome)
├──────────────────────────────────────────────────────────────────────┤
│  Slack Digest                                              [···]      │ ← SurfaceIdentityHeader h1
│  Recurring · Daily · Next: in 9h · Last run: 4h ago                  │   metadata strip (no Pause btn)
│  → /workspace/context/slack/                                         │   domain link inline
├──────────────────────────────────────────────────────────────────────┤
│  Apr 14 09:00  3 channels · 4 new observations                       │ ← compact run receipts
│  Apr 13 09:00  3 channels · 1 new observation                        │   (not a document card)
│  Apr 12 09:00  2 channels · 0 new                                    │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  Work › Reporting › Daily Update                                      │ ← PageHeader (chrome)
├──────────────────────────────────────────────────────────────────────┤
│  Daily Update                                              [···]      │ ← SurfaceIdentityHeader h1
│  Recurring · Daily · Last output: Apr 14                             │   metadata strip
├──────────────────────────────────────────────────────────────────────┤
│  Objective                                                           │ ← only for produces_deliverable
│  · Deliverable: Daily workspace update                               │
│  · Audience: You — quick morning scan                                │
├──────────────────────────────────────────────────────────────────────┤
│  Latest output  ·  2026-04-14T09:00                                  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ [iframe with rendered HTML — DeliverableMiddle]                │  │
│  └───────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  Work › Slack Bot › Slack Post                                        │ ← PageHeader (chrome)
├──────────────────────────────────────────────────────────────────────┤
│  Slack Post                                    [Fire ↗]  [···]        │ ← Fire is primary action
│  One-time · Target: #general · Last fired: Apr 12                    │
├──────────────────────────────────────────────────────────────────────┤
│  Latest payload  ·  Apr 12                                           │ ← ActionMiddle
│  ┌──────────────────────────────────────────────┐                   │
│  │ [sent message markdown]                       │                   │
│  └──────────────────────────────────────────────┘                   │
│  Fire history …                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Filtering and deep-links

- `/work` — list mode, no filter
- `/work?agent={slug}` — list mode with the agent filter chip pre-applied (used by the breadcrumb's "Researcher's work" segment and by AgentContentView's "See this agent's work" link)
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
│  Specialists · 6 (ADR-176 universal roles)                           │
│  Assigned to tasks by TP. Accumulation or production phase.          │
│  ┌──────────────────────────┐  ┌──────────────────────────┐         │
│  │ 🧠 Researcher             │  │ 🧠 Analyst                │         │
│  │ specialist · accumulation │  │ specialist · accumulation │         │
│  │ 2 tasks · 2h ago · 100%  │  │ 1 task · 16h ago          │         │
│  └──────────────────────────┘  └──────────────────────────┘         │
│  ┌──────────────────────────┐  ┌──────────────────────────┐         │
│  │ 🧠 Writer                 │  │ 🧠 Tracker                │         │
│  │ specialist · accumulation │  │ specialist · accumulation │         │
│  │ 2 tasks · 16h ago        │  │ 1 task · 2h ago           │         │
│  └──────────────────────────┘  └──────────────────────────┘         │
│  ┌──────────────────────────┐  ┌──────────────────────────┐         │
│  │ 🎨 Designer               │  │ 💬 Thinking Partner       │         │
│  │ specialist · production   │  │ meta-cognitive            │         │
│  │ 0 tasks · never run      │  │ 2 tasks · daily           │         │
│  └──────────────────────────┘  └──────────────────────────┘         │
│                                                                      │
│  Platform Bots · 3                                                   │
│  Tied to platform integrations. Bridge external surfaces.            │
│  ┌──────────────────────────┐  ┌──────────────────────────┐         │
│  │ 🔌 Slack Bot              │  │ 🔌 Notion Bot             │         │
│  └──────────────────────────┘  └──────────────────────────┘         │
└──────────────────────────────────────────────────────────────────────┘
```

**Grouping** is by class (ADR-176): Specialists (6, including TP) / Platform Bots (3). Each section has a one-line description of what that class does. Per-card health glance shows: status, phase (accumulation/production/meta-cognitive), active task count, last run (color-coded by freshness), approval rate (only if `version_count >= 5`).

Click a card → URL transitions to `/agents?agent={slug}` → detail mode.

### Detail Mode (`/agents?agent={slug}`) — `AgentContentView`

In detail mode the page renders `<PageHeader />` followed by `<AgentContentView />`. `<SurfaceIdentityHeader />` inside AgentContentView is the real H1. The metadata strip stays compact (`Class · domain · N tasks · Ran Xh ago`); the header action area carries the single primary CTA (`Create Task`), and the detail body does the actual explanatory work.

The detail body follows two routing keys:

- **`agent.agent_class` chooses the component order and shell block**. Each class follows a different layout rationale:
  - **specialist** (Researcher, Analyst, Writer, Tracker, Designer): Role → Tasks → Capability summary. Tasks come first because the work is the point; capabilities explain how this specialist contributes.
  - **platform-bot**: Role → Connection → Source selection → Tasks. Connection state and source selection *enable* tasks, so they surface above the task list.
  - **meta-cognitive (TP)**: Role (no highlights, no "Create Task" CTA) → Tasks. TP page is minimal — no feedback distillation, no chip noise.
- **`task.output_kind` chooses the assigned-work card shape**. Tracking tasks say which folder they are working in, deliverable tasks say which folder they read from, external-action tasks summarize target/delivery, and maintenance tasks summarize system purpose. `type_key` is allowed to specialize labels, but it does not fork the page architecture.

This keeps the surface scalable: new agent types usually fit an existing class shell, and new task types usually fit an existing `output_kind` card.

No-task states vary by `agent_class`:

- specialists point to TP for tracker setup (not a generic "start one" instruction)
- synthesizer points to TP once specialists have trackers running
- platform bots point to connection/source setup above, then TP for digest task
- Thinking Partner names the missing maintenance work

Highlight chips (the small stat pills in the role block) are suppressed when zero — showing `0 tracking tasks` is noise, not signal. TP's `highlights()` returns `[]` unconditionally.

For platform bots specifically, `/agents?agent={slug}` is the canonical management surface for source selection. `/context` stays the single filesystem browser and no longer owns per-platform management pages.

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
- `web/components/chat-surface/ChatSurface.tsx` — page-level controller (ADR-165 v8). Owns Overview + Onboarding modal open state, parses both TP markers, renders both modals as siblings. "Overview" toggle lives in `SurfaceIdentityHeader.actions`.
- `web/components/chat-surface/WorkspaceStateView.tsx` — Overview modal: four read-only tabs (What I know / Heads up / Last time / Team activity). No `isEmpty` prop, no soft gate. (ADR-165 v8.)
- `web/components/chat-surface/OnboardingModal.tsx` — Onboarding modal: wraps ContextSetup for first-run identity capture. Opened by TP `<!-- onboarding -->` marker only. (ADR-165 v8.)
- `web/components/chat-surface/ContextSetup.tsx` — identity capture atom (URL inputs + file uploads + free-text). Sole consumer: `OnboardingModal`.
- `web/lib/workspace-state-meta.ts` — TWO parsers + TWO strippers for TP markers (workspace-state leads: `overview | flags | recap | activity`; onboarding: presence-only). Same pattern as ADR-162 inference-meta.
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
| 2026-04-10 | v9.6 | Agent detail UX pass. Component ordering now varies by `agent_class`: domain-stewards show Tasks before Context folder (work is the point, folder is where it lives); platform-bots keep Connection → Sources → Tasks (must connect before tasks make sense); TP/meta-cognitive omits highlights chips, `Create Task` CTA, and `LearnedBlock`. Highlight chips suppressed when zero. Domain trailing `/` removed from metadata strip. Role block titles and descriptions rewritten to be human-readable per class. Empty-state copy updated to reference TP for setup. Section labels: "Folder" → "Context folder", "Assigned work" → "Work". |
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
