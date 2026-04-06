# Surface Architecture — Chat + Agents + Context + Activity

**Date:** 2026-04-06 (v5 — pinned header + Browse/Tasks/Agent tabs, Finder-style freshness)
**Status:** Proposed
**Supersedes:** v3 (2026-04-04, task-cards-as-bridge center panel)
**Depends on:** [ADR-138](../adr/ADR-138-agents-as-work-units.md) (Agents as Work Units), [ADR-140](../adr/ADR-140-agent-workforce-model.md) (Workforce Model), [ADR-152](../adr/ADR-152-unified-directory-registry.md) (Directory Registry)

---

## Design Thesis: Knowledge Is the Hero

Four surfaces, each with a clear purpose:

| Surface | Route | Nav Label | Purpose | Chat |
|---------|-------|-----------|---------|------|
| **Home** | `/chat` | Home | Daily briefing + unscoped TP — workspace signals, strategic direction, onboarding | Full-page with persistent briefing header |
| **Agents** | `/agents` | Agents | Primary working surface — agent roster, three-tab center panel (Agent / Setup / Settings) | Right panel (agent-scoped TP) |
| **Context** | `/context` | Context | Workspace substrate — cross-agent domains, uploads, settings as browsable filesystem | Right panel (workspace-scoped TP) |
| **Activity** | `/activity` | Activity | Temporal observation — upcoming runs, past events, execution history | No chat (observation only) |

**Key shift from v4:** Pinned header above tabs carries agent identity + capability + actions at all times. Tabs renamed Browse/Tasks/Agent for clarity. Browse tab uses Finder-style per-file freshness timestamps (content freshness) while header shows agent work rhythm (worker freshness). Two separate freshness signals: the worker's schedule vs the knowledge's actual modification dates. Left sidebar uses folder icons + left-border highlight for selected state. No default agent selection — center shows minimal empty state until user clicks.

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
│ Logo  │  [Home | Agents | Context | Activity]  │  User Menu │
└─────────────────────────────────────────────────────────────┘
```

Four-segment toggle bar: `Home | Agents | Context | Activity`. `/agents` is `HOME_ROUTE` for returning users. New users (no tasks) land on `/chat` (Home) for onboarding. See [ONBOARDING-SCAFFOLD-AND-BRIEFING.md](ONBOARDING-SCAFFOLD-AND-BRIEFING.md) for Home page layout with daily briefing.

---

## 1. Home Page (`/chat` route, nav label "Home")

### Purpose

Daily command center + unscoped TP. The Home page shows the daily briefing (what happened, what's coming up, what needs attention) as a persistent collapsible header, with TP chat below. For new users, the onboarding flow (ContextSetup) replaces the briefing.

See [ONBOARDING-SCAFFOLD-AND-BRIEFING.md](ONBOARDING-SCAFFOLD-AND-BRIEFING.md) for full layout spec and briefing behavior.

### Layout

Full-width, max-width constrained (~720px centered). Persistent briefing header + chat below.

### Properties

- **Session:** Global TP session (`task_slug IS NULL`, `agent_slug IS NULL`)
- **Surface context:** `{ type: "chat" }`
- **Plus menu actions:** Create a task, Update my context, Web search, Upload file

### Daily briefing (returning user)

Persistent collapsible header — always visible, auto-collapses after first message. Shows: what happened (last 24h activity), coming up (scheduled runs), needs attention (dormant agents, empty domains), workspace signals (platform/entity/task counts).

### Cold Start + Onboarding (new user)

When there are no tasks, ContextSetup renders as full-page overlay above chat input (existing behavior). Briefing header does not render until workspace has active tasks.

---

## 2. Agents Page (`/agents`) — HOME

### Purpose

Primary working surface. User selects an agent from the left panel and sees a three-tab center panel. The master-detail pattern — navigation pinned left, content fills center — avoids cross-page redirects.

### Layout (desktop ≥ 1024px)

```
┌──────────────┬──────────────────────────┬──────────────────┐
│  LEFT PANEL  │    CENTER PANEL          │  RIGHT PANEL     │
│  Agent List  │    Three-Tab View        │  ChatPanel       │
│  (280px)     │    (flex-1)              │  (380px / FAB)   │
├──────────────┼──────────────────────────┼──────────────────┤
│              │  Operations     [▶ Run][⏸]│                  │
│ AGENTS       │  Domain Steward · projects│  Agent-scoped TP │
│ 📁 Comp Intel│  Works weekly · Ran 1h ago│                  │
│ 📁 Market Res│ ─────────────────────────│                  │
│ 📁 Biz Dev   │  [Browse] [Tasks(2)] [Agent]               │
│ 📂 Operations│ ─────────────────────────│                  │
│ 📁 Marketing │  📁 assets       3d ago  │                  │
│              │  📁 fundraising  1h ago  │                  │
│ CROSS-TEAM   │  📁 go-to-market 1h ago  │                  │
│ 📁 Exec Rpt  │  📄 _tracker.md  1h ago  │                  │
│              │  📄 status.md    1h ago  │                  │
│ INTEGRATIONS │                          │                  │
│ 📁 Slack Bot │                          │                  │
│ 📁 Notion Bot│                          │                  │
│ 📁 GitHub Bot│                          │                  │
└──────────────┴──────────────────────────┴──────────────────┘
```

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

### Right Panel: Agent-Scoped TP

ChatPanel scoped to the selected agent. Yarnnn logo FAB when collapsed.

- **Session:** Agent-scoped (`agent_slug` set)
- **Surface context:** `{ type: "agent-detail", agentSlug: "{slug}" }`
- **Header:** yarnnn logo + "TP" label + "· viewing {agent title}"

**Plus menu actions:**
- Run [task name] now (per active task)
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
