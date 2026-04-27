# ADR-167: List/Detail Surfaces with Kind-Aware Detail

> **⚠ Amended by [ADR-225](ADR-225-compositor-layer.md) Phase 2 (2026-04-27).** The `WorkDetail.tsx::KindMiddle` switch this ADR introduced is DELETED. Replaced by `MiddleResolver` (in `web/components/library/`) which consults bundle SURFACES.yaml via the compositor (`/api/programs/surfaces`) and applies 4-tier match resolution (task_slug → output_kind+condition → output_kind → agent_role/class). The four kind-aware middles (DeliverableMiddle, TrackingEntityGrid, ActionMiddle, MaintenanceMiddle) are PRESERVED at their existing location (`web/components/work/details/`) — they are now the kernel-default fallback path the resolver uses when no bundle middle matches. Singular Implementation: ONE dispatch path lives in MiddleResolver. The substantive change is *who decides which middle renders* (declarative bundle manifest + resolver, not hardcoded switch); the kernel-default behavior for workspaces with no active program is unchanged.

**Status:** Accepted (v2 amendment 2026-04-08 — see end; KindMiddle dispatch superseded by ADR-225 Phase 2 2026-04-27)
**Date:** 2026-04-08
**Author:** KVK + Claude
**Supersedes:** ADR-163 surface internals (Work + Agents pages); does NOT supersede ADR-163 itself (the four-surface restructure stays intact)
**Amended by:** ADR-225 Phase 2 (KindMiddle switch deleted; MiddleResolver replaces it)
**Related:** ADR-163 (Surface Restructure), ADR-166 (Registry Coherence Pass — output_kind), ADR-225 (Compositor Layer — declarative middle dispatch), commit b033513 (linkable breadcrumb scope bar)

---

## Context

Three things shipped in the last week that, together, made the current Work and Agents page shape obsolete:

1. **ADR-163** introduced four top-level surfaces: Chat | Work | Agents | Context. It carved Work out as a first-class destination and shrunk Agents to "roster + identity card."

2. **ADR-166** classified every task by `output_kind` — a 4-value enum (`accumulates_context | produces_deliverable | external_action | system_maintenance`) that describes what shape of work the task produces. The enum is now load-bearing for pipeline routing, playbook injection, and DELIVERABLE.md handling.

3. **Commit b033513** ("feat: add linkable breadcrumb scope bar") upgraded the breadcrumb from inert label to navigable scope path with `kind`-tagged segments and `href` links. Each segment now promises a destination: clicking `Work` lands you on `/work`, clicking `Competitive Intelligence's work` lands you on `/work?agent=competitive-intelligence`.

The breadcrumb's promise is broken in three places:

- **`/work` is not a meaningful overview destination.** The page auto-selects the first task on mount (`useEffect` that runs whenever `selectedSlug` is null and the list is non-empty), so clicking the `Work` breadcrumb segment from a task detail just shows you a different task's detail with a different selection state. There is no "Work overview" view to land on.

- **`WorkDetail` is uniformly blind to `output_kind`.** It always renders the same shape: header → objective → `<OutputPreview>` (an iframe over `api.tasks.getLatestOutput()`) → actions row. That fetch path is correct for `produces_deliverable` tasks and **wrong for the other three kinds**:
  - `accumulates_context` tasks (`track-competitors`, `slack-digest`, etc.) write to a context domain, not to a task output folder. The iframe is empty.
  - `external_action` tasks (`slack-respond`, `notion-update`) write to a third-party platform. The artifact lives off-platform.
  - `system_maintenance` tasks (`back-office-agent-hygiene`, `back-office-workspace-cleanup`) emit a hygiene log + side effects. The framing is wrong.

- **The left panel is dead chrome on a master-detail page that always has something selected.** Both Work and Agents use `ThreePanelLayout` with a permanent left list panel, but auto-select-first means you never actually need to scan the list to pick something — the page always lands you in detail. The left panel is just navigation between detail views, not a meaningful surface.

The breadcrumb refactor and the `output_kind` carve are pulling in the same direction: **the surfaces want to be list-first, kind-aware, and navigation-driven from the breadcrumb**, not master-detail with a frozen left sidebar.

## Decision

Collapse `/work` and `/agents` from master-detail surfaces into single surfaces with two modes — **list mode** and **detail mode** — switched on URL state. Make detail mode kind-aware by dispatching the middle band on `task.output_kind`. Delete the auto-select-first behavior. The breadcrumb's promise becomes deliverable.

### 1. Two surface modes, one URL convention

| URL | Mode | Renders |
|---|---|---|
| `/work` | list | `<WorkListSurface>` — full-width filterable list of tasks |
| `/work?agent={slug}` | list (filtered) | `<WorkListSurface>` with the agent filter pre-applied |
| `/work?task={slug}` | detail | `<WorkDetail>` for that task (kind-aware) |
| `/agents` | list | `<AgentRosterSurface>` — full-width roster grouped by class |
| `/agents?agent={slug}` | detail | `<AgentDetail>` (today's `<AgentContentView>`) |
| `/agents/{id}` | compatibility | Resolve id → redirect to `/agents?agent={slug}` |

The `?agent=` query param on `/work` is preserved as a deep-link shortcut. The breadcrumb (b033513) already targets it; preserving it costs nothing and keeps the breadcrumb's "Competitive Intelligence's work" segment functional. List mode's filter UI also supports applying/removing the agent filter, so the query param is just one way to arrive at a filtered state — not the only way.

### 2. Delete auto-select-first

Both `WorkPage` and `AgentsPage` currently have a `useEffect` that auto-selects the first item when nothing is selected. **Both are deleted.** When you land on `/work` with no `?task=` param, you see the list. When you land on `/agents` with no `?agent=` param, you see the roster. Selection is now an explicit action, driven by URL transitions (clicking a row updates the URL, breadcrumb reflects the new scope, browser back returns to list).

### 3. Left panel dissolves

`ThreePanelLayout.leftPanel` becomes optional. `/work` and `/agents` no longer pass it. The center surface owns the full width. The chat panel stays exactly as it is (FAB-overlaid, default closed). The breadcrumb takes over the navigation role the left panel used to play.

`/context` retains the left panel — it has a legitimate tree-nav use case (filesystem browser) that the list/detail pattern doesn't fit.

### 4. Kind-aware detail middle band

The data shows that the four `output_kind` values need fundamentally different centerpiece data, not just different cosmetics:

| `output_kind` | Centerpiece data | Where it lives |
|---|---|---|
| `accumulates_context` | Domain folder + entity files + last-run CHANGELOG | `workspace_files` under `/workspace/context/{domain}/` and `/tasks/{slug}/outputs/{date}/output.md` |
| `produces_deliverable` | Latest rendered HTML/markdown output | `workspace_files` under `/tasks/{slug}/outputs/{date}/` |
| `external_action` | Run history with platform target + status + sent message | `agent_runs` table + `/tasks/{slug}/outputs/{date}/output.txt` |
| `system_maintenance` | Hygiene log + side-effect record | `agent_runs` + `/tasks/{slug}/outputs/{date}/output.md` |

The chrome (header, mode badge, agent, schedule, next/last run, Run now, Pause, Edit via chat, assigned-to footer) is uniform across all four — roughly 60% of the current `WorkDetail` component by line count. The middle band is where the four diverge irreconcilably.

`WorkDetail` becomes a thin shell:
```
WorkDetailShell
├── WorkHeader               (shared — chrome)
├── ObjectiveBlock           (shared — when objective exists; system_maintenance suppresses)
├── ┌──────────────────────┐
│   │ switch (output_kind) │
│   │  ├ accumulates → TrackingMiddle    │
│   │  ├ produces    → DeliverableMiddle │
│   │  ├ external    → ActionMiddle      │
│   │  └ system_main → MaintenanceMiddle │
│   └──────────────────────┘
├── ActionsRow               (shared — chrome)
└── AssignedAgentLink        (shared — chrome)
```

Four middle components, one shared shell. The dispatch is ~10 lines.

### 5. List mode for /work — filters, search, grouping

`WorkListSurface` is a full-width component with:

- **Filter chips** at the top, keyed on `output_kind`: `[ All ] [ Tracking ] [ Reports ] [ Actions ] [ System ]`. The chips are the primary navigation device.
- **Search box** that filters by task title (substring match).
- **Group-by dropdown**: defaults to "Output kind" (matching the chip filter). Other options: agent, status, schedule cadence.
- **Status filter**: defaults to active+paused, can include archived.
- **Agent filter**: pre-applied if `?agent={slug}` is in the URL; otherwise off. User can apply/remove via the list UI.
- **Row content**: status dot, title, mode badge, assigned agent, next/last run, essential star. Same row shape as today's `<WorkRow>`, just with the surface around it doing more.

Click a row → URL updates to `/work?task={slug}` → surface transitions to detail mode.

### 6. List mode for /agents — roster grouped by class

`AgentRosterSurface` is a full-width component with:

- **Grouped sections** by agent class: Domain Stewards (5) / Synthesizer (1) / Platform Bots (3) / Thinking Partner (1).
- **Per-agent card**: name, class label, domain (for stewards), active task count, approval rate (if ≥5 runs), last run, status indicator.
- **No filters in v1** — 9 agents at signup is small enough that grouping is sufficient. Filters can come later if the roster grows.

Click a card → URL updates to `/agents?agent={slug}` → surface transitions to detail mode. Legacy `/agents/{id}` links remain valid, but they redirect into the canonical surface instead of preserving a second detail implementation.

### 7. ThreePanelLayout becomes effectively two-panel-plus-FAB-chat

`ThreePanelLayout.leftPanel` goes from required to optional. The component name is preserved (rather than renaming to `TwoPanelLayout`) because `/context` still uses it with a left panel. This is cheaper than renaming and re-importing 4+ surfaces. The shape change is internal: when `leftPanel` is omitted, the center fills the available width and the collapsed-icon strip is not rendered.

## Why kind-aware detail (vs. one component with branching)

Three options were considered:

1. **Light** — keep one `WorkDetail` component, branch only the `OutputPreview` slot on `output_kind`. Smallest diff.
2. **Medium** — separate detail components per kind sharing a `WorkDetailShell` wrapper. **Chosen.**
3. **Heavy** — kind drives the whole route, full divergence. Overkill.

Option 1 was rejected because the three non-deliverable kinds need entirely different data fetches at the centerpiece, not just different rendering of the same data. Stuffing four mutually-exclusive data fetches into one component is strictly worse than splitting. Option 3 was rejected because the chrome (header, actions, footer) genuinely is shared — rebuilding it four times is strictly worse than wrapping it once.

## Why dissolve the left panel

The left panel was a remnant of the master-detail era. With auto-select-first deleted and the breadcrumb providing scope navigation, the panel adds nothing the breadcrumb + list mode don't already provide:

- Navigation between detail views? → Breadcrumb back to list, then click another row.
- "What's next on my schedule?" scan? → That belongs in list mode itself, sorted by `next_run_at`, not a permanent sidebar.
- Status overview? → Same — list mode with status grouping does this better than a cramped sidebar.

The left panel was solving the absence of a real list view. We're adding the real list view, so the left panel can go.

## Why query string URLs (not path segments)

`/work?task={slug}` instead of `/work/{slug}`. Three reasons:

1. **The breadcrumb (b033513) already targets query-string URLs.** Changing to path segments means rewriting the breadcrumb segment construction in two pages and potentially rewriting `BreadcrumbSegment.href` consumers.
2. **Legacy redirects from ADR-163** (`/tasks` → `/work`, `/workfloor` → `/chat`, `/orchestrator` → `/chat`) are written against the query-string convention. Changing to path segments triggers redirect surgery.
3. **Filter state and selection state co-exist.** `/work?agent=competitive-intelligence&task=competitive-brief` is a valid URL — agent filter pre-applied, task selected. Path segments would force a choice between `/work/agent/{slug}` and `/work/task/{slug}` and lose composability.

## Architectural constraints honored

- **ADR-163 stays intact.** Four surfaces. Same routes. Same toggle bar. This ADR changes only what happens *inside* `/work` and `/agents`.
- **ADR-166 stays intact.** `output_kind` enum, two-axis model, registry coherence — all unchanged. This ADR consumes `output_kind` as a routing key.
- **Commit b033513 (breadcrumb) stays intact.** No changes to `BreadcrumbContext`, `GlobalBreadcrumb`, or segment shape. The breadcrumb already does the right thing; it just needed real destinations to land on.
- **Backend untouched.** Zero API changes, zero schema changes, zero new endpoints. The four middle components consume existing `api.tasks.*` calls plus (for `TrackingMiddle`) a workspace-files read for the domain folder, which is already exposed.

## File-by-file change map

| File | Change |
|---|---|
| `web/components/shell/ThreePanelLayout.tsx` | `leftPanel` becomes optional. When omitted, center fills width and collapsed-icon strip not rendered. |
| `web/app/(authenticated)/work/page.tsx` | Switch on `?task=` for list/detail mode. Delete auto-select-first `useEffect`. List mode renders `<WorkListSurface>`, detail mode renders `<WorkDetail>`. No `leftPanel` prop. |
| `web/app/(authenticated)/agents/page.tsx` | Switch on `?agent=` for list/detail mode. Delete auto-select-first `useEffect`. List mode renders `<AgentRosterSurface>`, detail mode renders `<AgentContentView>`. No `leftPanel` prop. |
| `web/app/(authenticated)/agents/[id]/page.tsx` | Compatibility route only. Resolve id/slug and redirect to `/agents?agent={slug}` so there is one canonical detail surface. |
| `web/components/work/WorkList.tsx` | DELETED. Replaced by `WorkListSurface.tsx` (full-width with filters, search, grouping). |
| `web/components/work/WorkListSurface.tsx` | NEW. Full-width list with filter chips, search, group-by, agent filter from URL. |
| `web/components/work/WorkDetail.tsx` | Refactored to thin shell. Header, objective, actions row, assigned-to footer kept. `OutputPreview` extracted to `details/DeliverableMiddle.tsx`. Dispatches middle band on `task.output_kind`. |
| `web/components/work/details/DeliverableMiddle.tsx` | NEW. Today's `OutputPreview` extracted unchanged. Renders for `produces_deliverable` tasks. |
| `web/components/work/details/TrackingMiddle.tsx` | NEW. Renders domain status (entity count, freshness) + link to `/context?domain={key}` + last-run CHANGELOG (markdown summary from `outputs/{date}/output.md`). |
| `web/components/work/details/ActionMiddle.tsx` | NEW. Renders action history (when, target, status) from `agent_runs` + sent-message preview + link out to platform target. |
| `web/components/work/details/MaintenanceMiddle.tsx` | NEW. Renders hygiene log table from `outputs/{date}/output.md` + run history from `agent_runs`. |
| `web/components/agents/AgentTreeNav.tsx` | DELETED. Replaced by `AgentRosterSurface.tsx`. |
| `web/components/agents/AgentRosterSurface.tsx` | NEW. Full-width roster grouped by agent class with health glances per card. |
| `web/components/agents/AgentContentView.tsx` | Canonical agent detail body. Top shell varies by `agent_class`; assigned-work cards vary by task `output_kind`; `type_key` only lightly specializes labels. |
| `docs/design/SURFACE-ARCHITECTURE.md` | Bump to v9. Document list/detail mode collapse and kind-aware detail. |
| `docs/adr/ADR-167-list-detail-surfaces.md` | THIS FILE. New. |
| `CLAUDE.md` | ADR-167 entry added to ADR list. |

## What this does NOT touch

- ADR-163 four-surface restructure
- ADR-166 registry coherence
- Backend (zero changes)
- DB schema (zero changes)
- Legacy redirects (`/tasks`, `/workfloor`, `/orchestrator`)
- Chat panel behavior (FAB-overlaid, default closed)
- `WorkModeBadge`, `taskModeLabel()` mode collapse
- `/context` page (keeps its left panel)
- `/chat` page (already redesigned per ADR-165)
- Breadcrumb context, segment shape, or rendering

## Validation plan

- TypeScript clean (`tsc --noEmit` exit 0)
- Manual smoke test on KVK's actual data:
  - `/work` lands on list, no auto-selection, filter chips visible
  - Click `[ Tracking ]` chip → only `accumulates_context` tasks shown
  - Click a `track-competitors` row → detail mode with `<TrackingMiddle>` (not iframe)
  - Click `Work` breadcrumb → returns to list mode (preserved filter state OK)
  - `/work?agent=competitive-intelligence` → list mode with agent filter pre-applied
  - `/agents` lands on roster grouped by class
  - Click an agent card → identity detail
  - Click `Agents` breadcrumb → returns to roster
- Verify `daily-update` (produces_deliverable, essential) shows correct iframe preview
- Verify `back-office-agent-hygiene` (system_maintenance) shows hygiene log, not iframe

## Risks

- **Roster v1 might be too thin.** With 9 agents grouped into 4 sections, the roster surface might feel under-built compared to the work list. Acceptable in v1 — the structure is right, density can be added later. If it feels wrong in dogfooding we revisit.
- **Filter state vs URL state ambiguity.** If the user applies filters in the list UI, do those reflect in the URL? In v1: only the agent filter does (preserves the breadcrumb deep-link contract). Other filters (output_kind, status, schedule) live in component state only. If users want shareable filtered URLs we add more query params later.
- **No auto-select means landing on /work after a clean signup shows an empty-ish surface.** With KVK's 3 tasks this is fine. With a brand-new workspace (just `daily-update`) it's a list of one. Acceptable — the list grows organically and the daily-update anchor (ADR-161) ensures the list is never empty.

## Implementation status

- Phase 1 ✓: ADR + ThreePanelLayout `leftPanel` optional
- Phase 2 ✓: Extracted `DeliverableMiddle`, built `Tracking/Action/Maintenance` middles, refactored `WorkDetail` to dispatch
- Phase 3 ✓: Refactored `WorkPage` list/detail mode + built `WorkListSurface`
- Phase 4 ✓: Refactored `AgentsPage` list/detail mode + built `AgentRosterSurface`
- Phase 5 ✓: Updated SURFACE-ARCHITECTURE.md to v9, CLAUDE.md, smoke tested, committed (`d3b1bb4`)
- Phase 6 ✓ (v2 amendment): Breadcrumb collapse into PageHeader — see below

---

## V2 Amendment — Breadcrumb collapse into PageHeader

**Date:** 2026-04-08 (same day as v1)
**Trigger:** First dogfood of v1 surfaced two issues:
1. The separate `<GlobalBreadcrumb />` bar floating between the global header and `<main>` felt detached from the surface content.
2. The `WorkDetail` header band was re-stating the title that was already visible in the breadcrumb one row above. Detail pages had two competing "where am I" rows. The `★ Essential` badge added more visual weight to a row that was already redundant.

### Decision (v2)

**Move the breadcrumb out of the global layout and into the page content as a `<PageHeader />` component.** Each surface renders `<PageHeader />` as the first child of `ThreePanelLayout.children`. The breadcrumb's last segment IS the page title, so the per-page title bands inside `WorkDetail` and `AgentContentView` collapse into the row above.

This is **not** a new ADR. It's the same intent as v1 (the breadcrumb-as-navigation thesis from commit b033513 + ADR-167's surface mode collapse), just landing the visual simplification we missed on the first pass.

### What changed

| Before (v1) | After (v2) |
|---|---|
| `<GlobalBreadcrumb />` rendered in `AuthenticatedLayout` between global header and `<main>` | DELETED. `AuthenticatedLayout` no longer renders any breadcrumb chrome. |
| `WorkDetail` had its own `<WorkHeader>` band rendering title + mode badge + status row + Next/Last run row | DELETED. Title moves to PageHeader breadcrumb (last segment). Status metadata moves to PageHeader `subtitle` slot. |
| `WorkDetail` had `<ActionsRow>` with Run / Pause / Edit-via-chat at the bottom | DELETED. Actions move to PageHeader `actions` slot, inline with the breadcrumb. |
| `★ Essential` badge rendered next to the title | REMOVED. The `essential` flag stays in the schema and the DB (it's load-bearing — gates archive in `routes/tasks.py`). Users discover it functionally when they try to archive a daily-update and the API rejects it. No visual badge needed. |
| `AgentContentView` had its own `<AgentHeader>` band with avatar + name + class + domain + active task count + last run | DELETED. Identity metadata moves to PageHeader `subtitle`. The "first sentence as mandate" tagline is dropped (the breadcrumb already declares the current agent). |
| Pages set breadcrumb segments via `useEffect` and the global bar rendered them | UNCHANGED. Pages still call `setBreadcrumb()` with the same segment shape. Only the renderer location changes. |

### New file

- `web/components/shell/PageHeader.tsx` — consumes `BreadcrumbContext`, renders the segments inline as a `Surface › ancestor › current` path. Optional `subtitle` slot for the metadata strip and `actions` slot for inline buttons. Falls back to `defaultLabel` when no breadcrumb segments are set (so list-mode pages always have a title).

### Deleted files

- `web/components/shell/GlobalBreadcrumb.tsx` — the separate floating bar. Replaced entirely by `PageHeader`.

### Modified files

- `web/components/shell/AuthenticatedLayout.tsx` — drops `<GlobalBreadcrumb />` from the layout
- `web/app/(authenticated)/work/page.tsx` — renders `<PageHeader subtitle={metadata strip} actions={Run/Pause/Edit} />` as first child of ThreePanelLayout. Imports `WorkModeBadge`, `formatRelativeTime`, action handlers stay on the page.
- `web/app/(authenticated)/agents/page.tsx` — renders `<PageHeader subtitle={class · domain · tasks · last run} />` as first child
- `web/app/(authenticated)/context/page.tsx` — renders `<PageHeader defaultLabel="Context" />`. The context breadcrumb is built from the workspace tree path on selection (unchanged).
- `web/components/work/WorkDetail.tsx` — drops `WorkHeader`, `ActionsRow`, the `essential` star handling, and the `onRun`/`onPause`/`busy` props. Now content-only: ObjectiveBlock + KindMiddle + AssignedAgentLink.
- `web/components/agents/AgentContentView.tsx` — drops `AgentHeader` and the mandate-extraction helper. Now content-only: IdentityCard + HealthCard. Adds `meta-cognitive` to `CLASS_LABELS` (was missing — TP showed up as the raw key).

### Visual result

```
┌──────────────────────────────────────────────────────────────────────┐
│ yarnnn                   [Chat | Work | Agents | Context]      KV    │ ← global header (unchanged)
├──────────────────────────────────────────────────────────────────────┤
│ Work › reporting's work › Daily Update         [Run] [Pause] [Edit]  │ ← PageHeader: breadcrumb + actions
│ Recurring · Active · Reporting · daily · Next: in 1h                 │ ← PageHeader subtitle: metadata strip
├──────────────────────────────────────────────────────────────────────┤
│  Objective                                                           │
│  ...                                                                 │
│  [kind-aware middle band]                                            │
│  ...                                                                 │
│  → Assigned to Reporting                                             │
└──────────────────────────────────────────────────────────────────────┘
```

The detail page goes from **5 stacked bands** (header / objective / output / actions / footer) to **3** (PageHeader / objective / kind-middle, plus inline footer). Bands shrink, whitespace tightens, the page reads as one cohesive view instead of a stack of competing chrome.

For list-mode pages:

```
┌──────────────────────────────────────────────────────────────────────┐
│ yarnnn                   [Chat | Work | Agents | Context]      KV    │
├──────────────────────────────────────────────────────────────────────┤
│ Agents                                                               │ ← PageHeader: just the surface label
├──────────────────────────────────────────────────────────────────────┤
│ Domain Stewards · 5                                                  │ ← roster section starts immediately
│ ...                                                                  │
└──────────────────────────────────────────────────────────────────────┘
```

The previous version showed an empty floating bar above the roster (because list mode called `clearBreadcrumb()`); v2 always renders at least the surface label so the page never has an empty title slot.

### What didn't change in v2

- ADR-167 v1 architecture (list/detail mode collapse, kind-aware detail, deleted left sidebars, deleted auto-select-first)
- `BreadcrumbContext` shape (segments, kinds, hrefs)
- Pages still call `setBreadcrumb()` with the same multi-segment paths in detail mode
- The breadcrumb's deep-link contract (`/work?agent=competitive-intelligence` from "Competitive Intelligence's work" segment)
- The four kind-aware middle components in `web/components/work/details/`
- Backend (zero changes)

### `essential` flag — fate

Kept in the schema. Kept in `routes/tasks.py` archive guard. Kept in `workspace_init.py` daily-update scaffold. Kept on `Task` TypeScript type. The semantic meaning ("this task cannot be archived, system metadata") is load-bearing (ADR-161). What v2 removes is the **visual** treatment — no `★ Essential` badge, no gold star next to the title. The protection it provides is enforced functionally; the user discovers it when they try to archive and can't, not by reading a star upfront.
