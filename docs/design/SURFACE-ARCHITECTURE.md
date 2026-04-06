# Surface Architecture — Chat + Agents + Context + Activity

**Date:** 2026-04-06 (v7.2 — task-class-aware tabs, BI + intelligence room framing)
**Status:** Implementing
**Supersedes:** v7.1 (2026-04-06, tabs restored), v7 (unified shell), v6.1 (global breadcrumb)
**Depends on:** [ADR-138](../adr/ADR-138-agents-as-work-units.md) (Agents as Work Units), [ADR-140](../adr/ADR-140-agent-workforce-model.md) (Workforce Model), [ADR-152](../adr/ADR-152-unified-directory-registry.md) (Directory Registry)

---

## Design Thesis: Unified Shell, Intelligence Surfaces, One File Browser

Every surface shares **one shell** (`ThreePanelLayout`): optional left panel + center content + collapsible TP chat right panel + FAB toggle. The shell is a shared component — pages only provide the content, not the chrome.

**Three principles:**

1. **Agents page = intelligence surface.** Shows composed dashboards from workspace files — entity cards, synthesis, freshness signals. No file browsing. "View files" links to Context page. Single scrollable view per agent (no tabs).
2. **Context page = the only file browser.** All raw file viewing happens here. Agents page links into it with domain pre-filtering (`/context?domain=competitors`). One place to browse files, not three duplicate implementations.
3. **Shared shell, not duplicated layout.** Three-panel layout, chat panel, FAB toggle, data loading, polling, timestamp utilities — extracted once, used everywhere.

| Surface | Route | Nav Label | Center Content | Chat (right panel) |
|---------|-------|-----------|---------------|-------------------|
| **Home** | `/chat` | Home | Daily briefing dashboard | TP chat (unified session) |
| **Agents** (overview) | `/agents` | Agents | Agent roster (left) + empty state (center) | TP chat |
| **Agents** (selected) | `/agents?agent={slug}` | Agents | Agent roster (left) + scrollable intelligence view (center) | TP chat (agent-scoped context) |
| **Context** | `/context` | Context | Workspace tree (left) + file/folder viewer (center) | TP chat |
| **Context** (deep-linked) | `/context?domain={key}` | Context | Pre-filtered to domain folder | TP chat |
| **Activity** | `/activity` | Activity | Timeline feed | No chat |

**Key shift from v6.1:**

1. **Kill file browsing on Agents page.** `DomainBrowse`, `SynthesizerBrowse`, `EmptyBrowse` deleted. The Browse tab dissolves — its dashboard portion (AgentDashboard) becomes the default center view. "Browse files" links to `/context?domain={domain}` instead of embedding a second file browser.
2. **Flatten agent center panel.** Three tabs (Browse/Tasks/Agent) collapse into one scrollable view: dashboard (top) → tasks (middle) → agent identity (bottom). No tab switching needed.
3. **Extract shared shell.** `ThreePanelLayout` component handles: left panel (collapsible, configurable width), center content, right chat panel (collapsible, FAB toggle), chat header. Pages pass content, not layout code.
4. **Extract shared utilities.** One `formatRelativeTime()`, one freshness classifier, one `useAgentsAndTasks()` hook with built-in polling. No more three implementations of the same helpers.
5. **Context page gains domain pre-filtering.** URL param `?domain=competitors` auto-navigates to `/workspace/context/competitors` on load. Agents page "View files" links here.

---

## Route Map

```
/chat                → Home page. Daily briefing + TP chat. Full-page, unscoped.
/agents              → Agents page. Agent roster (left) + scrollable intelligence view (center). Agent-scoped TP panel.
/agents?agent={slug} → Agent selected. Dashboard + tasks + identity (single scroll).
/context             → Workspace explorer. Cross-agent domains, uploads, settings.
/context?domain={key}→ Pre-filtered to domain folder (deep-link from Agents page).
/activity            → Temporal activity log. Upcoming runs, past events.
/settings            → Billing, usage, memory, system, connectors, account.
```

**Deleted routes:** `/workfloor` (→ `/agents`), `/tasks` (→ `/agents`), `/orchestrator` (legacy redirect).

---

## Navigation

```
┌─────────────────────────────────────────────────────────────┐
│ yarnnn / CI / cursor  │  [Home | Agents | Context | Activity]  │  User Menu │
└─────────────────────────────────────────────────────────────┘
  ↑ global breadcrumb         ↑ toggle bar                         ↑ avatar
```

**Header**: Logo + global breadcrumb (left), toggle bar (center), user menu (right).

**Global breadcrumb** (`BreadcrumbContext`): Pages set breadcrumb segments into a shared context; the header reads and renders them. Max 2 depth segments after the logo. Provides spatial awareness — "where in the room am I?" — consistent across all surfaces. Briefing room metaphor: the toggle bar tells you which room, the breadcrumb tells you where you're standing.

| Surface | Breadcrumb |
|---------|------------|
| Home | _(empty — just logo)_ |
| Agents (overview) | _(empty)_ |
| Agents (selected) | `/ Competitive Intelligence` |
| Agents (browsing file) | `/ Competitive Intelligence / cursor` |
| Context (domain selected) | `/ Competitors` |
| Context (deep file) | `/ Competitors / cursor` |
| Activity | _(empty)_ |

Key files: `web/contexts/BreadcrumbContext.tsx`, `web/components/shell/GlobalBreadcrumb.tsx`.

**Toggle bar**: Four-segment pill: `Home | Agents | Context | Activity`. `/agents` is `HOME_ROUTE` for returning users. New users (no tasks) land on `/chat` (Home) for onboarding. See [ONBOARDING-SCAFFOLD-AND-BRIEFING.md](ONBOARDING-SCAFFOLD-AND-BRIEFING.md) for Home page layout with daily briefing.

---

## 1. Home Page (`/chat` route, nav label "Home")

### Purpose

Daily command center. Two-panel layout: daily briefing dashboard on the left, TP chat on the right. For new users, ContextSetup replaces the dashboard.

The Home page dashboard content comes from the Reporting agent's daily-update task. Same data, rendered as a structured dashboard rather than a flat report.

See [ONBOARDING-SCAFFOLD-AND-BRIEFING.md](ONBOARDING-SCAFFOLD-AND-BRIEFING.md) for onboarding flow.

### Layout (returning user)

```
┌────────────────────────────────┬─────────────────────┐
│  DAILY BRIEFING DASHBOARD      │  TP CHAT             │
│                                │                      │
│  What happened (24h)           │  [conversation]      │
│  · CI: 2 profiles updated     │                      │
│  · Slack: 3 channels digested │                      │
│                                │                      │
│  What changed                  │                      │
│  · New competitor: Windsurf    │                      │
│  · Market trend: AI agents    │                      │
│                                │                      │
│  Coming up                     │                      │
│  · Tomorrow: Slack, GitHub    │                      │
│  · Monday: CI, Biz Dev       │                      │
│                                │                      │
│  Workspace signals             │  [+] Ask anything... │
│  8 agents · 6 tasks · 3 plat │                      │
└────────────────────────────────┴─────────────────────┘
```

### Layout (new user, no tasks)

ContextSetup as full-page overlay. Dashboard not rendered until workspace has active tasks.

### Properties

- **Session:** Unified workspace session (ADR-159)
- **Surface context:** `{ type: "home" }`
- **Chat panel:** Collapsible right panel, same as all other pages

---

## 2. Agents Page (`/agents`) — HOME

### Purpose

Primary working surface. Intelligence surface — shows what agents know and what they're doing, not their raw files. Three-panel layout: agent roster (left), scrollable intelligence view (center), TP chat (right).

### Layout (desktop ≥ 1024px)

**No agent selected:**

```
┌──────────────┬──────────────────────────┬──────────────────┐
│  LEFT PANEL  │    EMPTY STATE           │  (FAB only)      │
│  Agent List  │    "Select an agent"     │                  │
│  (280px)     │                          │                  │
├──────────────┼──────────────────────────┤                  │
│ AGENTS       │                          │                  │
│ 📁 Comp Intel│                          │                  │
│ 📁 Market Res│                          │                  │
│ 📁 Biz Dev   │                          │                  │
│ 📁 Operations│                          │                  │
│ 📁 Marketing │                          │                  │
│ CROSS-TEAM   │                          │                  │
│ 📁 Reporting │                          │                  │
│ INTEGRATIONS │                          │                  │
│ 📁 Slack Bot │                          │                  │
└──────────────┴──────────────────────────┴──────────────────┘
```

**Agent selected (single scrollable view):**

```
┌──────────────┬──────────────────────────┬──────────────────┐
│  LEFT PANEL  │  SCROLLABLE VIEW         │  RIGHT PANEL     │
│  Agent List  │                          │  ChatPanel       │
├──────────────┤  ┌─ HEADER ────────────┐ ├──────────────────┤
│              │  │ Competitive Intel    │ │                  │
│ AGENTS       │  │ Steward · Ran 2h ago│ │  TP Chat         │
│ ▸ Comp Intel │  └────────────────────┘ │  (agent-scoped)  │
│ 📁 Market Res│                          │                  │
│ 📁 Biz Dev   │  ── DASHBOARD ─────────  │                  │
│ 📁 Operations│  What's New              │                  │
│ 📁 Marketing │  · Cursor raised $900M   │                  │
│              │  Landscape               │                  │
│ CROSS-TEAM   │  [rendered synthesis]    │                  │
│ 📁 Reporting │  Competitors (6)         │                  │
│              │  [entity cards]          │                  │
│ INTEGRATIONS │  [View files →]          │                  │
│ 📁 Slack Bot │                          │                  │
│              │  ── TASKS ─────────────  │                  │
│              │  [task cards]            │                  │
│              │                          │                  │
│              │  ── AGENT ─────────────  │                  │
│              │  Identity · Instructions │                  │
│              │  History · Feedback      │                  │
└──────────────┴──────────────────────────┴──────────────────┘
```

### Center Panel: Pinned Header + Task-Class-Aware Tabs

When an agent is selected, the center panel shows a pinned header above **adaptive tabs** that depend on what task classes the agent has. Inspired by BI dashboards (Looker, Metabase) + intelligence room briefings.

**BI + Intelligence Room framing:**
- **Report** = the briefing on the analyst's desk. The rendered deliverable. (BI: the dashboard/report view)
- **Data** = the source files the analyst maintains. Accumulated context. (BI: the data explorer)
- **Pipeline** = the analyst's assignment and schedule. (BI: ETL/pipeline config)

```
┌──────────────────────────────────────────────────────────────┐
│  Competitive Intelligence                                     │
│  Domain Steward · competitors/ · Works weekly · Ran 2h ago    │
├──────────────────────────────────────────────────────────────┤
│  [Report]     [Data]     [Pipeline (2)]     [Agent]           │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  (active tab content — full height, own scroll)               │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

#### Tab visibility — task-class-aware

Tabs appear based on what the agent actually has, not its class:

| Agent has... | Tabs shown | Default tab |
|---|---|---|
| Synthesis + context tasks | Report · Data · Pipeline · Agent | Report |
| Context tasks only (no synthesis yet) | Data · Pipeline · Agent | Data |
| Synthesis tasks only (Reporting agent) | Report · Pipeline · Agent | Report |
| Platform bot (digest only) | Data · Pipeline · Agent | Data |

#### Report tab — "What did this agent produce?"

Latest synthesis task output rendered as hero. Version history below (prior outputs, click to view).

The report layout is **tailored per task type** — not a generic iframe:

| Task type | Report layout | Emphasis |
|---|---|---|
| `competitive-brief` | Landscape, threat/opportunity cards, change signals | Who moved, what changed |
| `market-report` | Segment sizing, trend arrows, opportunities | Where the market is going |
| `project-status` | Progress indicators, blockers, milestone timeline | What's on track |
| `meeting-prep` | Contact profile, history, talking points | Who you're meeting |
| `content-brief` | Topic outline, audience, competitive angle | What to write |
| `daily-update` | Cross-domain summary, signal highlights | Executive briefing |
| `stakeholder-update` | Multi-domain roll-up, key decisions | Board/investor view |

**Pragmatic path:** Start with the structural change (task-class-aware tabs, Report as default when outputs exist). Tailored report layouts iterate per task type over time. Initial Report tab renders HTML iframe or markdown (same as current synthesizer view) — the tailoring is frontend-only work on top.

**Empty state (no outputs yet):** "No reports yet — this agent's synthesis tasks will produce deliverables here."

#### Data tab — "What does this agent know?"

Composed domain intelligence view. Entity cards, synthesis summary, freshness signals. NOT a file browser — that's the Context page.

- Domain stewards: entity cards + synthesis content + what's new (current AgentDashboard)
- Platform bots: latest observations per source
- Agents without a domain: tab not shown

"View files" link at bottom → `/context?domain={domain}`.

#### Pipeline tab — "What work is assigned?"

Task cards with objectives, schedule, delivery, actions. Context flow summary (domain reads/writes). Unchanged from v7.

#### Agent tab — "Who is this agent?"

Identity, AGENT.md, history, feedback. Low-frequency reference. Unchanged from v7.

### What was deleted (v6.1 → v7+)

- **Browse tab** — dissolved. File browsing removed entirely from Agents page.
- **`DomainBrowse`, `SynthesizerBrowse`, `EmptyBrowse` components** — deleted.
- **Embedded ContentViewer on Agents page** — deleted. Context page is the only file viewer.
- **Agent-class-based rendering** — replaced with task-class-based tab visibility.

### Rendering model — task-class-driven, not agent-class-driven

The rendering key is `task.task_class` ("context" or "synthesis"), not `agent.agent_class`. An agent with both types of tasks shows both Report and Data tabs.

| Tab | Data source | Component |
|---|---|---|
| **Report** | `getLatestOutput(slug)` + `listOutputs(slug)` per synthesis task | Report viewer (tailored per type_key, initially generic) |
| **Data** | `getDomainEntities(domain)` + `getFile(synthesis)` | Domain dashboard (entity cards, synthesis, freshness) |

No LLM cost — pure frontend rendering of existing workspace files and task outputs.

### Left Panel: Agent Roster

Unchanged from v6.1. Flat agent list, three sections (Agents, Cross-Team, Integrations), freshness timestamps, task count. No default selection.

### Right Panel: Unified TP Chat

Same `ChatPanel` component on every page via shared `ThreePanelLayout`. Unified session (ADR-159). Surface context shifts TP's awareness per page.

**Plus menu actions:**
- Run [task name] now (per active task)
- Assign a new task
- Web research
- Upload file

---

## 3. Context Page (`/context`) — The Only File Browser

### Purpose

Workspace-level substrate explorer. **The single place for all raw file browsing.** Cross-agent context domains, uploads, settings files. Agents page links here for deep file exploration.

### Deep-linking

`/context?domain={key}` auto-navigates to `/workspace/context/{path}` on load. Example: Agents page "View files" link for Competitive Intelligence → `/context?domain=competitors` → tree auto-expands to `context/competitors/` folder.

### Layout

Three-panel explorer via shared `ThreePanelLayout`:
- **Left:** WorkspaceTree (Domains, Uploads, Settings)
- **Center:** ContentViewer (directory listing + type-aware file preview)
- **Right:** Workspace-scoped ChatPanel (via shared shell)

---

## 4. Activity Page (`/activity`)

### Purpose

Temporal observation. Upcoming scheduled runs, past execution events, system activity. No chat — read-only timeline.

---

## 5. Task Naming Convention

**Rule: A task name is the user's description of the work. Freeform. Never includes frequency, agent name, or type classification.**

- Good: "Track Competitors", "Q2 Board Deck", "Monitor HN for AI launches"
- Bad: "Weekly Competitor Report" (frequency is config, not identity)
- Bad: "Competitive Intelligence - Track" (agent name is redundant)
- Bad: "context-track-competitors" (type classification is internal)

The task type registry provides default names (e.g., `display_name: "Track Competitors"`), but users and TP can override with any name. Schedule, mode, and type_key are separate fields — they don't belong in the name.

---

## 6. TP Context Injection

### `load_surface_content()` by surface type

| Surface Type | Context Loaded |
|-------------|----------------|
| `"chat"` | Agent roster summary, task list, platform status, workspace state |
| `"agent-detail"` | Full AGENT.md, owned domain summary, assigned tasks list, recent outputs |
| `"task-detail"` | Full TASK.md, run_log.md (last 5), latest output summary, assigned agent AGENT.md |
| `"context"` | Navigation-aware context (path, domain, entity) per WORKSPACE-EXPLORER-UI.md |

---

## 7. Session Architecture (ADR-159)

**Unified session**: one session per workspace. No agent-scoped or task-scoped sessions. Surface context is metadata per message, not a session boundary. Messages persist across all page navigations.

| Surface | Session | Surface Context |
|---------|---------|-----------------|
| Home page | Global (workspace) | `{ page: "home" }` |
| Agents page (agent selected) | Global (workspace) | `{ page: "agents", agentSlug: "..." }` |
| Context page | Global (workspace) | `{ page: "context", path: "..." }` |

TP receives a compact index (~200-500 tokens) instead of full working memory. Surface context shifts TP's focus without creating new sessions. See [ADR-159](../adr/ADR-159-filesystem-as-memory.md) and [sessions.md](../features/sessions.md).

---

## 8. Mobile Layout (< 1024px)

**Chat page:** Full-width chat. No change.
**Agents page:** Agent list as top selector. Center panel full-width with tabs. Chat as bottom sheet.
**Context page:** File tree as drawer. Content viewer full-width. Chat as bottom sheet.
**Activity page:** Full-width feed. No change.

---

## 9. Data Sources

| Component | API Endpoint | Notes |
|-----------|-------------|-------|
| Agent roster | `GET /api/agents` | Returns `agent_class`, `context_domain`. |
| Tasks | `GET /api/tasks` | Returns `context_reads`, `context_writes`, `task_class`, `objective`. Client-side group by `agent_slugs`. |
| Domain tree | `GET /api/workspace/tree?prefix=/workspace/context/{domain}` | Existing. |
| Task outputs | `GET /api/tasks/{slug}/outputs` | Existing. |
| File content | `GET /api/workspace/file?path=...` | Existing. |
| Agent detail | `GET /api/agents/{id}` | Returns feedback_summary, rendered_outputs, agent_memory. |
| Agent-scoped chat | `POST /api/chat` with `surface_context.agentSlug` | Existing. |

---

## 10. Implementation Sequence (v7)

| Step | What | Scope |
|------|------|-------|
| 1 | Extract shared `ThreePanelLayout` shell component | Frontend, medium |
| 2 | Extract shared hooks (`useAgentsAndTasks`) and utilities (`formatRelativeTime`, freshness) | Frontend, small |
| 3 | Refactor `AgentContentView` — flatten tabs into single scroll, delete file browsing components | Frontend, medium |
| 4 | Add domain pre-filtering to Context page (`?domain=` URL param) | Frontend, small |
| 5 | Refactor Agents page to use shared shell | Frontend, small |
| 6 | Refactor Home page to use shared shell | Frontend, small |
| 7 | Delete dead code: `DomainBrowse`, `SynthesizerBrowse`, `EmptyBrowse`, duplicate timestamp utils | Frontend, cleanup |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-25 | v1 — Agent cards (left) + TP chat (left) + tasks/workspace tabs (right). |
| 2026-03-25 | v2 — Output-first. Workfloor: output feed + agent roster grid. Task page: output hero + trajectory. Chat as drawer. |
| 2026-04-04 | v3 — Agent-centric reframe. Agents page replaces workfloor + tasks page. Tasks dissolve into agent responsibilities. Chat becomes dedicated page. Task-cards-as-bridge center panel. |
| 2026-04-05 | v4 — Three-tab center panel (Agent / Setup / Settings). Knowledge is the hero on the Agent tab. Task metadata collapses to a status line. Task naming convention: freeform, never includes frequency. Left panel section labels: Your Team, Cross-Team, Integrations (no filter pills). Chat page renamed to Home with persistent daily briefing header. Agent work rhythm framing (display-only). |
| 2026-04-06 | v5 — Pinned header + Browse/Tasks/Agent tabs. Finder-style freshness. Folder icons in left panel. |
| 2026-04-06 | v6 — Dashboard + Chat two-panel model. Composed agent dashboards from workspace files (not file browser). Unified TP chat panel across all pages. Reporting agent daily-update = Home page dashboard. File system secondary (Context page + links). Agent dashboard templates per domain type. |
| 2026-04-06 | v6.1 — Global breadcrumb in header. BreadcrumbContext + GlobalBreadcrumb component. Pages set segments, header renders. Replaces context page local breadcrumb bar and agent header browse path. "Briefing room" spatial awareness: toggle bar = which room, breadcrumb = where you're standing. |
| 2026-04-06 | v7 — Unified shell refactor. ThreePanelLayout shared component eliminates three duplicated three-panel layouts. All file browsing removed from Agents page — Context page is the single file browser. Context page gains `?domain=` deep-link param. Shared hooks and utilities extracted. ~200 lines of duplicate DomainBrowse/SynthesizerBrowse/EmptyBrowse deleted. |
| 2026-04-06 | v7.1 — Tabs restored. Three user intents (know/do/identity) shouldn't be stacked in one scroll. |
| 2026-04-06 | v7.2 — Task-class-aware tabs. BI + intelligence room framing: Report (deliverables) / Data (accumulated context) / Pipeline (task config) / Agent (identity). Tabs appear based on task_class presence, not agent_class. Report tab is default when synthesis outputs exist; Data tab default otherwise. Tailored report layouts per task type (iterative — start generic, specialize over time). |
