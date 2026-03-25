# ADR-139: Workfloor + Task Surface Architecture

> **Status**: Proposed (v2 — output-first, chat-as-drawer)
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
6. **Chat is a tool, not a surface** — chat is an intervention drawer, not the default view. The user supervises outputs and reaches for chat when they need to steer. (v2 revision)

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
┌─ Left Panel (flex-1) ──────────┬─ Right Panel (400px) ─────────┐
│                                │  Agent Roster (2×3 grid)      │
│  Output Feed                   │  ┌──────┐ ┌──────┐ ┌──────┐  │
│  ┌──────────────────────────┐  │  │ Res  │ │ Cont │ │ Mktg │  │
│  │ Weekly Competitive Brief │  │  │ 🟢   │ │ ⏸    │ │ 🟢   │  │
│  │ Market Intelligence · 2h │  │  │ 2 tsk│ │ 1 tsk│ │ 1 tsk│  │
│  │ ┌─ output preview ────┐ │  │  └──────┘ └──────┘ └──────┘  │
│  │ │ Executive Summary:  │ │  │  ┌──────┐ ┌──────┐ ┌──────┐  │
│  │ │ CrewAI launched...  │ │  │  │ CRM  │ │ Slck │ │ Notn │  │
│  │ └────────────────────┘ │  │  │ ⏸    │ │ 🟢   │ │ 🔴   │  │
│  └──────────────────────────┘  │  │ 0 tsk│ │ 1 tsk│ │ 0 tsk│  │
│  ┌──────────────────────────┐  │  └──────┘ └──────┘ └──────┘  │
│  │ Daily Slack Recap       │  │                               │
│  │ Slack Bot · 6h ago      │  │  Quick stats + compact tabs   │
│  │ ┌─ output preview ────┐ │  │  for Tasks/Workspace/Platform │
│  │ │ #engineering: Team   │ │  │                               │
│  │ └────────────────────┘ │  │                               │
│  └──────────────────────────┘  │                               │
│  (scrollable, reverse-chrono)  │                               │
└────────────────────────────────┴───────────────────────────────┘
                                     Chat Drawer →  (slides from right, ⌘K or FAB)
```

**Left panel: Output Feed (hero)**
- Most recent outputs from all tasks, reverse-chronological
- Each card: task title, agent name, timestamp, output preview (~100 chars)
- Click → `/tasks/{slug}` (full output)
- This is what the user opens the workfloor to see: proof the system is alive

**Right panel: Agent Roster (living office)**
- 2×3 grid of agent "desk" cards (6 agents from ADR-140 roster)
- Each card: name, status dot (pulsing green = running, steady green = healthy, amber = overdue, red = error, gray = paused), task count
- Active agents have subtle shimmer animation — the "living office" feeling
- Below roster: quick stats + compact tabs for Tasks list, Workspace files, Platform status

**Chat: Drawer** (not a panel)
- Slides in from right edge (~400px), overlays right panel
- Triggered by FAB button (bottom-right) or ⌘K
- Global TP session. Surface context: `{ type: "workfloor" }`
- Use cases: create agent/task, direct workforce, ask questions
- Can be pinned open for chat-heavy interaction

**Design principle (v2):** Output feed is the heartbeat (left, hero). Agent roster is the living office (right, at-a-glance team health). Chat is an intervention tool (drawer, on-demand).

### `/tasks/{slug}` — Task Working Page (task-scoped)

```
┌─ Left Panel (flex-1) ──────────┬─ Right Panel (400px) ─────────┐
│                                │ Task Details                   │
│  Latest Output (rendered HTML) │                               │
│  ┌──────────────────────────┐  │ Status: active 🟢 · recurring  │
│  │                          │  │ Cadence: weekly                │
│  │  Executive Summary       │  │ Next run: Mar 28 09:00         │
│  │                          │  │ Delivery: email                │
│  │  CrewAI launched their   │  │ Agent: Market Intel →          │
│  │  enterprise tier this    │  │                               │
│  │  week, pricing at...     │  │ ── Objective ──                │
│  │                          │  │ Deliverable: Weekly AI...      │
│  │  [full rendered output]  │  │ Audience: Founder              │
│  │                          │  │ Purpose: Track competitor...   │
│  │                          │  │ Format: Doc + charts           │
│  │                          │  │                               │
│  │                          │  │ ── Success Criteria ──         │
│  │                          │  │ ☑ Cover CrewAI, AutoGen...    │
│  │                          │  │ ☑ Pricing comparison          │
│  │                          │  │ ☐ Positioning implications    │
│  │                          │  │                               │
│  │                          │  │ ── Run Trajectory ──           │
│  │                          │  │ ● Mar 25 ✓ confidence: high   │
│  │                          │  │ ○ Mar 18 ✓ confidence: med    │
│  │                          │  │ ○ Mar 11 ✓ confidence: low    │
│  │                          │  │   ↑ improving trend            │
│  │                          │  │                               │
│  └──────────────────────────┘  │ [⚙ Settings] [▶ Run Now]      │
└────────────────────────────────┴───────────────────────────────┘
                                     Chat Drawer →  (slides from right, ⌘K or FAB)
```

**Left panel: Latest Output (hero)**
- Rendered HTML output at full panel width, scrollable
- This is the deliverable — what the user came to see
- Clicking a run history entry in right panel swaps the displayed output
- If no output yet: "This task hasn't produced any output yet. Next run: {date}" + "Run Now" button
- Approve/reject/edit actions inline on the output (feedback loop)

**Right panel: Task Meta + Run Trajectory**
- Task metadata: status badge + mode label, cadence, next run, delivery, assigned agent
- Objective (from TASK.md `## Objective`): deliverable, audience, purpose, format
- Success criteria: checklist with self-assessment status (☑ met / ☐ missed) from latest run
- Run trajectory: date + status + self-assessment confidence level, with trend indicator (↑ improving / → stable / ↓ declining). This is the eval surface — closest analog to autoresearch's results.tsv
- Settings gear → modal for editing cadence, delivery, status, criteria. Run Now button.

**Chat: Drawer** (same pattern as workfloor)
- Task-scoped TP session (keyed by `task_slug`)
- TP has TASK.md + run_log.md + agent context injected
- Use cases: "Focus on pricing this week", "The competitor section is weak", "Change delivery to Slack"
- Surface context: `{ type: "task-detail", taskSlug }`

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

### Onboarding flow (ADR-140 pre-scaffolded roster)

1. User signs up → roster of 6 agents created automatically (ADR-140)
2. User lands on `/workfloor` — agent roster visible (all paused, 0 tasks), output feed empty
3. Chat drawer auto-opens with suggested prompts: "Weekly competitive intel", "Daily Slack recap"
4. User describes work → TP creates task, assigns to existing roster agent
5. Agent activates, output feed starts populating
6. User connects platforms → knowledge base enriches, bots activate

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
2. Left panel: output feed (reverse-chrono cards from all tasks)
3. Right panel: agent roster (2×3 grid) + quick stats + compact tabs (Tasks/Workspace/Platforms)
4. Chat drawer component (slides from right, FAB trigger + ⌘K)
5. Update `HOME_ROUTE` in `routes.ts` to `/workfloor`
6. Redirect `/orchestrator` → `/workfloor`
7. New endpoint: `GET /api/tasks/outputs/recent` (latest outputs across all tasks)

### Phase 2: Task page (frontend + backend)
1. Create `/tasks/[slug]` page with `WorkspaceLayout`
2. Left panel: latest output (rendered HTML, full width hero)
3. Right panel: task meta + objective + success criteria checklist + run trajectory with confidence/trend
4. Chat drawer (task-scoped TP, same component as workfloor)
5. Add `task_slug` column to `chat_sessions` (migration)
6. Update `chat.py` session routing for task-scoped sessions
7. Update `load_surface_content()` for task context injection

### Phase 3: Agent page (frontend)
1. Update `/agents/[slug]` — identity display + memory browser (left), assigned tasks + dev stats (right)
2. No chat drawer on this page (reference surface only)
3. Surface context: `{ type: "agent-identity", agentSlug }`

### Phase 4: Navigation + cleanup
1. Update sidebar nav: Workfloor (home), Activity, Integrations, Settings
2. Fold `/context` into workfloor Workspace tab
3. Delete `/orchestrator` page (after redirect period)
4. Delete `ChatAgent` class and agent_chat mode (dormant code)
5. Update onboarding: chat drawer auto-opens on first visit with suggested prompts

---

## Cost Impact

No cost change — same TP, same sessions, same primitives. Surface reorganization only.

---

## Future Considerations

### Task page as collaboration surface (not this ADR)
When multi-user support arrives, the task page's chat tab becomes a shared workspace where team members discuss the task's output. The session model already supports this — task-scoped sessions are keyed by task, not user.

### Agent marketplace (not this ADR)
Pre-configured agent identities shown as "hire" cards on the workfloor. The agent cards grid naturally accommodates this — available agents vs. your agents.
