# ADR-231 Phase 3 Atomic Cutover — Development Sequence Plan (Full-Rename Edition)

> **Date**: 2026-04-29
> **Branch state at planning time**: main @ `01828ae` (Phase 1 + 2 + 3.1 complete)
> **Scope**: Phase 3 (the heavy cutover) + Phase 4 (frontend) + Phase 5 (docs) per ADR-231 §Implementation Phases
> **Discipline (locked)**: Singular Implementation rule 1 — full rename, not URL-stability shims. Every commit lands green. The cutover commit deletes legacy paths same-commit as new paths. No backwards-compat aliases. The vocabulary on disk and over the wire matches the architectural model.

---

## Why "full rename" matters here

The earlier draft of this plan suggested keeping `/api/tasks` URL externally for "bookmark stability" while renaming internally. **That was a backwards-compat shim in disguise.** Singular Implementation rule 1 forbids it. A frontend that calls `/api/tasks` while the backend dispatches against `recurrence_declaration` is the same coherence violation the rule exists to prevent — vocabulary drift between layers manifests as drift in the operator's mental model.

Bookmark stability is an Era 1 concern for an alpha-stage product with no public-API consumers. There are no third-party clients. The frontend, the MCP server, and operational scripts are the only callers; all are in this repo and all migrate in lockstep. Frontend bookmarks of `/work` (the user-facing route) survive — the `/api/*` surface is internal plumbing.

So the rule for this cutover: **every name on disk, every URL on the wire, every type in TypeScript, every Python symbol matches the architectural model post-cutover**. Old names disappear. No aliases. No "internal-only" rename hedges.

---

## The vocabulary (locked before any code lands)

| Architectural concept | Backend symbol | Frontend symbol | URL path | Filesystem |
|---|---|---|---|---|
| Recurrence declaration (the YAML legibility wrapper) | `RecurrenceDeclaration` | `Recurrence` (type), `RecurrenceDetail` | `/api/recurrences` | `_recurring.yaml`, `_spec.yaml`, `_action.yaml`, `back-office.yaml` |
| Recurrence shape | `RecurrenceShape` enum | `RecurrenceShape` type-literal union | (query param `shape=`) | path-implied |
| One firing | "invocation" (Axiom 9 atom) | "invocation" | (no surface — narrative entry is the surface) | narrative entry |
| Manual fire | `FireInvocation` primitive | `api.recurrences.fire(slug)` | `POST /api/recurrences/{slug}/fire` | — |
| Output | "output" (per recurrence) | "output" | `/api/recurrences/{slug}/outputs/...` | `/workspace/reports/{slug}/{date}/output.md` etc. |
| User-facing surface | — | `/work` route | `/work` | — |

**Banned post-cutover** (must grep clean except in ADR markdown history):
- `task_pipeline`, `TaskWorkspace`, `task_types`, `TASK_TYPES`, `task_derivation`, `ManageTask`, `task_md`, `parse_task_md`, `output_kind`, `task_class`, `essential` (DB column), `mode` (on `tasks` table), `task_slug` (variable name in dispatch path)
- Frontend `Task`, `TaskDetail`, `TaskOutput`, `TaskMode`, `TaskModeLabel`, `TaskCreate`, `TaskType`, `TaskTypesResponse`, `taskModeLabel`, `useAgentsAndTasks`, `useTaskDetail`, `useTaskOutputs`
- URL `/api/tasks/*`
- Frontend route `/tasks` (note: `/work` survives; `/tasks` route directory is deleted in 3.8)

**Survives** (these are different concepts — not subject to rename):
- `tasks` DB table (it's the **scheduling index**, not the work substrate; ADR-231 D4 Path B locked this name as the index identifier). Internal docstring + table COMMENT call this out so future readers understand why the table name doesn't follow the rename.
- `narrative` entries — already the canonical Axiom 9 vocabulary.
- `agents`, `agent_runs`, `workspace_files`, `workspace_blobs`, `workspace_file_versions` — outside ADR-231 scope.

---

## Architectural reality check (informs sequencing)

Three audit findings shape the sequence:

1. **The `tasks` table is already thin.** Real columns: `id, user_id, slug, status, schedule, next_run_at, last_run_at, created_at, updated_at, mode, essential`. ADR-231 D4's "drop heavy columns" is just `mode` + `essential` + add `declaration_path` + `paused`. Migration 164 is small.

2. **The dispatcher boundary is already abstract.** Phase 2 made `invocation_dispatcher.dispatch(decl)` the call site. The Phase 3.2 body rewrite is opaque to callers — same external contract, new internals. This decouples 3.2 (dispatcher rewrite) from 3.6 (caller migration).

3. **`task_pipeline.execute_task` is mechanical work, ~70% of which ports verbatim.** Mandate gate, capability gate, context gather, Sonnet generation, section parsing, compose call, delivery, narrative emission, token accounting — all survive. What dies: the `tasks`-row read prefix, `TaskWorkspace` slug-rooted I/O, `parse_task_md`, the 9-action `ManageTask` surface. The dispatcher rewrite is **substrate substitution**, not a rebuild.

---

## Frontend rename audit (full scope)

Concrete files affected by the full rename in Phase 3.8 — exhaustively enumerated to avoid scope-creep mid-cutover.

**Type renames** ([web/types/index.ts](web/types/index.ts)):
- `Task` → `Recurrence`
- `TaskDetail` → `RecurrenceDetail`
- `TaskOutput` → `RecurrenceOutput`
- `TaskMode` → DELETED (replaced by `RecurrenceShape` literal union)
- `TaskModeLabel` → DELETED (label derives from shape, not mode)
- `taskModeLabel()` → DELETED (replaced by `recurrenceShapeLabel()`)
- `TaskCreate` → DELETED (creation is `UpdateContext(target="recurrence")`, no separate type)
- `TaskType` / `TaskTypesResponse` → DELETED (registry already dissolved per ADR-207 P4b; types finish dying here)
- `TaskStatus` → `RecurrenceStatus`
- `TaskSectionEntry` → `RecurrenceSectionEntry`

**API client** ([web/lib/api/client.ts](web/lib/api/client.ts)):
- `api.tasks.*` namespace → `api.recurrences.*`
- All `/api/tasks/*` URLs → `/api/recurrences/*`

**Hooks**:
- [web/hooks/useAgentsAndTasks.ts](web/hooks/useAgentsAndTasks.ts) → `useAgentsAndRecurrences.ts`
- [web/hooks/useTaskDetail.ts](web/hooks/useTaskDetail.ts) → `useRecurrenceDetail.ts`
- [web/hooks/useTaskOutputs.ts](web/hooks/useTaskOutputs.ts) → `useRecurrenceOutputs.ts`

**Components** (rename + content reshape):
- [web/components/tasks/](web/components/tasks/) directory → `web/components/recurrences/`
  - `ProcessTab.tsx` → `ProcessTab.tsx` (renamed inside, internals rewritten — see 3.8 substantive changes)
  - `TaskTreeNav.tsx` → `RecurrenceTreeNav.tsx`
  - `TaskContentView.tsx` → `RecurrenceContentView.tsx`
- [web/components/chat-surface/TaskSetupModal.tsx](web/components/chat-surface/TaskSetupModal.tsx) → `RecurrenceSetupModal.tsx`
- [web/components/chat-surface/TaskSetup.tsx](web/components/chat-surface/TaskSetup.tsx) → `RecurrenceSetup.tsx`
- [web/components/work/WorkModeBadge.tsx](web/components/work/WorkModeBadge.tsx) → `WorkShapeBadge.tsx` (ADR-231 D8: shape, not mode)
- [web/components/work/WorkListSurface.tsx](web/components/work/WorkListSurface.tsx) → keeps name; internal `taskModeLabel` → `recurrenceShapeLabel`
- [web/components/work/details/ActionMiddle.tsx](web/components/work/details/ActionMiddle.tsx) — comment update for `api.recurrences.listOutputs` reference
- [web/components/work/details/PlatformSourcesSection.tsx](web/components/work/details/PlatformSourcesSection.tsx) — `api.tasks.updateSources` → `api.recurrences.updateSources`

**Pages**:
- [web/app/(authenticated)/tasks/](web/app/(authenticated)/tasks/) directory → DELETED. The `/tasks` route was a legacy alias; `/work` is canonical per ADR-167 v2 + ADR-180. Frontend bookmarks of `/tasks` get a 404 (acceptable — no public consumers; alpha-stage; the surface is `/work`).
- [web/app/(authenticated)/work/page.tsx](web/app/(authenticated)/work/page.tsx) — internals: `api.tasks.run/update` → `api.recurrences.fire/update`.
- [web/app/(authenticated)/context/page.tsx](web/app/(authenticated)/context/page.tsx) — `api.tasks.list` → `api.recurrences.list`.
- [web/app/(authenticated)/settings/system/page.tsx](web/app/(authenticated)/settings/system/page.tsx) — `api.tasks.list/update` → `api.recurrences.list/update`. Comment about `GET /api/tasks` filtering rewrites to `/api/recurrences`.

**Lib**:
- [web/lib/task-types.ts](web/lib/task-types.ts) → DELETED. Task type registry already dissolved per ADR-207 P4b; this file was scaffolding for Edge Cases that no longer exist.

**Routes that survive named the same**:
- `/work` (URL + route directory) — operator-facing, ADR-180/214 canonical.

---

## Sub-phase ordering principle

Each commit lands green. No commit leaves the build in a half-state. The vocabulary lock above means **no commit is permitted to introduce both old + new names simultaneously** — when a name flips, it flips fully in that commit. The exceptions:

- **3.2** introduces `_dispatch_*` private functions in `invocation_dispatcher.py` while `task_pipeline.execute_task` still exists. This is acceptable because the *external* contract is `dispatch(decl)`, which already shipped in Phase 2. Internal helpers are not part of the vocabulary surface.
- **3.6** clusters caller migrations by importer. Each commit migrates one cluster fully. Inside a cluster, no callers remain on the old API mid-commit.
- **3.7** is a single atomic deletion. It is the moment the legacy module names disappear.
- **3.8** is a single atomic frontend rename (potentially split into 2 commits: (a) backend route rename + API client rename, (b) component/hook/page rename). Each lands green. **No alias retention.**

---

## Phase 3.2 — Dispatcher Body Rewrite (YAML-native pipeline)

**Goal**: `invocation_dispatcher.dispatch(decl)` is the canonical execution path. Reads the recurrence YAML directly. Writes to natural-home substrate. Delegates compose / delivery / token accounting to existing services. No `tasks` table read at this layer.

**LOC**: ~600 added (`invocation_dispatcher.py` body) + ~50 helper extractions from `task_pipeline.py` ported into the dispatcher (or into `services/scheduling.py` if cron-related). `task_pipeline.execute_task` STILL EXISTS at this commit but is no longer called by `FireInvocation` / scheduler — it survives only for not-yet-migrated callers (3.6). Its deletion lands in 3.7.

**What gets absorbed from `task_pipeline.py`**:

| Pipeline step | Destination |
|---|---|
| Mandate gate (ADR-207) | `_dispatch_generative` precondition |
| Capability gate (ADR-207 P3) | `_dispatch_generative` precondition |
| Context-domain gather (`_gather_context_domains`) | port wholesale to `_gather_recurrence_context` (declaration-driven, not slug-driven) |
| Pre-gather (ADR-182 prior-output / inventory) | port to `_gather_recurrence_context` |
| Sonnet generation (`_generate`) | port wholesale; signature unchanged (takes prompt + tool surface) |
| Section parsing | reuse `compose/sections.parse_draft_into_sections` (already in compose/) |
| Persist sections + manifest (`_persist_sections_and_manifest`) | port to `_persist_recurrence_output` (output path computed from `decl.output_path` + `{date}`, not slug) |
| Compose HTML (`compose/task_html.compose_task_output_html`) | reuse, pass natural-home path |
| Delivery (`services.delivery.deliver_from_output_folder`) | reuse, pass natural-home path |
| Token accounting | reuse existing `token_usage` write path |
| Narrative emission (ADR-219) | reuse `services.narrative.write_narrative_entry` |
| Daily-update empty-state (ADR-161) | inline special-case keyed on `decl.slug == "daily-update"` |
| Maintain-overview empty-state (ADR-204) | inline special-case |
| Outcome reconciliation (ADR-195) | becomes `_dispatch_maintenance` reading `executor:` from YAML |

**What dies at the dispatcher boundary** (not at the codebase level — yet):

| Step | Reason |
|---|---|
| `tasks` row read at step 0–1 | Replaced by `decl` parameter |
| `TaskWorkspace` slug-rooted I/O | Replaced by natural-home paths from `decl` |
| `parse_task_md` call | Replaced by parsed YAML on `decl.data` |
| `tasks.next_run_at` sentinel write at step 0 | Moves to `services/scheduling.py` in Phase 3.3 |
| `tasks.last_run_at` write at end | Moves to scheduler post-dispatch in 3.3 |

**Dispatch branches**:

```python
async def dispatch(client, user_id, decl, *, context=None) -> dict:
    if decl.shape == RecurrenceShape.MAINTENANCE:
        return await _dispatch_maintenance(client, user_id, decl)
    if decl.shape == RecurrenceShape.ACTION:
        return await _dispatch_action(client, user_id, decl, context=context)
    return await _dispatch_generative(client, user_id, decl, context=context)
```

`_dispatch_generative` covers DELIVERABLE + ACCUMULATION (~400 LOC); empty-state branches as inline keyed cases.
`_dispatch_maintenance` reads `decl.executor`, calls dotted Python path (~30 LOC).
`_dispatch_action` writes to platform via `target_capability` (~80 LOC).

**Test gate**:
- Extend [api/test_adr231_recurrence.py](api/test_adr231_recurrence.py): 4 dispatch tests (one per shape) asserting declaration read → natural-home write → narrative emit. Mock-based.
- Manual smoke: kvk's alpha-trader-2 workspace — fire one DELIVERABLE + one ACCUMULATION + one ACTION declaration via `FireInvocation` and verify outputs land at natural homes.

**Risk**: Med. Largest single-commit work. Mitigated by ~70% verbatim porting from `task_pipeline.py`.

**Commit**: `feat(adr-231): Phase 3.2 — invocation_dispatcher YAML-native body (replaces task_pipeline as canonical path)`

---

## Phase 3.3 — Scheduler Migration (walks recurrence YAMLs)

**Goal**: `unified_scheduler.py` queries the filesystem for due declarations via the thin `tasks` index, not via slug-keyed `tasks` rows. Scheduler is the sole writer of `tasks.next_run_at` / `last_run_at`.

**LOC**: ~100 net delete (510 → ~250) + ~80 added (new `services/scheduling.py`).

**Concrete changes**:

1. **New `services/scheduling.py`** (clear ownership documented in module docstring per discipline rule 10):
   - `compute_next_run_at(decl, last_run_at, now) -> datetime` — `croniter` against `decl.schedule`.
   - `materialize_scheduling_index(client, user_id) -> int` — walks declarations via `walk_workspace_recurrences`; upserts thin `tasks` row `(user_id, slug, declaration_path, schedule, next_run_at, last_run_at, paused, status)`. Idempotent. Hooked from every `UpdateContext(target="recurrence")` write + every scheduler tick (defensive).
   - `get_due_declarations(client, now) -> list[(user_id, RecurrenceDeclaration)]` — query `tasks` for due rows, then re-parse YAML from filesystem (table is the index; YAML is truth).

2. **`unified_scheduler.py` rewrite**:
   - `get_due_tasks` → `get_due_declarations`.
   - `execute_due_tasks` body: `await invocation_dispatcher.dispatch(decl)`.
   - CAS atomic claim on `tasks.next_run_at` preserved (right primitive regardless of row contents).
   - Post-dispatch: `compute_next_run_at` + write `tasks.last_run_at` + `tasks.next_run_at`.

3. **`UpdateContext(target="recurrence")` hooks** `materialize_scheduling_index` post-write so the index stays fresh without operator intervention. Index reconstruction-from-filesystem is always available.

**Test gate**:
- Extend [api/test_adr231_recurrence.py](api/test_adr231_recurrence.py): `test_scheduling_index_materialization`, `test_get_due_declarations_filters_paused`, `test_compute_next_run_at_with_croniter`.
- Smoke: kvk's market-scan declaration fires after a YAML edit through the new scheduler path.

**Risk**: Low-Med.

**Commit**: `feat(adr-231): Phase 3.3 — scheduler walks recurrence declarations (tasks table is thin index)`

---

## Phase 3.4 — DB Migration 164 (thin tasks scheduling index)

**Goal**: Schema reflects the post-cutover `tasks` table as the **scheduling index** per ADR-231 D4 Path B. The table name survives because it identifies *the index*, not the work substrate. Migration adds a COMMENT making this explicit so future readers see the intent.

**Migration 164** ([supabase/migrations/164_adr231_thin_tasks_index.sql](supabase/migrations/164_adr231_thin_tasks_index.sql)):

```sql
-- ADR-231 D4 Path B: tasks table becomes the thin scheduling index.
-- Authoritative recurrence-declaration substrate is workspace_files YAML
-- at declaration_path. This table is fully reconstructable from filesystem
-- via services.scheduling.materialize_scheduling_index().
--
-- Naming note: the table identifier "tasks" is preserved as the index
-- identifier (per ADR-231 D4 Path B). The COMMENT makes this explicit
-- so the name doesn't suggest task-as-substrate (which dissolved per D2).

-- Step 1: drop dissolved columns
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_mode_check;
ALTER TABLE tasks DROP COLUMN IF EXISTS mode;
ALTER TABLE tasks DROP COLUMN IF EXISTS essential;

-- Step 2: add declaration_path — pointer to authoritative YAML
ALTER TABLE tasks ADD COLUMN declaration_path TEXT;
CREATE INDEX idx_tasks_declaration_path ON tasks (declaration_path);

-- Step 3: explicit paused flag (was implicit via status='paused')
ALTER TABLE tasks ADD COLUMN paused BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE tasks SET paused = TRUE WHERE status = 'paused';

-- Step 4: simplify status enum (paused is no longer a status; it's a flag)
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_status_check;
ALTER TABLE tasks ADD CONSTRAINT tasks_status_check CHECK (
  status IN ('active', 'completed', 'archived')
);
UPDATE tasks SET status = 'active' WHERE status = 'paused';

-- Step 5: refresh next_run_at index incorporating paused gate
DROP INDEX IF EXISTS idx_tasks_next_run;
CREATE INDEX idx_tasks_next_run
  ON tasks (next_run_at)
  WHERE status = 'active' AND paused = FALSE;

COMMENT ON TABLE tasks IS
  'ADR-231 D4 Path B thin scheduling index. Authoritative recurrence-'
  'declaration substrate is workspace_files YAML at declaration_path. '
  'This table is materialized from filesystem state and is fully '
  'reconstructable via services.scheduling.materialize_scheduling_index(). '
  'The table name "tasks" identifies the SCHEDULING INDEX, not work substrate '
  '(which dissolved per ADR-231 D2). See ADR-231 §D4 for the rationale on '
  'preserving this identifier.';

COMMENT ON COLUMN tasks.declaration_path IS
  'Workspace path to the authoritative YAML recurrence declaration. '
  'See services.recurrence.RecurrenceDeclaration for the substrate model.';
```

**Sequence with 3.5**: 3.5 (the data migration script) lands as a code-only commit *before* this migration runs. Then this migration runs against staging + production. The script is then *executed* against each workspace as an operational step, populating `declaration_path` and clearing `/tasks/{slug}/TASK.md`.

**Update [docs/database/ACCESS.md](docs/database/ACCESS.md)** in the same commit per discipline rule 4: add migration 164 entry; update tasks-table column list reflecting post-migration state.

**Test gate**:
- Migration runs cleanly on staging.
- New `api/test_adr231_thin_index.py`: assert post-migration `tasks` row carries `declaration_path` for every active row; `mode` + `essential` gone.

**Risk**: Low.

**Commit**: `feat(adr-231): Phase 3.4 — migration 164 thin tasks scheduling index + ACCESS.md sync`

---

## Phase 3.5 — Data Migration Script (TASK.md → YAML at natural homes)

**Goal**: All existing `tasks` rows + their `/tasks/{slug}/TASK.md` files migrate to YAML declarations at natural-home locations. Idempotent. Reversible via ADR-209 revision history.

**Script**: [api/scripts/migrate_to_recurrence_declarations.py](api/scripts/migrate_to_recurrence_declarations.py) (~250 LOC, named to match the new vocabulary).

**Flow per task row**:
1. Read row → derive `(slug, schedule, status, mode, essential)`.
2. Read `/tasks/{slug}/TASK.md` via the (still-existing-at-this-phase) `TaskWorkspace.read_task()`.
3. Parse via `task_pipeline.parse_task_md()` — last legitimate use; the parser dies in 3.7.
4. Determine shape from `**Output:**` field:
   - `produces_deliverable` → DELIVERABLE
   - `accumulates_context` → ACCUMULATION
   - `external_action` → ACTION
   - `system_maintenance` → MAINTENANCE
5. Build YAML at natural-home path per `derive_declaration_path()`. Append-or-create semantics for multi-decl files (ACCUMULATION + MAINTENANCE).
6. Write via `services.authored_substrate.write_revision` with `authored_by="system:adr-231-migration"` and message describing the migration.
7. Update `tasks` row: `declaration_path = <new YAML path>`.
8. Migrate output substrate: copy `/tasks/{slug}/outputs/` to `/workspace/reports/{slug}/` (or domain location for ACCUMULATION). ADR-209 revisions for every move. Source path archived (final revision marking migrated; row deleted from `workspace_files`).
9. `TASK.md` + `DELIVERABLE.md` + `memory/*.md` archived via final ADR-209 revision then deleted from `workspace_files`.

**Idempotency**: Check for existing declaration at target path before writing. Re-runs safe.

**Reversibility**: Every write is an ADR-209 revision; rollback is a `write_revision` to prior content.

**Operational sequence** (script lives in repo at this phase; not yet run):
- Phase 3.5 commit lands the script.
- Phase 3.4 commit lands the migration.
- After 3.4 deploys, run script in dry-run against kvk's workspace + alpha-trader-2 + alpha-commerce. Eyeball.
- Run live against the same workspaces. Verify.
- Phase 3.6 begins.

**Test gate**:
- New `api/test_adr231_data_migration.py`: synthetic workspace with one task per shape; run script; assert YAML at correct natural-home path; assert `tasks.declaration_path` populated; assert ADR-209 revisions recorded; assert legacy paths deleted.

**Risk**: Med. Operator data touched. Mitigated by ADR-209 reversibility + dry-run flag + idempotency.

**Commit**: `feat(adr-231): Phase 3.5 — data migration script (TASK.md → recurrence YAML at natural homes)`

---

## Phase 3.6 — Caller Migrations (~30 production files)

**Goal**: Every caller of `task_pipeline.execute_task` / `ManageTask` / `task_workspace` / `task_types` / `task_derivation` routes through `invocation_dispatcher.dispatch(decl)` / `UpdateContext(target="recurrence")` / `walk_workspace_recurrences` / `services.scheduling`.

Per Singular Implementation: **inside each cluster commit, no caller in that cluster remains on the old API mid-commit.** The cluster either fully migrates or doesn't ship.

### 3.6.a — Backend route layer (4 commits)

| Commit | Files | Net change |
|---|---|---|
| 3.6.a.1 | `api/routes/tasks.py` | Internals rewritten to read declarations + call dispatcher. **Filename stays as `tasks.py` until 3.8 backend rename**, when it moves to `recurrences.py`. (3.6 is internals-only; 3.8 is the surface rename.) ~600 LOC rewrite. |
| 3.6.a.2 | `api/routes/admin.py`, `api/routes/agents.py` | Replace `execute_task(slug)` with `dispatch(decl)`. Resolve declaration from slug via walker. ~50 LOC. |
| 3.6.a.3 | `api/routes/chat.py`, `api/routes/workspace.py`, `api/routes/system.py`, `api/routes/account.py`, `api/routes/integrations.py` | Replace `tasks` table reads + `task_workspace` reads with declaration walker. ~80 LOC. |
| 3.6.a.4 | `api/mcp_server/server.py` | Replace `tasks` table queries with declaration walker. ~30 LOC. |

### 3.6.b — Service layer (4 commits)

| Commit | Files | Net change |
|---|---|---|
| 3.6.b.1 | `api/services/trigger_dispatch.py` | `task_pipeline.execute_task` → `invocation_dispatcher.dispatch`. ~10 LOC. |
| 3.6.b.2 | `api/services/delivery.py`, `api/services/compose/task_html.py`, `api/services/compose/assembly.py`, `api/services/feedback_distillation.py`, `api/services/outcomes/high_impact.py` | `TaskWorkspace` slug-rooted reads → declaration-derived natural-home reads. ~120 LOC. |
| 3.6.b.3 | `api/services/agent_creation.py`, `api/services/workspace_init.py` | `task_types` registry calls → YAML declaration writes via `UpdateContext(target="recurrence")`. ~80 LOC. |
| 3.6.b.4 | `api/services/working_memory.py`, `api/services/mcp_composition.py`, `api/services/task_deliverable_inference.py`, `api/services/primitives/repurpose.py`, `api/services/primitives/update_context.py` (cleanup) | `tasks` table reads + `task_types` lookups → declaration walker / direct YAML reads. ~100 LOC. |

### 3.6.c — Scripts (1 commit)

| Commit | Files | Net change |
|---|---|---|
| 3.6.c.1 | `api/scripts/alpha_ops/{backfill_required_capabilities,verify}.py`, `api/scripts/alpha_ops/activate_persona.py` | TASK.md authorship + `tasks` row writes → YAML declaration writes. ~60 LOC. |

**Test gate after each cluster**: existing tests pass; no test imports legacy modules within migrated cluster.

**Test gate after 3.6 fully complete**: zero call sites of legacy task modules outside `task_pipeline.py` itself (which still exists, calls itself recursively or sits cold). The grep gate in 3.7 confirms.

**Risk**: Med. Many small commits; each isolated; each green.

**Commit messages**: `refactor(adr-231): Phase 3.6.<N> — migrate <cluster> to invocation_dispatcher / walk_workspace_recurrences`

---

## Phase 3.7 — Atomic Legacy Deletion

**Goal**: Single commit. ~9,800 LOC across 5 files goes. Singular Implementation rule 1 honored at the file level.

**Files deleted in this single commit**:

| File | LOC | Reason |
|---|---|---|
| `api/services/task_pipeline.py` | 4,204 | Dispatcher absorbed survivors in 3.2. |
| `api/services/primitives/manage_task.py` | 1,498 | `FireInvocation` + `UpdateContext(target="recurrence")` replaced. |
| `api/services/task_workspace.py` | 319 | Natural-home paths replaced slug-rooted I/O. |
| `api/services/task_types.py` | 1,836 | ADR-207 P4b dissolved registry authority; this finishes the deletion. |
| `api/services/task_derivation.py` | 334 | Replaced by walker-based derivation in 3.6.b.4. |

**Same-commit updates**:
- `api/services/primitives/registry.py`: remove `ManageTask` registration. Verify `FireInvocation` + `UpdateContext` are the only recurrence-related primitives.
- `api/main.py`: remove any explicit imports of deleted modules (none expected post-3.6 but safety check).
- Any test imports of deleted modules removed (zero expected post-3.6).

**Final grep gate (in-commit, must return clean)**:

```bash
# Backend code:
grep -rn "from services.task_pipeline\|services\.task_pipeline\b" api/ --include="*.py" | grep -v "docs/adr"
grep -rn "from services.primitives.manage_task\|\bManageTask\b" api/ --include="*.py"
grep -rn "from services.task_workspace\|\bTaskWorkspace\b" api/ --include="*.py"
grep -rn "from services.task_types\|\bTASK_TYPES\b" api/ --include="*.py"
grep -rn "from services.task_derivation\|task_derivation" api/ --include="*.py"
grep -rn "parse_task_md\|build_task_md\|task_md_content" api/ --include="*.py"

# Symbol references in dispatch path (these flag pre-migration variable shapes):
grep -rn "task_slug" api/services/invocation_dispatcher.py api/services/scheduling.py
```

All return clean. The naming surface in dispatch code uses `decl.slug` / `decl.declaration_path` / `decl.shape` — never `task_slug`.

**Test gate**: `pytest api/` clean. Backend boots clean.

**Risk**: Low if 3.6 thorough. Grep gate is the safety net.

**Commit**: `refactor(adr-231): Phase 3.7 — atomic legacy deletion (~9,800 LOC, task abstraction sunset complete)`

---

## Phase 3.8 — Frontend Full Rename + Surface Reshape

**Goal**: Frontend vocabulary fully matches the architectural model. `/api/tasks` → `/api/recurrences`. `Task` → `Recurrence`. `TaskMode` → DELETED (replaced by `RecurrenceShape`). `/work` surface reshapes to recurrence-list + filter-over-narrative per ADR-231 D7. **No alias retention; no URL preservation; full rename.**

This is the largest single user-visible commit window. Strategy: **two commits**, each green, each atomic for its scope.

### 3.8.a — Backend route rename + API client rename

**Backend**:
- Rename `api/routes/tasks.py` → `api/routes/recurrences.py`.
- Rename internal symbols: `list_tasks` → `list_recurrences`, `get_task` → `get_recurrence`, `create_task` → DELETED (creation routes via `UpdateContext`), `update_task` → `update_recurrence`, `archive_task` → `archive_recurrence`, `trigger_task_run` → `fire_recurrence`, `list_task_outputs` → `list_recurrence_outputs`, `export_task_output` → `export_recurrence_output`, etc.
- `api/main.py`: `from routes import ... tasks ...` → `... recurrences ...`; `app.include_router(tasks.router, prefix="/api/tasks")` → `app.include_router(recurrences.router, prefix="/api/recurrences")`.
- Pydantic response models renamed (`TaskResponse` → `RecurrenceResponse`, etc.).

**Frontend API client**:
- [web/lib/api/client.ts](web/lib/api/client.ts): `api.tasks.*` namespace → `api.recurrences.*`. All URLs `/api/tasks/*` → `/api/recurrences/*`. Type imports updated.
- [web/types/index.ts](web/types/index.ts): full type rename per vocabulary table above. Old types removed (no aliases).

**Test gate**: Backend boots; frontend builds; manual smoke against `/work` (which now calls `/api/recurrences/*` end-to-end).

**Commit**: `refactor(adr-231): Phase 3.8.a — full rename /api/tasks → /api/recurrences (backend routes + frontend API client)`

### 3.8.b — Frontend hooks/components/pages rename + /work surface reshape

**Hooks**:
- `useAgentsAndTasks` → `useAgentsAndRecurrences`
- `useTaskDetail` → `useRecurrenceDetail`
- `useTaskOutputs` → `useRecurrenceOutputs`
- All call sites updated.

**Components**:
- Rename `web/components/tasks/` → `web/components/recurrences/`.
- `TaskTreeNav` → `RecurrenceTreeNav`. `TaskContentView` → `RecurrenceContentView`.
- `web/components/chat-surface/TaskSetupModal.tsx` → `RecurrenceSetupModal.tsx`. `TaskSetup.tsx` → `RecurrenceSetup.tsx`.
- `web/components/work/WorkModeBadge.tsx` → `WorkShapeBadge.tsx`; internals reshape to `RecurrenceShape` not `TaskMode`.
- `web/components/work/details/{Action,Deliverable,Tracking,Maintenance}Middle.tsx` — internal references updated.

**Pages**:
- DELETE `web/app/(authenticated)/tasks/` directory (legacy alias; `/work` is canonical per ADR-180/214). The frontend route `/tasks` returns 404.
- `web/app/(authenticated)/work/page.tsx` reshapes to recurrence-list + filter-over-narrative per ADR-231 D7.
- `web/app/(authenticated)/context/page.tsx` + `/settings/system/page.tsx` — call site updates.

**Lib**:
- DELETE `web/lib/task-types.ts` (registry already dissolved per ADR-207 P4b).

**Final frontend grep gate (in-commit, must return clean except for ADR markdown)**:

```bash
# These must return clean across web/ excluding node_modules:
grep -rn "\bTaskMode\b\|\btaskModeLabel\b" web/ --include="*.ts" --include="*.tsx" | grep -v node_modules
grep -rn "\bTaskDetail\b\|\bTaskOutput\b\|\bTaskCreate\b" web/ --include="*.ts" --include="*.tsx" | grep -v node_modules
grep -rn "/api/tasks" web/ --include="*.ts" --include="*.tsx" | grep -v node_modules
grep -rn "api\.tasks\." web/ --include="*.ts" --include="*.tsx" | grep -v node_modules
grep -rn "useTaskDetail\|useTaskOutputs\|useAgentsAndTasks" web/ --include="*.ts" --include="*.tsx" | grep -v node_modules
```

**Risk**: Med. Wide churn across 20+ files. Mitigated by clear vocabulary table + grep gate in-commit.

**Commit**: `refactor(adr-231): Phase 3.8.b — full rename Task → Recurrence (frontend types/hooks/components/pages) + /work reshape`

---

## Phase 3.9 — Documentation Sync + Final Grep Gate

**Goal**: Documentation reflects post-ADR-231 reality. Grep gate confirms no live doc still references deleted symbols.

**Doc updates**:

- [CLAUDE.md](CLAUDE.md): File Locations table — remove `task_pipeline` / `task_types` / `manage_task` / `task_workspace` / `task_derivation` rows; add `invocation_dispatcher` / `recurrence` / `scheduling` / `FireInvocation`. Schema section — update `tasks` table description to match migration 164 COMMENT. Common Pitfalls — refresh post-rename.
- [docs/architecture/FOUNDATIONS.md](docs/architecture/FOUNDATIONS.md): Axiom 9 status flips to **Implemented**.
- [docs/architecture/GLOSSARY.md](docs/architecture/GLOSSARY.md): "task" gets a `(legibility wrapper, not substrate)` gloss; "recurrence declaration" added as canonical term.
- [docs/architecture/SERVICE-MODEL.md](docs/architecture/SERVICE-MODEL.md): execution-loop frame points at `invocation_dispatcher` not `task_pipeline`.
- [docs/architecture/primitives-matrix.md](docs/architecture/primitives-matrix.md): `ManageTask` row deleted; `FireInvocation` row added; `UpdateContext` widened-targets row updated.
- [docs/architecture/invocation-and-narrative.md](docs/architecture/invocation-and-narrative.md): implementation-finished status added.
- [docs/database/ACCESS.md](docs/database/ACCESS.md): tasks table description matches migration 164 reality (already updated in 3.4 — confirm).
- [api/prompts/CHANGELOG.md](api/prompts/CHANGELOG.md): closing entry summarizing the prompt evolution end-to-end (Phase 1 entry already landed; this is the closer).

**ADR amendment banners**:
- ADR-138: amended-by ADR-231; tasks-as-units framing dissolved per D-summary.
- ADR-149: amended-by ADR-231; lifecycle dissolved into substrate ops per D5.
- ADR-161: superseded-by ADR-231; daily-update reframed per D6.
- ADR-166: amended-by ADR-231; output_kind enum dissolved per D2.
- ADR-167 v2: amended-by ADR-231; /work data source per D7.
- ADR-207: amended-by ADR-231; TASK_TYPES sunset finished per D5.
- ADR-219: implementation-finished-by ADR-231.

**Final grep gate**:

```bash
# Active docs (excluding ADR markdown which preserves history):
grep -rn "task_pipeline\|ManageTask\|TaskWorkspace\|TASK_TYPES\|task_derivation" docs/ \
  --exclude-dir=adr \
  | grep -v "Superseded\|Amended\|Was:\|history\|deprecated"
```

Must return clean. ADR markdown preserves historical references (that's its purpose).

**Test gate**: `pytest api/` green; frontend builds; backend boots.

**Risk**: Low.

**Commit**: `docs(adr-231): Phase 3.9 — implementation status flip + ADR amendment banners + final grep gate`

---

## Aggregate sequence

| Phase | Title | Commits | LOC delta | Risk |
|---|---|---|---|---|
| 3.2 | Dispatcher YAML-native body | 1 | +600 | Med |
| 3.3 | Scheduler walks recurrence YAMLs | 1 | -100 net | Low-Med |
| 3.4 | Migration 164 (thin tasks index) + ACCESS.md | 1 | +50 SQL | Low |
| 3.5 | Data migration script | 1 | +250 | Med |
| 3.6.a | Route layer migration | 4 | ~760 churn | Med |
| 3.6.b | Service layer migration | 4 | ~310 churn | Med |
| 3.6.c | Scripts migration | 1 | ~60 churn | Low |
| 3.7 | Atomic legacy deletion | 1 | -9,800 | Low (post-3.6) |
| 3.8.a | Backend routes + API client full rename | 1 | ~150 churn | Med |
| 3.8.b | Frontend types/hooks/components/pages rename + /work reshape | 1 | ~800 churn | Med |
| 3.9 | Doc sync + grep gate | 1 | ~500 doc | Low |

**Total**: ~16 commits across one focused work block. Estimated session count: 2–3 fresh-context windows.

---

## What stays exactly as-is (zero rename)

- `tasks` DB table identifier — Path B index per ADR-231 D4. Migration 164 COMMENT documents the intent.
- `agents`, `agent_runs`, `workspace_files`, `workspace_blobs`, `workspace_file_versions` — outside ADR-231 scope.
- `narrative` substrate — already canonical Axiom 9 vocabulary.
- ADR-209 attribution machinery — every YAML write attributed.
- ADR-219 narrative-entry emission — single write path preserved.
- ADR-194 v2 Reviewer dispatch — entirely unchanged.
- ADR-228 cockpit four-face contract — already reads natural-home substrate.
- ADR-230 persona/program activation flow — operates atop new substrate.
- ADR-141 execution-mechanism layers — preserved.
- Bundle reference-workspaces ship YAML declarations (already migrated in 3.1).
- Mandate gate (ADR-207) preserved at dispatch entry.
- Capability gate (ADR-207 P3) preserved at dispatch entry.
- Token accounting (`token_usage` table) preserved.
- Daily-update empty-state (ADR-161) preserved as dispatcher special-case.
- `/work` user-facing route + URL — operator-facing canonical surface (ADR-180/214).

---

## Singular Implementation enforcement points

- **3.2**: legacy `task_pipeline.execute_task` exists but is no longer called by `FireInvocation` / scheduler. Singular at the call-site boundary — same external contract.
- **3.6**: per-commit cluster migration; no caller in cluster remains on old API mid-commit.
- **3.7**: atomic deletion; in-commit grep gate confirms zero call sites.
- **3.8.a**: full URL rename; no `/api/tasks` redirect, no alias.
- **3.8.b**: full type rename; no `Task` alias, no `TaskMode` alias.
- **3.9**: final doc grep gate; zero live-doc references to deleted symbols.

---

## Open decisions (locked here)

1. **Frontend `/tasks` route deletion** — DELETE. No 301 redirect. The canonical route is `/work`; alpha-stage means no public bookmark consumers.
2. **API URL `/api/tasks` → `/api/recurrences`** — full rename, no alias.
3. **`tasks` DB table identifier** — preserved as the Path B index name. Migration COMMENT documents why.
4. **`TaskMode` type** — DELETED. Mode (recurring/goal/reactive) was a TASK.md field; post-cutover it's `RecurrenceShape` (deliverable/accumulation/action/maintenance) which is implied by substrate location.
5. **`taskModeLabel()` helper** — DELETED. Replaced by `recurrenceShapeLabel(shape)` if still needed for UI; existing call sites in `WorkListSurface` + `WorkModeBadge` (renamed `WorkShapeBadge`) updated.

---

## Verification checkpoints

- **After 3.2**: `FireInvocation(shape, slug)` produces correct natural-home output + narrative entry; `task_pipeline.execute_task` still callable.
- **After 3.3**: scheduler tick fires alpha-trader-2 daily market scan via dispatcher; `tasks.next_run_at` updated correctly.
- **After 3.4**: migration 164 applied; `tasks.declaration_path` populated for personas + kvk; ACCESS.md reflects new schema.
- **After 3.5**: kvk's workspace has zero `/tasks/{slug}/TASK.md` files; spot-check one of each shape.
- **After 3.6**: `pytest api/` green. Manual smoke: chat-fired one-shot invocation works; recurring report fires; `FireInvocation` works.
- **After 3.7**: backend grep gate clean; `pytest api/` green.
- **After 3.8.a**: backend routes serve `/api/recurrences/*`; frontend builds; `/work` calls `/api/recurrences/*`.
- **After 3.8.b**: frontend grep gate clean; `/work` renders recurrence-list + narrative-filter; pause/resume/fire/archive end-to-end.
- **After 3.9**: doc grep gate clean.

---

## Discipline checklist (auto-injected per hook, satisfied by this plan)

- [x] **Singular Implementation** — full rename, no aliases, no URL preservation, no backwards-compat shims; legacy code deleted same-commit (3.7) or via cluster migration (3.6).
- [x] **Docs alongside code** — ADR-231 status updates per phase; ACCESS.md updated in 3.4; CLAUDE.md / FOUNDATIONS / GLOSSARY / SERVICE-MODEL / primitives-matrix updated in 3.9; ADR amendment banners in 3.9.
- [x] **Check ADRs first** — phase honors ADR-138, 141, 149, 161, 166, 167, 194 v2, 195 v2, 207, 209, 219, 228, 230 commitments per ADR-231 §Relationship to existing canon.
- [x] **Database** — migration 164 sequence verified; runs through psql per `docs/database/ACCESS.md`; ACCESS.md updated in same commit.
- [x] **Quality checks** — every type/route/URL renamed in lockstep; grep gates inside 3.7 + 3.8.a + 3.8.b + 3.9 enforce alignment.
- [x] **Render parity** — Migration 164 propagates via Render Postgres connection; verify Unified Scheduler boot post-migration; no env-var drift from this work.
- [x] **Prompt changes** — Phase 3.2 (FireInvocation description tightening) + Phase 3.9 (closing CHANGELOG entry).
- [x] **Primitive renames** — `ManageTask` → `FireInvocation` already grep-cleared in Phase 2 commits; final gate in 3.7. Doc references updated in 3.9.
- [x] **Git** — conventional commits per phase; ADR-231 phase reference in every message.
- [x] **Progress** — TodoWrite tracking active.
