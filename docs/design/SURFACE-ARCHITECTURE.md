# Surface Architecture — Chat + Agents + Context + Activity

**Date:** 2026-04-06 (v6.1 — global breadcrumb, briefing room spatial awareness)
**Status:** Proposed
**Supersedes:** v5 (2026-04-06, pinned header + Browse/Tasks/Agent tabs)
**Depends on:** [ADR-138](../adr/ADR-138-agents-as-work-units.md) (Agents as Work Units), [ADR-140](../adr/ADR-140-agent-workforce-model.md) (Workforce Model), [ADR-152](../adr/ADR-152-unified-directory-registry.md) (Directory Registry)

---

## Design Thesis: Dashboard + Chat, Everywhere

Every surface is **dashboard + chat**. The dashboard varies by context. The chat is TP (same unified session everywhere). The file system lives on the Context page.

| Surface | Route | Nav Label | Dashboard (left/center) | Chat (right panel) |
|---------|-------|-----------|------------------------|-------------------|
| **Home** | `/chat` | Home | Daily briefing: what happened, what changed, what's next | TP chat (unified session) |
| **Agents** (overview) | `/agents` | Agents | Agent roster cards (overview grid) | TP chat |
| **Agents** (selected) | `/agents?agent={slug}` | Agents | Composed agent dashboard from domain files | TP chat (agent-scoped context) |
| **Context** | `/context` | Context | File system browser (left panel + content viewer) | TP chat |
| **Activity** | `/activity` | Activity | Timeline feed | No chat |

**Key shift from v5:**

1. **Dashboard-first, not file-first.** Agent views show a composed dashboard (rendered from workspace files) as the default — not a file browser. "What did this agent find?" not "Browse the files it wrote."
2. **Unified two-panel layout.** Dashboard left, TP chat right. Same pattern on every page. Chat is a collapsible right panel with FAB toggle — same component, same session, same conversation across all pages.
3. **File system is secondary.** Accessed via Context page or "Browse files →" links from agent dashboards. Not embedded in every surface.
4. **Reporting agent = Home page.** The daily-update task output IS the Home page dashboard content. No duplication — one source, one surface.

---

## Route Map

```
/chat                → Home page. Daily briefing + TP chat. Full-page, unscoped.
/agents              → Agents page. Agent roster + three-tab center panel. Agent-scoped TP panel.
/agents?agent={slug} → Agent selected. Three-tab view: Agent / Setup / Settings.
/context             → Workspace explorer. Cross-agent domains, uploads, settings.
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

Primary working surface. Three-panel layout: agent roster (left), composed dashboard or overview (center), TP chat (right). The center panel shows a composed agent dashboard — rendered from workspace files, not a file browser.

### Layout (desktop ≥ 1024px)

**No agent selected (overview):**

```
┌──────────────┬──────────────────────────┬──────────────────┐
│  LEFT PANEL  │    AGENT OVERVIEW        │  RIGHT PANEL     │
│  Agent List  │    (card grid)           │  ChatPanel       │
│  (280px)     │                          │  (380px / FAB)   │
├──────────────┼──────────────────────────┼──────────────────┤
│              │  Your Team               │                  │
│ AGENTS       │  8 agents · 6 tasks      │  TP Chat         │
│ 📁 Comp Intel│                          │  (unified)       │
│ 📁 Market Res│  [CI] [MR] [BD]         │                  │
│ 📁 Biz Dev   │  [Op] [MC] [ER]         │                  │
│ 📁 Operations│  [Slack] [Notion] [GH]  │                  │
│ 📁 Marketing │                          │                  │
│ CROSS-TEAM   │                          │                  │
│ 📁 Reporting │                          │                  │
│ INTEGRATIONS │                          │                  │
│ 📁 Slack Bot │                          │                  │
└──────────────┴──────────────────────────┴──────────────────┘
```

**Agent selected (composed dashboard):**

```
┌──────────────┬──────────────────────────┬──────────────────┐
│  LEFT PANEL  │    AGENT DASHBOARD       │  RIGHT PANEL     │
│  Agent List  │    (composed view)       │  ChatPanel       │
├──────────────┼──────────────────────────┼──────────────────┤
│              │  Competitive Intelligence│                  │
│ AGENTS       │  Works weekly · Ran 2h   │  TP Chat         │
│ 📁 Comp Intel│  ────────────────────────│  (agent-scoped)  │
│ 📁 Market Res│                          │                  │
│ 📁 Biz Dev   │  ## What's New           │                  │
│ 📂 Operations│  · Cursor raised $900M   │                  │
│ 📁 Marketing │  · Ahrefs launched AI    │                  │
│              │                          │                  │
│ CROSS-TEAM   │  ## Landscape            │                  │
│ 📁 Reporting │  [rendered synthesis]    │                  │
│              │                          │                  │
│ INTEGRATIONS │  ## Competitors (6)      │                  │
│ 📁 Slack Bot │  [entity cards/table]    │                  │
│ 📁 Notion Bot│                          │                  │
│              │  [Browse files →]        │                  │
│              │  [Tasks] [Settings]      │                  │
└──────────────┴──────────────────────────┴──────────────────┘
```

### Composed Agent Dashboard

The center panel's default view is a **composed page** assembled from the agent's workspace files. No LLM cost — pure frontend rendering of existing files.

Each agent type has a fixed template:

| Agent Type | Dashboard sections | Source files |
|---|---|---|
| **Competitive Intelligence** | What's New (signals) + Landscape (synthesis) + Competitors (entity cards) | `signals/`, `_landscape.md`, `{entity}/profile.md` |
| **Market Research** | Trends + Segments + Overview | `_overview.md`, `{segment}/analysis.md` |
| **Business Development** | Recent activity + Contacts + Relationships | `_portfolio.md`, `{contact}/profile.md` |
| **Operations** | Status + Projects + Blockers | `_overview.md`, `{project}/status.md` |
| **Marketing & Creative** | Research + Topics + Content pipeline | `{topic}/research.md` |
| **Reporting** | Latest report (rendered HTML) + Run history | Task outputs |
| **Platform bots** | Latest digest (rendered) + Observations | `{source}/latest.md` |

The dashboard reads from the existing workspace API (`getDomainEntities`, `getFile`). Sections that have no data show "No data yet — this section populates as the agent works."

**Secondary actions** (below the dashboard):
- **Browse files →** — links to Context page filtered to this domain
- **Tasks** — expandable section showing task config (objective, schedule, actions)
- **Settings** — agent identity, AGENT.md, history

### Left Panel: Agent Roster (Finder-style)

Flat agent list, no tree expansion, no filter pills. Three sections:

- **Agents** — domain stewards (5 agents)
- **Cross-Team** — synthesizers (1 agent)
- **Integrations** — platform bots (3 agents)

Each agent shows: folder icon (open when selected, closed when not), agent name, domain path, right-aligned freshness timestamp with color coding (green <24h, gray <72h, amber >72h), task count. Selected agent gets left-border highlight + accent background.

No default selection — center panel shows minimal empty state ("Select an agent") until user clicks.

The roster is fixed (ADR-140: pre-scaffolded, no deletion). All 8+ agents always visible. Agents without tasks show as dormant — communicating "ready to work."

### Center Panel: Pinned Header + Three Tabs

When an agent is selected, the center panel shows a pinned header (always visible) above three tabs:

```
┌──────────────────────────────────────────────────────────────┐
│  Operations                                     [▶ Run] [⏸] │
│  Domain Steward · projects/ · Works weekly · Ran 1h ago      │
├──────────────────────────────────────────────────────────────┤
│  [Browse]          [Tasks (2)]          [Agent]              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  (tab content — full height, own scroll)                     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Header** carries: agent name + action buttons (line 1), class label · domain · cadence · last run (line 2). Actions (Run/Pause) are always accessible — not buried in a tab. Header communicates the "autonomous worker" signal: who is this, what it's responsible for, that it's active.

**Browse** is the default tab. Tab resets to Browse when switching agents.

---

### Tab 1: Browse (Default) — "What does this agent know?"

The knowledge tab. Finder-style domain browser with per-item freshness timestamps. Header (above tabs) provides the worker-level context; this tab provides the knowledge-level view.

**Two distinct freshness signals:**
- **Header:** "Ran 1h ago" = agent's last execution (worker rhythm)
- **File list:** per-item `Modified` column = content freshness (knowledge state)

A user sees: "This agent runs weekly, it last ran 1h ago, and during that run it updated fundraising/ and go-to-market/ but product-development/ hasn't changed in 2 weeks."

#### Domain Steward Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Name                                           Modified     │
├──────────────────────────────────────────────────────────────┤
│  📁 cursor                                        1h ago     │
│     3 items                                                  │
│  📁 openai                                        3d ago     │
│     2 items                                                  │
│  📁 anthropic                                     2w ago     │
│     2 items                                                  │
│  📄 landscape.md                                  1h ago     │
│  📁 assets                                        3d ago     │
│     5 items                                                  │
└──────────────────────────────────────────────────────────────┘
```

Folders show item count as subtitle. Modified timestamps use relative format (1h ago, 3d ago, 2w ago). Folder timestamps inherit most recent child's `updated_at`. Clicking a folder or file navigates into `ContentViewer` with a Back button.

#### Synthesizer Layout

Latest rendered output as hero (HTML iframe or markdown), with run history below.

#### Bot Layout

Same as domain steward — observations directory with per-channel freshness.

#### Empty State

Centered message: "Knowledge will accumulate as tasks run" (domain steward), "No outputs yet" (synthesizer), "Connect platform to populate" (platform bot).

---

### Tab 2: Tasks (N) — "What work is assigned?"

Task cards with objectives, schedule, delivery, and actions. Tab label shows count: "Tasks (2)".

**Context flow summary** at top: colored dots showing which domains this agent writes to (green) and reads from (blue).

**Per-task card** shows: status dot (green/amber/gray) + title + mode badge (recurring/goal/reactive), objective (deliverable, audience, purpose), schedule inline (cadence · next · last), action buttons (Run Now, Pause/Resume, Edit via TP).

**CRUD model:** Actions are TP-mediated buttons, not inline edit forms. "Run Now" calls `api.tasks.run()`. "Pause" calls `api.tasks.update({ status: 'paused' })`. "Edit via TP" opens the right-panel chat with a pre-composed prompt.

**Empty state:** Centered message + "Assign via TP" button that opens chat with a task-creation prompt.

Note: Run/Pause actions are also available in the pinned header (primary task only) for quick access without switching to this tab.

---

### Tab 3: Agent — "Who is this agent?"

Identity, history, and feedback. Low-frequency reference material — the worker profile.

Sections: Identity (name, role, class, domain, origin), Instructions (rendered AGENT.md), History (quality score + trend, total runs, last run), Feedback (from agent memory), Created date.

---

### Right Panel: Unified TP Chat

Same ChatPanel component on every page. Unified session (ADR-159) — conversation persists across all navigations. Surface context shifts TP's awareness.

- **Session:** Unified workspace session (same everywhere)
- **Surface context:** Varies per page (home/agents/context), sent per message
- **Header:** yarnnn logo + "TP" label + context subtitle
- **Toggle:** FAB button (yarnnn logo) shows/hides the panel. Same across all pages.

**Plus menu actions:**
- Run [task name] now (per active task, agent pages)
- Assign a new task
- Web research
- Upload file

---

## 3. Context Page (`/context`)

### Purpose

Workspace-level substrate explorer. Browsing the full workspace filesystem: cross-agent context domains, uploads, settings files. This is the "Finder" view — for when the user wants to browse across agents, not within one.

The Context page shows the same domain directories that appear on individual agent views, but organized by workspace structure rather than by agent ownership. It's the cross-cutting view.

### Layout

Three-panel explorer (unchanged):
- **Left:** WorkspaceTree (Domains, Uploads, Settings)
- **Center:** ContentViewer
- **Right:** Workspace-scoped ChatPanel

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

## 10. Implementation Sequence

| Step | What | Scope |
|------|------|-------|
| 1 | Rewrite `AgentContentView` as three-tab component | Frontend, medium |
| 2 | Build Agent tab (status line + domain browser / output viewer) | Frontend, medium |
| 3 | Build Setup tab (task details + actions) | Frontend, medium |
| 4 | Build Settings tab (identity, history, feedback) | Frontend, medium |
| 5 | Wire new API data (agent detail endpoint for feedback, AGENT.md) | Frontend + backend, small |
| 6 | Clean up old task-cards-as-bridge code | Frontend, cleanup |

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
