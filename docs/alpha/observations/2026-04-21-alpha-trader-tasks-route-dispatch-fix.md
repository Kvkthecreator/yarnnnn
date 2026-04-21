# 2026-04-21 — alpha-trader — POST /api/tasks dispatches through ManageTask (architectural fix shipped)

## Classification
- **Objective:** A-system
- **Within-A scope:** systematic-workflow
- **FOUNDATIONS dimension:** Substrate
- **Severity:** dead-stop (pre-fix)
- **Resolution path:** component-patch (landed)
- **Money impact:** decision-impact

## Context
Follow-up to
`2026-04-21-alpha-trader-phase-1-seeding-bypassed-architecture.md`.
After that scaffold pass landed the persona-identity files, the next
step was activating the six Simons-persona tasks. Before flipping
status=active, I spot-checked TASK.md for `track-universe` and
discovered it was a skeleton — no `**Mode:**`, no `**Agent:**`, no
`## Team`, no `**Output:**`, no DELIVERABLE.md. Activating would
have fired the scheduler at tasks whose pipeline inputs were absent,
producing either 500s or garbage writes.

## What happened

Root-caused to `api/routes/tasks.py::create_task` — a structurally
incomplete duplicate of `services/primitives/manage_task._handle_create`
(the canonical primitive per ADR-168 Commit 3). The route:

- Wrote TASK.md via a route-scoped `_format_task_md` that serialized
  only `## Objective` + `## Success Criteria` + `## Process` + `## Output Spec`
  and omitted every `**Slug:**`/`**Agent:**`/`**Mode:**`/`**Output:**`
  metadata field + `## Team`.
- Hardcoded DB `tasks.mode` to the schema default (`recurring`),
  silently swallowing any `reactive` or `goal` intent from the caller.
  This directly broke ADR-178's critical invariant that `tasks.mode` ==
  TASK.md `**Mode:**`.
- Skipped DELIVERABLE.md (ADR-149), feedback.md (ADR-181),
  memory/steering.md (ADR-149), awareness.md (ADR-154).
- Skipped context-domain scaffold for declared `context_writes` (ADR-151).
- Did not validate that the assigned agent existed.
- Did not compute `next_run_at` from the schedule.

Net effect: any task created via the REST API was unrunnable. The
only path that produced a complete TASK.md was the chat path through
`ManageTask._handle_create`. External scripts (like the Alpha-1
scaffold driver) and any future non-chat caller hit the broken path.

## Friction

The architectural gap is the broader concern — not the six alpha
tasks. Two callers of task-creation diverged in structure despite
ADR-168 explicitly naming a singular implementation. The divergence
was invisible until an end-to-end scaffold pass hit the broken path.

The ADR-178 `mode` invariant was especially silent: the route-level
default of `recurring` overrode `reactive` mode without logging, so
any reactive task created via REST would become a dead recurring task
with `schedule=None` — it would never fire, never error, just exist.

## Resolution (landed)

Commit `b523795` (on main, deploying now):

- `api/routes/tasks.py` `create_task` rewritten as a thin dispatcher.
  Parses `TaskCreate` → delegates to
  `services.primitives.manage_task._handle_create(auth, payload)`.
- Route-scoped `_format_task_md` **deleted**. TASK.md serialization
  now lives exclusively in `_build_custom_task_md` /
  `build_task_md_from_type` (manage_task.py).
- `TaskCreate` Pydantic model extended to the full ManageTask input
  shape: `mode`, `agent_slug`, `type_key`, `team`, `delivery`,
  `page_structure`.
- API boundary now requires `type_key` OR `agent_slug` (400 without).
- DB `tasks.mode` populated from payload — ADR-178 invariant holds
  on create, not just on update.

`api/scripts/alpha_ops/scaffold_trader.py` updated to supply the
full shape per task (agent_slug + mode + team + delivery). No
post-create pause step — TASK.md is complete at creation, so tasks
are immediately runnable.

### Follow-up micro-fix surfaced by the same scaffold pass

With the route dispatching correctly, the six alpha tasks scaffolded
through `_handle_create` exposed one more latent bug: for
`mode=reactive` tasks, `_handle_create` was defaulting `schedule` to
`"weekly"` and computing a `next_run_at` — contradicting ADR-149's
reactive contract (reactive is dispatch-and-done, caller-triggered,
never cron-driven). `trade-proposal` was given `schedule=weekly,
next_run_at=2026-04-27` at create time, which would have let the
scheduler fire it on its own timeline rather than only when
`signal-evaluation` event-triggered it.

Fixed in `_handle_create`:
- `if not schedule and mode != "reactive"` — no default schedule for reactive.
- New explicit branch: `mode == "reactive"` → `next_run_at = None`.

Also patched the live `trade-proposal` row (schedule → NULL, next_run_at →
NULL) + stripped `**Schedule:**` from its TASK.md body so the filesystem
and DB agree.

### Verification after both fixes land

- `verify.py alpha-trader` → 23/23 green
- All 6 TASK.md files carry `**Slug:** / **Agent:** / **Mode:** /
  **Schedule:** (where applicable) / **Delivery:** / ## Objective /
  ## Success Criteria / ## Team`
- All 6 DELIVERABLE.md files scaffolded (577–698 chars each)
- All 6 feedback.md + memory/steering.md + awareness.md files seeded
- trade-proposal: `mode=reactive, schedule=NULL, next_run_at=NULL` (correct)
- Other 5 recurring tasks: `next_run_at` populated at their cron tick

## Architecture-level framing

This observation exercised exactly what alpha testing is for:
**surfacing duplicate-implementation drift that only shows up when
a second caller exists.** Before Alpha-1, only the chat path
(YARNNN → ManageTask) ever created tasks, so `routes/tasks.py`'s
divergence was latent. The scaffold driver became the second caller
and the gap collapsed immediately.

Lesson for the architecture ledger: any primitive named as
"canonical" in an ADR (here ADR-168) needs a structural grep-gate
in `test_recent_commits.py` or equivalent — so route-scoped
duplicates can't reappear without a failing test.

## Counterfactual (Objective B)

Without this fix, any operator (real or Claude-as-operator) creating
tasks via API → scheduler fires against TASK.md with no team → run
either 500s or produces garbage. For a Simons-persona trader, that
means: `signal-evaluation` never actually evaluates signals → no
`trade-proposal` fires → no proposal ever lands in the Queue → no
capital moves. Objective B is fully gated on this path working.

## Links

- Fix commit: b523795 on main
- Original observation (this one is the resolution):
  `2026-04-21-alpha-trader-phase-1-seeding-bypassed-architecture.md`
  (item #4 in its Friction section — "DELIVERABLE.md not scaffolded
  at task-create" was understated; the real gap was the entire
  TASK.md serialization path)
- Canonical reference: [primitives-matrix.md](../../architecture/primitives-matrix.md) (ADR-168)
- ADRs: ADR-149, ADR-151, ADR-154, ADR-168, ADR-178, ADR-181
