# Task Modes

**Status:** Canonical (rewritten 2026-04-13 for ADR-138 + ADR-178)
**Date:** 2026-04-13
**Related:**
- [ADR-138: Agents as Work Units](../adr/ADR-138-agents-as-work-units.md) — mode is a task property, not an agent property
- [ADR-178: Task Creation Routes](../adr/ADR-178-task-creation-routes.md) — mode defaults per creation route; mode sync invariant
- [ADR-149: Task Lifecycle Architecture](../adr/ADR-149-task-lifecycle-architecture.md) — evaluate/steer/complete actions; goal mode completion
- [ADR-168: Primitive Matrix](../adr/ADR-168-primitive-matrix.md) — ManageTask(action="update", mode=) is the mutation primitive

> **Replaces:** the prior `docs/features/agent-modes.md` which described mode as an *agent* property and referenced dissolved concepts (proactive mode, coordinator mode, agent pulse, PM agents, project meeting rooms). All of those are deleted. Mode is a **task property** — temporal behavior belongs to the work, not the worker.

---

## What mode is

**Mode** is YARNNN's **lifecycle management posture** over the lifetime of a task — how YARNNN evaluates, steers, and completes (or doesn't) across invocations. Mode lives on the task, not the agent.

### Mode vs pulse — the orthogonal layers

Mode is **distinct from pulse** (FOUNDATIONS Axiom 9 / [invocation-and-narrative.md](../architecture/invocation-and-narrative.md)). Pulse describes how each invocation fires (periodic cron, reactive event, addressed user action). Mode describes what YARNNN does *between* invocations (re-run forever, evaluate toward completion, dispatch-and-done).

The two layers align but are independently meaningful:

| Task mode | Typical pulse | What mode governs |
|---|---|---|
| `recurring` | Periodic | No completion condition; invocations fire indefinitely; YARNNN's job is quality-maintenance across invocations |
| `goal` | Periodic, bounded | Has a completion condition; YARNNN evaluates after each invocation and calls `complete` when met |
| `reactive` | Reactive | Dispatch-and-done per event; no accumulation loop across invocations |

An invocation of a `goal`-mode task and an invocation of a `recurring`-mode task can be structurally identical — the difference is what YARNNN does between them. Mode is the lifecycle layer; pulse is the invocation layer. This doc covers mode.

Three modes exist. That is the complete set.

| Mode | Character | Scheduling | Completion |
|------|-----------|-----------|-----------|
| `recurring` | Open-ended delivery | Fixed schedule (daily, weekly, monthly, custom cron) | Never completes — runs indefinitely |
| `goal` | Bounded delivery | Runs on schedule; TP evaluates → steers → completes | TP calls `ManageTask(action="complete")` when done |
| `reactive` | Event-triggered | Fires when the assigned agent receives a platform event | Dispatch-and-done per event |

Mode is set at task creation and is mutable. TP changes mode via `ManageTask(action="update", mode="goal")`.

---

## The three modes

### Recurring — Open-ended delivery

> "Show up reliably. Do the same job, better each time."

A recurring task runs on a fixed schedule. Every run produces a new output. No completion condition — it runs until paused or archived.

**When to use:** Any work product where regularity is itself the value. The task should be there on schedule regardless of what changed.

**Examples:** Weekly competitive brief. Daily workspace update. Monthly market report.

**DELIVERABLE.md at creation (ADR-178):** Rich for output-driven tasks (Route A) — full output spec, section kinds, quality criteria. Thin for context-driven tasks (Route B) — context file structure, entity coverage goals. Both grow via feedback inference after evaluate cycles.

---

### Goal — Bounded delivery

> "Work toward a clear objective. Stop when it's done."

A goal task runs on a schedule but tracks progress toward a completion point. After each run, TP evaluates the output against DELIVERABLE.md and decides: continue, steer, or complete. When the objective is met, TP calls `ManageTask(action="complete")` — scheduling clears, no more runs.

**When to use:** Work with a defined end state. A research task covering specific competitors. A deck for a specific board meeting. A content series with a defined endpoint ("10 posts on AI agents").

**Examples:** "Research and brief me on these 5 competitors — done when each has a full profile." "Prepare investor materials for the Series A close."

**TP posture in goal mode:**
1. Run fires on schedule → agent produces output
2. TP evaluates: `ManageTask(action="evaluate")` → assesses output against DELIVERABLE.md quality criteria
3. TP steers if gaps: `ManageTask(action="steer", steering="...")` → guidance written to `memory/steering.md` for next run
4. TP completes when done: `ManageTask(action="complete")` → task status set to `completed`, scheduling cleared

---

### Reactive — Event-triggered

> "Wait for the right signal. Act when it arrives."

A reactive task does not run on a schedule. It fires when the assigned platform bot receives a relevant event — a Slack message matching criteria, a Notion page updated, a GitHub issue opened. Each firing is dispatch-and-done: the agent processes the event and produces output (or performs an action). No accumulation loop.

**When to use:** External-action tasks and platform-triggered responses. Slack bot replies, Notion updates, GitHub issue triage.

**Examples:** Slack bot responding to a mention. Notion page summary triggered on update. GitHub issue routed to a team member.

**Note:** Reactive is the natural mode for `external_action` output_kind tasks (ADR-166). It does not apply to `produces_deliverable` tasks — those accumulate context and need schedule-driven runs to compound their context.

---

## Mode and creation routes (ADR-178)

Mode is not chosen arbitrarily at creation. The task creation route shapes the mode default:

| Creation route | Default mode | Rationale |
|----------------|-------------|-----------|
| Route A — output-driven, open-ended deliverable | `recurring` | Deliverable is expected on a schedule indefinitely |
| Route A — output-driven, bounded deliverable | `goal` | Deliverable has a completion event ("until the board meeting") |
| Route B — context-driven (tracking/accumulation) | `recurring` | Context accumulation is open-ended by nature |
| External action task | `reactive` | Platform event triggers the action |
| Back office / maintenance task | `recurring` | System tasks run on schedule |

TP infers the correct mode default during task creation from the user's language. Mode is always mutable after creation.

---

## Critical invariant: DB ↔ TASK.md sync

Mode is stored in two places:

1. `tasks.mode` column (DB) — scheduling index; queried by the scheduler to determine what runs and when
2. TASK.md `**Mode:**` field (filesystem) — execution contract; read by `execute_task()` as part of TASK.md parsing

**These must be identical at all times.** A divergence means the scheduler and the pipeline see different task characters. This is a silent, hard-to-debug failure.

**Enforcement:** `ManageTask(action="update", mode=...)` patches both atomically:
1. Updates `tasks.mode` in the DB
2. Reads TASK.md, regex-replaces `**Mode:**` line, writes back

No other code path should modify mode. If mode needs to change (TP decision, UI action), it must go through `ManageTask(action="update")`.

**At-creation consistency:** `ManageTask(action="create")` sets `tasks.mode` in the DB and writes `**Mode:** {mode}` in the scaffolded TASK.md in the same operation.

---

## Choosing the right mode

Ask one question: **Does this task have a completion condition?**

- **No** (keep delivering on schedule forever) → `recurring`
- **Yes** (stop when X is done) → `goal`
- **Neither** (fires on platform events, not schedule) → `reactive`

When in doubt, start `recurring`. TP can switch a task to `goal` mode when the user expresses a bounded intent ("I want this done by the product launch").
