# ADR-180: Work/Context Surface Split — Task-Scoped vs. Workspace-Scoped

**Date:** 2026-04-14
**Status:** Amended (2026-04-16)
**Deciders:** Kevin
**Supersedes:** ADR-163 (Surface Restructure) — nav order and surface responsibility sections
**Extends:** ADR-167 (List/Detail Surfaces), ADR-176 (Work-First Agent Model)
**Governed by:** SURFACE-ARCHITECTURE.md v14

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

## Decision (original, 2026-04-14)

### Nav order: `Chat | Work | Files | Agents`

Priority order reflects user navigation frequency:
- Chat: where work is directed and results surface
- Work: operational dashboard — task health, schedule, configuration, team
- Files: knowledge surface — what the workspace knows and what tasks have produced
- Agents: roster reference — who's on the team (visited rarely)

### Work = operational only *(amended — see below)*

### Context = knowledge surface *(amended — see below)*

### Breadcrumb: task-first on Work

`Work › {task title}` — no agent middle segment. *(Preserved in amendment.)*

---

## Amendment (2026-04-16): Task-Scoped vs. Workspace-Scoped

### What happened

Phase 3 ("remove DeliverableMiddle from Work, replace with OutputsLinkBlock") shipped at 12:29 on 2026-04-14 — then was **reverted 5 hours later** (commit 609e23d). DeliverableMiddle was put back into Work as inline output. The commit message explicitly states: "OutputsLinkBlock removed."

The revert was correct. Sending users to a different nav item to see what their task just produced is a disruptive UX — you create a task, it runs, you want to see the output, and the system tells you to go somewhere else. The "factory floor vs. library" metaphor breaks down because nobody walks to a separate building to see what the factory just made.

Meanwhile, for `accumulates_context` tasks, TrackingEntityGrid shows entity cards on Work — but clicking them bounces you to `/context?path=...` with no return link. Users leave their task detail page to browse entity files, then navigate back manually.

The result was an **identity crisis**: Context renders task outputs via regex path detection (Identity A: task-aware companion), while also presenting itself as a generic filesystem browser with 4 virtual sections (Identity B: raw explorer). Neither identity is clean.

### The correct boundary

The original ADR drew the line between "operational" and "knowledge." The correct line is between **task-scoped** and **workspace-scoped**.

**Task-scoped: everything about a single task is reachable from its Work detail page.** A `produces_deliverable` task shows its output inline. An `accumulates_context` task lets you browse its domain entities inline — without navigating away.

**Workspace-scoped: cross-task knowledge views and user uploads live on Context.** "What do I know about competitors across all tasks?" is a different question from "is my track-competitors task healthy?" Context is the cross-task knowledge archive, not a per-task file browser.

### Revised surface responsibilities

| Surface | Scope | The question it answers |
|---|---|---|
| **Work** | Task-scoped | "What is this task doing, and what has it produced/accumulated?" |
| **Context** | Workspace-scoped | "What does my workspace know overall? What have I uploaded?" |

### Work = task-scoped (amended from "operational only")

Work answers: *what is this task configured to do, is it healthy, and what has it produced or accumulated?*

Work shows, per `output_kind`:
- `produces_deliverable`: DeliverableMiddle inline (output as hero — already shipped, Phase 3 revert preserved)
- `accumulates_context`: TrackingEntityGrid with **inline domain browsing** — entity clicks open a DomainBrowser (ContentViewer + WorkspaceTree composed for a single domain) within the Work detail page, NOT a navigation to Context
- `external_action`: ActionMiddle (fire + history — unchanged)
- `system_maintenance`: MaintenanceMiddle (hygiene log — unchanged)

### Context = workspace-scoped (simplified from 4 sections to 2)

Context answers: *what does my workspace know across all tasks?*

Context shows:
- **Context domains** (`/workspace/context/{domain}/`) — with task provenance headers ("Written by: track-competitors · weekly")
- **Uploads** (`/workspace/uploads/`) — user-contributed documents not tied to any task

Context does **not** show:
- ~~Outputs section~~ — task deliverable outputs are on Work (DeliverableMiddle)
- ~~Settings section~~ — Identity/Brand are on Settings page

Nav label remains **Files** — it is still a filesystem browser, just a narrower one.

### What changes from original ADR-180

| Aspect | Original (2026-04-14) | Amended (2026-04-16) |
|---|---|---|
| Boundary | Operational vs. Knowledge | Task-scoped vs. Workspace-scoped |
| DeliverableMiddle | Hosted in Context only | Stays in Work (Phase 3 revert preserved) |
| TrackingEntityGrid | Links out to Context | Opens inline DomainBrowser on Work |
| Context Outputs section | Added (Phase 5) | **Deleted** — outputs live on Work |
| Context Settings section | Kept | **Deleted** — Settings has its own page |
| Context tree | 4 sections (Context, Outputs, Uploads, Settings) | 2 sections (Context domains, Uploads) |
| Work detail | "Operational only" — no output rendering | Task-scoped — full output + domain browsing |

### What does NOT change from original

- Nav order: `Chat | Work | Files | Agents` — preserved
- Breadcrumb: `Work › {task title}` (task-first, no agent middle) — preserved
- Agents at position 4 — preserved
- Work list surface (WorkListSurface.tsx) — unchanged
- Agent detail page — unchanged
- `external_action` and `system_maintenance` KindMiddle dispatch — unchanged
- All API endpoints — no backend changes

---

## Rationale (original, preserved for context)

### Why the original "operational only" thesis was wrong

The factory/library metaphor assumed users want to manage tasks and read outputs as separate activities. In practice, the primary user journey is: check on task → see what it produced. Forcing a surface switch for this core loop creates friction. The Phase 3 revert within 5 hours confirmed this — the code told us the ADR was wrong.

### Why task-scoped vs. workspace-scoped is the right boundary

Task-scoped browsing ("what did track-competitors accumulate?") is a drill-down from the task. Workspace-scoped browsing ("what do I know about competitors across all tasks and uploads?") is a cross-cutting view. These are genuinely different questions asked at different times, and the boundary between them is clean.

### Why Context domains still need their own surface

Context domains outlive individual tasks (ADR-176: domains created by work demand, shared across tasks). A user may want to browse all competitor intelligence regardless of which tracking task produced it. This cross-task knowledge view doesn't belong inside any single task's detail page.

### Why Agents stays at position 4

Under ADR-176, agents are the labor pool that serves work. The natural user journey is: Chat → Work → (drill into task output/context). Agents is a reference surface visited infrequently.

---

## Implementation (amended)

### Phase 1 — Nav reorder (ToggleBar.tsx) ✅ Shipped
Swap positions of `agents` and `context` in the SEGMENTS array.

### Phase 2 — Work breadcrumb simplification (work/page.tsx) ✅ Shipped
`Work › {task title}` only. `Agents › Agent › Task` path preserved for Agents-surface navigation.

### Phase 3 — DeliverableMiddle stays in Work ✅ Shipped (via revert)
Phase 3 as originally specified was reverted same-day. DeliverableMiddle renders inline in Work as hero output. This is now the correct behavior per the amended boundary.

### Phase 4 — TrackingMiddle FilesTab removal ✅ Shipped
FilesTab deleted. TrackingMiddle is Activity-only (run receipts, data contract).

### Phase 5 — Context Outputs section ✅ Shipped → **TO BE DELETED** (amendment)
Phase 5 shipped but is now redundant. Outputs section and Settings section will be removed from Context in the amendment implementation.

### Phase 6 — SURFACE-ARCHITECTURE.md ✅ Shipped → **TO BE UPDATED to v14** (amendment)

### Phase 7 — Inline domain browsing on Work (NEW, amendment)
Refactor TrackingEntityGrid: extract `router.push(CONTEXT_ROUTE)` to an `onNavigate` callback prop. Create `DomainBrowser` wrapper (ContentViewer + WorkspaceTree scoped to a single domain). Embed in TrackingMiddle — entity clicks open the inline browser, not a navigation to Context.

### Phase 8 — Context simplification (NEW, amendment)
Remove Outputs section from `buildContextNodes()`. Remove Settings section. Delete the regex-based DeliverableMiddle routing branch from context/page.tsx. Add task provenance headers to domain folder views ("Written by: track-competitors · weekly"). Result: Context tree has 2 sections (Context domains, Uploads).

### Phase 9 — SURFACE-ARCHITECTURE.md v14 (NEW, amendment)
Update design thesis, surface responsibilities, component map, route map.

---

## Breadcrumb patterns (amended)

| State | Pattern |
|---|---|
| Work list | `Work` (single segment) |
| Work task detail (from Work) | `Work › Task Title` |
| Work task detail (from Agents) | `Agents › Agent Name › Task Title` |
| Context list | `Files` (single segment) |
| Context domain | `Files › Domain Name` |
| Context domain entity | `Files › Domain Name › Entity Name` |
| Context domain file | `Files › Domain Name › Entity Name › filename` |
| Context upload | `Files › Uploads › filename` |
| Agents list | `Agents` |
| Agents detail | `Agents › Agent Name` |

**Removed**: `Context › Task Title › Latest` — task outputs no longer hosted on Context.

---

## Rejected alternatives

**Keep outputs in Work, add tabs.** (Original, still rejected.) Adding tabs to accommodate two questions in one surface leads to tab sprawl.

**Keep Agents at position 3.** (Original, still rejected.) Importance ≠ navigation frequency.

**Merge Context and Work into one surface.** (Original, still rejected.) Cross-task knowledge browsing is a different activity from task detail inspection.

**"Operational only" Work with link-out to Context for outputs.** (The original Phase 3 — rejected by the revert.) Forcing a surface switch for the core "check task → see output" loop creates unacceptable friction. The code told us this within 5 hours.
