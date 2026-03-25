# Surface Architecture — Workfloor + Tasks + Agents

**Date:** 2026-03-25
**Status:** Proposed
**ADR:** [ADR-139](../adr/ADR-139-workfloor-task-surface-architecture.md)
**Depends on:** [ADR-138](../adr/ADR-138-agents-as-work-units.md) (Agents as Work Units)
**Supersedes:** [WORKSPACE-LAYOUT-NAVIGATION.md](WORKSPACE-LAYOUT-NAVIGATION.md) (persistent panel architecture — layout pattern preserved, surfaces redefined)

---

## Route Map

```
/workfloor              → Home. Agents + TP chat + tasks/workspace panels.
/tasks/{slug}           → Task working page. Output + chat + task details.
/agents/{slug}          → Agent identity page. Read-only reference + actions.
/activity               → Global activity log.
/integrations           → Platform connections (OAuth, source management).
```

**Deleted routes:** `/orchestrator` (→ `/workfloor`), `/projects/*` (ADR-138), `/context` (→ workfloor Workspace tab).

---

## 1. Workfloor (`/workfloor`)

### Purpose
Landing page. User sees their team (agents) and their work queue (tasks). TP chat available for workspace-level commands.

### Layout (desktop ≥ 1024px)

```
┌─ Left Panel (flex-1) ──────────┬─ Right Panel (400px) ─────────┐
│                                │ [Tasks] [Workspace]            │
│  Agent Cards (grid)            │                               │
│  ┌──────┐ ┌──────┐ ┌──────┐  │ Tasks tab:                    │
│  │ name │ │ name │ │ name │  │  TaskRow: title, status badge, │
│  │ type │ │ type │ │ type │  │    cadence, last output,       │
│  │ tasks│ │ tasks│ │ tasks│  │    assigned agent → link       │
│  └──┬───┘ └──┬───┘ └──┬───┘  │                               │
│     ↓ /agents/{slug}          │ Workspace tab:                │
│                                │  FileList: IDENTITY.md,       │
│  ─────────────────────────     │    BRAND.md, preferences.md,  │
│  TP Chat Area                  │    notes.md, /knowledge/ tree │
│  (global session, scrollable)  │  PlatformStatus: Slack 🟢,   │
│  ┌──────────────────────────┐  │    Notion 🟢                  │
│  │ input + send             │  │                               │
│  └──────────────────────────┘  │                               │
└────────────────────────────────┴───────────────────────────────┘
```

### Design Inspiration: OpenClaw "Agents Team" Office

Reference: OpenClaw's team overview uses an office metaphor where each agent has a visual "desk" with personality, status indicators (working/idle), and a sidebar roster with filters. Key takeaways for workfloor:

1. **Agent status is the hero** — each card prominently shows WORKING / IDLE / ERROR state, not buried in metadata
2. **Sidebar roster with filters** — `[ALL] [WORKING] [IDLE]` tabs let you quickly scan team health. We adapt this as status filters on the agent grid.
3. **Visual personality per agent** — each agent has a distinct visual identity (desk scene, avatar). We can't do pixel art, but we CAN give each archetype a distinct color + icon + personality tagline from AGENT.md.
4. **Live activity indicators** — green dots for active, progress percentages for in-flight work. We show: 🟢 last run succeeded, 🟡 overdue, 🔴 failed, ⏳ running now.
5. **Team-level timestamp** — "TIME: 00:06 PM" shows workspace is alive. We show last activity timestamp.

### Components

**AgentCard** (left panel, grid — inspired by OpenClaw desk cards):
- **Status indicator**: prominent — `WORKING` (currently executing), `READY` (idle, next run scheduled), `PAUSED`, `ERROR`
- Agent title + archetype icon (🔬 researcher, 👁 monitor, ✍️ producer, ⚙️ operator)
- Archetype-specific color accent (research=blue, monitor=green, producer=purple, operator=orange)
- Assigned task count badge
- Last activity: "delivered 2h ago" or "running..." with progress
- One-line tagline from AGENT.md `## Identity` (first sentence)
- Click → `/agents/{slug}`

**AgentGrid filter bar** (above cards):
- `[All] [Working] [Ready] [Paused]` — quick filter by status
- Sort: most recent activity first (default)

**TaskRow** (right panel, Tasks tab):
- Task title (from TASK.md `# {title}`)
- Status badge: `active` 🟢 | `paused` ⏸ | `completed` ✓ | `archived` 📦
- Cadence label: "weekly", "daily", "monthly"
- Last output: relative time ("2h ago", "3d ago") or "never"
- Assigned agent name (small text)
- Click → `/tasks/{slug}`

**WorkspaceFileList** (right panel, Workspace tab):
- List of workspace-level MD files with click-to-expand preview
- Knowledge base tree (`/knowledge/` subdirectories)
- Platform connection status cards

**TPChat** (left panel, bottom):
- Reuses existing `ChatArea` / `ChatFirstDesk` components
- Global TP session (no task_slug, no agent_id)
- Surface context: `{ type: "workfloor" }`
- Slash commands: `/create-agent`, `/create-task`, `/status`

### Data Sources

| Component | API Endpoint | Notes |
|-----------|-------------|-------|
| AgentCard grid | `GET /api/agents` | Existing endpoint, add task_count |
| TaskRow list | `GET /api/tasks` | New endpoint (Phase 3 of ADR-138) |
| WorkspaceFileList | `GET /api/workspace/files?prefix=/workspace/` | Existing workspace read |
| KnowledgeTree | `GET /api/workspace/files?prefix=/knowledge/` | Existing workspace list |
| PlatformStatus | `GET /api/platforms` | Existing endpoint |
| TPChat | `POST /api/chat` | Existing, surface_context.type = "workfloor" |

### Empty State (onboarding)

When no agents exist:
```
┌────────────────────────────────────────────────┐
│                                                │
│  Welcome to your workfloor.                    │
│                                                │
│  Tell me what kind of work you need help with: │
│                                                │
│  "I need weekly competitive intelligence"      │
│  "Help me track our Slack activity"            │
│  "I want monthly investor updates"             │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │ input + send                             │  │
│  └──────────────────────────────────────────┘  │
│                                                │
└────────────────────────────────────────────────┘
```

TP processes the intent → creates agent + task → cards appear.

---

## 2. Task Page (`/tasks/{slug}`)

### Purpose
Working surface for a specific task. Output is the hero. Chat available for steering.

### Layout (desktop ≥ 1024px)

```
┌─ Left Panel (flex-1) ──────────┬─ Right Panel (400px) ─────────┐
│                                │ Task Details                   │
│  [Output] [Chat]               │                               │
│                                │ Status: active 🟢              │
│  Output tab (default):         │ Cadence: weekly                │
│  ┌──────────────────────────┐  │ Next run: Mar 28               │
│  │                          │  │ Delivery: email                │
│  │  Rendered HTML output    │  │ Agent: market-intel →          │
│  │  (full width, scroll)    │  │                               │
│  │                          │  │ ── Objective ──                │
│  │                          │  │ Deliverable: Weekly AI...      │
│  │                          │  │ Audience: Founder              │
│  │                          │  │ Purpose: Track competitor...   │
│  └──────────────────────────┘  │ Format: Doc + charts           │
│                                │                               │
│  Chat tab:                     │ ── Success Criteria ──         │
│  TP chat (task-scoped)         │ • Cover CrewAI, AutoGen...     │
│  "Focus on pricing             │ • Include pricing comparison   │
│   comparisons this week"       │                               │
│                                │ ── Run History ──              │
│                                │ ● Mar 25 ✓  [view]            │
│                                │ ○ Mar 18 ✓  [view]            │
│                                │ ○ Mar 11 ✓  [view]            │
│                                │                               │
│                                │ [⚙ Settings] [▶ Run Now]      │
└────────────────────────────────┴───────────────────────────────┘
```

### Left Panel Tabs

**Output tab** (default):
- Renders latest task output HTML in an iframe or sanitized HTML container
- Full left-panel width for readability
- If no output yet: empty state with "This task hasn't produced any output yet. Next run: {date}" or "Run Now" button
- Clicking a run history entry in right panel swaps the displayed output

**Chat tab:**
- TP chat scoped to this task
- Task-scoped session (keyed by `task_slug` in `chat_sessions`)
- TP has TASK.md + run_log.md + agent context injected
- Directives here update TASK.md (via TP primitives) or agent memory
- Surface context: `{ type: "task-detail", taskSlug: "{slug}" }`

### Right Panel Sections

**Task metadata** (top, always visible):
- Status badge (active/paused/completed/archived)
- Cadence (human-readable)
- Next run timestamp
- Delivery channel
- Assigned agent (link to `/agents/{slug}`)

**Objective** (from TASK.md `## Objective`):
- Deliverable, audience, purpose, format — rendered as compact key-value pairs

**Success Criteria** (from TASK.md `## Success Criteria`):
- Bulleted list

**Run History** (scrollable list):
- Date + status indicator (✓ success, ✗ failed, ⏳ running)
- Active item highlighted (currently displayed in left panel)
- Click to view past output
- Most recent at top

**Actions** (bottom):
- Settings gear → slide-out or modal for editing cadence, delivery, status (direct manipulation)
- Run Now button → triggers immediate task execution via API

### Data Sources

| Component | Source | Notes |
|-----------|--------|-------|
| Output HTML | `GET /api/tasks/{slug}/outputs/latest` | New endpoint, reads from workspace |
| Task details | `GET /api/tasks/{slug}` | New endpoint, parses TASK.md |
| Run history | `GET /api/tasks/{slug}/runs` | New endpoint, reads output manifests |
| TPChat | `POST /api/chat` with `surface_context.taskSlug` | Task-scoped session |
| Run Now | `POST /api/tasks/{slug}/run` | New endpoint, triggers execution |

---

## 3. Agent Page (`/agents/{slug}`)

### Purpose
Reference surface for agent identity and development. Not a working surface — no dedicated chat.

### Layout (desktop ≥ 1024px)

```
┌─ Left Panel (flex-1) ──────────┬─ Right Panel (400px) ─────────┐
│                                │ Agent Identity                 │
│  AGENT.md Content              │                               │
│  ┌──────────────────────────┐  │ Market Intelligence            │
│  │ # Market Intelligence    │  │ 🔬 researcher                  │
│  │                          │  │                               │
│  │ ## Identity              │  │ ── Assigned Tasks ──           │
│  │ Domain expert in...      │  │ • Weekly Briefing →            │
│  │                          │  │ • Pricing Alert →              │
│  │ ## Expertise             │  │                               │
│  │ - AI agent platforms     │  │ ── Development ──              │
│  │ - Competitive analysis   │  │ Total runs: 12                 │
│  │                          │  │ Active since: Mar 1            │
│  │ ## Capabilities          │  │ Last run: Mar 25               │
│  │ - web_search, chart...   │  │ Approval rate: 92%             │
│  └──────────────────────────┘  │                               │
│                                │ ── Memory Files ──             │
│  ── Memory Browser ──          │ observations.md (2.1k)         │
│  [observations] [preferences]  │ preferences.md (850)           │
│  [self_assessment] [directives]│ self_assessment.md (1.2k)      │
│                                │ directives.md (400)            │
│  Expanded file content here    │                               │
│                                │ ── Actions ──                  │
│                                │ [Edit Identity] [Pause] [Del]  │
└────────────────────────────────┴───────────────────────────────┘
```

### Left Panel
- AGENT.md rendered as markdown (identity, expertise, capabilities)
- Memory browser: tabbed or accordion — each memory file expandable with content preview
- All read-only on this surface

### Right Panel
- Archetype badge + display name
- Assigned tasks list (links to `/tasks/{slug}`)
- Development stats: run count, tenure, last run, approval rate
- Memory file list with sizes
- Action buttons: Edit Identity (opens chat or modal), Pause, Archive

### Interaction Model
- **No chat on this page** — this is a reference surface
- To steer agent identity: go to `/workfloor` and tell TP "update Market Intel's expertise"
- To steer agent behavior on a task: go to `/tasks/{slug}` and use task-scoped chat
- Edit Identity button could: (a) navigate to workfloor with pre-filled prompt, or (b) open inline edit modal for AGENT.md

---

## 4. Session Architecture

### Session Scoping

```
chat_sessions
├── task_slug IS NULL     → Global TP session (workfloor, agent pages)
└── task_slug = '{slug}'  → Task-scoped session (task page)
```

### Migration

```sql
-- ADR-139: Task-scoped sessions
ALTER TABLE chat_sessions ADD COLUMN task_slug TEXT;

-- Index for session lookup
CREATE INDEX idx_chat_sessions_task_slug ON chat_sessions(user_id, task_slug)
  WHERE task_slug IS NOT NULL;
```

### Session Routing (chat.py)

```python
if surface_context and surface_context.task_slug:
    session = await get_or_create_session(
        client, user_id, scope="daily", task_slug=surface_context.task_slug
    )
else:
    session = await get_or_create_session(
        client, user_id, scope="daily"  # Global TP
    )
```

### Agent-scoped sessions (DEPRECATED)

`chat_sessions.agent_id` is no longer written to. Existing rows preserved for history. Column drop deferred to cleanup migration.

---

## 5. TP Context Injection

### `load_surface_content()` updates

| Surface Type | Context Loaded |
|-------------|----------------|
| `"workfloor"` | Agent list (title, role, task count), task list (title, status, cadence, last_run), platform status |
| `"task-detail"` | Full TASK.md, run_log.md (last 5 entries), latest output summary (first 500 chars), assigned agent AGENT.md, agent memory highlights |
| `"agent-identity"` | Full AGENT.md, memory file summaries, assigned tasks list |

### System prompt additions

Task-scoped TP gets a preamble:

```
You are helping the user manage the task "{task_title}".

Task definition:
{task_md_content}

Recent run log:
{run_log_last_5}

Assigned agent: {agent_title} ({agent_role})
Agent expertise: {agent_expertise_summary}
```

This ensures TP answers are grounded in the specific task context without the user having to explain what they're looking at.

---

## 6. Navigation Sidebar

### Structure

```
┌─────────────────┐
│ 🏠 Workfloor     │  ← home, always first
│ 📋 Activity      │
│ 🔗 Integrations  │
│ ⚙️ Settings      │
└─────────────────┘
```

### Changes from current

| Before | After |
|--------|-------|
| Orchestrator (home) | Workfloor (home) |
| Agents (list) | Removed — agents visible on workfloor |
| Projects (list) | Removed — ADR-138 |
| Context | Removed — folded into workfloor Workspace tab |
| Activity | Unchanged |
| Integrations | Unchanged |
| Settings | Unchanged |

### Breadcrumb Pattern

```
Workfloor                           → /workfloor
Workfloor > Weekly Briefing         → /tasks/{slug}
Workfloor > Market Intelligence     → /agents/{slug}
```

---

## 7. Mobile Layout (< 1024px)

Same content, stacked vertically:

**Workfloor mobile:**
- Agent cards (horizontal scroll or compact list)
- TP chat (full width)
- Tasks/Workspace as bottom sheet or tab bar

**Task page mobile:**
- Output (full width, default view)
- Chat (swipe or tab to switch)
- Task details as bottom sheet

**Agent page mobile:**
- Identity content (full width)
- Memory browser (accordion)
- Actions as bottom bar

---

## 8. API Endpoints (New)

| Method | Route | Purpose |
|--------|-------|---------|
| `GET` | `/api/tasks` | List user's tasks (slug, status, cadence, last_run, agent) |
| `GET` | `/api/tasks/{slug}` | Task details (parsed TASK.md + DB metadata) |
| `POST` | `/api/tasks` | Create task (writes TASK.md + DB row) |
| `PATCH` | `/api/tasks/{slug}` | Update task (cadence, delivery, status) |
| `DELETE` | `/api/tasks/{slug}` | Archive task |
| `GET` | `/api/tasks/{slug}/outputs/latest` | Latest output HTML |
| `GET` | `/api/tasks/{slug}/outputs` | Output history (manifests) |
| `POST` | `/api/tasks/{slug}/run` | Trigger immediate execution |

These are defined in ADR-138 Phase 3 (`api/routes/tasks.py`). This doc specifies the frontend contract.

---

## Relationship to Other Design Docs

- **SURFACE-ACTION-MAPPING.md** — principle preserved. Directives via chat, config via panel. This doc applies that principle to the new surface architecture.
- **WORKSPACE-LAYOUT-NAVIGATION.md** — layout pattern (persistent right panel, ~400px) preserved. Surfaces redefined. That doc should be marked as superseded by this one.
- **AGENT-PRESENTATION-PRINCIPLES.md** — agent card design carries forward to workfloor AgentCard component.
