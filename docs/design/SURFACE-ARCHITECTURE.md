# Surface Architecture — Chat + Agents + Context + Activity

**Date:** 2026-04-05 (v4 — three-tab center panel, knowledge-first agent view)
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

**Key shift from v3:** The center panel no longer stacks agent header → task cards → domain files vertically. Instead, a **three-tab model** puts knowledge (domain files/outputs) as the hero on the default Agent tab, with task configuration and agent settings on separate tabs. Task metadata collapses to a single status line — tasks are operational infrastructure, not the primary thing users look at.

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
│              │                          │                  │
│ YOUR TEAM    │  [Agent | Setup | Settings]                │
│ ● Comp Intel │                          │  Agent-scoped TP │
│ ● Market Res │  (tab content fills      │                  │
│ ● Biz Dev    │   remaining space)       │                  │
│ ● Operations │                          │                  │
│ ● Marketing  │                          │                  │
│              │                          │                  │
│ CROSS-TEAM   │                          │                  │
│ ● Exec Rpt   │                          │                  │
│              │                          │                  │
│ INTEGRATIONS │                          │                  │
│ ● Slack Bot  │                          │                  │
│ ● Notion Bot │                          │                  │
│ ● GitHub Bot │                          │                  │
└──────────────┴──────────────────────────┴──────────────────┘
```

### Left Panel: Agent Roster

Flat agent list, no tree expansion, no filter pills. Three sections:

- **Your Team** — domain stewards (5 agents)
- **Cross-Team** — synthesizers (1 agent)
- **Integrations** — platform bots (3 agents)

Each agent shows: name, domain label + task count, binary status dot (green = active tasks, gray = dormant).

The roster is fixed (ADR-140: pre-scaffolded, no deletion). All 8 agents always visible. Agents without tasks show as dormant — communicating "ready to work."

### Center Panel: Three-Tab Model

When an agent is selected, the center panel shows three tabs:

```
┌──────────────────────────────────────────────────────────────┐
│  [Agent]   [Setup]   [Settings]                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  (tab content)                                               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Agent** is the default tab. Tab selection persists per agent (navigating away and back remembers the last tab).

---

### Tab 1: Agent (Default) — "What does this agent know?"

The knowledge tab. Domain files and outputs are the hero — 90% of the space. Task metadata collapses to a single status line.

#### Domain Steward Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Competitive Intelligence                                     │
│  Maintains competitor profiles, pricing, strategy, and        │
│  market positioning                                           │
│                                                               │
│  ● Active · Updated 2h ago · Weekly                           │
│  competitors/ → signals/                                      │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  📁 cursor/                             4 files               │
│  📁 openai/                             3 files               │
│  📁 anthropic/                          3 files               │
│  📄 landscape.md                                              │
│  📁 assets/                             5 files               │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│  📄 Latest: Competitive Landscape Brief · Apr 3 · View →     │
└──────────────────────────────────────────────────────────────┘
```

**Components (top to bottom):**

1. **Agent header** — agent name + description (from AGENT.md or task objective). 2-3 lines max.
2. **Status line** — single line: active/paused dot, freshness ("Updated 2h ago"), cadence ("Weekly"), context flow ("competitors/ → signals/"). This is the task metadata, collapsed. Click to go to Setup tab.
3. **Domain browser** (hero, fills remaining space) — the agent's owned context directory. Uses existing `ContentViewer` — folders drill in, files render inline. This is the master-detail file browser, not a flat list.
4. **Latest output footer** (conditional) — if the agent has a synthesis task, show the latest output as a single-line card. Click to render full output.

#### Synthesizer Layout

Same structure, but the hero is the output viewer instead of the domain browser:

```
┌──────────────────────────────────────────────────────────────┐
│  Reporting                                          │
│  Cross-domain composition of competitor, market, and          │
│  relationship intelligence into executive summaries           │
│                                                               │
│  ● Active · Last delivered Apr 3 · Weekly                     │
│  Reads: competitors/, market/, relationships/                 │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  (Rendered HTML output — latest deliverable)           │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  Run history:                                                 │
│  Apr 3, 2026 · delivered                                      │
│  Mar 27, 2026 · delivered                                     │
│  Mar 20, 2026 · delivered                                     │
└──────────────────────────────────────────────────────────────┘
```

#### Bot Layout

Same structure — observations directory is the hero:

```
┌──────────────────────────────────────────────────────────────┐
│  Slack Bot                                                    │
│  Monitors selected Slack channels for decisions, action       │
│  items, and key discussions                                   │
│                                                               │
│  ● Active · Updated 6h ago · Daily                            │
│  slack/ → signals/ · Connected ✓                              │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  📁 general/                            latest.md             │
│  📁 engineering/                        latest.md             │
│  📁 product/                            latest.md             │
│  📄 _tracker.md                                               │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

#### Empty State (no tasks, domain empty)

```
┌──────────────────────────────────────────────────────────────┐
│  Competitive Intelligence                                     │
│  Ready to track competitor profiles, pricing, and strategy    │
│                                                               │
│  ○ No active tasks                                            │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  📂 (empty)                                                   │
│  Knowledge will accumulate as tasks run.                      │
│                                                               │
│  [Assign a task →]  (opens TP chat with prompt)               │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

### Tab 2: Setup — "How is this configured?"

Operational configuration — everything about how the work gets done. TP-mediated actions rather than CRUD forms.

```
┌──────────────────────────────────────────────────────────────┐
│  TASKS                                                        │
│                                                               │
│  Track Competitors                                            │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Status: ● Active         Mode: Recurring              │  │
│  │                                                        │  │
│  │  Objective                                             │  │
│  │  · Deliverable: Maintained competitor intelligence     │  │
│  │  · Audience: Internal — feeds synthesis tasks          │  │
│  │  · Purpose: Keep competitor profiles current           │  │
│  │                                                        │  │
│  │  Schedule                                              │  │
│  │  · Cadence: Weekly                                     │  │
│  │  · Next run: Apr 7, 9:00 AM                           │  │
│  │  · Last run: Apr 3 (2 days ago)                       │  │
│  │                                                        │  │
│  │  Delivery                                              │  │
│  │  · Channel: None (context task — writes to workspace) │  │
│  │                                                        │  │
│  │  Context Flow                                          │  │
│  │  · Reads: competitors/                                 │  │
│  │  · Writes: competitors/, signals/                      │  │
│  │                                                        │  │
│  │  [Run Now]  [Pause]  [Edit via TP →]                  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  Competitive Landscape Brief                                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Status: ● Active         Mode: Recurring              │  │
│  │  ...                                                   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  OUTPUT SPEC (DELIVERABLE.md)                                 │
│  · Format: Structured entity files per competitor             │
│  · Quality criteria: min 3 profiles, updated within 30 days  │
│                                                               │
│  SOURCES                                                      │
│  · Web search, Platform signals, Workspace context            │
└──────────────────────────────────────────────────────────────┘
```

**Components:**

1. **Task sections** — one section per assigned task. Shows objective, schedule, delivery, context flow. Each task has action buttons: Run Now, Pause/Resume, "Edit via TP" (opens chat with a task-edit prompt).
2. **Output spec** — from DELIVERABLE.md. Quality criteria, format expectations.
3. **Sources** — what data sources this agent's tasks use (web, platforms, workspace).

**CRUD model:** Actions are TP-mediated buttons, not inline edit forms. "Run Now" calls `api.tasks.run()`. "Pause" calls `api.tasks.update({ status: 'paused' })`. "Edit via TP" opens the right-panel chat with a pre-composed prompt like "I want to change the schedule for Track Competitors."

**Multiple tasks:** If an agent has 2+ tasks, each gets its own expandable section. Most agents have 1-2 tasks.

---

### Tab 3: Settings — "Who is this agent?"

Identity, history, and feedback. Low-frequency reference material.

```
┌──────────────────────────────────────────────────────────────┐
│  IDENTITY                                                     │
│  · Name: Competitive Intelligence                             │
│  · Role: competitive_intelligence (Domain Steward)            │
│  · Domain: competitors/                                       │
│  · Origin: Pre-scaffolded                                     │
│                                                               │
│  INSTRUCTIONS (AGENT.MD)                                      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  (Rendered AGENT.md content — editable?)               │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  PLAYBOOKS                                                    │
│  · playbook-outputs.md                                        │
│  · playbook-research.md                                       │
│                                                               │
│  HISTORY                                                      │
│  · Quality: 85% (↑ improving)                                │
│  · Total runs: 12                                             │
│  · Apr 3 ✓ · Mar 27 ✓ · Mar 20 ✓ · Mar 13 ✓               │
│                                                               │
│  FEEDBACK                                                     │
│  · "Include pricing data in profiles" (Mar 27)                │
│  · "More detail on funding rounds" (Mar 15)                   │
│  · Learned: always include pricing, funding in profiles       │
│                                                               │
│  STEERING NOTES                                               │
│  · "Focus on AI code generation companies next cycle"         │
└──────────────────────────────────────────────────────────────┘
```

**Components:**

1. **Identity** — agent name, role, domain, class, origin. Read-only (identity is fixed at scaffold time per ADR-140).
2. **Instructions** — AGENT.md content. View and potentially edit inline (or via TP).
3. **Playbooks** — list of playbook files with view links.
4. **History** — quality score, trend, total runs, recent run list with status icons.
5. **Feedback** — from `memory/feedback.md`. User corrections and TP evaluations.
6. **Steering notes** — from `memory/steering.md`. TP's notes for next cycle.
7. **Learned preferences** — computed from edit patterns across runs.

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

## 7. Session Architecture

| Surface | Session Key | Scope |
|---------|-------------|-------|
| Chat page | `user_id` (global) | Unscoped — workspace-level TP |
| Agents page (agent selected) | `user_id` + `agent_slug` | Agent-scoped TP |
| Context page | `user_id` (global) | Workspace-scoped TP (same session as chat) |

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
