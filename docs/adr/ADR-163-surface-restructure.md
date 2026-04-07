# ADR-163: Surface Restructure — Chat as Home, Work as First-Class, Activity Absorbed

**Status:** Proposed
**Date:** 2026-04-08
**Authors:** KVK, Claude
**Supersedes:** SURFACE-ARCHITECTURE.md v7.2 (task-class-aware tabs on Agents page)
**Extends:** ADR-138 (Agents as Work Units), ADR-140 (Agent Workforce Model), ADR-149 (Task Lifecycle), ADR-161 (Daily Update Anchor), ADR-162 (Inference Hardening)
**Related:** ADR-159 (Filesystem-as-Memory)

---

## Context

### The Frontend Churn Is a Symptom, Not the Disease

Over the last ten commits, the agents page has iterated through at least four distinct tab layouts:

- `Dashboard / Tasks / Agent` (v6) — three tabs, stacked intent
- Tabs removed (v7) — flattened single scrollable view
- Tabs restored (v7.1) — "three user intents need separation"
- `Report / Data / Pipeline / Agent` (v7.2) — task-class-aware, BI-framed

Each iteration solved a local problem but did not resolve the underlying ambiguity: **the Agents page was doing three jobs that belong on three different surfaces** — work observation (what tasks are doing), agent identity (who this agent is), and context browsing (what files exist). Every tab restructure was an attempt to hide the ambiguity behind a different chrome.

The correct fix is not another tab layout. The correct fix is to **separate the surfaces so each answers exactly one question**, and let the nav tell the user which question they're asking.

### The Vocabulary Problem

The nav today is `Home | Agents | Context | Activity`. This has two problems:

1. **"Home" is opaque.** It actually points to `/chat`, but users can't tell that from the label. The chat surface is the intellectual center of the product (TP is there), but its nav label says nothing about that.

2. **"Activity" is a vestige.** ADR-129 introduced Activity as a separate substrate; subsequent ADRs moved activity surfaces to per-entity locations (task timelines, agent histories, briefing feeds). The top-level `/activity` page became a catch-all for events that didn't have a natural home. It duplicates information already surfaced elsewhere.

3. **There is no first-class "Work" destination.** Tasks are work units (ADR-138), but the user has no top-level nav item that says "your work lives here." Today they have to navigate through an agent to see tasks. That's the wrong information architecture — agents are WHO, tasks are WHAT, and the user wants to see both axes independently.

### The Mode-Vocabulary Problem

The schema has three task modes (`recurring | goal | reactive`), and users have been asked to see all three. The right design is two user-facing modes (`Recurring | One-time`) with the schema preserved for execution-layer distinction. This was locked in earlier in the conversation that motivated this ADR, but no surface currently reflects the collapse.

### The Inference Visibility Problem (from ADR-162 Sub-phase D)

ADR-162 wrote source-provenance HTML comments and gap reports into inference output, but the frontend doesn't yet parse them. The Context tab still renders IDENTITY.md and BRAND.md as raw markdown with no signals. The user has no visible cue that inference just ran, no "here's what's missing" markers, no source captions.

The ADR-162 decision was to defer these frontend changes to ADR-163 because they're Context-tab frontend changes that should land with the broader restructure, not as a separate commit. This ADR picks up that deferred work.

---

## Decision

### Four changes, one commit

1. **Nav restructure:** `Chat | Work | Agents | Context` replaces `Home | Agents | Context | Activity`. `/chat` becomes the new HOME_ROUTE. `/work` becomes a real top-level destination. `/activity` is deleted entirely and its content absorbed into the surfaces that naturally own it.

2. **Mode collapse (surface only):** UI labels show `Recurring` and `One-time` only. Schema keeps `recurring | goal | reactive` untouched. Mapping table: `recurring → Recurring`, `goal → One-time`, `reactive → One-time`. Users see two modes; the execution layer still distinguishes three.

3. **Agents page shrinks:** the `Report / Data / Pipeline / Agent` tab layout dissolves. The Agents page becomes a **roster surface**: a list of agents (left), an identity/health card for the selected agent (center), and a link to the agent's work on `/work`. No more tab thrash because the page only does one job now.

4. **Inference visibility (ADR-162 Sub-phase D frontend):** the Context tab renders the inference-meta HTML comments as source-provenance captions, parses the gaps field from the latest inference response to show missing-info markers inline, and surfaces "what changed" via the existing TP notification channel.

---

### Change 1: Nav Restructure — `Chat | Work | Agents | Context`

**ToggleBar v5** (`web/components/shell/ToggleBar.tsx`):

```
┌────────────────────────────────────────┐
│  [Chat] [Work] [Agents] [Context]      │
└────────────────────────────────────────┘
```

Each segment's purpose — these are the questions each surface answers:

| Segment | Route | The question | The answer |
|---|---|---|---|
| **Chat** | `/chat` | "What should I do? What's happening?" | TP chat + briefing dashboard (daily-update rendered as structured view) |
| **Work** | `/work` | "What is my workforce doing?" | Task list (left) + task detail (center) — schedule, last run, next run, output, pipeline, mode |
| **Agents** | `/agents` | "Who's on my team?" | Agent roster (left) + agent identity + health (center) |
| **Context** | `/context` | "What does my workspace know?" | Workspace filesystem browser (unchanged from current) |

**Route changes:**

- `HOME_ROUTE` changes from `/agents` to `/chat`.
- New top-level route `/work` — a real page, not a redirect. The catchall at `/tasks/[[...slug]]` is replaced with a `/work` structure. For backwards compat on bookmarks, `/tasks` redirects to `/work`.
- `/activity` is deleted. The page file is removed. The route no longer exists. Any remaining references in the codebase are either removed or redirected to the surface that owns the equivalent content (usually `/chat` for workspace-wide, `/work/[slug]` for task-scoped, `/agents/[id]` for agent-scoped).

**Why "Work" and not "Tasks":** the word "task" is a productivity-tool cliché that means "thing I should do myself." YARNNN's tasks are the opposite — they're things the user has delegated to autonomous agents. "Work" is broader and more accurate to the relationship: this is work being done on your behalf. The schema column stays `tasks.slug`, the API stays `/api/tasks`, but the user-facing word is "Work". The internal naming stays "task" in code — consistency with the database column is more important than lexical purity in the code layer.

**Nav label copy** throughout the user-facing surface is "Work." Internal code comments, API paths, variable names, file paths all remain "task." This is the one permitted split between surface vocabulary and code vocabulary.

### Change 2: Mode Collapse (Surface Only)

**Schema:** unchanged. `tasks.mode` still has the CHECK constraint `recurring | goal | reactive`. Migration is not required.

**Mapping:**

```
Database value  →  Surface label
─────────────────────────────────
recurring       →  Recurring
goal            →  One-time
reactive        →  One-time
```

**Where this mapping is applied:**

1. `web/types/index.ts`: add a `TaskMode` type alias and a helper `taskModeLabel(mode: string): 'Recurring' | 'One-time'`.
2. All task-displaying components (`/work/[slug]` page, work list, chat briefing dashboard) use the helper, never the raw schema value.
3. The create-task flow (wherever tasks are created from a UI form, if at all — most are created via TP chat) exposes only two mode options: `Recurring` and `One-time`. Under the hood, "One-time" resolves to `goal` (the default for deliverable-style one-time tasks; `reactive` is only used for trigger-based cases set up via TP chat directly).

**Why the surface collapses but the schema doesn't:** the schema answers *"what does the execution layer need to distinguish?"* and the execution layer genuinely needs three modes — `goal` has the revision loop, `reactive` has the dispatch-and-done, `recurring` has the heartbeat-evaluation path (see ADR-149's mode-specific behavior). The surface answers *"what does the user need to choose?"* and the user only needs to choose between "runs on a schedule indefinitely" and "runs when I ask, completes when done." The distinction between goal and reactive matters to the pipeline, not to the user.

**Mode evolution stays supported.** A user can convert a One-time task to Recurring via TP chat. That's an `UPDATE tasks SET mode='recurring', schedule='daily'` under the hood. The user says "make this weekly" and the conversion is invisible.

### Change 3: Agents Page Shrinks — Roster + Identity Only

**Current (v7.2):** Agents page has four tabs (`Report | Data | Pipeline | Agent`). Pipeline tab shows task config, schedule, actions. Report tab shows synthesis outputs. Data tab shows domain entities. Agent tab shows identity.

**New:** Agents page has **no tabs**. The center panel shows one surface: agent identity.

```
┌─────────────┬─────────────────────────────────────┬─────────────┐
│ Agent       │  Competitive Intelligence            │ TP Chat     │
│  Roster     │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━     │             │
│             │                                      │             │
│ • Comp Intel│  [Avatar]                            │             │
│ • Mkt Rsch  │  Domain: /workspace/context/         │             │
│ • Biz Dev   │          competitors/                │             │
│ • Operations│  Status: active                      │             │
│ • Marketing │                                      │             │
│ • Reporting │  ## Identity (AGENT.md)              │             │
│ • Slack Bot │  ...                                  │             │
│ • Notion Bot│                                      │             │
│ • GitHub Bot│  ## Health                           │             │
│             │  • Tasks assigned: 3                 │             │
│             │  • Approval rate: 100%               │             │
│             │  • Last run: 2h ago                  │             │
│             │                                      │             │
│             │  [See this agent's work →] (→/work)  │             │
└─────────────┴─────────────────────────────────────┴─────────────┘
```

**What moves to `/work`:**
- Pipeline tab (task config, schedule, trigger/pause actions)
- Report tab (synthesis outputs)

**What moves to `/context`:**
- Data tab (domain entities — this was already a view over files in `/workspace/context/`, so it was always a duplicate)

**What stays on `/agents`:**
- Roster (left sidebar)
- Identity (AGENT.md display)
- Health signals (tasks assigned count, approval rate, last run)
- A link to `/work?agent={slug}` for "see this agent's work"
- A link to `/context?domain={domain}` for "see this agent's domain"

**Why this is right:** the Agents page has only one job — "who is this agent, and are they healthy?" Every other question has a better home. The tab thrash stops because there are no tabs to thrash. The page is smaller, faster, and correctly scoped.

### Change 4: Inference Visibility (ADR-162 Sub-phase D Frontend)

This picks up the deferred frontend work from ADR-162. Three pieces, all small, all in the Context tab under the Identity/Brand files.

**Piece 1: Source provenance captions.** The inference-meta HTML comment at the bottom of IDENTITY.md and BRAND.md (written by `_append_inference_meta` in Phase 2) is parsed by the Context tab renderer. Below each file's title, a small caption shows:

```
Last updated 2h ago · from: pitch-deck.pdf, acme.com
```

If there's no inference-meta comment (e.g., the file is a manually-edited placeholder), the caption is omitted.

**Piece 2: Gap markers inline in the rendered file.** When the Context tab loads IDENTITY.md or BRAND.md, it fetches the latest stored gap report (if any — we'll need to persist this somewhere; see "Where the gap report lives" below) and renders "needs more info" pills next to any section that corresponds to an unfilled gap field. Clicking a pill sends a pre-filled message to TP in the chat panel: "I want to add my company name to my identity."

**Piece 3: Change highlighting via existing notification channel.** When TP calls `UpdateContext(target='identity'|'brand')`, the existing TP notification channel (`web/contexts/TPContext.tsx` + `NotificationCard.tsx`) already surfaces the tool call as a notification card in the chat stream. ADR-163 extends the card's rendering:

```
┌────────────────────────────────────────────────┐
│  ✎  Updated your identity                      │
│     Added: company, domains of attention       │
│     Missing: work patterns                     │
│     [View identity →]                          │
└────────────────────────────────────────────────┘
```

The "Added" and "Missing" fields come from the `gaps` field in the UpdateContext response (Phase 2 Sub-phase A). The "View identity" link navigates to `/context?file=IDENTITY.md`.

**Where the gap report lives:** Piece 2 requires persisting the gap report so the Context tab can render markers without re-running inference. Two options:

- **Option A:** Store gaps as part of the inference-meta HTML comment in the file itself. The comment becomes: `<!-- inference-meta: {"target": "identity", "inferred_at": "...", "sources": {...}, "gaps": [...]} -->`. Pros: single source of truth, no schema change, already co-located with the file. Cons: gaps are embedded in every file version, slightly larger file size, stale gaps persist if the user manually edits the file.
- **Option B:** New `workspace_files.gap_report` column or similar. Pros: clean separation. Cons: schema change for a small signal.

**Decision: Option A.** The gap report is extended into the existing inference-meta comment. This means `_append_inference_meta()` in `context_inference.py` is extended to accept and embed the gap report. `_handle_shared_context` in `update_context.py` passes the gap result into the meta builder. No schema change.

### Activity Absorption — Where Each Event Type Goes

The `/activity` page today surfaces four categories:

1. **Upcoming** (scheduled tasks) → moves to `/work` (each task shows its next run; the work list can be sorted by upcoming)
2. **Past / task events** (task_executed, agent_run) → moves to per-task detail on `/work/[slug]` (run history) and per-agent health on `/agents`
3. **Past / workspace events** (platform connections, context updates, scheduler heartbeats) → moves to `/chat` briefing dashboard as a "Recent activity" feed. The dashboard is the right home because it's where the user lands to find out "what's happening in my workspace."
4. **System events** (errors, diagnostics) → moves to Settings under a "System Status" collapsible section. These are diagnostic, not operational, and shouldn't be top-level noise.

The `/activity` page file is deleted outright. No legacy redirect — the page didn't have meaningful bookmarks because it was a catch-all.

### Surfaces the user sees after this ADR ships

```
/chat         → Chat (home). Daily briefing dashboard on left, TP chat on right.
                Recent workspace activity surfaced in the dashboard.

/work         → Work. Task list on left, task detail on center. Mode labels: Recurring / One-time.
                Upcoming section (sorted by next_run_at). Task detail shows schedule,
                last run, pipeline, output, actions.

/work/{slug}  → Task detail, full-page if opened directly.

/agents       → Agents. Roster on left, identity card in center. Links to /work and /context.

/agents/{id}  → Agent identity detail (alias for /agents?agent={id}).

/context      → Context. Workspace filesystem browser. Identity/Brand files have source
                provenance captions and gap markers.

/settings     → Settings. Existing structure + new "System Status" expandable for diagnostics.
```

Four top-level destinations. Each answers exactly one question. No overlap.

---

## Code Changes (Map)

### Backend

| File | Change |
|---|---|
| `api/services/context_inference.py` | Extend `_append_inference_meta()` to accept and embed `gap_report` (Option A above) |
| `api/services/primitives/update_context.py` | Pass gap report into the meta builder |

### Frontend — routes and nav

| File | Change |
|---|---|
| `web/lib/routes.ts` | `HOME_ROUTE` → `/chat`. `HOME_LABEL` → `"Chat"`. New `WORK_ROUTE = "/work"`. Remove `ACTIVITY_ROUTE` |
| `web/components/shell/ToggleBar.tsx` | Update SEGMENTS to `[Chat, Work, Agents, Context]`. Icons: Home → MessageCircle for Chat, new Briefcase/Target/etc. for Work, remove Activity entry |
| `web/app/(authenticated)/activity/page.tsx` | DELETE — file removed |
| `web/app/(authenticated)/tasks/[[...slug]]/page.tsx` | DELETE or convert to redirect to `/work` |
| `web/app/(authenticated)/work/page.tsx` | NEW — work list + detail, or thin layout wrapper |
| `web/app/(authenticated)/work/[slug]/page.tsx` | NEW — task detail |
| `web/app/(authenticated)/work/layout.tsx` | NEW — work layout |
| `web/app/(authenticated)/orchestrator/page.tsx` | Update redirect target: `/agents` → `/chat` (new home) |
| `web/app/(authenticated)/workfloor/page.tsx` | Update redirect: `/agents` → `/chat` |
| `web/lib/supabase/middleware.ts` | Update middleware to reflect new HOME_ROUTE |
| `web/app/auth/callback/page.tsx` | Update post-auth landing to `/chat` |
| `web/app/auth/login/page.tsx` | Update post-login target to `/chat` |
| `web/app/admin/layout.tsx` | Update admin back-link target |
| `web/components/settings/MemorySection.tsx` | Update `router.push(HOME_ROUTE...)` references (will auto-update if it uses `HOME_ROUTE`) |
| `web/components/surfaces/IdleSurface.tsx` | Update `router.push(HOME_ROUTE...)` references |

### Frontend — agents page shrink

| File | Change |
|---|---|
| `web/app/(authenticated)/agents/page.tsx` | Remove tab-based content. Keep roster + identity center panel. Add "See this agent's work" link to `/work?agent={slug}` |
| `web/components/agents/AgentContentView.tsx` | DELETE tabs. Collapse to identity + health card. Extract `ReportTab` and `PipelineTab` into `/work` page |
| `web/components/agents/AgentDashboard.tsx` | Keep — still used by agent identity center panel |
| `web/components/agents/AgentSettingsPanel.tsx` | Keep — still used by settings drawer |

### Frontend — work surface (new)

| File | Change |
|---|---|
| `web/components/work/WorkList.tsx` | NEW — left sidebar listing tasks, sorted by next_run_at. Uses two-mode label helper. |
| `web/components/work/WorkDetail.tsx` | NEW — center panel. Absorbs Pipeline + Report tab content from the old AgentContentView |
| `web/components/work/WorkModeBadge.tsx` | NEW — renders "Recurring" or "One-time" from raw schema value |
| `web/hooks/useWorkList.ts` | NEW — hook for fetching and polling the task list (may reuse `useAgentsAndTasks`) |

### Frontend — inference visibility

| File | Change |
|---|---|
| `web/app/(authenticated)/context/page.tsx` or equivalent | When rendering IDENTITY.md / BRAND.md, parse inference-meta comment, render source caption below title |
| `web/lib/inference-meta.ts` | NEW — `parseInferenceMeta(content: string): { sources, gaps, inferredAt } \| null` helper |
| `web/components/context/GapMarker.tsx` | NEW — inline pill component for "missing info" markers |
| `web/contexts/TPContext.tsx` | Extend UpdateContext notification detection to surface gap data in card |
| `web/components/tp/NotificationCard.tsx` | New "identity updated" variant showing what changed + what's missing |

### Types

| File | Change |
|---|---|
| `web/types/index.ts` | Add `taskModeLabel(mode: string): 'Recurring' \| 'One-time'` helper. Mark `mode` JSDoc to reflect the three-to-two collapse rule |

---

## Documentation Changes

| File | Change |
|---|---|
| `docs/adr/ADR-163-surface-restructure.md` | This file |
| `docs/design/SURFACE-ARCHITECTURE.md` | Full rewrite to v8. Document new nav, new route map, new surface purposes, mode collapse policy, Activity absorption |
| `docs/architecture/SERVICE-MODEL.md` | Update "Entity Model" and any nav references |
| `docs/architecture/FOUNDATIONS.md` | Small extension to Axiom 6 noting that the two-mode surface is a deliberate design decision aligned with the "describe your work" onramp |
| `CLAUDE.md` | Add ADR-163 entry to Key Architecture References. Update file locations table for new `/work` page components |
| `api/prompts/CHANGELOG.md` | Entry for any TP prompt changes (likely just terminology — "tasks" → "work" in user-facing phrasings) |

---

## Migration Notes

**Zero data migration.** No schema change. The `tasks` table is untouched. The only migration is code + surfaces + docs.

**Bookmarks:**
- `/agents` still works (shrinks to identity-only view)
- `/tasks` and `/tasks/{slug}` redirect to `/work` and `/work/{slug}`
- `/activity` returns 404 (intentional — the content moved, no single destination replaces it)
- `/orchestrator` and `/workfloor` keep redirecting (updated target)

**New users:** land on `/chat` after signup (was `/agents`). The Chat surface is the intellectual center of the product — landing there makes the product's purpose immediately visible.

**Returning users:** also land on `/chat` by default. Their daily-update task (from ADR-161) is already producing content, so the briefing dashboard has something real to show.

---

## Why This Is the Right Place to Stop Iterating

The tab thrash on the Agents page stopped being about UX and started being about ontology. Four tab layouts in ten commits is the signal that the tabs were being asked to separate concerns that the page itself was conflating. Separating the concerns *at the surface level* — by giving Work, Agents, and Context their own top-level destinations — ends the thrash because no single surface has to do three jobs anymore.

This is also the reason mode vocabulary gets fixed here and not in a separate ADR: "how does the user think about a task" and "where does the user look at a task" are the same question. Answering them together avoids a second round of churn when the mode labels change later.

---

## Open Questions

1. **Should `/work` have its own chat panel like `/agents` does (ThreePanelLayout)?** Decision: yes, default to the same ThreePanelLayout pattern. The TP chat panel is consistent across all non-Context surfaces. Context is the one exception because it's a file browser, not a work surface.

2. **How does the chat briefing dashboard know what "recent activity" to show?** Decision: initial cut uses the same data the current `/activity` page uses (activity_log table), filtered to the last 72 hours. The dashboard renders the last 10-15 events in a compact timeline. No filter UI in v1 — just the raw recent feed.

3. **What about the "Upcoming" section from the old Activity page?** Decision: moves to the top of `/work` as a sort mode. The work list, by default, shows active tasks sorted by `next_run_at` ascending — so the upcoming runs are naturally at the top.

4. **Should we rename `tasks` in the database to `work_items`?** No. The schema column stays `tasks`. Naming consistency with the code layer is more important than lexical purity. The one permitted split is the user-facing label.

5. **What about the agent health signals currently on the Agents page — do they belong in the new minimal Agents view?** Yes. The health card on the agent identity view shows: tasks assigned count, approval rate (if >= 5 runs), last run timestamp. This is the one "work signal" the Agents page keeps, because it's asking "is this agent healthy?" — which is an agent question, not a work question.

6. **Does the `/work` page duplicate some data from `/agents`?** Minimally — a task row shows its assigned agent's name and links to `/agents?id=`. This is a one-way link, not data duplication. The task row doesn't cache agent details; it fetches by reference.

7. **What happens to the `docs/design/SURFACE-ARCHITECTURE.md` document?** Full rewrite to v8. The file stays at the same path, revision history gets appended, the content reflects the new four-surface model.

---

## Revision History

| Date | Change |
|---|---|
| 2026-04-08 | v1 — Initial. Nav rename to Chat/Work/Agents/Context. Mode collapse surface-only (schema preserved). Agents page shrinks to roster+identity. Activity absorbed into per-surface contexts. Inference visibility frontend pieces from ADR-162 Sub-phase D. One commit. |
