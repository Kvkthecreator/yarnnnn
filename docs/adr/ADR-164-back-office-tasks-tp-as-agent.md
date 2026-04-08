# ADR-164: Back Office Tasks — TP as Agent, Unified Scheduled Work

**Status:** Implemented
**Date:** 2026-04-08
**Authors:** KVK, Claude
**Updates (by necessity):** FOUNDATIONS.md Axiom 1 — formalizes TP as an agent (special role: meta-cognitive)
**Extends:** ADR-138 (Agents as Work Units), ADR-140 (Agent Workforce Model), ADR-141 (Unified Execution Architecture), ADR-146 (Primitive Hardening), ADR-149 (Task Lifecycle), ADR-156 (Composer Sunset), ADR-161 (Daily Update Anchor)
**Related:** ADR-163 (Surface Restructure)

---

## Context

After ADRs 161 / 162 / 163 shipped, a pattern became visible in the codebase that was never explicitly modeled: **scheduled work that the system does on its own behalf was living in private code paths rather than in the task substrate.**

Concrete examples:
- `_pause_underperformers()` in `unified_scheduler.py` — lifecycle hygiene for agents. Runs on every scheduler tick. Not a task. No charter. No run log. No user visibility.
- Ephemeral file cleanup in `unified_scheduler.py` — deletes expired `/working/` files. Runs hourly. Not a task. No charter.
- Scheduler heartbeat writes to `activity_log` — diagnostic metrics. Not a task.

All three are **scheduled actions**. All three read workspace state and make decisions. All three have side effects (pausing agents, deleting files, logging). Yet none of them is expressible as a task, which means:

1. Users can't see them, inspect them, or reason about them.
2. Their thresholds (e.g., "8 runs + 30% approval") are hardcoded in Python rather than declarative markdown.
3. Adding new scheduled maintenance work means writing new Python functions in the scheduler rather than composing from the primitive layer.
4. The architecture has two parallel execution paths: tasks (declarative, user-visible) and hardcoded hygiene (imperative, hidden).

The same tension appeared when the question of "task lifecycle warrant" surfaced earlier in the conversation that produced this ADR: *"how do we decide whether a task is still earning its keep, and act on that decision?"* Every answer we considered — a harness, a new agent class, a workspace watch layer, ops tasks — was trying to work around a structural gap: **the task substrate is the right home, but tasks require an agent owner, and there was no agent to own system work.**

TP was the obvious owner. Its mandate is "manage the user's attention allocation and the workforce's health." Evaluating a task's freshness IS attention allocation work. Pausing an underperforming agent IS workforce health work. These are exactly TP's domain. But TP was not a first-class agent in the data model — it had no slug, no workspace folder, no row in `agents`. It lived only as a class instantiated per chat request in `routes/chat.py`. You could not, today, assign a task to TP.

### The core realization (from the conversation)

> **Primitives are runtime-agnostic, not chat-specific.** `execute_primitive(auth, name, input)` dispatches to a single handler regardless of caller. A scheduler-triggered call to `ManageTask(action="evaluate")` executes identically to a TP-chat-triggered call. The split between `CHAT_PRIMITIVES` and `HEADLESS_PRIMITIVES` is a tool exposure policy for LLM callers, not a separation of code paths.

> **If primitives are runtime-agnostic, and tasks are the unit of scheduled work, and TP's responsibilities are orchestration work that can be scheduled — then TP should be able to own tasks, and every piece of scheduled work (user-facing and system-facing) should be a task.**

This ADR implements that realization.

---

## Decision

### 1. TP is an agent (meta-cognitive class)

TP becomes a first-class entity in the agents data model. Concretely:

- **New agent class**: `meta-cognitive`, added to the Python `AGENT_TEMPLATES` registry (there is no `agent_class` DB column — it's template metadata derived at runtime). Alongside the existing three (`domain-steward`, `synthesizer`, `platform-bot`).
- **New agent template**: `thinking_partner` in `AGENT_TEMPLATES` with `class='meta-cognitive'`, `display_name='Thinking Partner'`, `domain=None` (TP does not own a context domain — its domain is orchestration itself).
- **Added to `DEFAULT_ROSTER`**: `{"title": "Thinking Partner", "role": "thinking_partner"}` as the tenth default roster entry. From day 1, every workspace has a TP agent row.
- **Workspace folder**: `/agents/thinking-partner/AGENT.md` scaffolded at workspace init, describing TP's role to itself (yes, TP reads it during task execution — same pattern as every other agent).
- **Slug**: `thinking-partner` (derived from the title "Thinking Partner" by `get_agent_slug()` in `services/workspace.py`, which recomputes the slug from title and ignores the DB `slug` column). Not `tp` — the slug convention mirrors the other domain agents.

**This does not change what TP is when it's running in chat.** `ThinkingPartnerAgent` class in `api/agents/thinking_partner.py` remains the conversation execution class. The new agents table row is about *ownership of tasks*, not about replacing the chat execution path. TP-in-chat invokes `ThinkingPartnerAgent.execute_stream_with_tools()`. TP-in-task invokes a new execution branch in `task_pipeline.execute_task()`. Same entity, two execution modes — exactly like how a domain agent exists as both an identity row and a task execution target.

### 2. Back office tasks

"Back office task" is a **conversational term**, not a data model concept. There is no `task_kind` column, no enum, no hidden flag. A back office task is simply a task whose assigned agent is TP. The substrate is unchanged.

A task is a back office task if and only if its `## Process` section in TASK.md resolves to `tp` as the assigned agent. That's the whole definition. Everything else — visibility, scheduling, execution, outputs — is identical to a user task.

Examples of back office tasks (all owned by TP):
- `back-office-agent-hygiene` — daily, deterministic executor, reads `agent_runs`, pauses underperformers (migrated from `_pause_underperformers`)
- `back-office-workspace-cleanup` — daily, deterministic executor, deletes expired ephemeral files (migrated from scheduler cleanup block)
- `back-office-task-freshness` — weekly, LLM-backed executor, iterates stale tasks, calls `ManageTask(action="evaluate")` on candidates, surfaces retirement candidates into working memory *(scoped out of this ADR — see "Future Work")*

### 3. Visible by default

Per discourse: **nothing about back office tasks is hidden from the user by default.** The `/work` surface shows every task, user-owned and TP-owned, in one list. A user who wants to see only their domain tasks filters by agent = anything-except-TP. A user who wants to see only system maintenance filters by agent = TP. The filter primitive is "by agent" — the same primitive that exists for any other kind of filtering — not a special "hide back office" toggle.

This is load-bearing for the architecture's coherence. The moment we introduce a hidden-by-default flag, we introduce a second data model for "internal stuff" and the purity of "a task is a task, an agent is an agent" breaks. Visibility is the price we pay for coherence, and transparency turns out to be a feature — the user can inspect the machinery of their workspace if they want to.

### 4. No new schema columns

No `task_kind` enum. No `visibility` flag. No `is_internal` boolean. The ownership relation (task → agent → `role`) is sufficient to distinguish back office tasks from user tasks. Any filter the frontend needs can be expressed as "tasks where agent.role = 'thinking_partner'" — a join, not a denormalized field.

The only schema-adjacent change is the addition of a new value to the `agents.agent_class` check constraint (`meta-cognitive`). That's one ALTER statement, no new columns.

### 5. The task pipeline dispatches on agent role

`task_pipeline.execute_task()` currently loads the assigned agent row and then runs a Sonnet generation step. After this ADR, the pipeline dispatches based on `agent.role`:

```
resolve agent from TASK.md → load agent row from DB
    ↓
IF agent.role == 'thinking_partner':
    → dispatch to _execute_tp_task(task_slug, task_info, agent)
    → TP task branch reads TASK.md `## Process` section, which declares
      one of two executor types:
        (a) deterministic Python function — referenced by dotted path,
            e.g., "executor: services.back_office.agent_hygiene.run"
        (b) LLM prompt — referenced inline, e.g., "prompt: evaluate stale tasks"
    → Executor runs, writes structured output to /tasks/{slug}/outputs/{date}/
    → Same run log, same manifest, same delivery path as any other task
ELSE:
    → Standard agent execution branch (existing flow, unchanged)
```

The dispatch is a single `if` in `execute_task()`. The deterministic branch is a new function `_execute_tp_task()` that lives alongside the existing execution code. The existing agent execution path is untouched for non-TP tasks.

### 6. Back office tasks produce outputs, same as any other task

A back office task's output is a structured signal rendered the same way any task output is rendered. Example run output for `back-office-agent-hygiene`:

```markdown
# Agent Hygiene — 2026-04-08

## Summary
Reviewed 9 active agents. Found 0 underperformers. No action taken.

## Observations
| Agent | Runs | Approval rate | Action |
|---|---|---|---|
| Competitive Intelligence | 3 | 100% | OK |
| Market Research | 2 | 100% | OK |
| Reporting | 30 | 100% | OK |
| ... | | | |

## Thresholds
- Minimum runs before review: 8
- Minimum approval rate: 30%
- Only non-user-configured agents eligible for auto-pause

<!-- executor: deterministic · source: services.back_office.agent_hygiene · version: 1 -->
```

This is a regular markdown file in `/tasks/back-office-agent-hygiene/outputs/{date}/output.md`. The `/work` surface's task detail renders it like any other output. Users can scroll through history of hygiene runs the same way they scroll through history of weekly briefings.

The executor writes this output deterministically — no LLM call, no generation cost, just string formatting of observed state plus the actions taken. Cost: zero.

### 7. Scheduler shrinks to a pure dispatcher

After migration, `api/jobs/unified_scheduler.py` contains:

1. The `get_due_tasks()` query
2. The `execute_due_tasks()` loop with atomic claim
3. The scheduler diagnostic heartbeat (once-per-hour write to `activity_log` — see section 9)

That's it. `_pause_underperformers` is deleted (migrated to a task). The ephemeral cleanup block is deleted (migrated to a task). The scheduler has no knowledge of what any particular task does — it just dispatches `execute_task(slug)` for everything that's due.

This is a ~150-line reduction in `unified_scheduler.py` and an elimination of every "imperative hygiene logic" special case from the scheduler file.

### 8. Workspace init scaffolds back office tasks from day 1

Per the conversation commitment — *"these will most likely need to be task initialized from day 1"* — workspace_init.py Phase 5 (from ADR-161) expands. At signup, every workspace receives:

| Task | Agent | Essential | Cadence | Purpose |
|---|---|---|---|---|
| `daily-update` | `executive` (Reporting) | Yes | daily | User-facing briefing (ADR-161) |
| `back-office-agent-hygiene` | `tp` | Yes | daily | Pause underperforming agents |
| `back-office-workspace-cleanup` | `tp` | Yes | daily | Delete expired ephemeral files |

The TP agent row itself is scaffolded in Phase 2 (agent roster) of workspace_init, alongside the existing 9 domain agents. Total roster becomes 10 agents.

All back office tasks are marked `essential=true` (ADR-161 flag) — they cannot be archived, only paused. If a user explicitly pauses `back-office-agent-hygiene`, the hygiene stops running until the user resumes it. This is consistent with ADR-161's "essential tasks respect user agency" principle: essential means the system defaults to having it, not that it cannot be stopped.

### 9. Activity: mostly absorbed into task runs, minimal residual

The audit of `activity_log` event types found 16 distinct types. Nine are task-lifecycle shaped (`agent_run`, `task_executed`, `task_created`, `task_triggered`, `task_paused`, `task_resumed`, `task_completed`, `task_evaluated`, `task_steered`) — these are **redundant denormalizations** of data already in `agent_runs` and `tasks` tables. Writing them to activity_log is duplication.

Seven are genuinely workspace-scoped events that don't map to task runs:

| Event type | Source | Disposition |
|---|---|---|
| `integration_connected` / `integration_disconnected` | OAuth callbacks | **Stay in activity_log** — these are user-triggered workspace events, not task runs |
| `chat_session` | Chat session lifecycle | **Stays in activity_log** — session boundaries, not task-shaped |
| `memory_written` | UpdateContext writes | **Stays in activity_log** — workspace state changes |
| `agent_feedback` | Feedback distillation | **Stays in activity_log** — user corrections |
| `scheduler_heartbeat` | Hourly scheduler diagnostic | **Stays in activity_log** — infrastructure metric, not user-surfaced |
| `agent_scheduled` (auto-pause from hygiene) | `_pause_underperformers` (being migrated) | **Becomes a task run output** of `back-office-agent-hygiene` |

**Decision for ADR-164:**
1. The nine task-lifecycle event writes to `activity_log` are **deleted** from the codebase. Users who want "task X ran yesterday" query the task's run history directly. The briefing dashboard's "recent activity" feed sources from `agent_runs` joined to `tasks` for task-lifecycle events, unioned with `activity_log` for the residual workspace events.
2. `activity_log` retains its role as the home for workspace-level non-task events (platform connections, chat sessions, memory writes, feedback distillation, scheduler diagnostics).
3. No full deprecation of `activity_log`. The table stays, with a narrower, more principled role.

This is the honest answer. Not "activity is replaced entirely by task runs" — which would require bending the task model to cover OAuth events — but "the task-shaped portion of activity is replaced by task runs, and the residual stays in activity_log."

### 10. FOUNDATIONS Axiom 1 update (mandatory)

The existing Axiom 1 establishes TP as meta-cognitive and agents as domain-cognitive, separated as different *kinds* of entity. That framing was accurate for the pre-ADR-164 architecture where TP had no row in `agents` and tasks required agent ownership. It needs revision for the post-ADR-164 architecture where TP is an agents-table row.

**The replacement framing (proposed; open to refinement):**

> **TP is an agent.** It is the *meta-cognitive* agent — a special role distinct from the domain agents of the workforce, but structurally the same kind of entity. TP has a row in the agents table, a slug (`tp`), a workspace folder (`/agents/tp/`), and can own tasks. What makes TP distinct is its *domain*: where domain agents own a segment of the user's work (competitors, market, projects), TP owns the user's attention allocation and the workforce's health. TP's tasks are the tasks of orchestration — deciding what should run, evaluating what has run, maintaining the workspace.
>
> The rule remains clean: **every task has an owner, and the owner determines the class of work.** A task owned by Competitive Intelligence produces competitive analysis. A task owned by TP produces orchestration judgment (agent health decisions, task freshness evaluations, workspace maintenance). If you can answer "what domain does this work serve?" the task belongs to a domain agent. If you can only answer "it serves the coherence of the system itself," the task belongs to TP.
>
> This is not a collapse of the two-layer model; it is the formalization of what TP already does. TP was always the orchestrator; making TP a first-class task owner means orchestration work can be scheduled, inspected, and reasoned about the same way domain work is. The meta/domain distinction persists — it is now expressed as "what does this task's output serve?" instead of "is this entity an agent or not?"

The table in Axiom 1 that lists "Examples: Singular" for TP becomes "Examples: TP (singular, meta-cognitive) plus agents of domain work (domain-cognitive)." TP is still singular within its class, but the class exists.

### 11. TP retains runtime differentiation

TP running in a chat session (`ThinkingPartnerAgent` class) and TP running as a task executor (`_execute_tp_task` branch) are **two runtime modes of the same entity**, differentiated by context:

- **Chat runtime**: invoked from `routes/chat.py`. Receives a user message, streams a response, calls tools (`CHAT_PRIMITIVES`). Full conversation context. User-present.
- **Task runtime**: invoked from `task_pipeline.execute_task()`. Receives a TASK.md, reads context, runs a declarative executor (deterministic or LLM-backed), writes an output file. No user, no streaming. Task-scoped.

Both runtimes share the same workspace, the same AGENT.md, the same memory, the same primitive layer. What differs is the caller and the output format. This is the runtime-agnostic principle made concrete: TP is one entity, its execution adapts to the runtime that called it.

A domain agent (say, Competitive Intelligence) has the same two runtimes today: chat (when the user asks TP to include CI in a conversation) and task (when `track-competitors` is dispatched by the scheduler). TP now fits the same pattern.

---

## Schema Changes

**Correction after audit:** the `agents` table has no `agent_class` column. Agent class lives only in Python `AGENT_TEMPLATES` as template metadata derived at runtime. The DB-level constraint that needs updating is `agents_role_check` — adding `thinking_partner` as a valid role.

Migration 142 (applied to production during implementation):

```sql
ALTER TABLE agents
DROP CONSTRAINT IF EXISTS agents_role_check;

ALTER TABLE agents
ADD CONSTRAINT agents_role_check CHECK (role = ANY (ARRAY[
  'competitive_intel'::text,
  'market_research'::text,
  'business_dev'::text,
  'operations'::text,
  'marketing'::text,
  'executive'::text,
  'slack_bot'::text,
  'notion_bot'::text,
  'github_bot'::text,
  'thinking_partner'::text,  -- ADR-164: TP
  -- ... legacy aliases preserved
]));
```

That's the only schema change. No new columns, no new tables, no data migration. The `meta-cognitive` class is pure Python — added to `AGENT_TEMPLATES['thinking_partner'].class` and resolved at runtime via `get_agent_class_and_domain()`.

---

## Code Changes (Map)

### Agent framework

| File | Change |
|---|---|
| `api/services/agent_framework.py` | Add `thinking_partner` to `AGENT_TEMPLATES` with `class='meta-cognitive'`. Add to `DEFAULT_ROSTER` as the tenth entry. Add `meta-cognitive` to class validation helpers. Define TP's default AGENT.md content. |
| `api/services/agent_creation.py` | Reserve `tp` slug. |

### Workspace init

| File | Change |
|---|---|
| `api/services/workspace_init.py` | Phase 2 (agent roster) now scaffolds 10 agents including TP. Phase 5 (default tasks) scaffolds back office tasks in addition to daily-update. New helper `_create_back_office_tasks()` writes the TASK.md files and inserts `tasks` rows with `essential=true`, assigned to `tp`. |

### Back office executors

| File | Change |
|---|---|
| `api/services/back_office/__init__.py` | NEW — package marker |
| `api/services/back_office/agent_hygiene.py` | NEW — contains the rule currently in `_pause_underperformers`. Exports `run(client, user_id, task_slug)` which returns a structured output dict the pipeline writes to `outputs/{date}/output.md`. |
| `api/services/back_office/workspace_cleanup.py` | NEW — contains the ephemeral file cleanup currently in `unified_scheduler.py`. Exports `run(client, user_id, task_slug)`. |

### Task pipeline

| File | Change |
|---|---|
| `api/services/task_pipeline.py` | `execute_task()` gains a dispatch branch after agent resolution: `if agent['role'] == 'thinking_partner': return await _execute_tp_task(...)`. New function `_execute_tp_task()` reads TASK.md `## Process` for executor declaration, imports the referenced Python function (if deterministic) or runs a focused TP prompt (if LLM-backed), writes output, manages run log and manifest. |

### Task types

| File | Change |
|---|---|
| `api/services/task_types.py` | New task type category: `back_office`. Three initial task types: `back-office-agent-hygiene`, `back-office-workspace-cleanup`. (`back-office-task-freshness` is scoped as future work, not in this ADR.) Each type declares its executor via a new `executor` field in the process step. |

### Scheduler

| File | Change |
|---|---|
| `api/jobs/unified_scheduler.py` | DELETE `_pause_underperformers()` function (migrated to task). DELETE ephemeral cleanup block in `run_unified_scheduler()` (migrated to task). DELETE `_pause_underperformers()` call in main loop. Scheduler becomes: `get_due_tasks() → execute_due_tasks() → scheduler_heartbeat if hourly`. Constants `UNDERPERFORMER_MIN_RUNS`, `UNDERPERFORMER_MAX_APPROVAL` move to `back_office/agent_hygiene.py`. |

### Activity log cleanup (task-lifecycle events)

| File | Change |
|---|---|
| `api/services/task_pipeline.py` | Delete `write_activity(event_type="task_executed", ...)` calls. Task execution is visible via `agent_runs` rows and task run log. |
| `api/services/primitives/manage_task.py` | Delete `write_activity(event_type="task_triggered"/"task_paused"/"task_resumed"/"task_completed"/"task_evaluated"/"task_steered")` calls. These are redundant — the task state transitions are in the `tasks` table, and evaluation/steering write to task memory directly. |
| `api/routes/tasks.py` | Delete `write_activity(event_type="task_created")` call. Task existence is in the `tasks` table. |
| `api/routes/agents.py` | Review and delete `agent_run` activity writes where they duplicate `agent_runs` rows. |

**What is NOT deleted from activity_log:** `integration_connected`, `integration_disconnected`, `chat_session`, `memory_written`, `agent_feedback`, `scheduler_heartbeat`. These remain as workspace-level non-task events.

### TP chat primitives

`ManageTask`, `ManageAgent`, `CreateTask`, `UpdateContext` — all already runtime-agnostic. No changes. TP in chat continues to call them; TP in task runtime can also call them via the same `execute_primitive()` dispatch.

### Frontend

| File | Change |
|---|---|
| `web/components/work/WorkList.tsx` | No change to the default view. All tasks visible. The existing list already sorts by next_run_at which handles back office tasks naturally. |
| `web/components/work/WorkDetail.tsx` | No change required. Back office task outputs render identically (markdown, or structured output). |
| `web/components/agents/AgentTreeNav.tsx` | TP appears in the roster as the 10th agent. Same row shape, same selection behavior. Visually flagged as `meta-cognitive` class (new icon, same pattern as existing classes). |
| `web/lib/agent-identity.ts` | Add `thinking_partner` to display_name/tagline/color maps. |

### Documentation

| File | Change |
|---|---|
| `docs/adr/ADR-164-back-office-tasks-tp-as-agent.md` | This file |
| `docs/architecture/FOUNDATIONS.md` | Axiom 1 rewrite per section 10 above |
| `docs/architecture/SERVICE-MODEL.md` | New "Back Office Tasks" subsection. Entity Model section updated — TP joins the 9 domain agents as the 10th agent |
| `docs/architecture/registry-matrix.md` | Add TP row to agent roster, new meta-cognitive class |
| `docs/design/SURFACE-ARCHITECTURE.md` | Update to v9 — `/work` shows all tasks (no change), agents page includes TP, no new filter UI |
| `CLAUDE.md` | ADR-164 entry |
| `api/prompts/CHANGELOG.md` | Entry noting TP's task runtime mode and any prompt changes |

---

## What This ADR Does NOT Do

Scoped out, to keep the ADR tight and the commit reviewable:

1. **The task freshness / lifecycle warrant work.** This was the question that started the conversation — "when should a task be retired?" It will be built as `back-office-task-freshness` in a follow-up ADR *using* the machinery this ADR establishes. This ADR makes that future work possible; it does not ship the feature itself. Noted for future reference.

2. **Full activity_log deprecation.** This ADR deletes task-lifecycle event writes but keeps the table for workspace events. Full sunset would require migrating integration events and chat session events to different homes, which is not obviously desirable and not necessary for the architectural move.

3. **Task type / primitive re-optimization.** Per discourse: the existing task types and primitives may want refinement once the new substrate is proven — e.g., some task types may become back office tasks, some primitives may find cleaner homes. These optimizations emerge naturally *after* the architecture is hardened. Not in this ADR.

4. **Renaming `agent_runs` to `task_runs`.** The table name is historical (pre-ADR-138) and would be a clearer name now that tasks are first-class. Rename is a mechanical change with broad touch — noted for future, not in scope here.

5. **Frontend filter UI for "by agent".** The default view (all tasks visible) is already the right behavior. Adding a filter-by-agent UI is polish, not part of the architectural move. Noted for future.

6. **`back-office-task-freshness` task type implementation.** The ADR scopes the agent hygiene and workspace cleanup migrations because those are straightforward lifts of existing code. The freshness task requires new logic and is a follow-up.

---

## Migration Order (implementation phases)

1. **Schema migration 142** — add `meta-cognitive` to the agents_class check constraint. Zero data impact.
2. **Agent framework** — register `thinking_partner` template, add to DEFAULT_ROSTER. Existing workspaces will gain TP on next workspace_init call (idempotent).
3. **TP agent row backfill** — for existing accounts (including canary), insert a `tp` agent row via direct SQL. This is a one-time operation like the ADR-161 daily-update backfill.
4. **Back office executor modules** — create `api/services/back_office/agent_hygiene.py` and `workspace_cleanup.py`. Code-complete but not yet called by anything.
5. **Task pipeline TP dispatch** — add `_execute_tp_task()` function. Add the `if agent['role'] == 'thinking_partner'` branch. Regular agent tasks are unaffected.
6. **Task types registration** — add `back-office-agent-hygiene` and `back-office-workspace-cleanup` to `TASK_TYPES` with their TASK.md templates.
7. **Workspace init Phase 5 expansion** — scaffold the two back office tasks at workspace init. Backfill for existing accounts including canary.
8. **Scheduler cleanup** — delete `_pause_underperformers()`, delete the ephemeral cleanup block, delete the call sites. Scheduler file shrinks.
9. **Activity log cleanup** — delete task-lifecycle `write_activity` calls across routes/services. Single-pass find-and-remove.
10. **Frontend updates** — TP appears in roster, new class icon, everything else defaults through.
11. **Documentation** — FOUNDATIONS, SERVICE-MODEL, SURFACE-ARCHITECTURE, CLAUDE.md, CHANGELOG.

Each step is verifiable independently. Steps 1-3 establish TP as an entity. Steps 4-6 establish the executor machinery. Step 7 wires it into new-workspace scaffolding. Steps 8-9 delete the old imperative code. Steps 10-11 update the surfaces and docs.

**Canary protocol:** same as ADR-161. Schema migration applied to production first via psql. TP agent row + back office task rows manually backfilled for KVK's account before code is committed. Manual trigger of `back-office-agent-hygiene` once to verify end-to-end. Then commit and push.

---

## Risks

### Risk 1: FOUNDATIONS Axiom 1 update dilutes the two-layer model

The current Axiom 1 framing is load-bearing for how YARNNN thinks about intelligence. Making TP an agent could be read as collapsing the layers.

**Mitigation:** the proposed update (section 10) is careful to preserve the meta/domain distinction — it moves the distinction from "is it an agent" to "what does the task's output serve." The two layers persist; they're just expressed through task ownership instead of through entity-type separation.

**If this mitigation is insufficient**, the ADR is wrong and should not be written. The user explicitly authorized the update if axiomatic reasoning warrants it (*"I'm willing to update FOUNDATIONS and Axiom if the discourse warrants it fundamentally"*), but the discourse needs to be rigorous. The stress-testing in the conversation that produced this ADR is the record of that rigor.

### Risk 2: TP-in-task execution drifts from TP-in-chat behavior

TP has one identity but two runtime modes. If those modes evolve independently, the entity becomes incoherent — TP-in-chat says one thing about task freshness, TP-in-task does another.

**Mitigation:** TP-in-task executes *declarative* tasks with *declared* executors. The TASK.md charter names exactly what the executor does. There's no free-roaming judgment — the executor is either a Python function (deterministic) or a small focused prompt (single-decision LLM call). TP-in-chat, which has full judgment capacity, reads the same TASK.md files and the same back office task outputs, so its awareness stays aligned with what the task runtime actually did.

### Risk 3: Back office tasks proliferate and create noise

Easy-to-create back office tasks could lead to 10+ hygiene tasks over time, cluttering the `/work` surface.

**Mitigation:** discipline constraint. Each new back office task requires an ADR (or at minimum a documented justification). Existing back office tasks are the template — new ones should fit the pattern (scheduled, declarative, deterministic or single-prompt). Over-proliferation is a code review concern, not a framework limitation.

### Risk 4: Migration breaks existing hygiene in production

`_pause_underperformers` runs today and will be deleted in step 8. Between step 8 and the back office tasks actually running, there's a window where hygiene is "down."

**Mitigation:** order the implementation so the back office task is fully wired (steps 4-7) before the scheduler cleanup (step 8). Canary on KVK's account to verify the back office task runs successfully at least once before committing the scheduler deletion.

### Risk 5: Activity log cleanup deletes events someone depends on

Some frontend component or analytics query may depend on `task_executed` activity events specifically.

**Mitigation:** before deleting, grep the codebase for every consumer of the deleted event types. If a frontend component reads them, migrate it to query `agent_runs` + `tasks` directly in the same commit. Single-implementation rule — no legacy path left behind.

---

## Open Questions

1. **Should TP's `agent_id` be a fixed UUID** (so the same value across all workspaces) **or per-workspace like other agents?** Leaning: per-workspace, because agents are user-scoped and TP's workspace folder (`/agents/tp/AGENT.md`) may evolve per-user via in-session edits. Fixed UUID would be a minor optimization but creates cross-workspace coupling.

2. **What happens if the user tries to delete (archive) TP?** Leaning: blocked by the `essential` flag pattern from ADR-161, applied to the TP agent row itself. TP is essential infrastructure and cannot be archived. The user CAN pause individual back office tasks.

3. **Does TP appear in the workforce headcount for tier limits?** Leaning: no. The tier limit ADRs count domain-producing agents. TP is infrastructure. Add an exclusion in `get_active_agent_count()` for `role='thinking_partner'`, same pattern as the PM exclusion (from superseded ADR-122).

4. **Should the frontend visually distinguish TP from domain agents?** Leaning: yes, a different icon (gear instead of user) to signal its role. But it appears in the same roster list, same row shape. Consistent hierarchy.

5. **Can a user reassign a back office task from TP to a domain agent?** Leaning: no — back office tasks are defined by having TP as owner. Reassigning would make them user tasks, which would be a different task type. If the user wants the behavior of a back office task done by a domain agent, they should create a new task of the appropriate type.

---

## Revision History

| Date | Change |
|---|---|
| 2026-04-08 | v1 — Initial. TP becomes a first-class agent (meta-cognitive class). Back office tasks are tasks owned by TP. Visible by default, no hidden flag. Schema change minimal (one check constraint). Task pipeline dispatches on agent role. Agent hygiene and workspace cleanup migrated from scheduler to back office tasks. Task-lifecycle activity events cleaned up; residual workspace events remain. FOUNDATIONS Axiom 1 updated. Task freshness / retire work scoped for follow-up. |
