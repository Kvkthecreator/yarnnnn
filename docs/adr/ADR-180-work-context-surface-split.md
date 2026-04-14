# ADR-180: Work/Context Surface Split — Operational vs. Knowledge

**Date:** 2026-04-14
**Status:** Implemented
**Deciders:** Kevin
**Supersedes:** ADR-163 (Surface Restructure) — nav order and surface responsibility sections
**Extends:** ADR-167 (List/Detail Surfaces), ADR-176 (Work-First Agent Model)
**Governed by:** SURFACE-ARCHITECTURE.md v11

---

## Context

ADR-163 established four surfaces: `Chat | Work | Agents | Context`. The nav order placed Agents at position 3 and Context at position 4.

Two problems emerged from real use and the adoption of ADR-176 (Work-First Agent Model):

**1. Work was carrying two incompatible jobs.**
Work answered both "is this task healthy/scheduled?" (operational) and "what did it produce?" (documentary). These are different questions asked at different times. `DeliverableMiddle` embedded full output rendering inside the Work surface. `TrackingMiddle` had a Files tab that already punted domain file browsing to Context — acknowledging the split was natural but only doing it halfway.

**2. Nav order implied wrong conceptual priority.**
`Agents` at position 3 placed agent identity above workspace knowledge. Under ADR-176, work exists first and agents serve work. A user's primary navigation loop is Chat → Work → outputs/knowledge. Agents is a reference surface visited infrequently, not a primary destination.

**3. Breadcrumb embedded agent-containment framing.**
`Work › Analyst › Track Competitors` implied the agent owns the task. Under ADR-176 the agent is a team participant, not a container. The agent middle segment was inserted on every task detail view, even when the user navigated directly from the Work list.

---

## Decision

### Nav order: `Chat | Work | Context | Agents`

Priority order reflects user navigation frequency:
- Chat: where work is directed and results surface
- Work: operational dashboard — task health, schedule, configuration, team
- Context: knowledge surface — what the workspace knows and what tasks have produced
- Agents: roster reference — who's on the team (visited rarely)

### Work = operational only

Work answers: *is this task configured, healthy, and running correctly?*

Work shows: schedule, mode, status, assigned agent(s), objective, run history, actions (run/pause/edit).

Work does **not** show: task output documents, domain files, accumulated knowledge. For `produces_deliverable` and `accumulates_context` tasks, the detail view shows the objective and a direct link to Context for the output/knowledge.

### Context = knowledge surface (documents + outputs)

Context answers: *what does the workspace know, and what has it produced?*

Context shows:
- Accumulated domain knowledge (`/workspace/context/{domain}/`)
- Task deliverable outputs (`/tasks/{slug}/outputs/latest/`)
- Uploads (`/workspace/uploads/`)
- Settings files (IDENTITY.md, BRAND.md, CONVENTIONS.md)

The context tree gains a fourth top-level section: **Outputs** — listing all tasks that have produced deliverables. Clicking a task entry shows the latest output via the existing DeliverableMiddle component, now hosted in Context.

### Breadcrumb: task-first on Work

`Work › {task title}` — no agent middle segment.

The agent-middle-segment (`Work › Analyst › Track Competitors`) implied containment that doesn't exist. Agent is visible in the task metadata strip (always was); it doesn't belong in navigation chrome.

Exception preserved: when user navigates from `/agents` surface via "Manage task" link, the breadcrumb correctly reads `Agents › {Agent} › {task}` — tracing actual navigation history, not implying ownership.

---

## Rationale

### Why outputs belong in Context, not Work

Task deliverables are documents the workspace produced. Domain knowledge is accumulated intelligence. Both are the *knowledge state* of the workspace — the same thing at different timescales (deliverable = point-in-time output, domain = accumulated over runs). Hosting them on the same surface (Context) makes the workspace's knowledge browsable as a unified thing.

Work is where you *manage* the process that produces knowledge. Context is where you *read* what was produced. Same split as a factory floor (Work) vs. a library (Context).

### Why TrackingMiddle's FilesTab was already acknowledging this

TrackingMiddle already linked out to `/context?domain={key}` from its Files tab — it knew the files lived in Context and was pointing there. The logical completion is: remove the tab and let Context own that view directly, rather than embedding a partial view of Context inside Work.

### Why Agents moves to position 4

Under ADR-176, agents are the labor pool that serves work — not the organizing principle. The natural user journey is: hear about something in Chat → check on its status in Work → read what it produced in Context. Agents is a reference surface: you visit it to understand who's doing what or to review agent identity. It belongs at the end of the nav, not in the middle.

---

## Implementation

### Phase 1 — Nav reorder (ToggleBar.tsx)
Swap positions of `agents` and `context` in the SEGMENTS array.
Update `routes.ts` comment.

### Phase 2 — Work breadcrumb simplification (work/page.tsx)
Remove the agent middle segment from the `else` branch (task detail without `?agent=` param).
Remove the `else if (agentFilter)` branch entirely (list mode with agent filter — chip in the list UI already communicates the filter).
Result: `Work › {task title}` only. `Agents › Agent › Task` path preserved (explicit Agents-surface navigation).

### Phase 3 — WorkDetail simplification (WorkDetail.tsx)
For `produces_deliverable` and `accumulates_context` tasks:
- Remove `DeliverableMiddle` and the `TrackingMiddle` (Files tab) from KindMiddle dispatch
- Replace with a thin `OutputsLinkBlock` component: "View outputs in Context →" linking to `/context?path=/tasks/{slug}/outputs/latest`
- For `accumulates_context`: link to `/context?domain={domain}` (primary context_writes domain)
- `external_action` and `system_maintenance` kinds: unchanged

### Phase 4 — TrackingMiddle simplification (TrackingMiddle.tsx)
Remove `FilesTab` function entirely.
Remove tab strip and tab type enum.
Component becomes single-purpose: Activity tab only (run receipts, last-run log, data contract).

### Phase 5 — Context surface enhancement (context/page.tsx + ContentViewer.tsx)
Add `Outputs` as fourth top-level folder in `buildContextNodes()`.
Populated from `api.tasks.list()` filtered to tasks with `last_run_at` and `output_kind: 'produces_deliverable'`.
`ContentViewer` gains a routing branch for `/tasks/*/outputs` paths → renders `DeliverableMiddle` directly.
Breadcrumb in context/page.tsx gains a case for `/tasks/` paths → `Context › {task title} › Latest`.

### Phase 6 — SURFACE-ARCHITECTURE.md update
Bump to v11. Update nav order table, surface responsibility table, breadcrumb patterns table.

---

## What does NOT change

- Work list surface (WorkListSurface.tsx) — grouping by output_kind, filters, search: unchanged
- Agent detail page (`/agents?agent={slug}`) — unchanged
- `external_action` and `system_maintenance` KindMiddle dispatch — unchanged (no outputs to migrate)
- `DeliverableMiddle` component itself — not deleted, just moves from Work to Context hosting
- `?agent=` query param on `/work` — preserved for Agents-surface navigation (breadcrumb path only)
- Context domain tree (workspace/context/) — unchanged structure
- All API endpoints — no backend changes

---

## Breadcrumb patterns after this ADR

| State | Pattern |
|---|---|
| Work list | `Work` (single segment) |
| Work task detail (from Work) | `Work › Task Title` |
| Work task detail (from Agents) | `Agents › Agent Name › Task Title` |
| Context list | `Context` (single segment) |
| Context domain | `Context › Domain Name` |
| Context domain file | `Context › Domain Name › filename` |
| Context task output | `Context › Task Title › Latest` |
| Agents list | `Agents` |
| Agents detail | `Agents › Agent Name` |

---

## Rejected alternatives

**Keep outputs in Work, add tabs.** This is where the previous 10 surface architecture versions went — adding tabs to accommodate two incompatible questions in one surface. Each version ended up with more tabs and more confusion. The split is the right move.

**Keep Agents at position 3.** Considered. The counter-argument is "agents are important, shouldn't be last." But importance ≠ navigation frequency. The roster is a reference, not a daily destination. Position 4 reflects that honestly.

**Merge Context and Work into one surface.** The opposite of this ADR — rejected because it recreates the same problem: one surface, two incompatible questions.
