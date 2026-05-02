# ADR-243: Schedule Surface — Cadence-Framed Sibling of /work

**Status:** Implemented (Phase 1 — list view; Phase 2 calendar deferred)
**Date:** 2026-05-01
**Dimensional classification:** **Channel** (primary, Axiom 6)

## Context

ADR-231 Phase 3.7 dissolved the `tasks` substrate (filesystem + heavy DB columns), making **Recurrence** the canonical concept: a scheduled unit of work declared as YAML at a natural-home path, with the `tasks` table reduced to a thin scheduling index. ADR-214 collapsed the cockpit nav to four tabs (`Chat | Work | Agents | Files`).

The `/work` surface today (ADR-241 era) frames recurrences by **output kind** — tabs split into "My Work" (grouped by Reports / Tracking / Actions), "Connectors", "System", "Decisions". This is a *what does it produce* lens. Useful, but it doesn't answer the operator's other natural question: **"what's on my schedule?"** — the *when does it run* lens.

Operator vocabulary check (per ADR-212 layered-naming):
- "Task" — internal jargon, retired from the surface (ADR-231 renamed types `Recurrence`, but URL slugs/code variables still partially say "task" — ADR-231 Phase 3.8 debt).
- "Recurrence" — substrate vocabulary, accurate but jargony.
- "Schedule" — operator vocabulary. The user thinks "what's on my schedule" — recurring cadences, planned one-time runs, reactive triggers — without caring about internal classification.

The cleanest fix is **not** to rebrand `/work` (which has settled output-kind framing and 200+ commits of UX behind it) but to **add a sibling surface that reads the same substrate through the cadence lens**.

## Decision

**Add `/schedule` as a fifth top-level cockpit tab**, sibling to `/work`. The nav becomes `Chat | Work | Schedule | Agents | Files`. Surface is a list view sectioned by cadence; each row links into the existing `/work?task={slug}` detail surface (no duplicate detail UI).

### Decisions locked in

1. **Additive surface, not a rename.** `/work` stays untouched. `/schedule` reads the same `useAgentsAndRecurrences()` data and renders a different framing. No API changes, no data layer changes, no schema changes.

2. **Three cadence sections** in the list view (V1 classification):
   - **Recurring** — recurrence has a non-empty `schedule` field (anything other than null/empty/`"on-demand"`).
   - **Reactive** — recurrence has no schedule AND `shape === 'action'` (fires on platform events, not on cadence).
   - **One-time** — recurrence has no schedule AND `shape !== 'action'` (goal-mode, runs once, completes).

   This is the operator's natural temporal taxonomy. Same `recurrenceLabel(schedule)` helper from `web/types/index.ts` powers the binary badge on `/work`; on `/schedule` we extend it via `cadenceCategory(recurrence)` to the three-way split.

3. **Detail click-through goes to `/work?task={slug}`.** No `?recurrence=` URL on `/schedule`. The detail view is canonical at `/work` (ADR-241 surfaces the operator-facing detail). `/schedule` is a list-only entry point that hands off to `/work` for any deeper read.

4. **Calendar view is Phase 2, deferred.** The visual cadence-grid (week/month) framing is a natural next iteration but doesn't carry weight pre-users. Documented in code (`web/app/(authenticated)/schedule/page.tsx` header) and here. Phase 2 promotion criteria: at least one alpha operator authoring 5+ recurrences AND requesting cadence-grid visualization.

5. **Tab placement: between Work and Agents.** `Chat | Work | Schedule | Agents | Files`. Work and Schedule are sibling operations surfaces; placing Schedule adjacent keeps related concerns together.

6. **Backend untouched.** Existing `/api/recurrences/*` endpoints serve `/schedule` directly via `useAgentsAndRecurrences()`. The hook's `tasks: Recurrence[]` field is reused (despite the lingering name — Phase 3.8 cleanup is ADR-231 debt, not this ADR's concern).

## Consequences

### Preserved

- ADR-214 four-tab framing extends to five tabs; `Chat | Work | Agents | Files` ordering preserved with Schedule slotted in.
- ADR-231 substrate (Recurrence YAML at natural-home paths, thin `tasks` table).
- ADR-241 `/work` detail surface remains canonical for any single recurrence.
- ADR-167 v2 list-vs-detail surface convention: `/schedule` list mode only (no detail mode), so no auto-select to worry about.

### New

- `web/app/(authenticated)/schedule/page.tsx` — list surface.
- `web/components/schedule/ScheduleListSurface.tsx` — the cadence-sectioned list component.
- `web/lib/schedule.ts` — `cadenceCategory(recurrence)` helper + section-ordering constants.
- `SCHEDULE_ROUTE` constant in `web/lib/routes.ts`.
- `/schedule` added to `PROTECTED_PREFIXES` in `web/lib/supabase/middleware.ts`.

### Rejected alternatives

- **Rename `/work` → `/schedule` (Path A from earlier discussion).** Operator-vocabulary win, but creates a fifth nav rename in three weeks (`/agents` → `/team` → `/agents` → `/schedule`?). Churn risk too high pre-users for a vocabulary tweak.
- **Add a "Schedule" tab inside `/work`'s tabbed shell (alongside My Work / Connectors / System / Decisions).** Conflates two framings on one page; loses the "single roof for cadence-thinking" intent. The user's stated framing is "schedule as a top-level lens", which deserves a top-level destination.
- **Calendar/timeline as default V1.** Too much UX surface for an additive sibling page. List view ships in <1 day; calendar would force decisions on event-density rendering, time-zone handling, resize behavior. Phased.
- **Detail mode on `/schedule` (`/schedule?recurrence=…`).** Two detail views diverge over time. `/work` is canonical; `/schedule` defers to it.

### Cleanup items NOT in this ADR

- **ADR-231 Phase 3.8 vocabulary debt** (URL `?task=` param, `routes/tasks.py` filename, `TaskResponse` model, frontend `task` variable names). Tracked separately. Not blocking — the `/schedule` surface does not introduce new "task" references.
- **Mode-collapse on `/work` row badge** (already done — `WorkShapeBadge` shows Recurring / One-time per ADR-231).
- **Reactive cadence rendering on `/work`.** `/work` does not currently distinguish Reactive from One-time visually. Out of scope here; can be folded into an `/work` polish pass later.

## Implementation

### Phase 1 — List view (this commit)

- `cadenceCategory(recurrence)` returns `'recurring' | 'reactive' | 'one-time'` per Decision 2.
- `ScheduleListSurface` renders three sections in order: Recurring → Reactive → One-time. Empty sections elide. Empty workspace shows a "Nothing scheduled yet" empty state with a chat CTA (matches `AgentRosterSurface` empty-state pattern).
- Each row: title, cadence summary (humanized schedule string for recurring; "On-event" for reactive; "One-time" for one-time), next-run time, status dot, click → `/work?task={slug}`.
- Tab added to `ToggleBar.tsx` between Work and Agents. `SCHEDULE_ROUTE = "/schedule"` exported from `routes.ts`. `/schedule` added to `PROTECTED_PREFIXES` in middleware.

### Phase 2 — Calendar view (deferred)

- Toggle on `/schedule` between List and Calendar.
- Week/month grid showing recurrences placed at their next-run timestamps.
- Hover-card shows title + cadence summary; click → `/work?task=`.
- Triggers: alpha operator authoring 5+ recurrences AND requesting cadence-grid visualization.

## References

- ADR-167 v2: List/Detail Surfaces (list-only convention)
- ADR-212: LAYER-MAPPING correction (vocabulary discipline)
- ADR-214: Four-tab nav (becomes five with this ADR)
- ADR-231: Task Abstraction Sunset (Recurrence as canonical substrate)
- ADR-241: Single Cockpit Persona (`/work` as detail surface)
- `web/types/index.ts::recurrenceLabel()` — binary badge helper extended here to three-way `cadenceCategory()`
