# Deliverable-First User Flow

> Design document for the user-facing flow changes driven by ADR-145 (Task Type Registry).
> This is the front-end surfacing strategy for pre-meditated orchestration.

---

## The Shift

**Before (agent-first):**
Sign up → see 6 agents → describe your work → TP enriches context → maybe create a task → hope output is good

**After (deliverable-first):**
Sign up → "What do you want delivered?" → pick from catalog → task scaffolded → first output delivered → evaluate against clear promise

**Core principle:** Agents are infrastructure. Tasks (deliverables) are the product surface. Users should never need to understand agent types to get value.

---

## Flow: Sign-Up to First Deliverable

### Step 1: Sign Up
No change. Email or Google OAuth → account created → agents pre-scaffolded silently.

### Step 2: Landing (Workfloor)
User lands on workfloor. **No agent strip visible by default.** Instead:

```
┌─────────────────────────────────────────────────────────┐
│  What do you want delivered?                            │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ 🔍       │  │ 📊       │  │ 💬       │              │
│  │ Comp.    │  │ Market   │  │ Slack    │              │
│  │ Intel    │  │ Research │  │ Recap    │              │
│  │ Brief    │  │ Report   │  │          │              │
│  │          │  │          │  │          │              │
│  │ weekly   │  │ monthly  │  │ daily    │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ 🤝       │  │ 📋       │  │ 🚀       │              │
│  │ Meeting  │  │ Status   │  │ GTM      │              │
│  │ Prep     │  │ Report   │  │ Tracker  │              │
│  │          │  │          │  │          │              │
│  │ on-demand│  │ weekly   │  │ weekly   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                         │
│  [Browse all 13 deliverable types →]                    │
│                                                         │
│  ── or tell me what you need ──                         │
│  [Chat input: "I want a weekly..."]                     │
└─────────────────────────────────────────────────────────┘
```

**Key decisions:**
- Show 6 most popular task types as cards (not all 13)
- Each card: icon + name + one-line description + default schedule
- "Browse all" link to full catalog
- Chat still available below as alternative path
- Platform-requiring types (Slack Recap, Notion Sync) show "requires Slack/Notion" badge — clicking triggers OAuth flow

### Step 3: Select a Deliverable Type

User clicks a task type card. **Inline expansion or modal** (not a new page):

```
┌─────────────────────────────────────────────────────────┐
│  Competitive Intelligence Brief                         │
│  Research-backed competitive analysis with charts,      │
│  diagrams, and evidence-linked findings.                │
│                                                         │
│  How it works:                                          │
│  [Research Agent] ──investigates──→ [Content Agent]     │
│  ──formats & visualizes──→ Branded deliverable          │
│                                                         │
│  Schedule: [Weekly ▼]                                   │
│  Focus: [e.g., "AI agent platforms"] ___________        │
│  Deliver to: [Email ▼] [you@example.com]                │
│                                                         │
│  [Preview example output]                               │
│                                                         │
│  [Create & Run First Time →]                            │
└─────────────────────────────────────────────────────────┘
```

**Key decisions:**
- Pipeline shown as visual flow (agent icons with arrows), not technical jargon
- Focus field = the topic/domain this deliverable covers
- Schedule has sensible default from registry, user can change
- "Preview example output" shows a real sample
- "Create & Run First Time" scaffolds task AND triggers immediate first run

### Step 4: First Run

Task created, first execution starts immediately. User returns to workfloor, which now shows:

```
┌─────────────────────────────────────────────────────────┐
│  Your Deliverables                                      │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │ ⏳ Competitive Intelligence Brief        weekly   │  │
│  │    First run in progress...                       │  │
│  │    Research Agent investigating → Content Agent   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  [+ Add another deliverable]                            │
│                                                         │
│  ── Chat ──                                             │
│  [Steer, adjust, or ask about your deliverables]        │
└─────────────────────────────────────────────────────────┘
```

### Step 5: First Output Delivered

When the pipeline completes:

```
┌───────────────────────────────────────────────────────┐
│ ● Competitive Intelligence Brief          weekly      │
│   Latest: just now · Next: Mon Mar 30                 │
│   [View Output →]                                     │
└───────────────────────────────────────────────────────┘
```

Click → task detail page with output rendered.

### Step 6: Ongoing Usage

Workfloor becomes a deliverables dashboard:

```
┌─────────────────────────────────────────────────────────┐
│  Your Deliverables                                      │
│                                                         │
│  ● Competitive Intel Brief     weekly    Latest: 2d ago │
│  ● Slack Recap                 daily     Latest: 3h ago │
│  ● Meeting Prep: Acme Corp    on-demand Latest: 1d ago │
│                                                         │
│  [+ Add deliverable]                                    │
│                                                         │
│  Agents (6)  ▸  (collapsed, expandable)                 │
└─────────────────────────────────────────────────────────┘
```

**Agents are still visible** but collapsed — power users can expand to see the roster, rename agents, view agent detail. But the default view is deliverables.

---

## Workfloor Redesign

### Current Tabs
1. Tasks
2. Context (Identity / Brand / Documents)
3. Platforms

### Proposed Tabs
1. **Deliverables** (was: Tasks) — active task types with status, latest output, next run
2. **Context** — Identity, Brand, Documents (unchanged)
3. **Platforms** — Slack, Notion connections (unchanged)

### Agent Strip
- **Current:** Prominent 3-column grid at top of workfloor
- **Proposed:** Collapsed single-line strip below deliverables. Expandable. Shows: "6 agents · 3 with active tasks". Expand → same grid as before.
- **Rationale:** Agents are infrastructure. They matter for power users who want to customize agent identity or view agent workspace. But for onboarding and daily use, deliverables are the hero.

### Empty State (No Tasks)
- **Current:** "No tasks yet — set up your context first, then ask chat to create one"
- **Proposed:** Task type catalog cards (same as Step 2 above). The empty state IS the onboarding.

### Chat Panel
- **Current:** Suggested chips: "Tell me about myself", "Update my brand", "Help me set up my first task"
- **Proposed:** Suggested chips change based on state:
  - No tasks: "What kind of deliverable do you need?" / "Set up competitive intelligence" / "Connect Slack for daily recaps"
  - Has tasks: "Review latest output" / "Adjust focus for [task]" / "Add another deliverable"

---

## Task Detail Page Changes

### Current Tabs
1. Output
2. Task (definition)
3. Schedule
4. Agents

### Proposed Changes
- **Output tab** — unchanged (shows latest deliverable)
- **Task tab** — add pipeline visualization: which agents ran, in what order, with step status
- **Schedule tab** — unchanged
- **Agents tab** → **Pipeline tab** — show the multi-step execution plan, not just assigned agents. Each step shows: agent type, step role, status (completed/running/pending), and expandable step output

### Pipeline Visualization (Pipeline Tab)

```
Pipeline: Research → Content

┌─ Step 1: Investigate ──────────────────────────────┐
│  🔍 Research Agent                    ✓ Completed  │
│  "Investigate competitive landscape..."             │
│  [View step output ▸]                               │
└────────────────────────────────────────────────────┘
         │
         ▼
┌─ Step 2: Compose ─────────────────────────────────┐
│  📊 Content Agent                     ✓ Completed  │
│  "Format findings into branded deliverable..."      │
│  [View step output ▸]                               │
└────────────────────────────────────────────────────┘
         │
         ▼
   📄 Final deliverable → Output tab
```

---

## Task Creation Flows (All Paths)

### Path 1: Catalog Selection (Primary)
Workfloor empty state or "+ Add deliverable" → browse catalog → select type → customize focus/schedule/delivery → create

### Path 2: Chat (Natural Language)
User tells TP "I want a weekly competitive brief" → TP matches to task type → confirms with user → scaffolds

### Path 3: TP Suggestion (Proactive)
TP heartbeat detects opportunity (e.g., user connected Slack but has no Slack Recap) → suggests task type → user accepts

### All Paths Converge
Regardless of entry point, the result is:
1. `type_key` resolved from registry
2. TASK.md scaffolded with objective from registry template + user customization
3. Pipeline agents resolved from user's roster
4. First run triggered

---

## Navigation Changes

### Context Dropdown (Top Bar)
- **Current:** Workfloor, Tasks, Agents, Context, Activity, Settings
- **Proposed:** Workfloor, Deliverables (was Tasks), Context, Settings
  - Agents accessible from workfloor (collapsed strip) or context page
  - Activity de-emphasized (or folded into settings)

### Route Changes
| Current | Proposed | Rationale |
|---------|----------|-----------|
| `/workfloor` | `/workfloor` | No change (still HOME_ROUTE) |
| `/tasks` | `/deliverables` | Rename to match mental model |
| `/tasks/[slug]` | `/deliverables/[slug]` | Rename |
| `/agents` | Keep but de-emphasize | Infrastructure, not primary |
| `/context` | `/context` | No change |

**Note:** Route rename is optional for Phase 1. Can ship with `/tasks` internally and rename later. The display label should say "Deliverables" regardless.

---

## Onboarding Changes

### Current Onboarding
1. Sign up
2. Land on workfloor
3. See agent strip + platform prompt
4. "Describe your work" → TP enriches context
5. Maybe create a task via chat

### Proposed Onboarding
1. Sign up
2. Land on workfloor → empty state IS the task type catalog
3. "What do you want delivered?" → pick task type(s)
4. Customize focus + schedule → create task
5. Optional: connect platforms to enrich (prompted if task type benefits)
6. First run executes → user sees concrete output

**Key difference:** User gets a deliverable within minutes of sign-up, not after a multi-step context enrichment process. Context enrichment happens naturally as they use the product (connect platforms, chat with TP, edit outputs → feedback loop).

### Platform Connection Prompting
Instead of upfront "connect platforms", prompt contextually:
- User picks "Slack Recap" → "This needs Slack. Connect now?"
- User picks "Competitive Intel" → works immediately (web search), but: "Connect Slack for richer competitive signals"
- User picks "Meeting Prep" → "Connect Slack or Notion for relationship context" (optional enhancement)

---

## Component Impact Inventory

### New Components
- `TaskTypeCatalog` — grid of task type cards for onboarding + "+ Add deliverable"
- `TaskTypeCard` — individual card (icon, name, description, schedule, pipeline preview)
- `TaskTypeDetailModal` — expansion view with customization (focus, schedule, delivery)
- `PipelineVisualization` — step flow diagram for task detail page Pipeline tab
- `PipelineStepCard` — individual step in pipeline (agent, role, status, expandable output)

### Modified Components
- `workfloor/page.tsx` — deliverables as hero, agent strip collapsed, empty state = catalog
- `tasks/[slug]/page.tsx` — Agents tab → Pipeline tab with visualization
- `AuthenticatedLayout.tsx` — nav dropdown labels (Tasks → Deliverables)
- Chat suggested chips — state-aware prompts

### Potentially Removable
- `PlatformOnboardingPrompt` — replace with contextual platform prompts per task type
- Agent strip as primary hero — demote to collapsed infrastructure view

---

## Phase Plan

### Phase 1: Catalog + Scaffolding
- Task type catalog component (cards grid)
- Workfloor empty state shows catalog
- "+ Add deliverable" button on workfloor
- `GET /api/tasks/types` endpoint serves registry
- Task creation from type → scaffold TASK.md
- Single-step execution (existing pipeline)

### Phase 2: Pipeline Visualization + Multi-Step
- Pipeline tab on task detail page
- Multi-step pipeline execution (ADR-145 Phase 2)
- Step output viewer
- Pipeline progress indicator during execution

### Phase 3: Onboarding Refinement
- Task type selection as the primary onboarding path
- Contextual platform connection prompts
- Example output previews
- Chat-aware: TP knows about task types and suggests them conversationally

### Phase 4: Route + Nav Polish
- Consider `/deliverables` route rename
- Nav dropdown update
- Agent strip collapse as default
- State-aware chat suggested chips
