# ADR-090: Work Tickets Consolidation

**Status:** Approved
**Date:** 2026-03-03
**Authors:** Kevin Kim, Claude (analysis + audit)
**References:**
- [ADR-017: Unified Work Model](ADR-017-unified-work-model.md) — original work_tickets architecture (superseded)
- [ADR-042: Deliverable Execution Simplification](ADR-042-deliverable-execution-simplification.md) — when deliverables took over
- [ADR-080: Unified Agent Modes](ADR-080-unified-agent-modes.md) — agent unification
- [ADR-083: Remove RQ Worker](ADR-083-remove-rq-worker.md) — inline execution

---

## Context

YARNNN has two parallel execution systems that grew independently and now overlap:

| System | Tables | Execution | Output storage |
|--------|--------|-----------|----------------|
| **Deliverables** (current) | `deliverables`, `deliverable_versions` | `deliverable_execution.py` → `generate_draft_inline()` → Claude API | `deliverable_versions.draft_content/final_content` |
| **Work Tickets** (legacy) | `work_tickets`, `work_outputs` | `work_execution.py` → `agents/factory.py` → `DeliverableAgent` | `work_outputs.content` |

The work tickets system was YARNNN's original agent execution layer (ADR-009/017). Deliverables evolved to replace it for all scheduled and user-configured work. Today:

- **93 work_tickets rows** in production — all created by `deliverable_execution.py` as audit records, zero from standalone work execution
- **0 pending/recurring work tickets** — the scheduler's `get_due_work()` always returned `[]` (dead RPCs, schema mismatch)
- **The `work_scheduler.py` module doesn't exist** — `project_tools.py` imports it, causing `ModuleNotFoundError` when TP tries to create recurring work

The work tickets system is effectively dead as an execution path but alive as plumbing: `deliverable_execution.py` writes to `work_tickets` for audit tracking, frontend surfaces display work_ticket data, and the digest email counts work_ticket rows.

### What "work" actually means in the codebase today

1. **Execution audit trail** — `deliverable_execution.py` creates a `work_tickets` row (task="deliverable.generate") for every deliverable run. This is just a progress/status record, not agent dispatch.

2. **Historical outputs** — `work_outputs` has content from early development when agents produced outputs via the work_tickets path. No new rows are written here by the deliverables system (it stores content in `deliverable_versions`).

3. **TP tool surface** — TP can theoretically invoke `create_work`, `list_work`, `get_work` via `project_tools.py` handlers. But `create_work` with recurring frequency crashes (missing module), and the tool definitions aren't in the primitives registry.

4. **Frontend surfaces** — `WorkListSurface` and `WorkOutputSurface` show work ticket data. `IdleSurface` lists recent work alongside deliverables. Users see "deliverable.generate" tickets mixed with actual deliverable cards.

---

## Decision

### Retire work_tickets as an execution system. Keep it as an audit table (renamed for clarity).

### Phase 1: Delete dead code (immediate)

Already done (commit `44c941e`):
- Deleted `get_due_work()`, `process_work()`, and scheduler loop block from `unified_scheduler.py`
- Dropped `get_due_work_templates` RPC from production
- Fixed `notifications_source_type_check` constraint

Still to do:
1. **Delete `api/routes/agents.py`** — dead stub, not mounted in `main.py`, all endpoints return 501
2. **Delete work handlers from `api/services/project_tools.py`** — `handle_create_work()`, `handle_list_work()`, `handle_get_work()`, `handle_update_work()`, `handle_delete_work()` and their tool registrations
3. **Delete `api/services/work_execution.py`** — the standalone execution engine (only called from deleted scheduler code and dead project_tools handlers)
4. **Delete `api/agents/` directory** — `base.py`, `factory.py`, `deliverable.py`, `__init__.py` — only imported by `work_execution.py`
5. **Remove "work" entity from primitives** — remove `work` from `refs.py` TABLE_MAP, `execute.py` ACTION_CATALOG, `write.py` entity handling, `list.py`/`read.py` entity types

### Phase 2: Redirect frontend surfaces

1. **`WorkListSurface`** → Show deliverable runs from `deliverable_versions` instead of `work_tickets`
2. **`WorkOutputSurface`** → Show `deliverable_versions.final_content` instead of `work_outputs.content`
3. **`IdleSurface`** → Show recent deliverable versions instead of `api.work.listAll()`
4. **Remove `api.work.*` from `web/lib/api/client.ts`** — no longer needed
5. **Remove `api/routes/work.py`** — all endpoints dead after Phase 1 + 2

### Phase 3: Clean up audit trail

1. **Replace `work_tickets` writes in `deliverable_execution.py`** — move to `activity_log` (which already has `event_type="deliverable_generated"`) or a new `deliverable_runs` table
2. **Replace `work_execution_log` writes** — consolidate into `activity_log`
3. **Update `account.py`** — remove work_tickets/work_outputs from purge and stats
4. **Update `digest.py`** — count `deliverable_versions` instead of `work_tickets`
5. **Update `chat.py`** — `surface_type="work-output"` reads from `deliverable_versions`

### Phase 4: Drop tables (after migration period)

1. Drop `work_outputs` table (no new writes after Phase 1)
2. Drop `work_execution_log` table (replaced in Phase 3)
3. Drop `work_tickets` table (replaced in Phase 3)
4. Drop related RPC functions and indexes

---

## Dependency Map

Files that reference `work_tickets` and the phase that addresses them:

| File | Operation | Phase |
|------|-----------|-------|
| `api/jobs/unified_scheduler.py` | `get_due_work()`, `process_work()` | **Done** (deleted in `44c941e`) |
| `api/services/work_execution.py` | Full CRUD lifecycle | Phase 1 (delete file) |
| `api/agents/factory.py` | Agent creation for work execution | Phase 1 (delete file) |
| `api/agents/base.py`, `deliverable.py` | Agent classes | Phase 1 (delete files) |
| `api/services/project_tools.py` | 5 work handlers + tool registrations | Phase 1 (delete handlers) |
| `api/services/primitives/refs.py` | `TABLE_MAP["work"]` | Phase 1 (remove entry) |
| `api/services/primitives/execute.py` | `work.run` action | Phase 1 (remove handler) |
| `api/services/primitives/write.py` | `_process_work()` | Phase 1 (remove function) |
| `api/routes/agents.py` | Dead stub (not mounted) | Phase 1 (delete file) |
| `web/components/surfaces/WorkListSurface.tsx` | `api.work.listAll()` | Phase 2 (redirect) |
| `web/components/surfaces/WorkOutputSurface.tsx` | `api.work.get()` | Phase 2 (redirect) |
| `web/lib/api/client.ts` | `api.work.*` methods | Phase 2 (remove) |
| `api/routes/work.py` | 7 endpoints | Phase 2 (delete after frontend redirect) |
| `api/services/deliverable_execution.py` | `create_work_ticket()`, `complete/fail_work_ticket()` | Phase 3 (replace with activity_log) |
| `api/routes/account.py` | Purge + stats queries | Phase 3 (update queries) |
| `api/jobs/digest.py` | Completed/in-progress counts | Phase 3 (use deliverable_versions) |
| `api/routes/chat.py` | Surface context for `work-output` | Phase 3 (use deliverable_versions) |
| `api/scripts/purge_user_data.py` | Bulk delete | Phase 3 (update) |
| `api/scripts/verify_schema.py` | Schema check | Phase 3 (update) |

---

## Consequences

### Positive
- Eliminates parallel execution system that causes user confusion (work tickets showing alongside deliverables)
- Removes ~800 lines of dead/broken code (work_execution.py, agents/, project_tools handlers)
- Fixes latent `ModuleNotFoundError` bug in TP's `create_work` tool
- Single source of truth for execution history (deliverable_versions + activity_log)

### Negative
- Loss of ad-hoc agent execution (TP can't spin up arbitrary agents without a deliverable). This is acceptable — the feature was broken (missing `work_scheduler.py`) and never surfaced to users as a first-class capability.
- Multi-phase migration — can't drop tables until all writers/readers are redirected

### Neutral
- The `work_tickets` table schema stays in production until Phase 4. It receives writes from `deliverable_execution.py` until Phase 3 replaces them.
- Frontend surfaces continue to work through Phase 1 (routes still exist). They break at Phase 2 only when explicitly redirected.

---

## Implementation Priority

Phase 1 (immediate — this session) → Phase 2 (with ADR-087 Phase 3 frontend work) → Phase 3 (next sprint) → Phase 4 (after validation period)

Phase 2 naturally combines with ADR-087 Phase 3 since both involve frontend changes to deliverable-related surfaces.
