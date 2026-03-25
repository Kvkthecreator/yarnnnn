# ADR-139: Workfloor + Task Surface Architecture

> **Status**: Proposed
> **Date**: 2026-03-25
> **Authors**: KVK, Claude
> **Depends on**: ADR-138 (Agents as Work Units — project layer collapse)
> **Supersedes**: ADR-124 (Meeting Room — project chat surface), ADR-125 (Project-Native Sessions — project session scoping), ADR-134 (Output-First Project Surface — project layout)
> **Evolves**: ADR-037 (Chat-First Surface Architecture), ADR-080 (Unified Agent Modes — chat surfaces), ADR-087 (Agent Scoped Context — session routing)
> **Preserves**: Surface-Action Mapping principle (SURFACE-ACTION-MAPPING.md — directives via chat, configuration via panel)

---

## Context

ADR-138 collapses the three-layer system (Workspace → Projects → Agents) into Agents (WHO) + Tasks (WHAT) + Workfloor (WHERE). The project layer is deleted — no `/projects` routes, no meeting rooms, no PM agents.

The current frontend has:
- `/orchestrator` — TP global chat + project list sidebar
- `/agents/[id]` — agent detail with agent-scoped TP chat + right panel (runs, instructions, memory, settings)
- `/projects/[slug]` — **DELETED** (was meeting room with multi-agent chat)

We need new surfaces that match the collapsed architecture.

### Design constraints

1. **Solo founder with 1-5 agents** — surfaces must feel productive at small scale, not empty
2. **TP is the single conversational interface** — all chat routes through TP, scoped by surface
3. **Output is what users care about** — the rendered deliverable is the hero, not config or chat
4. **Surface-Action Mapping preserved** — directives flow through chat, configuration lives in panels
5. **Two session scopes only** — global (workfloor) and task-scoped (task page). No agent-scoped sessions (agent steering happens via workfloor TP or task TP).

---

## Decision

### Two primary surfaces

| Route | Name | Purpose | Session Scope |
|-------|------|---------|---------------|
| `/workfloor` | Workfloor | Home — team overview + workspace management | Global TP |
| `/tasks/{slug}` | Task Page | Work surface — output + task steering | Task-scoped TP |
| `/agents/{slug}` | Agent Page | Identity — expertise, memory, development | Global TP (surface context) |

Supporting surfaces (unchanged):
| Route | Purpose |
|-------|---------|
| `/context` | Platform source curation |
| `/activity` | Global activity log |
| `/integrations` | Platform connections |

### Route changes

| Before | After | Rationale |
|--------|-------|-----------|
| `/orchestrator` (home) | `/workfloor` (home) | Name reflects the shared operating substrate, not just the chatbot |
| `/agents/[id]` | `/agents/{slug}` | Slug-based (consistent with workspace paths) |
| `/projects/[slug]` | **DELETED** | ADR-138 — no projects |
| — | `/tasks/{slug}` | **NEW** — task working surface |

---

## Surface Layouts

### `/workfloor` — Home (workspace-scoped)

```
┌──────────────────────────┬───────────────────────┐
│                          │ [Tasks] [Workspace]    │
│  Agents Display          │                       │
│                          │ Tasks tab:            │
│  ┌────────┐ ┌────────┐  │ ┌───────────────────┐ │
│  │Market  │ │Team    │  │ │ Weekly Briefing  → │ │
│  │Intel   │ │Observer│  │ │ ✓ delivered 2h ago │ │
│  │🔬 2 tasks│👁 1 task│  │ └───────────────────┘ │
│  └────────┘ └────────┘  │ ┌───────────────────┐ │
│                          │ │ Pricing Alert    → │ │
│  ┌────────┐              │ │ ⏳ next run: 3d   │ │
│  │Content │              │ └───────────────────┘ │
│  │Writer  │              │                       │
│  │✍️      │              │ Workspace tab:        │
│  └────────┘              │ • IDENTITY.md         │
│                          │ • BRAND.md            │
│  ── TP Chat ──────────── │ • preferences.md      │
│  "Create a researcher    │ • /knowledge/ ▾       │
│   for market analysis"   │                       │
│                          │ Platform status       │
│  /create-agent           │ • Slack 🟢 • Notion 🟢│
└──────────────────────────┴───────────────────────┘
```

**Left panel:**
- Agent cards grid/list — name, archetype icon, task count, health indicator
- Each card links to `/agents/{slug}`
- TP chat input at bottom — workspace-scoped commands
- Chat history scrolls above input (same pattern as current orchestrator)

**Right panel (tabbed):**
- **Tasks tab** — task list with status badges, cadence, last output date. Each row links to `/tasks/{slug}`. Sorted by last activity.
- **Workspace tab** — workspace-level MD files (IDENTITY.md, BRAND.md, preferences.md, notes.md), knowledge base browser, platform connection status.

**TP scope:** Global session. Actions available: create agent, create task, workforce health, onboarding, slash commands. Surface context: `{ type: "workfloor" }`.

**Design principle:** Agents are the visual anchor (left, prominent). Tasks are the work queue (right, scannable). Chat is the command line (bottom, always available).

### `/tasks/{slug}` — Task Working Page (task-scoped)

```
┌────────────────────────┬──────────────────────┐
│                        │ Task Details          │
│  [Output] [Chat]       │                      │
│                        │ Status: active 🟢     │
│  Output tab (default): │ Cadence: weekly       │
│  ┌──────────────────┐  │ Next run: Mar 28      │
│  │                  │  │ Delivery: email        │
│  │ Latest rendered  │  │ Agent: market-intel →  │
│  │ HTML output      │  │                      │
│  │ (full width,     │  │ ── Objective ──       │
│  │  scrollable)     │  │ Deliverable: Weekly.. │
│  │                  │  │ Audience: Founder     │
│  │                  │  │ Purpose: Track comp.. │
│  └──────────────────┘  │ Format: Doc + charts  │
│                        │                      │
│  Chat tab:             │ ── Success Criteria ──│
│  TP chat               │ • Cover CrewAI, etc.  │
│  (task-scoped)         │ • Include pricing     │
│  "Focus on pricing     │                      │
│   this week"           │ ── Run History ──     │
│                        │ Mar 25 ✓ [view]       │
│                        │ Mar 18 ✓ [view]       │
│                        │ Mar 11 ✓ [view]       │
└────────────────────────┴──────────────────────┘
```

**Left panel (tabbed):**
- **Output tab** (default) — latest rendered HTML output at full panel width. Scrollable. Run history entries in right panel swap the displayed output when clicked.
- **Chat tab** — TP chat scoped to this task. Session keyed by `task_slug`. Conversation persists across visits. User steers the task: "focus on pricing", "add a recommendations section", "change delivery to Slack".

**Right panel:**
- Task metadata: status, cadence, next run, delivery channel, assigned agent (links to `/agents/{slug}`)
- Objective (from TASK.md `## Objective`)
- Success criteria (from TASK.md `## Success Criteria`)
- Run history (date + status, clicking swaps left panel output)
- Settings gear icon → edit config (cadence, delivery, status) via direct manipulation

**TP scope:** Task-scoped session. Surface context: `{ type: "task-detail", taskSlug }`. TP has task context injected — TASK.md content, run_log.md, latest output summary, assigned agent identity. Directives in chat update TASK.md or agent memory as appropriate.

### `/agents/{slug}` — Agent Identity Page

```
┌────────────────────────┬──────────────────────┐
│                        │ Agent Identity        │
│  Agent Overview        │                      │
│                        │ Market Intelligence   │
│  AGENT.md content      │ 🔬 researcher         │
│  (identity, expertise, │                      │
│   capabilities)        │ ── Assigned Tasks ──  │
│                        │ • Weekly Briefing →   │
│  ── Memory Browser ──  │ • Pricing Alert →     │
│  • observations.md     │                      │
│  • preferences.md      │ ── Development ──     │
│  • self_assessment.md  │ Runs: 12             │
│  • directives.md       │ Since: Mar 1         │
│                        │ Last run: Mar 25      │
│                        │                      │
│                        │ ── Actions ──         │
│                        │ [Edit Identity]       │
│                        │ [Pause Agent]         │
│                        │ [Archive]             │
└────────────────────────┴──────────────────────┘
```

**Left panel:** Agent identity (AGENT.md rendered) + memory file browser (expandable sections showing observations, preferences, self-assessment, directives). Read-only display — edits happen via workfloor TP chat ("update Market Intel's expertise to include pricing analysis").

**Right panel:** Archetype badge, assigned tasks (links to `/tasks/{slug}`), development stats (run count, tenure, last run), action buttons (edit, pause, archive).

**No dedicated chat on this page.** Agent steering happens via:
- Workfloor TP: "update Market Intel's capabilities"
- Task TP: "focus on pricing in the weekly briefing" (steers agent in task context)

This is a **reference surface**, not a working surface. The user comes here to inspect agent state, not to have a conversation.

---

## Session Architecture

### Two session scopes

| Scope | Key | Rotation | Surfaces |
|-------|-----|----------|----------|
| Global TP | `user_id` | 4h inactivity | `/workfloor`, `/agents/{slug}` |
| Task-scoped TP | `user_id` + `task_slug` | 4h inactivity | `/tasks/{slug}` |

### Schema change

```sql
ALTER TABLE chat_sessions ADD COLUMN task_slug TEXT;
```

Session routing in `chat.py`:
- If `surface_context.taskSlug` → find/create session with `task_slug` match
- Else → find/create global session (no task_slug)

### Agent-scoped sessions: DEPRECATED

Current `chat_sessions.agent_id` column becomes unused. Agent identity steering flows through global TP (workfloor) or task-scoped TP. No separate agent session scope.

The `agent_id` column is kept for backwards compatibility during migration but not written to for new sessions. Drop in a future cleanup migration.

---

## TP Context Injection by Surface

| Surface | Injected Context |
|---------|-----------------|
| `/workfloor` | Agent list summary, task list summary, workspace files, platform status |
| `/tasks/{slug}` | TASK.md content, run_log.md, latest output summary, assigned agent AGENT.md + memory highlights |
| `/agents/{slug}` | Agent AGENT.md, memory files, assigned tasks list (uses global TP session, surface context only) |

Surface context drives what TP knows, not which TP instance answers. Same TP, same primitives, different contextual awareness.

---

## Navigation

### Sidebar (persistent)

```
🏠 Workfloor          (home, always first)
📋 Activity
🔗 Integrations
⚙️ Settings
```

Context (`/context`) folds into Workfloor's Workspace tab (platform sources are workspace-level config). Integrations remains standalone (OAuth flows, connection management).

### Breadcrumbs

- `/workfloor` → **Workfloor**
- `/tasks/{slug}` → **Workfloor** > **Weekly Competitive Briefing**
- `/agents/{slug}` → **Workfloor** > **Market Intelligence**

Tasks and agents are children of workfloor in the navigation hierarchy.

---

## Interaction Patterns

### Surface-Action Mapping (preserved from existing principle)

| Action Type | Surface | Examples |
|-------------|---------|----------|
| **Directives** (what agent should care about) | Chat (workfloor or task) | "focus on pricing", "use formal tone", "ignore #random" |
| **Configuration** (structural settings) | Right panel direct manipulation | Cadence dropdown, delivery toggle, status switch |
| **Reference** (accumulated state) | Panels, read-only | Memory browser, run history, agent identity |
| **Creation** (new entities) | Chat | "create a researcher agent", "add a weekly briefing task" |

### Onboarding flow

1. User signs up → lands on `/workfloor` (empty state)
2. Empty state shows: "What kind of work do you need help with?" prompt in TP chat
3. User describes work → TP creates agent + task
4. Agent card appears in left panel, task appears in right panel
5. User connects platforms → knowledge base populates
6. First task runs on cadence → output appears on task page

---

## What Gets Deleted

| Component | Reason |
|-----------|--------|
| `/orchestrator` route | Replaced by `/workfloor` |
| `/projects/` routes | Already deleted (ADR-138) |
| Agent-scoped session creation | No longer needed — global or task-scoped only |
| `ChatAgent` class usage | Was dormant (never wired into routing) — can be fully deleted |
| `chat_sessions.agent_id` writes | Deprecated — kept in schema, not written |
| Project panels in orchestrator | Replaced by agent cards + task list |

---

## Implementation Phases

### Phase 1: Route + Layout (frontend)
1. Create `/workfloor` page with `WorkspaceLayout`
2. Left panel: agent cards grid (read from `/api/agents`)
3. Right panel: tabbed — Tasks (read from `/api/tasks`) | Workspace (read workspace files)
4. TP chat at bottom of left panel (reuse existing chat components)
5. Update `HOME_ROUTE` in `routes.ts` to `/workfloor`
6. Redirect `/orchestrator` → `/workfloor`

### Phase 2: Task page (frontend + backend)
1. Create `/tasks/[slug]` page with `WorkspaceLayout`
2. Left panel: tabbed — Output (rendered HTML) | Chat (task-scoped TP)
3. Right panel: task details from TASK.md + run history from `/tasks/{slug}/outputs/`
4. Add `task_slug` column to `chat_sessions` (migration)
5. Update `chat.py` session routing for task-scoped sessions
6. Update `load_surface_content()` for task context injection

### Phase 3: Agent page (frontend)
1. Update `/agents/[slug]` — remove chat, add identity display + memory browser
2. Right panel: assigned tasks (links to task pages), development stats, actions
3. Surface context: `{ type: "agent-identity", agentSlug }`

### Phase 4: Navigation + cleanup
1. Update sidebar nav: Workfloor (home), Activity, Integrations, Settings
2. Fold `/context` into workfloor Workspace tab
3. Delete `/orchestrator` page (after redirect period)
4. Delete `ChatAgent` class and agent_chat mode (dormant code)
5. Update onboarding empty state for workfloor

---

## Cost Impact

No cost change — same TP, same sessions, same primitives. Surface reorganization only.

---

## Future Considerations

### Task page as collaboration surface (not this ADR)
When multi-user support arrives, the task page's chat tab becomes a shared workspace where team members discuss the task's output. The session model already supports this — task-scoped sessions are keyed by task, not user.

### Agent marketplace (not this ADR)
Pre-configured agent identities shown as "hire" cards on the workfloor. The agent cards grid naturally accommodates this — available agents vs. your agents.
