# ADR-166: Registry Coherence Pass — Drop `category`, Refine `output_kind`

> **⚠ Superseded by [ADR-207](ADR-207-primary-action-centric-workflow.md) (2026-04-22).** The `output_kind` classification enum dissolves. Tasks self-declare behavior via TASK.md fields (`schedule`, `context_reads`, `context_writes`, `emits_proposal`, `required_capabilities`, `output_spec`); pipeline and surfaces derive role from declarations, not from a classification key. ADR-207 deletes `TASK_TYPES` wholesale alongside the classification.

**Status:** Superseded by ADR-207 (output_kind classification dissolves)
**Date:** 2026-04-08
**Authors:** KVK, Claude
**Extends:** ADR-138 (Tasks as Work Units), ADR-140 (Agent Workforce Model), ADR-145 (Task Type Registry), ADR-149 (Task Lifecycle), ADR-152 (Unified Directory Registry), ADR-163 (Surface Restructure), ADR-164 (Back Office Tasks)
**Related:** ADR-165 (Chat Artifact Surface — different scope)

---

## Context

After ADRs 138 → 164 progressively evolved the agent and task models, the task type registry has accumulated overlapping classification axes that no longer earn their keep. A coherence audit conducted on 2026-04-08 surfaced four issues:

### Issue 1: `category` is redundant and has only one consumer (which is dead)

The `category` field on every task type is grouped under `TASK_TYPE_CATEGORIES` (`context | synthesis | platform | back_office`). Audit results:

- **Backend usage**: only the `list_task_types(category=...)` filter helper and the `/api/tasks/types` query param. No consumer logic depends on it.
- **Frontend usage**: exactly one consumer — `web/components/workfloor/TaskTypeCatalog.tsx`. That component is **not imported anywhere** in the current frontend (verified by grep). It's leftover from the pre-ADR-163 surface design and should have been deleted with the rest of that surface. ADR-165's chat artifact surface replaced it for task type discovery.
- **Owner-implies-category**: in every case where `category` carries information, the assigned agent's class already carries the same signal. Tasks owned by `meta-cognitive` (TP) are back office. Tasks owned by `synthesizer` are synthesis. Platform-bot tasks are platform-shaped. The category field is denormalized owner metadata.

**Conclusion**: drop `category` entirely. Drop `TASK_TYPE_CATEGORIES`. Delete the orphaned `TaskTypeCatalog.tsx` component (singular implementation discipline).

### Issue 2: `task_class` is load-bearing but not derivable from owner alone

Initial intuition was that `task_class` was also redundant with owner. The audit disproved this:

| Owner class | Task types | task_class values |
|---|---|---|
| `meta-cognitive` (TP) | back-office-* | always `back_office` ✓ |
| `synthesizer` (Reporting) | daily-update, stakeholder-update | always `synthesis` ✓ |
| `domain-steward` (5 stewards) | track-* (4) + briefs/reports/materials/preps (8) | **mixed** |
| `platform-bot` (3 bots) | digests (3) + write-backs (2) | **mixed** |

Domain stewards do two shapes of work: accumulate context (`track-*`) AND produce deliverables from accumulated context (`competitive-brief`, `market-report`). Platform bots do two shapes: read-write context (`*-digest`) AND post to external platforms (`slack-respond`, `notion-update`). The owner class doesn't disambiguate which shape — a separate signal is required.

That signal is `task_class`. It's also **load-bearing for prompt construction**: `agent_framework.TASK_PLAYBOOK_ROUTING` filters which playbooks the agent loads at task execution time based on the task's class. Removing `task_class` would either bloat the prompt with all playbooks or strip the agent of the right methodology. Neither is acceptable.

**Conclusion**: keep the field but rename it and refine the enum.

### Issue 3: The current three-value enum miscategorizes external actions

Today the enum is `context | synthesis | back_office`. This forces `slack-respond` and `notion-update` into `synthesis` because there's no other place for them — but they're not synthesis tasks. They take an action against an external platform (post a message, comment on a page). They don't synthesize accumulated context into a deliverable; they read context briefly and write an external API call.

The miscategorization shows up in two places:
1. The playbook routing loads them with the heavy synthesis playbook stack (research, formatting, visual, rendering) when what they actually need is voice/formatting only.
2. The frontend treats them as "reports" in the daily briefing summary, which is misleading — they aren't reports.

**Conclusion**: introduce a fourth value — `external_action` — and reclassify the two write-back tasks.

### Issue 4: Vocabulary collision with `agent_class`

`agent_class` already exists in YARNNN's vocabulary (`domain-steward | synthesizer | platform-bot | meta-cognitive`). Using `task_class` for a different concept on a different entity is an overload that consistently produces confusion when reading code or documentation. Audit notes accumulated several instances where I wrote "class" and had to disambiguate which entity I meant.

**Conclusion**: rename `task_class` → `output_kind`. The new name describes what the field actually captures (the kind of output the task produces) and removes the collision.

### Issue 5: Smaller drift findings

While auditing, several smaller issues surfaced that should be cleaned up in the same pass:

- **`gtm-report` mode/schedule typo in `registry-matrix.md`**: doc shows `mode=weekly, schedule=content`. Code is correct (`mode=recurring, schedule=weekly`). Fix the doc.
- **`track-*` `context_reads` inconsistency**: `track-projects` and `track-relationships` read `signals` on input; `track-competitors` and `track-market` don't. No documented reason for the difference. Normalize: all four read their domain + signals (consistent input signature for the next-cycle directive pattern).
- **`signals` domain has no owner**: it's a cross-domain temporal log written by every track-* and digest task, read by every synthesis task. No agent owns it. This is intentional but undocumented in the registry matrix. Add an explicit note.
- **`gtm-report` redundancy**: it produces a market-leaning synthesis report with the same agent owner (`marketing`) and similar context reads as `market-report`. Per-task review concludes it should be merged into `market-report` rather than maintained as a separate type.
- **`meeting-prep` mode**: declared as `reactive` with `on-demand` schedule. Reactive normally means "fires on a trigger condition" but meeting-prep has a clear completion (the meeting happens). It's structurally a `goal` task, not a reactive one. Reclassify.
- **`stakeholder-update`**: reviewed and kept. Distinct from `daily-update` because it's a monthly executive cadence with cross-domain reads, intended for a different audience and rhythm. Not redundant.
- **`slack-respond` / `notion-update`**: reviewed and kept as task types (not promoted to chat primitives). They're recurring-eligible work — the user can set up "every Monday post the standup summary to #engineering" — and need to live in the task substrate so they have a charter, run history, and observability on `/work`. Reclassified as `external_action`.

---

## Decision

### 1. Drop `category` and `TASK_TYPE_CATEGORIES`

Remove the `category` field from every entry in `TASK_TYPES`. Remove the `TASK_TYPE_CATEGORIES` constant. Remove the `category` parameter from `list_task_types()`. Remove the `category` query param from `/api/tasks/types`. Remove `category` from the frontend `TaskType` interface and `TaskTypesResponse.categories[]` field.

Singular implementation: no parallel field, no migration shim. The orphaned `web/components/workfloor/TaskTypeCatalog.tsx` is **deleted entirely** in the same commit (not converted to use the new model — it has no consumers and ADR-165's chat artifact surface replaced its UX role).

### 2. Rename `task_class` → `output_kind`

Field rename across:
- `api/services/task_types.py` (TASK_TYPES entries)
- `api/services/task_pipeline.py` (parse_task_md output, dispatch logic)
- `api/services/agent_framework.py` (TASK_PLAYBOOK_ROUTING → TASK_OUTPUT_PLAYBOOK_ROUTING; get_relevant_playbooks signature)
- `api/services/workspace.py` (AgentWorkspace.load_context signature)
- `api/routes/tasks.py` (TaskResponse interface)
- `web/types/index.ts` (Task interface)
- `web/components/home/DailyBriefing.tsx`
- `web/components/tasks/TaskTreeNav.tsx`
- `web/components/chat-surface/artifacts/ContextGapsArtifact.tsx`

The TASK.md serialization line changes from `**Class:** synthesis` to `**Output:** produces_deliverable`. `parse_task_md` reads the new line; the old line is removed entirely (no backward parse).

### 3. Four-value `output_kind` enum

```
output_kind = accumulates_context
            | produces_deliverable
            | external_action
            | system_maintenance
```

| Value | Meaning | Where output goes | Examples |
|---|---|---|---|
| `accumulates_context` | Writes to a workspace context domain. No user-visible artifact this run. | `/workspace/context/{domain}/` | track-*, *-digest (slack/notion/github), research-topics |
| `produces_deliverable` | Writes a user-visible artifact for the user to read. | `/tasks/{slug}/outputs/{date}/output.md` | daily-update, *-brief, *-report, *-prep, *-update, *-material |
| `external_action` | Takes an action on an external platform via API write. | External platform (Slack message, Notion comment) | slack-respond, notion-update |
| `system_maintenance` | Owned by TP. Produces an orchestration signal. Deterministic, no LLM. | `/tasks/{slug}/outputs/{date}/output.md` (markdown report of what was observed/acted on) | back-office-* |

### 4. Refined playbook routing

```python
TASK_OUTPUT_PLAYBOOK_ROUTING: dict[str, list[str]] = {
    "accumulates_context":  ["research", "context"],
    "produces_deliverable": ["synthesis", "formatting", "visual", "rendering"],
    "external_action":      ["formatting"],   # voice/format only — no deep research
    "system_maintenance":   [],                # deterministic, no playbooks
}
```

`external_action` gets minimal playbook (voice + formatting) — slack-respond posts a message, it doesn't investigate. `system_maintenance` gets nothing because deterministic Python executors don't load playbooks (they call no LLM).

### 5. Per-task changes

Within the same ADR commit:

**Reclassifications (output_kind change only):**
- `slack-respond`: `synthesis` → `external_action`
- `notion-update`: `synthesis` → `external_action`

**Mode changes:**
- `meeting-prep`: `reactive` → `goal` (it has a completion criterion — the meeting happens — making it a bounded goal task, not a trigger-driven reactive task)

**Deletions:**
- `gtm-report`: deleted, merged into `market-report`. The `market-report` task type is updated to absorb gtm-report's intent (its description, audience, and quality criteria pull in the GTM-relevant framing). Any existing `gtm-report` task instances on KVK's account are migrated to `market-report` in the canary backfill.

**Normalizations:**
- `track-competitors`: `context_reads` becomes `["competitors", "signals"]` (was `["competitors"]`)
- `track-market`: `context_reads` becomes `["market", "signals"]` (was `["market"]`)
- `track-projects` and `track-relationships`: unchanged (already include signals)
- All four `track-*` tasks now have a consistent input signature: own domain + signals, output: own domain + signals.

**Documentation fix:**
- `registry-matrix.md`: `gtm-report` row removed (deleted task type). All references in the matrix updated to the new model.

### 6. Document `signals` as a special cross-cutting domain

In `docs/architecture/registry-matrix.md` and `docs/architecture/workspace-conventions.md` (if applicable), add an explicit note:

> **`signals/` is a special cross-cutting context domain.** No agent owns it. Every `accumulates_context` task writes a dated entry to it (recording what was observed this cycle), and every `produces_deliverable` task may read from it (to surface temporal context across domains). It's not a domain steward's territory — it's the workspace's shared timeline.

This is current behavior; the note just makes it explicit.

---

## Schema Changes

**None.** `tasks` table is untouched. The changes are entirely in the Python registry, the TASK.md serialization format, and frontend type definitions.

The TASK.md format change (`**Class:**` → `**Output:**`) requires backfill for any existing TASK.md files in production. KVK's canary account has 3 such files (daily-update, back-office-agent-hygiene, back-office-workspace-cleanup). They will be rewritten as part of the canary protocol.

---

## Code Changes (Map)

### Backend

| File | Change |
|---|---|
| `api/services/task_types.py` | Drop `TASK_TYPE_CATEGORIES`, drop `category` field from all 21 entries (becoming 20 after gtm-report deletion), rename `task_class` → `output_kind`, reclassify slack-respond/notion-update, change meeting-prep mode, normalize track-* reads, delete gtm-report entry, merge intent into market-report |
| `api/services/agent_framework.py` | Rename `TASK_PLAYBOOK_ROUTING` → `TASK_OUTPUT_PLAYBOOK_ROUTING`, expand to 4 keys, update `get_relevant_playbooks(agent_type, output_kind=)` signature |
| `api/services/task_pipeline.py` | `parse_task_md` reads `**Output:**` line into `output_kind` field; delete `**Class:**` parser; update propagation through `_execute_pipeline` and `AgentWorkspace.load_context()` callers |
| `api/services/workspace.py` | `AgentWorkspace.load_context(output_kind=)` signature rename |
| `api/routes/tasks.py` | `TaskResponse.task_class` → `TaskResponse.output_kind`, parser updates |
| `api/services/task_types.py:build_task_md_from_type` | Writes `**Output:** {output_kind}` line in generated TASK.md (replaces `**Class:** {task_class}`) |
| `api/services/task_types.py:list_task_types` | Drop `category` parameter; signature is `list_task_types(output_kind=None)` |

### Frontend

| File | Change |
|---|---|
| `web/types/index.ts` | `Task.task_class` → `Task.output_kind`. `TaskType.category` removed. `TaskTypesResponse.categories` removed. Type union for `output_kind` literal: `'accumulates_context' \| 'produces_deliverable' \| 'external_action' \| 'system_maintenance'` |
| `web/components/home/DailyBriefing.tsx` | `t.task_class === 'context'` → `t.output_kind === 'accumulates_context'`; same for synthesis. Counter labels stay the same (the user-facing words "tracking" and "reporting" don't change). |
| `web/components/tasks/TaskTreeNav.tsx` | Same field rename. Switch logic unchanged. |
| `web/components/chat-surface/artifacts/ContextGapsArtifact.tsx` | Same field rename. |
| `web/components/workfloor/TaskTypeCatalog.tsx` | **DELETED.** Orphaned, no consumers, replaced by ADR-165 chat artifact surface. |
| `web/lib/api/client.ts` | `tasks.listTypes()` no longer accepts category param; `TaskTypesResponse` shape updates |

### Documentation

| File | Change |
|---|---|
| `docs/adr/ADR-166-registry-coherence-pass.md` | This file |
| `docs/architecture/registry-matrix.md` | Substantial rewrite: drop category section, new output_kind table, fix gtm-report deletion, document signals as cross-cutting, add the four output_kind values |
| `docs/architecture/FOUNDATIONS.md` | Brief note: "task organization axes are type, mode, owner, output_kind" |
| `docs/architecture/SERVICE-MODEL.md` | Update task type catalog references |
| `docs/architecture/agent-framework.md` | Update TASK_PLAYBOOK_ROUTING reference |
| `docs/features/agent-types.md` | Field reference updates (task_class → output_kind) |
| `docs/features/task-types.md` | Field reference updates if any |
| `CLAUDE.md` | ADR-166 entry |
| `api/prompts/CHANGELOG.md` | Entry for the playbook routing rename + field rename + per-task changes |

---

## Canary Protocol

KVK's account has 3 TASK.md files written under the old `**Class:**` format. After the code change lands but before the next scheduler tick, these need to be rewritten:

1. `/tasks/daily-update/TASK.md` — `**Class:** synthesis` → `**Output:** produces_deliverable`
2. `/tasks/back-office-agent-hygiene/TASK.md` — `**Class:** back_office` → `**Output:** system_maintenance`
3. `/tasks/back-office-workspace-cleanup/TASK.md` — `**Class:** back_office` → `**Output:** system_maintenance`

Verified via psql before code commit. If KVK has any `gtm-report` task instances (none expected), they'll be migrated to `market-report`.

The same backfill logic ships as a one-time SQL update; not a migration script per se, just a UPDATE on `workspace_files.content` for the 3 known paths via psql during the canary step.

For new workspaces, `build_task_md_from_type()` writes the new format from the start.

---

## What This ADR Does NOT Do

- **No DB schema changes.** No migration. No new column.
- **No agent class changes.** Four agent classes stay (domain-steward, synthesizer, platform-bot, meta-cognitive).
- **No mode changes other than meeting-prep.** Recurring/goal/reactive enum unchanged at the schema level. Surface still shows two labels.
- **No back office task changes.** Phase 4 work preserved.
- **No collision with ADR-165.** Different file scope (chat artifact surface vs task registry).
- **No frontend surface restructure.** SURFACE-ARCHITECTURE v8.1 unchanged.
- **No new task types.** This is a cleanup pass, not an expansion.
- **No tier limit changes.** Roster unchanged.

---

## Risks

### Risk 1: Existing TASK.md files become unparseable post-rename

The pipeline reads `**Class:**` today; if I delete the parser before existing files are rewritten, they'll be parsed without `output_kind` and the agent's playbook loading will fall back to default (all playbooks loaded). This is a soft regression, not a failure — but it's avoidable.

**Mitigation**: rewrite KVK's 3 existing TASK.md files in the same canary step that runs the migration. Verified pre-commit.

### Risk 2: Frontend type union mismatch breaks tsc

The `output_kind` field uses literal-typed union in TypeScript. If any consumer compares against the old string values (e.g., `'context'`), tsc will catch it. This is a feature, not a risk — it's exactly the kind of regression I want the type system to flag.

**Mitigation**: comprehensive grep for `task_class` references before the commit; full `tsc --noEmit` clean build required.

### Risk 3: Breaking the `gtm-report` deletion if a user has one

KVK's account doesn't have a gtm-report task, but a future user could. If the registry deletes the type while a task instance still references it, `get_task_type('gtm-report')` returns None and the pipeline fails.

**Mitigation**: query `tasks` table for any `slug = 'gtm-report'` rows before code commit. If any exist, they get migrated to `market-report` (UPDATE the slug + rewrite TASK.md). KVK has zero — verified before commit.

### Risk 4: Playbook routing regression for `external_action`

The current routing for `synthesis` includes the visual/rendering playbooks. Reclassifying slack-respond/notion-update to `external_action` strips those playbooks. The agent's prompt becomes lighter. If those playbooks were carrying load (e.g., the slack-respond agent was using rendering instructions to format Slack mrkdwn), behavior changes.

**Mitigation**: I checked. The visual and rendering playbooks are about chart styling and HTML output composition — neither relevant to Slack messages or Notion comments. The `formatting` playbook (which I'm keeping for external_action) carries the voice/tone guidance that IS relevant. Net: the prompt gets tighter and more relevant.

---

## Validation Plan

Before commit:

1. **Python**: syntax check on all touched files; full import smoke test; wiring sanity (every TASK_TYPES entry has `output_kind`, no entry has `category`, no entry has `task_class`)
2. **Python**: end-to-end test that the playbook router returns the right playbooks for each output_kind
3. **TypeScript**: `npx tsc --noEmit` clean build (no `task_class` references survive)
4. **Database**: psql verify KVK's roster + tasks state; rewrite the 3 TASK.md files; verify pipeline parse on the new format
5. **Grep**: zero remaining `task_class` references in active code (excluding historical ADR/CHANGELOG entries that document the rename)
6. **Grep**: zero remaining `category` references in TASK_TYPES code paths

---

## Open Questions

None. Per discourse, the directional cut is locked in:
- Drop `category` ✓
- Rename `task_class` → `output_kind` with four values ✓
- Reclassify slack-respond/notion-update as `external_action` ✓
- Delete `gtm-report`, merge intent into `market-report` ✓
- Change `meeting-prep` mode `reactive` → `goal` ✓
- Keep `stakeholder-update` (distinct cadence/audience from daily-update) ✓
- Normalize `track-*` reads ✓
- Delete orphaned `TaskTypeCatalog.tsx` ✓

---

## Revision History

| Date | Change |
|---|---|
| 2026-04-08 | v1 — Initial. Registry coherence pass. Drop category, rename task_class→output_kind with four values, reclassify external actions, delete gtm-report, normalize track-* reads, delete orphaned TaskTypeCatalog. |
