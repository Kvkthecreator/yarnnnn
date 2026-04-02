# Surface Architecture — Workfloor + Tasks + Agents

**Date:** 2026-03-25 (v2 — output-first, chat-as-drawer)
**Status:** Proposed
**ADR:** [ADR-139](../adr/ADR-139-workfloor-task-surface-architecture.md)
**Depends on:** [ADR-138](../adr/ADR-138-agents-as-work-units.md) (Agents as Work Units), [ADR-140](../adr/ADR-140-agent-workforce-model.md) (Workforce Model)
**Supersedes:** [WORKSPACE-LAYOUT-NAVIGATION.md](WORKSPACE-LAYOUT-NAVIGATION.md) (layout pattern preserved, surfaces redefined)

---

## Design Principle: Output-First, Chat-as-Tool

Both primary surfaces (workfloor, task page) lead with **output** — the proof of value. Chat is not a panel. Chat is a **drawer** — an intervention tool the user reaches for when they need to steer, not the default view.

The shift: from "chat with your AI assistant" to "supervise your workforce, intervene when needed."

| Surface | Left panel (hero, ~60%) | Right panel (context, ~40%) | Chat |
|---------|------------------------|---------------------------|------|
| Workfloor | Output feed (all tasks) | Agent roster (living office grid) | Drawer (right edge, global TP) |
| Task page | Latest output (rendered HTML) | Task meta + run trajectory | Drawer (right edge, task-scoped TP) |
| Agent page | AGENT.md + memory browser | Assigned tasks + dev stats | No chat (reference surface) |

---

## Route Map

```
/workfloor              → Home. Output feed + agent roster. Chat as drawer.
/tasks/{slug}           → Task working page. Output hero + trajectory. Chat as drawer.
/agents/{slug}          → Agent identity page. Read-only reference + actions.
/activity               → Global activity log.
/integrations           → Platform connections (OAuth, source management).
```

**Deleted routes:** `/orchestrator` (→ `/workfloor`), `/projects/*` (ADR-138), `/context` (→ workfloor Workspace tab).

---

## 1. Workfloor (`/workfloor`)

### Purpose
Landing page. User answers: "What's happening with my work?" Isometric room provides ambient visual identity; floating panels provide functional access.

### Layout (desktop ≥ 1024px) — Overlay Architecture (v4, 2026-03-30)

Inspired by Habbo Hotel: room fills the viewport as persistent backdrop, all functional UI floats as overlapping panels. Everything visible in one screen — no scrolling past the room.

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Isometric Agent Room (full viewport, ambient backdrop)         │
│                                                                 │
│  ┌── Left Panel (340px) ───┐          ┌── Right Panel (380px) ─┐│
│  │ [Tasks] [Context]       │          │ Chat                  X ││
│  │ ─────────────────────── │          │                        ││
│  │ • Weekly Market Intel  w│          │ Messages...            ││
│  │ • Daily Slack Recap    d│          │                        ││
│  │ + Add deliverable       │          │                        ││
│  │                         │          │ [+ input ...]     Send ││
│  └─────────────────────────┘          └────────────────────────┘│
│                                                                 │
│            [ + New Task ]  [ Update Context ]  [ Chat ]         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Panels**: Semi-transparent (`bg-background/90 backdrop-blur-md`), rounded, shadowed. Both collapsible — bottom action bar shows toggle buttons when collapsed.

**Bottom action bar**: Centered, always visible. Primary actions:
- **+ New Task** — opens Tasks tab in left panel + catalog
- **Update Context** — sends "Update my context" to TP chat (opens chat if closed)
- **Chat** — toggle (visible only when chat panel collapsed)
- **Tasks** — toggle (visible only when left panel collapsed)

### Left Panel: Output Feed (Hero)

The most recent outputs from all tasks, reverse-chronological. This is what the user opens the workfloor to see.

**OutputFeedCard**:
- Task title (from TASK.md `# {title}`)
- Agent name + timestamp ("Market Intelligence · 2h ago")
- Output preview: first ~100 chars of the output, or a structured summary if available
- Status: delivered ✓, pending review ⏳, failed ✗
- Click → `/tasks/{slug}` (goes to full output)

**Empty state**: "Your agents haven't produced anything yet. Next run: {date}. Or tell me what you need →" (arrow points to chat FAB).

### Right Panel: Agent Roster (Living Office)

**Agent grid as spatial cards (2×3)** — inspired by OpenClaw's office metaphor. Each card is a "desk." The grid is always full (6 agents from ADR-140 roster), no scrolling needed.

**AgentDeskCard**:
- Agent display name (compact: "Research", "Content", "Slack")
- Status indicator — pulsing green dot = running now, steady green = healthy, amber = overdue, red = error, gray = paused
- Assigned task count badge
- Last activity: "2h ago" or "running..." with shimmer animation
- Archetype-specific accent color (research=blue, content=purple, marketing=teal, crm=amber, slack=green, notion=gray)
- Click → `/agents/{slug}`

**Liveness signals** (the OpenClaw feeling):
- Active agent cards have a subtle shimmer/pulse animation
- "Running now" state shows a progress indicator
- Timestamp recency tells you at a glance who's active vs dormant
- Status dots update in real-time (or on page focus via polling)

**Below roster**: Quick stats (runs this week, next scheduled, budget remaining) + compact tabs for Tasks list / Workspace files / Platform status. These are secondary — visible but not competing with the roster.

### Chat: Drawer (Not Panel)

Chat is a right-edge drawer that slides over the right panel when activated. Full-height, ~400px wide.

- **Trigger**: persistent FAB button (bottom-right corner) or keyboard shortcut
- **Scope**: Global TP session (no task_slug)
- **Can be pinned open** for chat-heavy interaction
- **Surface context**: `{ type: "workfloor" }`
- **Use cases**: "Create a new task", "Adjust the research agent's focus", "What happened with the briefing?", "Connect Slack"

**FAB ambient awareness** (ADR-155 Phase 3): The FAB communicates system state beyond just "click to open chat":
- **Idle**: static icon (default)
- **Working**: pulse animation (tool executing — inference, task run)
- **Notified**: badge count (side effects occurred while chat was closed)
- **Attention**: subtle glow (TP generated text while closed)

Tool results with user-visible side effects (workspace scaffolded, task created, etc.) render as inline action cards in the chat stream. When chat is closed, they queue and the FAB badge increments. Opening chat flushes the queue. See `docs/design/TP-NOTIFICATION-CHANNEL.md`.

This keeps the two-panel layout clean (output feed + roster) and makes chat an explicit mode shift: "I'm now directing" vs "I'm now supervising."

### Data Sources

| Component | API Endpoint | Notes |
|-----------|-------------|-------|
| OutputFeed | `GET /api/tasks/outputs/recent` | New endpoint — latest outputs across all tasks |
| AgentRoster | `GET /api/agents` | Existing, add task_count + last_activity |
| QuickStats | `GET /api/dashboard/stats` | New lightweight endpoint |
| TaskList (tab) | `GET /api/tasks` | Existing |
| WorkspaceFiles (tab) | `GET /api/workspace/files?prefix=/workspace/` | Existing |
| PlatformStatus (tab) | `GET /api/platforms` | Existing |
| Chat drawer | `POST /api/chat` | Existing, surface_context.type = "workfloor" |

### Empty State (onboarding — ADR-140 pre-scaffolded roster)

When agents exist (always, post ADR-140) but no tasks yet:

```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  Left: "No outputs yet"               Right: Agent roster (all    │
│  "Your team is ready.                  paused, 0 tasks each)      │
│   Tell me what you need:"                                          │
│                                                                    │
│  Suggested prompts:                                                │
│  • "Weekly competitive intelligence"                               │
│  • "Daily Slack recap"                                            │
│  • "Monthly investor update"                                      │
│                                        Chat drawer auto-opens      │
│  ┌──────────────────────────────┐                                  │
│  │ input + send                 │                                  │
│  └──────────────────────────────┘                                  │
└────────────────────────────────────────────────────────────────────┘
```

On first visit with no tasks, the chat drawer auto-opens with suggested prompts. The roster shows all 6 agents in paused/ready state — the team is visible even before they have work.

---

## 2. Task Page (`/tasks/{slug}`)

### Purpose
Working surface for a specific task. User answers: "How is this specific task doing?" Output is the hero.

### Layout (desktop ≥ 1024px)

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
│  │                          │  │ ○ Mar 11 ✓ confidence: high   │
│  │                          │  │ ○ Mar 4  ✓ confidence: low    │
│  │                          │  │   ↑ improving trend            │
│  │                          │  │                               │
│  └──────────────────────────┘  │ [⚙ Settings] [▶ Run Now]      │
└────────────────────────────────┴───────────────────────────────┘

                                 ┌─ Chat Drawer (slides from right) ─┐
                                 │ Task-scoped TP                     │
                                 │ "Focus on pricing comparisons      │
                                 │  this week"                        │
                                 │ ┌──────────────────────────────┐   │
                                 │ │ input + send                 │   │
                                 │ └──────────────────────────────┘   │
                                 └────────────────────────────────────┘
```

### Left Panel: Latest Output (Hero)

- Renders latest task output HTML in sanitized container (full left-panel width)
- This is the deliverable — what the user came to see
- If no output yet: empty state with "This task hasn't produced any output yet. Next run: {date}" + "Run Now" button
- Clicking a run history entry in right panel swaps the displayed output
- Approve/reject/edit actions inline on the output (feedback loop)

### Right Panel: Task Meta + Trajectory

**Task metadata** (top, always visible):
- Status badge (active/paused/completed/archived) + mode label (recurring/goal/reactive)
- Cadence (human-readable)
- Next run timestamp
- Delivery channel
- Assigned agent (link to `/agents/{slug}`)

**Objective** (from TASK.md `## Objective`):
- Deliverable, audience, purpose, format — compact key-value pairs

**Success Criteria** (from TASK.md `## Success Criteria`):
- Checklist with self-assessment status (from latest run's self-check)
- Shows which criteria the agent believes it met (☑) vs missed (☐)
- This is the closest thing to autoresearch's val_bpb — structured eval against defined criteria

**Run Trajectory** (scrollable list):
- Date + status (✓/✗/⏳) + self-assessment confidence level
- Active item highlighted (currently displayed in left panel)
- Trend indicator: "↑ improving" / "→ stable" / "↓ declining" based on recent confidence/edit patterns
- Click to view past output
- Most recent at top
- This is our results.tsv — the trajectory tells you if the task is getting better

**Actions** (bottom):
- Settings gear → modal for editing cadence, delivery, status, success criteria
- Run Now → triggers immediate execution

### Chat: Drawer (Task-Scoped)

Same drawer pattern as workfloor, but scoped to this task.

- **Scope**: Task-scoped TP session (keyed by `task_slug`)
- **TP context**: TASK.md + run_log.md + agent AGENT.md + memory highlights
- **Use cases**: "Focus on pricing this week", "The competitor section is weak", "Change delivery to Slack"
- **Surface context**: `{ type: "task-detail", taskSlug: "{slug}" }`

### Data Sources

| Component | Source | Notes |
|-----------|--------|-------|
| Output HTML | `GET /api/tasks/{slug}/outputs/latest` | Reads from workspace |
| Task details | `GET /api/tasks/{slug}` | Parses TASK.md + DB metadata |
| Run trajectory | `GET /api/tasks/{slug}/outputs` | Output history with manifests + self-assessment |
| Chat drawer | `POST /api/chat` with `surface_context.taskSlug` | Task-scoped session |
| Run Now | `POST /api/tasks/{slug}/run` | Triggers execution |

---

## 3. Agent Page (`/agents/{slug}`)

### Purpose
Reference surface for agent identity and development. Not a working surface — no chat, no drawer.

### Layout (desktop ≥ 1024px)

```
┌─ Left Panel (flex-1) ──────────┬─ Right Panel (400px) ─────────┐
│                                │ Agent Identity                 │
│  AGENT.md Content              │                               │
│  ┌──────────────────────────┐  │ Market Intelligence            │
│  │ # Market Intelligence    │  │ 🔬 researcher                  │
│  │                          │  │ "Investigates and analyzes"    │
│  │ ## Identity              │  │                               │
│  │ Domain expert in...      │  │ ── Assigned Tasks ──           │
│  │                          │  │ • Weekly Briefing → (recurring)│
│  │ ## Expertise             │  │ • Pricing Alert → (reactive)  │
│  │ - AI agent platforms     │  │                               │
│  │ - Competitive analysis   │  │ ── Development ──              │
│  │                          │  │ Total runs: 12                 │
│  │ ## Capabilities          │  │ Active since: Mar 1            │
│  │ - web_search, chart...   │  │ Last run: Mar 25               │
│  └──────────────────────────┘  │ Approval rate: 92%             │
│                                │                               │
│  ── Memory Browser ──          │ ── Memory Files ──             │
│  [observations] [preferences]  │ observations.md (2.1k)         │
│  [self_assessment] [directives]│ preferences.md (850)           │
│                                │ self_assessment.md (1.2k)      │
│  Expanded file content here    │ directives.md (400)            │
│                                │                               │
│                                │ ── Actions ──                  │
│                                │ [Edit Identity] [Pause] [Del]  │
└────────────────────────────────┴───────────────────────────────┘
```

### Left Panel
- AGENT.md rendered as markdown (identity, expertise, capabilities)
- Memory browser: tabbed or accordion — each memory file expandable with content preview
- All read-only on this surface

### Right Panel
- Archetype badge + display name + tagline
- Assigned tasks list (links to `/tasks/{slug}`) with mode labels
- Development stats: run count, tenure, last run, approval rate
- Memory file list with sizes
- Action buttons: Edit Identity (opens modal or navigates to workfloor chat), Pause, Archive

### Interaction Model
- **No chat on this page** — this is a reference surface
- To steer agent identity: use workfloor chat drawer ("update Market Intel's expertise")
- To steer agent behavior on a task: go to `/tasks/{slug}` and use task chat drawer

---

## 4. Chat Drawer Pattern (Shared)

The chat drawer is a consistent interaction pattern across both workfloor and task pages.

### Behavior

```
┌─ Main Layout (output + context) ────────┐┌─ Chat Drawer ──────┐
│                                          ││                    │
│  [existing two-panel layout]             ││  TP conversation   │
│  [unaffected when drawer is closed]      ││  (scoped to        │
│                                          ││   current surface) │
│                                          ││                    │
│                                          ││  ┌──────────────┐  │
│                                          ││  │ input        │  │
│                                          ││  └──────────────┘  │
└──────────────────────────────────────────┘└────────────────────┘
```

### Properties
- **Width**: ~400px, slides in from right edge
- **Overlay**: covers right panel (doesn't push layout)
- **Trigger**: FAB button (bottom-right, always visible) or ⌘K keyboard shortcut
- **Dismiss**: click outside, press Esc, or click FAB again
- **Pinnable**: user can pin drawer open (persists across navigation within same surface)
- **Scope**: Global TP on workfloor, task-scoped TP on task page
- **Context**: TP gets surface_context so it knows where the user is

### Why Drawer, Not Panel or Tab

| Option | Problem |
|--------|---------|
| Chat as left panel tab | Makes chat compete with output for the hero position. Output should be default. |
| Chat as right panel section | Mixes interaction modes (observation + input) in the same panel. Confusing. |
| Chat as separate page | Loses context. User leaves the output/task to chat, then has to navigate back. |
| **Chat as drawer** | Clean separation. Output + context always visible. Chat overlays when needed. Dismiss to return to supervision. |

### Session Architecture

```sql
-- ADR-139: Task-scoped sessions
ALTER TABLE chat_sessions ADD COLUMN task_slug TEXT;

CREATE INDEX idx_chat_sessions_task_slug ON chat_sessions(user_id, task_slug)
  WHERE task_slug IS NOT NULL;
```

| Drawer scope | Session key | Surface |
|---|---|---|
| Global TP | `user_id` (task_slug IS NULL) | `/workfloor`, `/agents/{slug}` |
| Task-scoped TP | `user_id` + `task_slug` | `/tasks/{slug}` |

---

## 5. TP Context Injection

### `load_surface_content()` updates

| Surface Type | Context Loaded |
|-------------|----------------|
| `"workfloor"` | Agent list (title, role, task count), task list (title, status, cadence, last_run), platform status |
| `"task-detail"` | Full TASK.md, run_log.md (last 5 entries), latest output summary (first 500 chars), assigned agent AGENT.md, agent memory highlights |
| `"agent-identity"` | Full AGENT.md, memory file summaries, assigned tasks list |

### Task-scoped TP preamble

```
You are helping the user manage the task "{task_title}".

Task definition:
{task_md_content}

Recent run log:
{run_log_last_5}

Assigned agent: {agent_title} ({agent_role})
Agent expertise: {agent_expertise_summary}
```

---

## 6. Navigation Sidebar

```
┌─────────────────┐
│ 🏠 Workfloor     │  ← home, always first
│ 📋 Activity      │
│ 🔗 Integrations  │
│ ⚙️ Settings      │
└─────────────────┘
```

### Breadcrumb Pattern

```
Workfloor                           → /workfloor
Workfloor > Weekly Briefing         → /tasks/{slug}
Workfloor > Market Intelligence     → /agents/{slug}
```

---

## 7. Mobile Layout (< 1024px)

**Workfloor mobile:**
- Output feed (full width, default view)
- Agent roster as horizontal card scroll (top bar)
- Chat as bottom sheet (swipe up)
- Tabs for Tasks/Workspace/Platforms at bottom

**Task page mobile:**
- Output (full width, default view)
- Task details as collapsible header
- Run trajectory as horizontal timeline
- Chat as bottom sheet (swipe up)

**Agent page mobile:**
- Identity content (full width)
- Memory browser (accordion)
- Actions as bottom bar

---

## 8. API Endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| `GET` | `/api/tasks` | List user's tasks |
| `GET` | `/api/tasks/{slug}` | Task details (parsed TASK.md + DB) |
| `POST` | `/api/tasks` | Create task |
| `PATCH` | `/api/tasks/{slug}` | Update task |
| `DELETE` | `/api/tasks/{slug}` | Archive task |
| `GET` | `/api/tasks/{slug}/outputs/latest` | Latest output HTML |
| `GET` | `/api/tasks/{slug}/outputs` | Output history + manifests + self-assessment |
| `POST` | `/api/tasks/{slug}/run` | Trigger immediate execution |
| `GET` | `/api/tasks/outputs/recent` | **New** — latest outputs across all tasks (workfloor feed) |
| `GET` | `/api/agents` | Agent list (add task_count, last_activity) |

---

## 9. Workfloor Liveness

The workfloor agent grid uses ambient CSS animations to communicate state without reading labels. Full spec: [WORKFLOOR-LIVENESS.md](WORKFLOOR-LIVENESS.md).

| State | Visual signal | Animation |
|-------|--------------|-----------|
| Working | Glow ring + shimmer sweep | `desk-glow` + `shimmer` keyframes |
| Ready | Calm presence, subtle breathing | `breathe` keyframe (scale 1.0→1.003) |
| Paused | Dimmed, desaturated | opacity 60% + grayscale |
| Empty | Dashed placeholder | Subtle border pulse (6s) |
| Error | Red border accent | Color transition only |
| TP | Always-on icon pulse | Distinct from agent states |

Polling: 30-second interval refreshes agent + task status. Immediate refresh on tab focus. No WebSockets.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-25 | v1 — Initial: agent cards (left) + TP chat (left) + tasks/workspace tabs (right). Chat as left panel. |
| 2026-03-25 | v2 — Output-first redesign. Workfloor: output feed (left hero) + agent roster grid (right, OpenClaw-inspired living office). Task page: latest output (left hero) + trajectory + meta (right). Chat becomes drawer (both surfaces) instead of panel/tab. Agent roster as 2×3 spatial grid with liveness indicators. Run trajectory with self-assessment confidence and trend indicators. Success criteria as checklist with eval status. Mode labels on task metadata. |
| 2026-03-25 | v2.1 — Agent-first workfloor (revised). Left panel: agent roster as hero (living office, birds-eye view) with TP as distinct orchestrator card. Right panel: tabbed (Tasks/Context/Platforms). Live task on each agent desk. Liveness spec added (WORKFLOOR-LIVENESS.md). |
| 2026-03-25 | v3 — Chat as persistent right panel (not drawer). Left: agent grid + TP card + compact tabs (Tasks/Context/Platforms) below. Right: TP chat always visible via WorkspaceLayout resizable panel. Animated SVG agent avatars with state-driven animations (working/ready/paused/idle/error). ChatDrawer removed from workfloor — chat is primary, not hidden. Task page keeps ChatDrawer (task-scoped). |
