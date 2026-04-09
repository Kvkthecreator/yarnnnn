# Deliverable-First User Flow

> Design document for the user-facing flow changes driven by ADR-145 (Task Type Registry).
> This is the front-end surfacing strategy for pre-meditated orchestration.

---

## The Shift

**Before (agent-first):**
Sign up → see 10 pre-scaffolded agents (9 domain + TP meta-cognitive) → describe your work → TP enriches context → maybe create a task → hope output is good

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
- **Proposed:** Collapsed single-line strip below deliverables. Expandable. Shows: "10 agents · N with active tasks" (9 domain + TP meta-cognitive). Expand → same grid as before.
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

---

## Output Rendering Strategy (Bigger Picture)

### Problem
Task outputs include structured content that raw `ReactMarkdown` doesn't handle well:
- **Tables** — competitive matrices, feature comparisons (now fixed with `remark-gfm`)
- **Charts** — rendered as PNG/SVG by RuntimeDispatch, referenced in markdown
- **Mermaid diagrams** — rendered as SVG/PNG, referenced in markdown
- **Composed HTML** — full brand-styled deliverable from compose engine
- **Embedded assets** — images, social cards, data visualizations

The current approach (markdown → ReactMarkdown) works for text but breaks for rich deliverables. The compose engine produces HTML, but the frontend needs to know when to show markdown vs. HTML.

### Current State (2026-03-27)
- `MarkdownRenderer` shared component with `remark-gfm` — handles tables, GFM features
- Task page `OutputTab` checks: HTML first → markdown fallback → empty state
- Chat messages use `MarkdownRenderer` with compact mode
- No asset embedding (chart/mermaid images not rendered inline)
- Compose HTML displayed via `iframe` with sandbox

### Rendering Decisions Needed

**1. Output display priority**
When a task produces both `output.md` and `output.html`, which do we show?
- Current: HTML via iframe if available, markdown fallback
- Proposal: HTML is the primary view (it's the "finished" deliverable). Markdown is the "source" view (for editing/feedback). Toggle between them.

**2. Asset embedding in markdown view**
Agent outputs reference assets (`chart-1.svg`, `competitive-map.png`) but the markdown viewer doesn't resolve these paths.
- Need: resolve workspace_files asset paths to actual URLs (Supabase storage or base64 inline)
- Approach: `MarkdownRenderer` gains an `assetResolver` prop that maps `![alt](assets/chart-1.svg)` to actual URLs

**3. Pipeline step output viewing**
Multi-step pipelines store step outputs in `step-{N}/output.md`. The Pipeline tab needs to render each step's output inline.
- Same `MarkdownRenderer` component, one per step
- Step outputs are intermediate work product — show as collapsible sections

**4. Composed HTML rendering**
The compose engine produces self-contained HTML with brand CSS, embedded SVGs, responsive layout.
- Current: `<iframe srcDoc={html} sandbox="allow-same-origin" />`
- Issue: iframe sizing (height calculation), no interaction, feels disconnected
- Alternative: `dangerouslySetInnerHTML` with sanitization (DOMPurify)
- Decision: keep iframe for now (security sandbox), add auto-height via postMessage

**5. Chat message rendering**
TP responses include tool results, inline suggestions, and markdown. Chat needs compact rendering.
- Current: `MarkdownRenderer` with `compact` prop
- Consider: tool result cards (already exist), inline asset previews, code blocks

### Proposed Component Architecture

```
OutputRenderer (top-level — decides HTML vs Markdown vs Empty)
├── HtmlOutputViewer (iframe with auto-height, sandbox)
├── MarkdownRenderer (remark-gfm, asset resolution, table styling)
│   └── AssetImage (resolves workspace_files paths to URLs)
├── PipelineStepViewer (collapsible step outputs)
└── OutputToolbar (toggle HTML/MD, export buttons, copy)
```

### Not Now (Future)
- Live mermaid rendering in markdown (currently pre-rendered as PNG/SVG)
- Inline chart editing (modify data → re-render)
- PDF/PPTX preview in-browser
- Side-by-side diff between output versions

---

## Frontend Prerequisite Considerations

### Context Buildup Is Still Required
ADR-145 task types don't remove the need for onboarding context. Without identity/brand/domain context, even the best pipeline produces generic output.

**Minimum viable context for meaningful task execution:**
1. **Identity** (IDENTITY.md) — who you are, role, company
2. **Domain** — what industry/space you operate in (inferred from identity or explicit)
3. **Focus** — the `focus` parameter on task creation customizes the deliverable

**Without platforms connected:**
- Research-based tasks (competitive intel, market research, due diligence) work via web search — output is thinner but functional
- Platform-dependent tasks (Slack Recap, Relationship Health) require the platform — prompt connection contextually

**Onboarding flow must ensure:**
- Identity is populated before task catalog is shown (or at least strongly encouraged)
- Task types that require platforms show connection prompts inline
- First-run output quality depends on available context — set expectations

### Surface-Primitives Map
`docs/design/SURFACE-PRIMITIVES-MAP.md` maps every surface to its primitives, commands, plus menu, and scope boundaries.

**When adding task type catalog to workfloor:**
- Update SURFACE-PRIMITIVES-MAP.md with new surface elements
- Catalog cards are NOT primitives — they're UI that scaffolds via `CreateTask`
- The `+ Add deliverable` button triggers catalog, not a primitive directly
- Chat plus menu may gain a "Browse deliverable types" action

### Workfloor Still Owns Cold Start
- `/workfloor` remains `HOME_ROUTE`
- Empty state transitions: no context → context enrichment → task catalog → active deliverables
- Agent strip remains accessible but collapsed — power user path, not default
- Chat panel always visible — TP can guide through all states
