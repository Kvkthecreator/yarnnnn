# Frontend Gap Report — Post-ADR-231 Substrate Migration

> **Date**: 2026-04-29
> **Scope**: All four cockpit surfaces (`/chat`, `/work`, `/agents`, `/context`) + design canon docs
> **Status**: Audit complete; gaps classified by severity. This memo answers "frontend hygiene vs frontend revamp?"

---

## Executive verdict

**Mostly hygiene + one logic break + one design-canon refresh.**

The post-3.7/3.8/3.10 frontend is structurally sound — the four-tab nav (ADR-214) is clean, the cockpit faces (ADR-228) read correct natural-home paths, the YARNNN prompt path is post-cutover (3.6.e), the `/work` URL preserves `?task=` semantics (ADR-219 D4 + ADR-231 D7 both treat declaration slug = task_slug). The major drift surfaces (`/api/tasks` URL → `/api/recurrences`, type names Task → Recurrence) shipped in commits `dd78700` + `6fb8cb6`.

**What still drifts**: a small set of concrete gaps where ADR-231 D1/D2/D6 made the substrate genuinely different from what the FE renders. These are *logic* gaps, not vocabulary gaps. Below.

---

## Gap classification

### Class A — Logic break (must fix; will break visibly post-cutover)

**A1. `/context` Reports section paths broken** ([web/app/(authenticated)/context/page.tsx:113](web/app/(authenticated)/context/page.tsx#L113))
- Code: `path: \`/tasks/${task.slug}/outputs/latest\``
- ADR-231 D2: `/tasks/{slug}/` filesystem dissolved. DELIVERABLE outputs live at `/workspace/reports/{slug}/{date}/output.md`.
- Effect: every Reports row deep-links to a path that doesn't exist in workspace_files. Click → 404.
- Fix: query the DELIVERABLE recurrence's natural-home substrate root (`/workspace/reports/{slug}/`) + show the latest dated subdir.

**A2. `/context` Reports detail handler regex** ([web/app/(authenticated)/context/page.tsx:456](web/app/(authenticated)/context/page.tsx#L456))
- Code: `if (/^\/tasks\/[^/]+\/outputs/.test(selectedNode.path))`
- Same root cause as A1 — pattern matches the dead `/tasks/{slug}/outputs/` namespace.
- Fix: regex `/^\/workspace\/reports\/[^/]+\//` (DELIVERABLE outputs) + handle ACCUMULATION via `/workspace/context/{domain}/` browser.

### Class B — Substrate-vocabulary mismatch (cosmetic; renders fine, drifts from canon)

**B1. ChatEmptyState chips push toward recurrence by default** ([web/components/chat-surface/ChatEmptyState.tsx:60-68](web/components/chat-surface/ChatEmptyState.tsx#L60))
- Current chips: `Track something recurring`, `Build a recurring report`
- ADR-231 D1: **invocation-first** is the default; recurrence is the *exception* on explicit intent.
- Effect: chips violate the architectural posture. New operators are nudged toward task scaffolding when a one-off invocation should be the default.
- Recommendation: add a "Do something now" chip (one-off seed) as the primary intent; keep "Track something recurring" + "Build a recurring report" as secondary chips. Or replace with: **"Ask for something" / "Track something" / "Build a recurring report" / "Upload a doc"** — invocation chip first.

**B2. TaskSetupModal docstring + comment refs `ManageTask(action="create")`** ([web/components/chat-surface/TaskSetupModal.tsx:11](web/components/chat-surface/TaskSetupModal.tsx#L11))
- Logic is correct (composes a chat message; YARNNN parses + dispatches; backend prompts route to `UpdateContext(target='recurrence', action='create')` post-3.6.e).
- Comment says "YARNNN calls ManageTask(action='create') in the same turn".
- Recommendation: comment refresh — "YARNNN calls UpdateContext(target='recurrence', action='create') in the same turn".

**B3. ChatSurface graduation comment refs ManageTask** ([web/components/chat-surface/ChatSurface.tsx:148](web/components/chat-surface/ChatSurface.tsx#L148))
- Comment says: "YARNNN then calls ManageTask(action='create')."
- Same as B2 — logic is correct, comment is stale.

**B4. `/api/recurrences/types` endpoint mention in client.ts comment** ([web/lib/api/client.ts:611](web/lib/api/client.ts#L611))
- Comment says the endpoint no longer exists, but uses old vocabulary.
- Already correct in spirit; cosmetic refresh worthwhile.

**B5. WorkPage breadcrumb comment ref to ADR-180** is fine; "Task" in operator-facing strings is acceptable per ADR-231 D8 (operator vocabulary may say "task" colloquially even though code says recurrence). No fix needed.

### Class C — Optional file-rename hygiene (deferred from Phase 3.10)

**C1.** `web/components/tasks/` → `web/components/recurrences/` (directory rename + import-path updates)
**C2.** `web/components/chat-surface/TaskSetupModal.tsx` → `RecurrenceSetupModal.tsx`
**C3.** `web/components/chat-surface/TaskSetup.tsx` → `RecurrenceSetup.tsx`
**C4.** `web/components/work/WorkModeBadge.tsx` → `WorkShapeBadge.tsx`
**C5.** `web/app/(authenticated)/tasks/` directory deletion (legacy alias; `/work` is canonical per ADR-180/214)

These are pure file moves with import-path updates. Zero behavior change. The vocabulary at the type/symbol/field layer is already post-cutover (Phase 3.10); only the enclosing filenames retain legacy "task" naming. No type errors result; cosmetic only.

### Class D — Design canon refresh (docs/design/SURFACE-CONTRACTS.md)

**D1. Files tab list-mode tree includes `tasks/{slug}/`** ([docs/design/SURFACE-CONTRACTS.md:75](docs/design/SURFACE-CONTRACTS.md#L75))
- Per ADR-231 D2, that directory dissolved.
- Refresh: replace with `reports/{slug}/`, `context/{domain}/_recurring.yaml`, `operations/{slug}/_action.yaml`, `_shared/back-office.yaml` per shape.

**D2. Work detail "Reads" lists `/workspace/tasks/{slug}/*`** ([docs/design/SURFACE-CONTRACTS.md:119](docs/design/SURFACE-CONTRACTS.md#L119))
- Same root cause; reads are now natural-home per shape.

**D3. Cookbook "Create Task" → `TaskSetupModal`** ([docs/design/SURFACE-CONTRACTS.md:227](docs/design/SURFACE-CONTRACTS.md#L227))
- File rename pending (C2); behavior correct.

**D4. Inline-to-task graduation refs `ManageTask(action='create')`** ([docs/design/SURFACE-CONTRACTS.md:190](docs/design/SURFACE-CONTRACTS.md#L190))
- Refresh: `UpdateContext(target='recurrence', action='create')`.

**D5. Snapshot overlay tabs reference paths** — currently `/workspace/context/_shared/MANDATE.md` etc. (correct post-ADR-206) — no fix.

**D6. Affordance cookbook "Edit | Task (DELIVERABLE, team, schedule by judgment)"** — semantics correct (Chat-shaped); vocabulary OK.

---

## Recommendation: hygiene + targeted fixes, not a revamp

**The frontend doesn't need a revamp.** The architectural posture is correct: four-tab nav, cockpit faces, kind-aware middles, narrative stream, deep-link substrate paths. What needs refresh is:

1. **Class A fixes (must)**: 2 path-regex updates in `/context/page.tsx`. ~30 LOC change. Fixes broken Reports deep-links.
2. **Class B fixes (worth doing)**: ChatEmptyState chips reorder for invocation-first per ADR-231 D1. ~15 LOC change. Plus 4 comment refreshes that take 2 minutes total.
3. **Class C (deferable)**: file/directory renames are cosmetic. Defer to a follow-on hygiene commit after the parallel ADR-233 session finishes (avoids merge churn).
4. **Class D (one commit)**: SURFACE-CONTRACTS.md refresh pass. Touches paths, primitive names, references. Pure docs commit.

Total scope: **~50 LOC code change + ~80 LOC docs refresh** in two commits. Not a revamp.

---

## What does NOT need to change

- Four-tab nav (ToggleBar) — ADR-214 clean.
- Cockpit four-face composition (`MandateFace`, `MoneyTruthFace`, `PerformanceFace`, `TrackingFace`) — ADR-228 paths are post-ADR-231 already (`_shared/MANDATE.md`, `_performance.md`, `_performance_summary.md`, `decisions.md`).
- Kind-aware middles (`DeliverableMiddle`, `TrackingEntityGrid`, `ActionMiddle`, `MaintenanceMiddle`) — `output_kind` discriminator preserved as compat alias derived from `RecurrenceShape`.
- `/work` URL `?task=` semantics — preserved per ADR-219 D4 (declaration slug = task_slug).
- Narrative stream rendering on `/chat` — ADR-219 substrate intact.
- TaskSetupModal flow — chat-message composer; YARNNN dispatches. Post-3.6.e prompts route correctly.
- "Make this recurring" graduation affordance — concept correct per ADR-219 D6 + ADR-231 D1; only the underlying primitive call vocabulary updates (handled by YARNNN's prompts, not the FE button itself).
- API client `api.recurrences.*` (commit `dd78700`).
- Type vocabulary `Recurrence`, `RecurrenceDetail`, `RecurrenceShape`, etc. (commit `6fb8cb6`).

---

## Concrete proposed commit sequence

**Commit 1 — Class A logic fix** (15 min):
- `/context/page.tsx`: replace `/tasks/${task.slug}/outputs/latest` path with natural-home reports path; update Reports node mapping; update detail-mode regex.
- Smoke: typecheck + manual click-through on /context Reports section.

**Commit 2 — Class B vocabulary refresh + chip reorder** (15 min):
- `ChatEmptyState.tsx`: reorder chips, add "Do something now" / "Ask for something" as the primary chip per ADR-231 D1 invocation-first default.
- `TaskSetupModal.tsx`: comment refresh.
- `ChatSurface.tsx`: comment refresh.
- `client.ts`: comment refresh.
- Smoke: typecheck.

**Commit 3 — Design canon refresh** (30 min):
- `docs/design/SURFACE-CONTRACTS.md` Class D refresh: Files list mode, Work reads, primitive references, cookbook entries.
- `docs/design/CHANGELOG.md` entry.

**Optional Commit 4 — Class C file renames** (defer ~1 day to avoid merge churn with ADR-233 parallel session):
- `git mv` directory + file renames; import path updates.

Total: 3 essential commits, 1 deferred. ~2 hours of focused work.

---

## Coordination with ADR-233 parallel session

Zero conflict. Class A/B/C/D all touch frontend + design docs; ADR-233 Phases 1-3 all touch backend (`api/agents/headless_prompts/`, `api/services/dispatch_helpers.py`, `api/services/invocation_dispatcher.py`). Different code clusters; standard `git pull --rebase` discipline before each commit suffices.
