# Surface Architecture — Chat + Agents + Context + Activity

**Date:** 2026-04-04 (v3 — agent-centric reframe + dedicated chat)
**Status:** Proposed
**Supersedes:** v2 (2026-03-25, output-first workfloor + task page + agent reference)
**Depends on:** [ADR-138](../adr/ADR-138-agents-as-work-units.md) (Agents as Work Units), [ADR-140](../adr/ADR-140-agent-workforce-model.md) (Workforce Model), [ADR-152](../adr/ADR-152-unified-directory-registry.md) (Directory Registry)

---

## Design Thesis: Agents Are Primary, Chat Is Explicit

Four surfaces, each with a clear purpose:

| Surface | Route | Purpose | Chat |
|---------|-------|---------|------|
| **Chat** | `/chat` | Unscoped TP — strategic direction, cross-cutting questions, workspace management | Full-page (hero) |
| **Agents** | `/agents` (home) | Primary working surface — agent roster with tasks as responsibilities, class-aware content | Right panel (agent-scoped TP) |
| **Context** | `/context` | Workspace substrate — domains, uploads, settings as browsable filesystem | Right panel (workspace-scoped TP) |
| **Activity** | `/activity` | Temporal observation — upcoming runs, past events, execution history | No chat (observation only) |

**Two shifts from v2:**

1. **Agent-centric, not task-centric.** Tasks dissolve into agent responsibilities. The left panel lists agents (stable roster), not tasks (transient work). Center panel dispatches by agent class — domain stewards show their directory, synthesizers show their deliverables, bots show their observations. Tasks are what agents are *working on*, not the primary navigation entity.

2. **Chat is a page, not a drawer.** TP is the singular action surface. Hiding it behind a FAB on two pages made the action surface secondary to the observation surfaces. A dedicated `/chat` page makes TP a first-class citizen — full-width, unscoped, the place where strategic conversations happen. Agent-scoped TP remains as a right panel on the agents page for task-level steering.

---

## Route Map

```
/chat                → Dedicated TP chat. Full-page, unscoped. Strategic direction.
/agents              → Home. Agent roster + class-aware content. Agent-scoped TP panel.
/agents?agent={slug} → Agent selected. Shows agent's domain/outputs + tasks.
/context             → Workspace explorer. Domains, uploads, settings. Workspace-scoped TP panel.
/activity            → Temporal activity log. Upcoming runs, past events.
/settings            → Billing, usage, memory, system, connectors, account.
```

**Deleted routes:** `/workfloor` (→ `/agents`), `/tasks` (→ `/agents`, tasks render as agent children), `/orchestrator` (legacy redirect).

---

## Navigation

```
┌─────────────────────────────────────────────────────────────┐
│ Logo  │  [Chat | Agents | Context | Activity]  │  User Menu │
└─────────────────────────────────────────────────────────────┘
```

Four-segment toggle bar. Each segment has a clear purpose:
- **Chat** — I want to direct (action surface)
- **Agents** — I want to supervise (primary observation + management)
- **Context** — I want to browse (workspace substrate)
- **Activity** — I want to review (temporal history)

`/agents` is `HOME_ROUTE` for returning users. New users (no tasks) land on `/chat` for onboarding. Post-OAuth and logo click land on `/agents`.

---

## 1. Chat Page (`/chat`)

### Purpose

Unscoped TP — the strategic conversation surface. User discusses workforce strategy, asks cross-cutting questions, creates tasks, updates workspace identity, uploads documents. This is the equivalent of walking into your office and talking to your chief of staff.

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│              Full-width ChatPanel                            │
│                                                              │
│  Messages (scrollable)                                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Assistant: Your competitive intel agent ran this        │  │
│  │ morning — 3 new entities discovered...                  │  │
│  │                                                         │  │
│  │ User: Create a weekly executive summary task            │  │
│  │                                                         │  │
│  │ Assistant: Created "Weekly Executive Summary" and        │  │
│  │ assigned it to Executive Reporting. First run scheduled  │  │
│  │ for Monday 9am. [View task →]                           │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ [+]  Type a message...                          [Send] │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

Full-width, max-width constrained (~720px centered). No side panels. Chat is the entire page.

### Properties

- **Session:** Global TP session (`task_slug IS NULL`, `agent_slug IS NULL`)
- **Surface context:** `{ type: "chat" }`
- **Component:** Reuses existing `ChatPanel` with `surfaceOverride`, full-width styling
- **Plus menu actions:** Create a task, Update my context, Web search, Upload file
- **Slash commands:** `/task`, `/research`, `/search`, `/web`, `/memory`

### Cold Start + Onboarding (no tasks, new user)

The chat page IS the onboarding surface. New users (0 tasks) are redirected here from auth callback instead of `/agents`.

When there's no chat history, `ContextSetup` renders as the empty state — the full onboarding component with:
- **Links** — paste company website, LinkedIn, etc.
- **Files** — upload docs (PDF, DOCX, TXT)
- **Notes** — describe your work in free text
- **Skip options** — "What can you track for me?" / "I want to create a task"

On submit, all inputs compose into a single message to TP, which calls `UpdateContext` + `ManageDomains` to scaffold the workspace. After the first message, ContextSetup disappears and the page becomes a normal chat.

This replaces the previous onboarding flow that lived on `/context` (setup-phase hero with ContextSetup). Onboarding is now fully consolidated on `/chat` — one surface, one flow.

### Why a page, not a drawer

| Option | Problem |
|--------|---------|
| Drawer on agents page | 380px width is cramped for strategic conversations. Competes with agent content. |
| Conditional center panel | Adds state complexity to an already-complex agents page. Morphing layout confuses. |
| **Dedicated page** | Clean separation. ChatPanel already portable (accepts `surfaceOverride`, `plusMenuActions`). ~50 lines of page wrapper. No state complexity added to other pages. |

The ChatPanel component is already designed for embedding — this is just a new full-width host.

---

## 2. Agents Page (`/agents`) — HOME

### Purpose

Primary working surface. User answers: "What are my agents working on? How are their domains? What did they produce?" This replaces both the workfloor (agent roster) and the tasks page (task management).

### Layout (desktop ≥ 1024px)

```
┌──────────────┬──────────────────────────┬──────────────────┐
│  LEFT PANEL  │    CENTER PANEL          │  RIGHT PANEL     │
│  Agent List  │    Agent-class-aware     │  ChatPanel       │
│  (280px)     │    content (flex-1)      │  (380px / FAB)   │
├──────────────┼──────────────────────────┼──────────────────┤
│              │                          │                  │
│ DOMAIN STEWARDS                        │  Agent-scoped TP │
│ ● Comp Intel │  [Steward → Domain]     │                  │
│   ├ track-…  │  Directory tree of      │  "Run the comp   │
│   └ comp-…   │  /workspace/context/    │   brief task"    │
│ ● Market Res │  {domain}/ + task list  │                  │
│ ● Biz Dev    │                          │  Plus menu:      │
│ ● Operations │  [Synth → Deliverables] │  · Run [task]    │
│ ● Marketing  │  Latest output (HTML)   │  · Assign task   │
│              │  + run history           │  · Review domain │
│ SYNTHESIZERS │                          │  · Web research  │
│ ● Exec Rpt   │  [Bot → Observations]   │                  │
│              │  Temporal log tree       │                  │
│ PLATFORM BOTS│                          │                  │
│ ● Slack Bot  │                          │                  │
│ ● Notion Bot │                          │                  │
└──────────────┴──────────────────────────┴──────────────────┘
```

### Left Panel: AgentNav (flat roster)

Flat agent roster — no tree expansion, no task children. Click an agent → center panel shows everything.

```
DOMAIN STEWARDS
● Competitive Intelligence
  competitors/ · 2 tasks
● Market Research
  market/ · 1 task
● Business Development
  relationships/ · 0 tasks
● Operations
  projects/ · 1 task
● Marketing & Creative
  content_research/ · 0 tasks

SYNTHESIZERS
● Executive Reporting
  synthesizer · 2 tasks

PLATFORM BOTS
● Slack Bot
  slack/ · 1 task
● Notion Bot
  notion/ · 0 tasks
```

Three sections matching agent classes. Each agent shows:
- **Name** (primary text)
- **Domain or class label** + task count (secondary text)
- **Status dot**: green (active tasks), gray (dormant), amber (paused tasks)

**Filter pills:** All | Active | Dormant

Tasks are NOT expandable children in the nav — they appear as task cards in the center panel. The left panel's job is agent selection only.

### Center Panel: Task-Cards-as-Bridge Model

The center panel has three zones, top to bottom:

1. **Agent header** — who this is, what they own/read
2. **Task cards** — what they're working on, with context_reads/writes visible (the bridge between agent and files)
3. **Content area** — domain files (stewards), output list (synthesizers), or full-render when file selected

#### Default state (no file selected)

```
┌──────────────────────────────────────────────────────────┐
│  Competitive Intelligence                                 │
│  Domain: competitors/ (12 entities, 3 stale)              │
│                                                           │
│  ── Tasks ─────────────────────────────────────────────── │
│  ┌─ Track Competitors (context · weekly) ───────────────┐ │
│  │  Writes: competitors/     Last: 2d ago  Next: Mon 9am│ │
│  │                                              [▸ Run] │ │
│  └──────────────────────────────────────────────────────┘ │
│  ┌─ Competitive Brief (synthesis · weekly) ─────────────┐ │
│  │  Reads: competitors/, market/  Latest: Apr 3 delivered│ │
│  │                        [▸ View output]       [▸ Run] │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                           │
│  ── Domain: competitors/ ──────────────────────────────── │
│  _tracker.md · _landscape.md                              │
│  anthropic/ (profile.md, signals.md)                      │
│  openai/ (profile.md, signals.md)                         │
│  cursor/ (profile.md, signals.md)                         │
└──────────────────────────────────────────────────────────┘
```

#### File/output selected state

```
┌──────────────────────────────────────────────────────────┐
│  Competitive Intelligence                                 │
│  Domain: competitors/                                     │
│                                                           │
│  ── Tasks ─────────────────────────────────────────────── │
│  [compact task cards — same as above, always visible]     │
│                                                           │
│  ── ← Back to overview ─────────────────────────────────  │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                                                      │ │
│  │  [Full rendered file — markdown, HTML iframe, etc.]  │ │
│  │                                                      │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

Task cards stay pinned. Content area swaps between browse (file/output list) and view (full render). "← Back" returns to browse. Both "View output" on a synthesis task card and clicking a domain file use the same mechanism — set `selectedFile` → full render.

#### Task card anatomy

Each task card shows:
- **Title** + type badge (`context` / `synthesis`) + schedule
- **Context flow**: `Writes: competitors/` or `Reads: competitors/, market/`
- **Status**: last run time, next run time, latest output status
- **Actions**: `[▸ Run]` button, `[▸ View output]` for synthesis tasks

The context_reads/context_writes come from the task API (parsed from TASK.md). These make the agent → directory → output data flow explicit.

#### Synthesizer variant

Same three-zone layout, but the content area shows output list instead of domain tree:

```
┌──────────────────────────────────────────────────────────┐
│  Executive Reporting                                      │
│  Reads across: competitors, market, relationships         │
│                                                           │
│  ── Tasks ─────────────────────────────────────────────── │
│  ┌─ Weekly Executive Summary (synthesis · weekly) ──────┐ │
│  │  Reads: competitors/, market/, relationships/         │ │
│  │  Latest: Apr 3 · delivered  [▸ View]         [▸ Run] │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                           │
│  ── Outputs ──────────────────────────────────────────── │
│  Apr 3, 2026 · delivered                                  │
│  Mar 27, 2026 · delivered                                 │
│  Mar 20, 2026 · delivered                                 │
└──────────────────────────────────────────────────────────┘
```

Clicking an output row → full render in content area (same pattern as file selection).

#### Bot variant

Same layout — task cards + temporal observation directory:

```
┌──────────────────────────────────────────────────────────┐
│  Slack Bot                                                │
│  Platform: Slack · Connected ✓ · 4 channels               │
│                                                           │
│  ── Tasks ─────────────────────────────────────────────── │
│  ┌─ Daily Slack Digest (context · daily) ───────────────┐ │
│  │  Writes: slack/           Last: 6h ago  Next: 9am    │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                           │
│  ── Observations: slack/ ─────────────────────────────── │
│  2026-04-04.md                                            │
│  2026-04-03.md                                            │
│  2026-04-02.md                                            │
└──────────────────────────────────────────────────────────┘
### Right Panel: Agent-Scoped TP

ChatPanel scoped to the selected agent. Yarnnn logo FAB when closed.

- **Session:** Agent-scoped (`agent_slug` set)
- **Surface context:** `{ type: "agent-detail", agentSlug: "{slug}" }`
- **Header:** yarnnn logo + "TP" label + "· viewing {agent title}"
- **Trigger:** FAB button (yarnnn logo, rotate-180 hover) or always-visible panel

**Plus menu actions:**
- Run [task name] now (per assigned task)
- Assign a new task
- Web research
- Upload file

### Empty State (no tasks assigned to selected agent)

Center panel shows agent header + empty task section + empty domain:

```
┌──────────────────────────────────────────────────────────┐
│  Competitive Intelligence                                 │
│  Domain: competitors/ (empty)                             │
│                                                           │
│  ── Tasks ─────────────────────────────────────────────── │
│  No tasks assigned yet.                                   │
│  [Assign a task →] (opens chat with prompt)               │
│                                                           │
│  ── Domain: competitors/ ──────────────────────────────── │
│  (Will accumulate as tasks execute)                       │
└──────────────────────────────────────────────────────────┘
```

### Data Sources

| Component | API Endpoint | Notes |
|-----------|-------------|-------|
| Agent roster | `GET /api/agents` | Returns `agent_class`, `context_domain`. |
| Tasks with domains | `GET /api/tasks` | Returns `context_reads`, `context_writes`, `task_class`. Client-side group by `agent_slugs`. |
| Domain tree | `GET /api/workspace/tree?prefix=/workspace/context/{domain}` | Existing. |
| Task outputs | `GET /api/tasks/{slug}/outputs` | Existing. |
| File content | `GET /api/workspace/file?path=...` | Existing. |
| Agent-scoped chat | `POST /api/chat` with `surface_context.agentSlug` | Existing. |

### Key Implementation Note

The agents page reuses existing components:
- `WorkspaceTree` + `ContentViewer` (from context page) for domain steward views
- `OutputView` + `RunHistoryView` (from task page) for synthesizer views
- `ChatPanel` (shared) for right panel

New components needed:
- `AgentTreeNav` — agent roster with expandable task children (replaces `TaskTreeNav`)
- Agent-class dispatcher — routes to domain/synthesizer/bot view based on agent class
- Responsibilities section — compact task list under each agent view

---

## 3. Context Page (`/context`)

### Purpose

Workspace substrate explorer. User browses the full workspace filesystem: context domains, uploads, settings files. This is the Finder/Explorer view of accumulated knowledge.

### Layout

Unchanged from current implementation. Three-panel explorer:
- **Left:** WorkspaceTree (unified file tree with synthetic roots: Domains, Uploads, Settings)
- **Center:** ContentViewer (type-aware file preview, directory listing)
- **Right:** Workspace-scoped ChatPanel (navigation-aware context injection)

See [WORKSPACE-EXPLORER-UI.md](WORKSPACE-EXPLORER-UI.md) for full spec.

### Change from v2

Tasks folder removed from the context page explorer. Tasks are now accessed exclusively through the agents page (as responsibilities under each agent). The context page focuses purely on workspace-level content:

```
yarnnn
├── Domains/
│   ├── Competitors/
│   ├── Market/
│   ├── Relationships/
│   ├── Projects/
│   ├── Content/
│   └── Signals/
├── Uploads/
└── Settings/
    ├── IDENTITY.md
    ├── BRAND.md
    └── AWARENESS.md
```

---

## 4. Activity Page (`/activity`)

### Purpose

Temporal observation. Upcoming scheduled runs, past execution events, system activity. No chat — this is a read-only timeline.

### Layout

Unchanged from current implementation:
- **Upcoming section:** Active tasks with next scheduled run
- **Past section:** Chronological activity feed grouped by date, with filter chips

---

## 5. TP Context Injection

### `load_surface_content()` by surface type

| Surface Type | Context Loaded |
|-------------|----------------|
| `"chat"` | Agent roster summary, task list, platform status, workspace state |
| `"agent-detail"` | Full AGENT.md, owned domain summary, assigned tasks list, recent outputs |
| `"task-detail"` | Full TASK.md, run_log.md (last 5), latest output summary, assigned agent AGENT.md |
| `"context"` | Navigation-aware context (path, domain, entity) per WORKSPACE-EXPLORER-UI.md |

### Agent-scoped TP preamble

```
You are helping the user manage the agent "{agent_title}" ({agent_type}).

Agent identity:
{agent_md_content}

Owned domain: {domain_name} ({entity_count} entities, last updated {last_update})

Assigned tasks:
{task_list_with_status}

Your role on this page:
- Help the user understand what this agent knows and what it's working on
- Steer task focus, trigger runs, review domain health
- You CANNOT create new agents here — direct the user to /chat for that
```

### Chat page TP preamble

```
You are on the user's chat page — their strategic command center.

Your team: {agent_roster_summary}
Active tasks: {task_list_summary}
Connected platforms: {platform_status}
Workspace state: {workspace_state_signal}

Your role here:
- Create and assign tasks to agents
- Update workspace identity and brand
- Answer cross-cutting questions about the workforce
- Help with strategic planning and workspace setup
```

---

## 6. Session Architecture

| Surface | Session Key | Scope |
|---------|-------------|-------|
| Chat page | `user_id` (global) | Unscoped — workspace-level TP |
| Agents page (agent selected) | `user_id` + `agent_slug` | Agent-scoped TP |
| Agents page (task drill-down) | `user_id` + `task_slug` | Task-scoped TP |
| Context page | `user_id` (global) | Workspace-scoped TP (same session as chat) |

---

## 7. Mobile Layout (< 1024px)

**Chat page:** Full-width chat. No change needed — already single-column.

**Agents page:** Agent list as top selector (horizontal scroll or dropdown). Center panel full-width. Chat as bottom sheet (swipe up).

**Context page:** File tree as drawer (hamburger). Content viewer full-width. Chat as bottom sheet.

**Activity page:** Full-width feed. No change needed.

---

## 8. API Changes Required

| Change | Endpoint | Notes |
|--------|----------|-------|
| Add `context_domain` to agents | `GET /api/agents` | Map from AGENT_TEMPLATES — which domain this agent stewards |
| Agent-scoped TP session | `POST /api/chat` | Accept `agent_slug` in surface context, route to agent-scoped session |
| Remove `/tasks` as standalone surface | Frontend only | `/tasks` redirects to `/agents`. Task detail accessed via agent drill-down. |

No new endpoints needed. All data already available through existing APIs.

---

## 9. Implementation Sequence

| Step | What | Scope |
|------|------|-------|
| 1 | Add `context_domain` to agents API response | Backend, small |
| 2 | Build `/chat` page (~50 lines, full-width ChatPanel wrapper) | Frontend, small |
| 3 | Build `AgentTreeNav` component (agents as parents, tasks as children) | Frontend, medium |
| 4 | Build agent-class-aware center panel dispatcher | Frontend, medium (reuses existing components) |
| 5 | Wire ChatPanel with agent-scoped context on agents page | Frontend, small |
| 6 | Compose into `/agents` page, set as HOME_ROUTE | Frontend, medium |
| 7 | Update toggle bar: Chat \| Agents \| Context \| Activity | Frontend, small |
| 8 | Add `/tasks` → `/agents` redirect, remove Tasks from context explorer | Frontend, small |
| 9 | Delete old tasks page + TaskTreeNav | Frontend, cleanup |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-25 | v1 — Agent cards (left) + TP chat (left) + tasks/workspace tabs (right). |
| 2026-03-25 | v2 — Output-first. Workfloor: output feed + agent roster grid. Task page: output hero + trajectory. Chat as drawer. |
| 2026-04-04 | v3 — Agent-centric reframe. Agents page replaces both workfloor + tasks page. Tasks dissolve into agent responsibilities. Chat becomes dedicated page. Four-surface model: Chat \| Agents \| Context \| Activity. |
