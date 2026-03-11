# ADR-090: Work Tickets Consolidation

**Status:** Phases 1–2 Complete. Phase 3 partially complete. Phase 4 (table drops) pending.
**Date:** 2026-03-03
**Authors:** Kevin Kim, Claude (analysis + audit)
**References:**
- [ADR-017: Unified Work Model](ADR-017-unified-work-model.md) — original work_tickets architecture (superseded)
- [ADR-042: Agent Execution Simplification](ADR-042-agent-execution-simplification.md) — when agents took over
- [ADR-080: Unified Agent Modes](ADR-080-unified-agent-modes.md) — agent unification
- [ADR-083: Remove RQ Worker](ADR-083-remove-rq-worker.md) — inline execution

---

## Context

YARNNN has two parallel execution systems that grew independently and now overlap:

| System | Tables | Execution | Output storage |
|--------|--------|-----------|----------------|
| **Agents** (current) | `agents`, `agent_runs` | `agent_execution.py` → `generate_draft_inline()` → Claude API | `agent_runs.draft_content/final_content` |
| **Work Tickets** (legacy) | `work_tickets`, `work_outputs` | `work_execution.py` → `agents/factory.py` → `AgentAgent` | `work_outputs.content` |

The work tickets system was YARNNN's original agent execution layer (ADR-009/017). Agents evolved to replace it for all scheduled and user-configured work. Today:

- **93 work_tickets rows** in production — all created by `agent_execution.py` as audit records, zero from standalone work execution
- **0 pending/recurring work tickets** — the scheduler's `get_due_work()` always returned `[]` (dead RPCs, schema mismatch)
- **The `work_scheduler.py` module doesn't exist** — `project_tools.py` imports it, causing `ModuleNotFoundError` when TP tries to create recurring work

The work tickets system is effectively dead as an execution path but alive as plumbing: `agent_execution.py` writes to `work_tickets` for audit tracking, frontend surfaces display work_ticket data, and the digest email counts work_ticket rows.

### What "work" actually means in the codebase today

1. **Execution audit trail** — `agent_execution.py` creates a `work_tickets` row (task="agent.generate") for every agent run. This is just a progress/status record, not agent dispatch.

2. **Historical outputs** — `work_outputs` has content from early development when agents produced outputs via the work_tickets path. No new rows are written here by the agents system (it stores content in `agent_runs`).

3. **TP tool surface** — TP can theoretically invoke `create_work`, `list_work`, `get_work` via `project_tools.py` handlers. But `create_work` with recurring frequency crashes (missing module), and the tool definitions aren't in the primitives registry.

4. **Frontend surfaces** — `WorkListSurface` and `WorkOutputSurface` show work ticket data. `IdleSurface` lists recent work alongside agents. Users see "agent.generate" tickets mixed with actual agent cards.

---

## Decision

### Retire work_tickets as an execution system. Keep it as an audit table (renamed for clarity).

### Phase 1: Delete dead code — COMPLETE (2026-03-03/04)

- Deleted `get_due_work()`, `process_work()`, scheduler loop block from `unified_scheduler.py` (commit `44c941e`)
- Dropped `get_due_work_templates` RPC from production
- Fixed `notifications_source_type_check` constraint
- Deleted `api/routes/agents.py`, `api/services/work_execution.py`, `api/agents/` directory
- Deleted 5 work handlers + tool registrations from `api/services/project_tools.py`
- Removed `work` entity from primitives (`refs.py`, `execute.py`, `write.py`, `list.py`, `read.py`)
- Total: ~2,405 lines deleted

### Phase 2: Redirect frontend surfaces — COMPLETE (2026-03-04)

- `WorkListSurface` → redirects to `/agents` (stub with navigation button)
- `WorkOutputSurface` → redirects to `/agents` (stub with navigation button)
- `api.work.*` methods removed from `web/lib/api/client.ts`
- `api/routes/work.py` deleted
- Dashboard Agents panel (ADR-091) replaces `IdleSurface` work listing

### Phase 3: Clean up audit trail — Partially complete

Done:
- `account.py` — already migrated; purge and stats use `agent_runs`, no `work_tickets` references
- `digest.py` — already migrated; counts `agent_runs` (comment-only reference to old path)
- `agent_execution.py` — no live writes to `work_tickets` (comment-only references)
- `chat.py` — `surface_type="work-output"` resolved

Remaining:
- **`web/lib/api/client.ts`** — account stats type still declares `work_tickets: number` and `work_outputs: number` (lines 522/526)
- **`web/app/(authenticated)/settings/page.tsx`** — danger zone UI still references `dangerStats.work_tickets` (delete button labels, confirmation dialogs)
- These two are cosmetic only — the backend no longer returns meaningful counts for these fields, but the UI still shows them

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
| `api/jobs/unified_scheduler.py` | `get_due_work()`, `process_work()` | ✅ Phase 1 done |
| `api/services/work_execution.py` | Full CRUD lifecycle | ✅ Phase 1 done (deleted) |
| `api/agents/factory.py` | Agent creation for work execution | ✅ Phase 1 done (deleted) |
| `api/agents/base.py`, `agent.py` | Agent classes | ✅ Phase 1 done (deleted) |
| `api/services/project_tools.py` | 5 work handlers + tool registrations | ✅ Phase 1 done |
| `api/services/primitives/refs.py` | `TABLE_MAP["work"]` | ✅ Phase 1 done |
| `api/services/primitives/execute.py` | `work.run` action | ✅ Phase 1 done |
| `api/services/primitives/write.py` | `_process_work()` | ✅ Phase 1 done |
| `api/routes/agents.py` | Dead stub (not mounted) | ✅ Phase 1 done (deleted) |
| `web/components/surfaces/WorkListSurface.tsx` | `api.work.listAll()` | ✅ Phase 2 done (redirect stub) |
| `web/components/surfaces/WorkOutputSurface.tsx` | `api.work.get()` | ✅ Phase 2 done (redirect stub) |
| `web/lib/api/client.ts` | `api.work.*` methods | ✅ Phase 2 done (removed); stats type still has `work_tickets`/`work_outputs` fields (Phase 3) |
| `api/routes/work.py` | 7 endpoints | ✅ Phase 2 done (deleted) |
| `api/services/agent_execution.py` | `create_work_ticket()`, `complete/fail_work_ticket()` | ✅ Phase 3 done (comment-only references remain) |
| `api/routes/account.py` | Purge + stats queries | ✅ Phase 3 done |
| `api/jobs/digest.py` | Completed/in-progress counts | ✅ Phase 3 done |
| `api/routes/chat.py` | Surface context for `work-output` | ✅ Phase 3 done |
| `api/scripts/purge_user_data.py` | Bulk delete | ✅ Phase 3 done (comment only) |
| `web/lib/api/client.ts` | Stats type `work_tickets`/`work_outputs` fields | Phase 3 remaining |
| `web/app/(authenticated)/settings/page.tsx` | Danger zone `dangerStats.work_tickets` UI | Phase 3 remaining |

---

## Consequences

### Positive
- Eliminates parallel execution system that causes user confusion (work tickets showing alongside agents)
- Removes ~800 lines of dead/broken code (work_execution.py, agents/, project_tools handlers)
- Fixes latent `ModuleNotFoundError` bug in TP's `create_work` tool
- Single source of truth for execution history (agent_runs + activity_log)

### Negative
- Loss of ad-hoc agent execution (TP can't spin up arbitrary agents without a agent). This is acceptable — the feature was broken (missing `work_scheduler.py`) and never surfaced to users as a first-class capability.
- Multi-phase migration — can't drop tables until all writers/readers are redirected

### Neutral
- The `work_tickets` table schema stays in production until Phase 4. It receives writes from `agent_execution.py` until Phase 3 replaces them.
- Frontend surfaces continue to work through Phase 1 (routes still exist). They break at Phase 2 only when explicitly redirected.

---

## Implementation Priority

Phase 1 ✅ → Phase 2 ✅ → Phase 3 (mostly done; remaining: settings page danger zone + client.ts stats type) → Phase 4 (table drops, after validation period)

Phase 2 naturally combines with ADR-087 Phase 3 since both involve frontend changes to agent-related surfaces.
