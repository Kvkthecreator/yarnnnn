# ADR-265: Activity Surface Rename + Mode Discriminator on execution_events

> **Status**: **Proposed** (2026-05-11)
> **Date**: 2026-05-11
> **Authors**: KVK, Claude

---

## Context

Two issues converged in the post-ADR-263 audit:

**Issue 1 — `/backend` is operator-unfriendly naming for a forensic ledger surface.**
The page exists for legitimate work — workspace-wide structured query over every invocation attempt ("which recurrence cost the most this week?", "show me all failures in the last 24h"). But "Backend" is plumbing vocabulary. The page's actual operator job is *activity audit*, not infrastructure inspection. The label colors how operators read the surface and signals an engineer concern rather than an operator one.

**Issue 2 — The substrate behind it carries dead taxonomy from a prior architectural era.**
`execution_events.shape` (migration 165, ADR-250 Phase 2) was originally one of `deliverable | accumulation | action | maintenance` — the four-shape output_kind enum that ADR-231 and ADR-261 dissolved. Post-ADR-261, every dispatcher call site writes the constant string `shape="recurrence"` with an explicit comment "shape is no longer a discriminator" ([invocation_dispatcher.py:150-490](../../api/services/invocation_dispatcher.py)). The frontend's `shapeLabel()` mapping ([backend/page.tsx:57-65](../../web/app/(authenticated)/backend/page.tsx)) maps these constants to "Report/Tracker/Action/System" labels that have not existed as real distinctions in months — the operator sees vestigial labels grouping nothing.

Meanwhile, ADR-263 introduced the discriminator that *actually* matters now — `recurrence.mode` (`judgment | mechanical`) — which determines whether an invocation incurs LLM cost. The substrate doesn't carry it. So the operator cannot query "show me all judgment-mode runs that exceeded $0.50 today" — the analytical job that motivated /backend's existence cannot be answered cleanly by /backend's own data.

Together: the surface is misnamed *and* its substrate has stale taxonomy and a missing field for the post-263 world. Both must move together — renaming without substrate alignment ships a misnamed-and-broken page; substrate alignment without rename keeps the operator-unfriendly label.

---

## Decision

Adopt three coordinated changes in one commit set.

### D1 — `/backend` → `/activity` (operator-readable rename)

The route, page label, nav label, and route constant all rename. The user-menu placement is unchanged (already settled). The page's structural shape stays — header, job-grouped list, per-row expand-on-failure — only the name changes operator-side.

- `BACKEND_ROUTE` → `ACTIVITY_ROUTE` in `web/lib/routes.ts`
- `/backend` directory renamed to `/activity` in `web/app/(authenticated)/`
- User-menu label "Backend" → "Activity"; icon `Cpu` → `Activity` (lucide-react)
- Redirect stub at `/backend` per ADR-236 Item 5 policy (preserves any bookmarks)
- `PROTECTED_PREFIXES` adds `/activity` and retains `/backend` as a legacy redirect entry

The name "Activity" was chosen for three reasons: (a) it is the operator's actual vocabulary for "what's been happening" (non-technical, non-engineer-flavored); (b) it pairs honestly with /feed — Feed is the narrative *of activity*, /activity is the structured ledger *of activity*; (c) it sets up a coherent component naming arc for the next phase of work (per-task Recent activity panels on /work?task=foo, Feed right-rail Today's activity widget) where the shared row component renders the same data filtered differently. Alternatives "Diagnostics," "Execution log," "Run log," "History," "Ledger" were rejected as engineer-voiced, narrow, or generic.

### D2 — `execution_events.shape` dropped; `execution_events.mode` added (substrate alignment with ADR-263)

The 4-value shape enum dissolves; the 2-value mode discriminator is added.

- Migration 171: `ALTER TABLE execution_events ADD COLUMN mode text;` then backfill all historical rows to `mode='judgment'` (the pre-263 default); then `ALTER TABLE execution_events DROP COLUMN shape;`. Index `idx_execution_events_status` retained; existing indexes preserved.
- `record_execution_event()` signature: parameter `shape: str` → `mode: str`. All 9 dispatcher call sites updated to pass `recurrence.mode` instead of the literal `"recurrence"`.
- `_dispatch_mechanical` writes `mode="mechanical"`; the Reviewer-invocation path writes `mode="judgment"`.
- API `GET /api/system/execution-events` gains optional `?mode=judgment|mechanical` filter param.
- `ExecutionEvent` TypeScript type: `shape: string` → `mode: 'judgment' | 'mechanical'`.

Why drop rather than repurpose: the column was carrying dead data with no other consumer. Repurposing risks downstream drift if any future caller assumes the old enum values. A clean drop + add is one column rename in effect with explicit new semantics — singular implementation per discipline 1.

### D3 — Frontend page restructure: dead taxonomy out, mode-aware UI in

The current page already renders most of what's needed. Two structural changes:

- **Delete the `shapeLabel()` function and its callsite.** The "Report/Tracker/Action/System" label-by-shape is vestigial post-261; removed entirely. The job group header no longer shows a shape label.
- **Add mode badge per job group header.** Each job group shows "Judgment" or "Mech" inline, matching the convention from [WorkListSurface.tsx:461-475](../../web/components/work/WorkListSurface.tsx) where the same distinction is already surfaced on the /work?tab=schedule list.
- **Add mode filter chip** to the page header (All / Judgment / Mech), wired to the new API filter param.

The "Today / 7d / 30d" summary strip and additional analytical affordances are deferred to a follow-up — V1 is rename + substrate alignment + remove dead taxonomy + add mode visibility. The per-row body, expand-on-failure detail, and totals strip in the page header are unchanged.

---

## Implementation Plan

Four phases, each landing in a green state.

### Phase 1 — ADR + migration + API
- Write this ADR
- Migration 171 — `execution_events.shape` drop + `mode` add + backfill
- Update `api/services/telemetry.py::record_execution_event` signature
- Update all 9 call sites in `api/services/invocation_dispatcher.py` (pass `recurrence.mode`)
- Update `api/routes/system.py::get_execution_events` — add `mode` filter param, update `ExecutionEventRow` Pydantic model, drop `shape` from SELECT
- Update `api/routes/admin.py` references if any reference `shape` directly

### Phase 2 — Frontend rename + substrate consumption
- Rename route directory `web/app/(authenticated)/backend/` → `/activity/`
- Update `web/lib/routes.ts` — `BACKEND_ROUTE` → `ACTIVITY_ROUTE`, both exported through the migration window
- Update `web/components/shell/UserMenu.tsx` — label "Backend" → "Activity", icon `Cpu` → `Activity`, route `/backend` → `/activity`
- Update `web/lib/supabase/middleware.ts::PROTECTED_PREFIXES` — add `/activity`, keep `/backend` in legacy redirects section
- Update `web/types/index.ts::ExecutionEvent` — `shape` → `mode` field
- Update `web/lib/api/client.ts::system.executionEvents` — add `mode` to options, update comment
- Update `web/app/(authenticated)/activity/page.tsx` — delete `shapeLabel`, add mode badge per `JobCard`, add mode filter chip

### Phase 3 — Redirect stub
- Create `web/app/(authenticated)/backend/page.tsx` as a thin redirect-stub component matching `/schedule`'s pattern — `router.replace('/activity')` on mount

### Phase 4 — Docs alignment + final grep
- Update CLAUDE.md if it references `/backend` (likely no — verified)
- Update any comment in `api/routes/system.py`, `api/routes/admin.py` referencing "backend page" → "activity page"
- Final grep: zero live-code references to `BACKEND_ROUTE`, `shapeLabel`, `execution_events.shape`. The redirect stub references `/backend` route by definition; that's expected.

---

## What This Does NOT Do

- **No merger with /feed.** The activity page and the Feed remain distinct surfaces serving distinct operator jobs (structured query vs operator narrative). See the per-message discourse leading to this ADR for the full reasoning — the survivor-bias case that motivated execution_events as a separate substrate is preserved by ADR-263 mechanical-mode work having zero LLM cost (and thus minimal narrative weight), while judgment-mode work fully surfaces on /feed via ADR-219 + commit `ba40487`.
- **No new analytical features.** Time-window summary strips, charts, cost-per-mode trends, per-task drill-in — all deferred. V1 is rename + alignment + mode visibility only.
- **No changes to /work?tab=schedule.** The schedule view continues to read recurrence config; it is unaffected by this ADR.
- **No changes to the /feed activity rendering.** The MessageRow / FeedPanel components are unchanged.
- **No backfill of mechanical-mode historical data.** All pre-migration-171 rows backfill to `mode='judgment'`. This is the correct default because mechanical-mode dispatch (ADR-263, ADR-264 SyncPlatformState) postdates ADR-250's table creation by ~3 weeks; historical rows are all judgment-mode in practice.

---

## Dimensional Classification (FOUNDATIONS v6.0)

- **Substrate** (Axiom 1): `execution_events.mode` is the new substrate column; `shape` retires.
- **Channel** (Axiom 6): /activity replaces /backend as the operator-readable channel for forensic activity audit. Per Derived Principle 12, the rename improves channel legibility for the non-technical ICP operator.
- **Mechanism** (Axiom 5): The dispatcher's telemetry write remains at the deterministic end of the spectrum. No mechanism change.

---

## Supersedes / Amends

- **Amends ADR-250**: `execution_events` schema gains `mode`, loses `shape`. Cost formula, spend guard, write discipline, Sentry wiring all preserved.
- **Closes audit finding from ADR-263 follow-on**: the stale `shape="recurrence"` dispatcher constant identified during the May 11 audit pass is resolved by D2.
- **Supersedes nothing structurally**: /backend was never ADR-ratified as a named surface — it was implementation incidental to ADR-250 Phase 4 (admin dashboard).

---

## Canonical Reference

Subsequent activity-related work (right-panel components on /feed, Recent activity panel on /work?task={slug}) builds on the `<ActivityRow>` component extracted in Phase 2 of this ADR. The discipline: one row renderer, three placement surfaces, scoped via filter props.
