# Surface Architecture — Chat + Work + Agents + Context

**Version:** v8 (2026-04-08)
**Status:** Canonical
**Governed by:** [ADR-163](../adr/ADR-163-surface-restructure.md) — Surface Restructure
**Active decision:** [ADR-165](../adr/ADR-165-chat-command-desk-windowed-surface.md) — changes `/chat` internal layout from two-panel dashboard + chat to a managed TP command desk; does not add a fifth top-level surface.

**Supersedes:**
- v7.2 (2026-04-06) — task-class-aware tabs on Agents page
- v7.1 (2026-04-06) — tabs restored
- v7 (2026-04-06) — unified shell, flat center panel
- v6.1 (2026-04-06) — global breadcrumb
- v6 (2026-04-05) — dashboard + TP chat two-panel

---

## Design Thesis: Four Surfaces, One Question Each

Every previous version of this doc was trying to cram multiple jobs into the Agents page because Agents was the only top-level destination that touched work. The result: four tab layouts in ten commits. ADR-163 fixes the thrash by giving each question its own surface.

| Surface | Route | The question it answers | The answer |
|---|---|---|---|
| **Chat** | `/chat` | "What should I do? What's happening?" | TP chat + briefing dashboard |
| **Work** | `/work` | "What is my workforce doing?" | Task list + task detail (schedule, output, actions) |
| **Agents** | `/agents` | "Who's on my team?" | Roster + identity card + health |
| **Context** | `/context` | "What does my workspace know?" | Filesystem browser |

Four destinations. Each answers exactly one question. No overlap.

The old `/activity` page is **deleted**. Its content is absorbed into the surfaces that naturally own it: per-task activity to `/work`, per-agent activity to `/agents`, workspace-wide activity to the Chat briefing dashboard, diagnostic events to Settings → System Status.

---

## Route Map

```
/chat                → Chat (home). Daily briefing dashboard + TP chat.
/work                → Work. Task list (left) + task detail (center) + TP chat (right).
/work?agent={slug}   → Work filtered to one agent's tasks.
/work?task={slug}    → Work deep-linked to a specific task's detail.
/agents              → Agents. Roster (left) + identity/health card (center) + TP chat (right).
/agents?agent={id}   → Agents with a specific agent pre-selected.
/context             → Context. Workspace filesystem browser.
/context?domain={k}  → Context pre-filtered to a domain folder.
/settings            → Settings. Memory, brand, system status (absorbed from /activity).
```

**Legacy routes still live for bookmark preservation:**
- `/tasks` and `/tasks/{slug}` → redirect to `/work` (forwards slug as `?task=`)
- `/workfloor` → redirect to `HOME_ROUTE` (`/chat`)
- `/orchestrator` → redirect to `HOME_ROUTE` with query params preserved (OAuth callbacks)

**Deleted routes:**
- `/activity` — returns 404; content absorbed elsewhere

---

## Navigation

### Top Bar

```
┌──────────────────────────────────────────────────────────────────────┐
│ yarnnn / <breadcrumb>     [Chat | Work | Agents | Context]    Avatar │
└──────────────────────────────────────────────────────────────────────┘
```

**Global breadcrumb** (`BreadcrumbContext`): pages set breadcrumb segments into a shared context; the header renders them. Max 2 segments after the logo. Each surface sets its own breadcrumb on selection.

| Surface state | Breadcrumb |
|---|---|
| Chat | _(empty — just logo)_ |
| Work (overview) | _(empty)_ |
| Work (task selected) | `/ Daily Update` |
| Work (filtered by agent) | `/ Competitive Intelligence's work` |
| Agents (overview) | _(empty)_ |
| Agents (selected) | `/ Competitive Intelligence` |
| Context (domain selected) | `/ Competitors` |
| Context (deep file) | `/ Competitors / cursor` |

**Toggle bar** (`web/components/shell/ToggleBar.tsx`): four-segment pill `Chat | Work | Agents | Context`. Icons: `MessageCircle`, `Briefcase`, `Users`, `FolderOpen`. `HOME_ROUTE` is `/chat` — both new and returning users land there.

---

## 1. Chat (`/chat`, HOME_ROUTE)

### Purpose
Daily command center. Two-panel layout: daily briefing dashboard on the left, TP chat on the right. The briefing dashboard surfaces the `daily-update` task's latest output (ADR-161) as a structured view, plus a compact "Recent activity" feed.

For new users with an empty workspace, the daily-update task still runs (deterministic empty-state template from ADR-161) and the briefing dashboard shows its honest "tell me what to track" message.

### Layout

```
┌──────────────────┬──────────────────────────────────┐
│  Briefing        │  TP Chat                         │
│                  │                                  │
│  Daily update    │  (conversation thread)           │
│  output (hero)   │                                  │
│                  │                                  │
│  Recent activity │                                  │
│  feed (last 72h) │                                  │
│                  │  [input ───────────────────────] │
└──────────────────┴──────────────────────────────────┘
```

The daily-update task is the intellectual center of the briefing. Its output is always fresh (recomputed daily), always honest (empty-state template for dormant workspaces), and always visible.

---

## 2. Work (`/work`)

### Purpose
Work is where the user looks at what their workforce is doing. First-class top-level destination (new in ADR-163). The left panel lists tasks sorted by upcoming. The center panel shows the selected task's full detail — schedule, next/last run, objective, latest output, and actions.

### Task Modes on the Surface (ADR-163)

The schema has three modes (`recurring | goal | reactive`). The surface has **two labels**: `Recurring` and `One-time`. Mapping:

```
recurring  → Recurring
goal       → One-time
reactive   → One-time
```

The `WorkModeBadge` component is the only place modes are rendered. Every task row and task detail header uses it. The mapping is enforced by `taskModeLabel()` in `web/types/index.ts`.

The execution layer still distinguishes three modes because `goal` has the revision loop and `reactive` has dispatch-and-done semantics (see ADR-149). Users never see the third option — they pick "Recurring" or "One-time", and TP resolves "One-time" to `goal` or `reactive` behind the scenes based on task type.

### Layout

```
┌──────────────────┬──────────────────────────────────┬─────────────┐
│  Work            │  Daily Update                    │  TP Chat    │
│                  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │             │
│  ACTIVE          │                                  │             │
│  • Daily Update  │  Recurring · Reporting · daily   │             │
│    Reporting     │  Next: tomorrow 9am UTC          │             │
│    Recurring     │                                  │             │
│    Next: 9am     │  ## Objective                    │             │
│  • Track Compet. │  ...                             │             │
│  • Track Market  │                                  │             │
│                  │  ## Latest output                │             │
│  PAUSED          │  [iframe with rendered HTML]     │             │
│  • Legacy task   │                                  │             │
│                  │  [Run now] [Pause] [Edit via TP] │             │
│                  │                                  │             │
│                  │  → Assigned to Reporting         │             │
└──────────────────┴──────────────────────────────────┴─────────────┘
```

### Left Sidebar (`WorkList`)
- Active tasks, sorted by `next_run_at` ascending
- Paused tasks below, sorted by `last_run_at` descending
- Each row: status dot, title, mode badge, assigned agent, next/last run
- Essential tasks (ADR-161) show a `★` marker

### Center Panel (`WorkDetail`)
- **Pinned header:** title, mode badge, status, assigned agent, schedule, next/last run, essential badge
- **Objective block:** deliverable, audience, purpose, format (from TASK.md)
- **Latest output preview:** iframe for HTML, markdown renderer for `.md`
- **Actions row:** Run now, Pause/Resume, Edit via TP (opens chat prompt)
- **Assigned agent link:** back to `/agents?agent={slug}`

### Filtering
- `/work?agent={slug}` filters the list to one agent's tasks. Used by "See this agent's work" link on `/agents`.
- `/work?task={slug}` deep-links to a specific task's detail.

### What Used to Live Here
- The old `Pipeline` tab on the Agents page (task config, schedule, actions) → now lives here.
- The old `Report` tab (latest synthesis outputs) → absorbed into the task detail's output preview.
- The old `Upcoming` section on `/activity` → now the default sort order of the work list.

---

## 3. Agents (`/agents`)

### Purpose
Agents is where the user looks at **who** is on their team, not **what** they're doing. Roster-only surface. The center panel is a single identity card for the selected agent — no tabs, no work observation, no domain browsing. Work moved to `/work`, context browsing moved to `/context`.

### Layout

```
┌──────────────────┬──────────────────────────────────┬─────────────┐
│  Agents          │  Competitive Intelligence        │  TP Chat    │
│                  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │             │
│  • Comp Intel    │                                  │             │
│  • Mkt Rsch      │  Domain Steward · competitors/   │             │
│  • Biz Dev       │  3 active tasks · Ran 2h ago     │             │
│  • Operations    │                                  │             │
│  • Marketing     │  ## Identity                     │             │
│  • Reporting     │  · Name: Competitive Intelligence│             │
│  • Slack Bot     │  · Role: competitive_intel       │             │
│  • Notion Bot    │  · Domain: competitors/          │             │
│  • GitHub Bot    │  · Created: Apr 7, 2026          │             │
│                  │                                  │             │
│                  │  ## Instructions (AGENT.md)      │             │
│                  │  ...                             │             │
│                  │                                  │             │
│                  │  ## Health                       │             │
│                  │  · Tasks assigned: 3             │             │
│                  │  · Approval rate: 100%           │             │
│                  │  · Last run: 2h ago              │             │
│                  │                                  │             │
│                  │  → See this agent's work         │             │
│                  │  → See this agent's context      │             │
└──────────────────┴──────────────────────────────────┴─────────────┘
```

### Identity Card Sections
- **Identity block:** name, role + class, domain, origin, creation date
- **Instructions block:** rendered AGENT.md via MarkdownRenderer
- **Feedback block:** distilled feedback from `agent_memory.feedback` if present

### Health Card Sections
- **Tasks assigned:** count of active tasks
- **Total runs:** from `version_count`
- **Approval rate:** from `quality_score`, only shown if runs >= 5, with trend arrow
- **Last run:** relative time
- **Links out:** "See this agent's work" → `/work?agent={slug}`, "See this agent's context domain" → `/context?domain={domain}`, "Chat about this agent" → opens TP chat

### What Used to Live Here (v7.2) — And Where It Moved
| Old Tab | Content | Moved to |
|---|---|---|
| **Report** | Latest synthesis task outputs | `/work` → per-task detail output preview |
| **Data** | Domain entity dashboard | `/context?domain={key}` |
| **Pipeline** | Task config, schedule, actions | `/work` surface |
| **Agent** | Identity, instructions, history | Stayed here (now the only thing on the page) |

---

## 4. Context (`/context`)

### Purpose
The only filesystem browser. Shows the workspace tree with domains, output folders, uploads, and IDENTITY/BRAND files. Unchanged from v7.2 structurally. ADR-163 adds one enhancement: inference-meta rendering.

### Inference Visibility (ADR-162 + ADR-163)

When the Context tab renders IDENTITY.md or BRAND.md, it uses `InferenceContentView` instead of the raw markdown renderer. The component:

1. Parses the `<!-- inference-meta: {...} -->` HTML comment embedded at the bottom of inference output (written by `_append_inference_meta()` in `api/services/context_inference.py`).
2. Strips the comment before rendering the markdown body.
3. Shows a source provenance caption above the body:
   - `Last updated from: pitch-deck.pdf · 2h ago`
   - `Last updated from: 2 documents, 1 URL · yesterday`
4. Shows a gap banner below the body when there's a high-severity unfilled gap from the deterministic gap detector (ADR-162 Sub-phase A):
   ```
   ⚠ Missing: company name
     What company or project are you building?
     [Chat to fill this in]
   ```

The gap banner's "Chat to fill this in" link navigates to `/chat?prompt=...` with a pre-filled message that drops the user into TP chat with a natural follow-up.

Currently wired for BrandSection in Settings (via `MemorySection.tsx`). A dedicated IdentitySection surface is a future addition — TP also consumes IDENTITY.md via working memory, so it's not invisible even without a UI surface.

---

## Component Map

### Shell
- `web/components/shell/ToggleBar.tsx` — top-level nav (4 segments)
- `web/components/shell/AuthenticatedLayout.tsx` — shell wrapper + TP provider
- `web/components/shell/ThreePanelLayout.tsx` — three-panel layout primitive (left + center + right chat)

### Chat
- `web/app/(authenticated)/chat/page.tsx` — Chat page (home)
- (Briefing dashboard component — TBD, consumes daily-update output)
- `docs/design/CHAT-COMMAND-DESK.md` — windowed command desk plan for `/chat` (ADR-165)

### Work
- `web/app/(authenticated)/work/page.tsx` — Work page (new in ADR-163)
- `web/components/work/WorkList.tsx` — left sidebar list (new)
- `web/components/work/WorkDetail.tsx` — center panel detail (new)
- `web/components/work/WorkModeBadge.tsx` — mode badge (the only mode renderer) (new)

### Agents
- `web/app/(authenticated)/agents/page.tsx` — Agents page (shrunk per ADR-163)
- `web/components/agents/AgentContentView.tsx` — identity + health card (rewritten per ADR-163)
- `web/components/agents/AgentTreeNav.tsx` — left sidebar roster (unchanged)

### Context
- `web/app/(authenticated)/context/page.tsx` — Context page (unchanged structurally)
- `web/components/context/InferenceContentView.tsx` — meta-aware inferred content renderer (new per ADR-163)
- `web/lib/inference-meta.ts` — parse helper (new per ADR-163)

### Types
- `web/types/index.ts` — `TaskMode` type + `taskModeLabel()` helper for surface mapping

### Routes
- `web/lib/routes.ts` — `HOME_ROUTE`, `CHAT_ROUTE`, `WORK_ROUTE`, `AGENTS_ROUTE`, `CONTEXT_ROUTE`

---

## Migration Notes for Implementers

When adding a new surface, ask: "what question does this answer?" If the answer overlaps with an existing surface, the new thing probably belongs inside that surface, not as a new nav item. Four surfaces is the stopping point — five becomes thrash again.

When modifying task rendering, always use `WorkModeBadge` or the `taskModeLabel()` helper. Never render `task.mode` directly. The two-mode surface is load-bearing for avoiding user confusion.

When adding per-entity activity surfaces, fold them into the entity's detail page (`/work/{slug}` or `/agents/{id}`). Don't build a new top-level activity destination — that's what ADR-163 deleted.

---

## Revision History

| Date | Version | Change |
|---|---|---|
| 2026-04-08 | v8.1 | ADR-165 accepted: `/chat` remains the Chat surface, but changes internally from two-panel layout to a managed TP command desk with deterministic windows for onboarding, briefing, work, context gaps, outputs, and agents. |
| 2026-04-08 | v8 | ADR-163 — Four-surface restructure: Chat \| Work \| Agents \| Context. Activity absorbed. Agents page shrunk to identity. New /work surface. Mode collapse (surface only). Inference visibility via InferenceContentView. |
| 2026-04-06 | v7.2 | Task-class-aware tabs on Agents (superseded) |
| 2026-04-06 | v7.1 | Tabs restored (superseded) |
| 2026-04-06 | v7 | Unified shell, flat center panel (superseded) |
| 2026-04-06 | v6.1 | Global breadcrumb added |
| 2026-04-05 | v6 | Dashboard + TP chat two-panel (superseded) |
