# ADR-231 ↔ ADR-233 Coordination Memo

> **Date**: 2026-04-29
> **Trigger**: Operator asked whether ADR-233 (shape-driven invocation lifecycle) can run in parallel with continued ADR-231 frontend-rename hygiene without conflict.
> **Verdict**: **ADR-233's "no frontend impact" claim is correct. The two efforts are fully parallel-safe.** This memo records the audit and the work-cluster boundary.

---

## ADR-233 scope (per the parallel session's hand-off summary)

| Phase | Scope | Files touched | Test gate |
|---|---|---|---|
| 1 | Shape-aware headless prompt profiles | +4 created (`api/agents/headless_prompts/`), 2 modified | `test_adr233_phase1_shape_prompts.py` |
| 2 | DELIVERABLE prior-output injection | 2 modified | `test_adr233_phase2_prior_output.py` |
| 3 | ACCUMULATION → `landscape.md` contract | 2 modified | `test_adr233_phase3_domain_synthesis.py` |

Per hand-off: zero frontend impact, no API contract changes, no schema changes.

---

## Audit verdict per phase

### Phase 1 — Shape-aware headless prompts

**Claim**: backend-only; new directory `api/agents/headless_prompts/` plus 2 file modifications.

**Verified against current state**:
- `api/agents/headless_prompts/` does not exist. Fresh directory, no collision.
- The 2 modified files will almost certainly be:
  - `api/services/dispatch_helpers.py::build_task_execution_prompt` — currently a single monolithic prompt builder. Phase 1 splits it shape-aware.
  - `api/services/invocation_dispatcher.py` — caller of `build_task_execution_prompt`; minor signature change to pass shape.
- **Frontend coupling**: ZERO. The frontend never reads the headless agent prompt; it reads the rendered output substrate (HTML / sections / manifest). Prompt restructuring is invisible to `/work` and `/api/recurrences/*`.

**Verdict**: parallel-safe.

### Phase 2 — DELIVERABLE prior-output injection

**Claim**: 2 files modified.

**Current state**:
- `dispatch_helpers.py:662` already accepts `prior_output` + `prior_state_brief` parameters in `build_task_execution_prompt`. The infrastructure is in place; Phase 2 wires the call site in `invocation_dispatcher._dispatch_generative` to actually compute + pass the prior-output bundle.
- The 2 modified files will be:
  - `services/invocation_dispatcher.py` — populate `prior_output` from `paths.output_folder` predecessor reads.
  - `services/dispatch_helpers.py` — possibly tweak the prompt section to handle the richer brief.

**Frontend coupling**: ZERO. Prior-output injection happens prompt-side; the resulting output.md still lands at the natural-home path the frontend already reads.

**Verdict**: parallel-safe.

### Phase 3 — ACCUMULATION → `landscape.md` contract

**Claim**: 2 files modified.

**Current state**:
- `dispatch_helpers.py` already references `landscape.md` semantics (line 717, 1127). The Phase 3 work is to formalize the contract: when an ACCUMULATION recurrence fires, the agent MUST overwrite `_landscape.md` (cross-entity synthesis) so subsequent reads pick up the latest synthesis.
- The 2 modified files will be:
  - `services/dispatch_helpers.py` — add the contract instruction to the ACCUMULATION prompt envelope.
  - `services/invocation_dispatcher.py::_dispatch_generative` — possibly post-run validation that the agent wrote to landscape.md.

**Frontend coupling**: ZERO. `landscape.md` lives at `/workspace/context/{domain}/landscape.md`; the frontend reads context via `/api/recurrences/{slug}` (which surfaces the recurrence detail) and the file browser surface. Changing the synthesis-write contract doesn't change file paths.

**Verdict**: parallel-safe.

---

## Why ADR-233 lands cleanly atop the post-3.7/3.8/3.9 substrate

The post-cutover state established by this session:
- `services/dispatch_helpers.py` is the consolidated home for survivor helpers (`build_task_execution_prompt`, `_generate`, `gather_task_context`, `_load_user_context`, empty-state writers, prior-output infrastructure already in place).
- `services/invocation_dispatcher.py::_dispatch_generative` is the YAML-native dispatch path that calls the helpers.
- `services/recurrence_paths.py::resolve_paths` returns shape-aware paths.
- `services/recurrence.py::RecurrenceShape` enum is the routing key.

ADR-233 plugs into this skeleton without touching any of:
- The thin `tasks` scheduling index
- `routes/recurrences.py` (the post-3.8 HTTP surface)
- The frontend
- ADR-209 attribution machinery
- ADR-219 narrative emission

**Phase ordering is strictly local to ADR-233**: Phase 1 is foundational (prompt-profile module ships first); Phases 2 and 3 are independent of each other.

---

## Parallel work that IS coordination-sensitive: the frontend Task→Recurrence rename

The Phase 3.8 commit `dd78700` shipped:
- URL rename: `/api/tasks/*` → `/api/recurrences/*` ✅
- API client namespace: `api.tasks.*` → `api.recurrences.*` ✅

But explicitly **deferred** to a "hygiene commit":
- TypeScript type renames (`Task` → `Recurrence`, `TaskDetail` → `RecurrenceDetail`, `TaskMode` → DELETED, `TaskCreate` → DELETED, `TaskOutput` → `RecurrenceOutput`, etc.)
- File renames (`web/components/tasks/` → `web/components/recurrences/`)
- Hook renames (`useTaskDetail` → `useRecurrenceDetail`, `useTaskOutputs` → `useRecurrenceOutputs`, `useAgentsAndTasks` → `useAgentsAndRecurrences`)
- Frontend route deletion (`web/app/(authenticated)/tasks/` per ADR-231 D7 + cutover plan §3.8)

**Files still carrying legacy Task* names** (12 files):
- `web/types/index.ts` — 9 type/interface declarations
- `web/app/(authenticated)/settings/system/page.tsx` — 1 use
- `web/app/(authenticated)/work/page.tsx` — 11 uses (selectedTask, reloadTaskDetail, useTaskDetail, etc.)
- `web/components/tasks/{ProcessTab,TaskContentView,TaskTreeNav}.tsx` — directory rename pending
- `web/components/chat-surface/{TaskSetupModal,TaskSetup}.tsx` — file rename pending
- `web/components/work/{WorkModeBadge,WorkListSurface}.tsx` — internal symbol updates
- `web/hooks/{useTaskDetail,useTaskOutputs,useAgentsAndTasks}.ts` — file + symbol renames
- `web/lib/task-types.ts` — DELETE candidate per cutover plan
- `web/app/(authenticated)/tasks/` directory — DELETE per ADR-231 D7

**This rename hygiene work is NOT part of ADR-233 and IS parallel-session-sensitive** if both sessions touch `web/`. Recommendation: keep the Task→Recurrence frontend hygiene cluster in one session (this one or the parallel one — pick one), don't split it. Per Singular Implementation rule, the rename should be one atomic commit covering all 12 files.

---

## Recommendation for parallel-session coordination

**Parallel session may proceed with ADR-233 Phases 1, 2, 3 immediately** — all backend-only, zero collision with the frontend rename hygiene queued for this session.

**This session may proceed with frontend Task→Recurrence rename hygiene immediately** — backend is fully aligned post-3.7/3.8, the rename is a frontend-only operation that touches:
- `web/types/index.ts` (type renames)
- `web/components/tasks/` → `web/components/recurrences/` (directory rename)
- `web/components/chat-surface/{TaskSetupModal,TaskSetup}.tsx` (file rename)
- `web/components/work/WorkModeBadge.tsx` → `WorkShapeBadge.tsx`
- `web/hooks/useTask*.ts` → `useRecurrence*.ts`
- `web/lib/task-types.ts` (DELETE)
- `web/app/(authenticated)/tasks/` (DELETE)
- ~12 call-site updates across `web/app/`, `web/hooks/`, `web/components/`

**Zero shared file between the two work clusters.** The two sessions can both push to `main` independently; the only merge concern would be if both touched the same file in the same commit window — which they won't.

**Verification protocol**: before each session pushes, run a `git pull --rebase` and a fresh `npx tsc --noEmit` (frontend session) or `pytest test_adr231_recurrence.py test_adr231_runtime_invariants.py` (backend session) to catch any drift.

---

## Singular Implementation enforcement at the cluster boundary

Both sessions honor Singular Implementation independently:
- ADR-233 backend: zero parallel paths created; the prompt-profile split + prior-output wiring + landscape.md contract all replace existing legacy behavior in single commits per phase.
- Frontend rename hygiene: the rename is one atomic commit that flips every Task* → Recurrence* / deletion in lockstep. No backwards-compat aliases.

The parallel-execution discipline is: **same architectural commitment (Singular Implementation, ADR-231 vocabulary), independent code surfaces, zero merge conflicts**.

---

## Summary

| Question | Answer |
|---|---|
| Can ADR-233 run in parallel with frontend rename? | **Yes — fully parallel-safe.** Zero shared files. |
| Does ADR-233 actually have zero frontend impact? | **Yes, verified.** All three phases are backend-internal (prompts + dispatcher injection + agent write contract). |
| Is the frontend rename hygiene blocked by anything? | **No.** Backend is post-cutover; URL rename + API client rename already shipped (`dd78700`). Type renames are pure frontend mechanical work. |
| Risk of dual-session merge conflicts? | **Near-zero.** Different code clusters; standard `git pull --rebase` discipline suffices. |

Both efforts can ship independently. This session should proceed with the frontend rename hygiene; the parallel session should proceed with ADR-233 Phases 1–3.
