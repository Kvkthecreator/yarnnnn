# ADR-161: Daily Update as Anchor — The Heartbeat Artifact

> **⚠ Superseded by [ADR-231](ADR-231-task-abstraction-sunset.md) (2026-04-29).** Per ADR-231 D6, daily-update reframes as a recurrence declaration at `/workspace/reports/daily-update/_spec.yaml` (or absent if the operator hasn't opted in per ADR-206). The `essential: true` flag dissolved with migration 164 (Phase 3.4). The deterministic empty-state template is preserved as a dispatcher special-case in `services.dispatch_helpers._execute_daily_update_empty_state`, now writing to natural-home output folders (`/workspace/reports/daily-update/{date}/output.md`) instead of `/tasks/daily-update/outputs/`. If the operator deletes the recurrence YAML, daily-update simply stops firing — there's no archive guard.
>
> **⚠ Amended by [ADR-205](ADR-205-primitive-collapse.md) (2026-04-22).** Daily-update task is preserved as the workspace heartbeat artifact. Owner changes from YARNNN-the-agent-row to YARNNN-the-workspace-identity (single persistent entity per workspace, tracked in `workspace_identity` table). Empty-state deterministic template, cadence, and essential guard all unchanged.
>
> **⚠ Superseded by [ADR-206](ADR-206-operation-first-scaffolding.md) (2026-04-22).** The "essential heartbeat at signup" framing is dissolved. Post-ADR-206, daily-update is **not** scaffolded at signup and is **not** flagged essential. It becomes an **opt-in task** offered by YARNNN in chat once the operator's declared operation is running and producing deliverables. The loop itself (proposals → review → execute → reconcile) is what makes the service feel alive; an email digest is an optional surfacing of the loop, not the heartbeat. The original ADR-161 rationale (prevent dormant signups from going silent) is addressed differently in ADR-206: a workspace with no declared operation IS meant to be silent until the operator declares one.

**Status:** Proposed
**Date:** 2026-04-07
**Authors:** KVK, Claude
**Amended by:** ADR-205 (owner = workspace identity)
**Superseded by:** ADR-206 (essential-heartbeat-at-signup framing dissolved; daily-update is opt-in post-operation-declared)
**Extends:** ADR-138 (Agents as Work Units), ADR-140 (Agent Workforce Model), ADR-141 (Unified Execution Architecture), ADR-149 (Task Lifecycle Architecture), ADR-152 (Unified Directory Registry)
**Related:** ADR-155 (Workspace Inference Onboarding), ADR-156 (Composer Sunset)

---

## Context

### The Dormancy Problem

After ADR-138 collapsed the project layer and ADR-140 pre-scaffolded a workforce roster, every new YARNNN workspace gets nine agents and six context domains at signup. None of those agents do any work until a task is created. Tasks are created exclusively by TP, exclusively in chat, exclusively in response to user input.

This produces a structural failure mode: **a user who signs up but never engages in chat ends up with a fully-scaffolded workspace that does literally nothing**. The scheduler runs every five minutes, queries the `tasks` table, finds zero rows, logs `[TASKS] No due tasks`, and exits. The user receives no email, no notification, no signal that the system exists. From the user's perspective, the product is dead. From the operator's perspective, the canary (the developer's own account) is silent and the bug is invisible until someone goes looking.

This was discovered empirically: the developer's own account had 9 agents and 0 tasks for an extended period, with no automated heartbeat to surface the gap.

### The Two Modes of Value (FOUNDATIONS Axiom 6)

FOUNDATIONS Axiom 6 establishes two valid modes of value: **autonomous** ("system recognizes need → creates agents → delivers value → user refines") and **directed** ("user asks TP → TP responds or creates agents"). The product bet is on autonomous as the differentiator, with directed as the always-available fallback.

But the autonomous mode has been gated on the directed mode in practice — autonomous work only begins after directed work creates the first task. The two modes were meant to be peers; in implementation, one is a prerequisite for the other.

### What's Missing: A Floor

There is no **floor** — no minimum guaranteed activity that proves the system exists. Every other surface (the dashboard, the agents page, the workspace files) is invisible unless the user actively opens YARNNN. Email is the only channel that reaches the user *outside* the application, and currently no email goes out unless a task explicitly delivers one, and no task exists by default.

The Composer sunset (ADR-156) committed to "single intelligence layer" — TP makes all judgment calls, in conversation, where the user can see them. But ADR-156 didn't address this asymmetry: TP can only judge when the user is present. There is no mechanism for the system to *be present to the user* when the user is not in chat.

---

## Decision

### The Daily Update Task is the Anchor

Every workspace, at signup, is scaffolded with exactly one task: a `daily-update` task with daily cadence and email delivery. This task is **essential** — it cannot be deleted, cannot be auto-paused, and the user cannot opt out of its existence (though they can pause it explicitly, see below).

The daily-update task is the **heartbeat artifact**: the user-facing manifestation of the system being alive. It is the only task that arrives in the user's inbox by default. Its content varies with workspace state — empty workspace produces an honest "no work yet, here's how to start" message; populated workspace produces an operational digest. Same task, same cadence, different content.

### What "Essential" Means

A task with `essential = true` has the following properties:

| Property | Behavior |
|---|---|
| **Deletion** | Blocked. `ManageTask(action="archive")` returns an error explaining the task cannot be archived. |
| **Auto-pause** | Excluded from any future lifecycle hygiene rules (ADR-156's underperformer pausing is agent-level, not task-level, so this is forward-looking — when ADR-160 lands, essential tasks are exempt from tenure-based auto-pause). |
| **Manual pause** | Allowed. The user can explicitly pause the daily-update via `ManageTask(action="pause")`. This is a deliberate user choice, not a system decision. The task remains in the workspace, paused, with a clear "essential — resume?" affordance. |
| **Cadence/delivery edits** | Allowed. The user (via TP) can change the schedule from daily to weekly, change the delivery email, change the content focus. The task itself remains essential. |
| **Type change** | Blocked. The task type stays `daily-update` for its lifetime — changing it would defeat the purpose of the anchor. |

The `essential` flag is set at workspace initialization and is not user-settable through any primitive. It is system metadata, not configuration.

### Empty-State Honesty

The daily-update task must be able to run against an empty workspace and produce a useful artifact at near-zero cost. The pipeline gains an explicit empty-state branch:

```
execute_task("daily-update")
    ↓
Read TASK.md → resolve agent (executive/Reporting)
    ↓
Check workspace state:
    - If no other active tasks AND no context domain entities exist:
        → emit "honest empty" output (deterministic template, no LLM call)
        → cost: ~$0
    - If context exists but no recent runs:
        → standard daily-digest with "quiet day" framing
        → cost: ~$0.03 (Sonnet, small prompt)
    - If context exists and recent runs occurred:
        → full operational digest reading run_log.md across tasks
        → cost: ~$0.05-0.15
```

The empty-state output is a **deterministic template**, not an LLM call. There's nothing to summarize when the workspace is empty; the LLM would just be expensive scaffolding around a fixed message. The template includes:

- A friendly greeting
- An honest acknowledgement that the workforce is here but hasn't been told what to do
- A direct call-to-action linking back to the chat surface
- Optionally: a short list of suggested first steps

This makes the cost of an unengaged user effectively zero (one deterministic email template per day, ~free) while preserving the heartbeat property.

### Scaffolding at Signup

`api/services/workspace_init.py`'s `initialize_workspace()` function gains a Phase 5 (after Phase 4, the manifest write):

```
Phase 5: Default Tasks
    ↓
Create one task:
    - slug: "daily-update"
    - type_key: "daily-update" (from TASK_TYPES registry)
    - mode: "recurring"
    - schedule: "daily"
    - delivery: "email" (resolves to user's email at run time)
    - essential: true
    - status: "active"
    - next_run_at: tomorrow 09:00 UTC
```

This is the only default task. No `track-*` tasks, no platform digests, no synthesis tasks beyond `daily-update` itself. The principle: **the system presumes nothing about what to track, but presumes everything about being present to the user**.

This is intentionally narrow. Future ADRs (notably the parked task tenure work in ADR-160-stub) may add more conditional default tasks. ADR-161 establishes only the floor.

### Idempotency and Backfill

`workspace_init.initialize_workspace()` is already idempotent (it checks for existing `WORKSPACE.md` before re-running). The new Phase 5 must also be idempotent: if a `daily-update` task already exists for the user, do nothing. If not, create it.

For existing users (workspaces created before this ADR), a one-time backfill is required. The backfill is deterministic:

```sql
-- Pseudocode
FOR each user with active workspace AND no daily-update task:
    INSERT into tasks (user_id, slug, mode, schedule, status, next_run_at, essential)
    VALUES (uid, 'daily-update', 'recurring', 'daily', 'active', tomorrow_09utc, true);
    -- Also write TASK.md via TaskWorkspace
```

The backfill runs once at deployment time, against production. It cannot create duplicates due to the existing `tasks_user_slug_unique` constraint, so it is safe to re-run.

### Removal from TP's Conditional Creation Path

Today, TP's onboarding prompt (`api/agents/tp_prompts/onboarding.py`) instructs TP to *conditionally* create a daily-update task as part of its scaffolding flow. This conditional creation path is deleted entirely. After this ADR:

- TP no longer creates daily-update tasks. They exist from signup, period.
- The TP onboarding prompt is updated to *acknowledge* the daily-update as already-existing, and to teach TP how to discuss adjustments to it (cadence, focus, pause/resume).
- If a user asks "can you set up a daily summary," TP recognizes it already exists and offers to refine it instead of creating a duplicate.

This is execution discipline #1 — singular implementation. The daily-update task has one creation path: signup. Not signup-or-conversation, not signup-as-default-with-chat-as-fallback. One path.

### Where the Heartbeat Lives in the Service Model

| Layer | Mechanism | What it does | Independence |
|---|---|---|---|
| **Infrastructure heartbeat** | Render cron, every 5 min | Polls tasks table, fires due tasks | Pure plumbing — user never sees |
| **Daily-update task** | One row in tasks, daily cadence | Produces user-facing artifact in inbox | Standard task in standard pipeline — same execution path as any other task |
| **User experiential heartbeat** | The fact that an email lands at 9am | The user knows the system is alive | Emergent from the above |

These three are conceptually fused but technically independent. The cron can run forever and produce nothing; the daily-update task can be paused; the email can fail to deliver. Each layer has its own failure mode and its own observability.

The daily-update task is **special only in metadata** (`essential = true`). Its execution path is the same as any other task — same `task_pipeline.execute_task()`, same delivery, same DELIVERABLE.md, same evaluation loop. The anchor is a property of the task, not of a separate code path.

---

## Schema Change

Migration `141_add_essential_flag_to_tasks.sql`:

```sql
ALTER TABLE tasks
ADD COLUMN essential boolean NOT NULL DEFAULT false;

CREATE INDEX idx_tasks_essential ON tasks(user_id, essential)
WHERE essential = true;

COMMENT ON COLUMN tasks.essential IS
  'ADR-161: Essential tasks (e.g., daily-update) cannot be deleted or auto-paused. Set at workspace initialization, not user-settable.';
```

The index is intentionally narrow (only essential tasks) since there will be at most one essential task per user.

---

## Code Changes

### `api/services/workspace_init.py`

Add `Phase 5: Default Tasks`:

```python
# Phase 5: Default Tasks (ADR-161)
try:
    from services.primitives.task import handle_create_task

    # Check if daily-update already exists (idempotent)
    existing = client.table("tasks").select("id").eq(
        "user_id", user_id
    ).eq("slug", "daily-update").execute()

    if not (existing.data or []):
        # Create via internal API to ensure TASK.md is written too
        await _create_essential_daily_update(client, user_id)
        result["tasks_created"] = ["daily-update"]
        logger.info(f"[WORKSPACE_INIT] Default task: daily-update (essential)")
except Exception as e:
    logger.warning(f"[WORKSPACE_INIT] Default tasks failed: {e}")
```

A new helper `_create_essential_daily_update()` performs the creation directly (without going through `handle_create_task` which requires an `auth` object):

```python
async def _create_essential_daily_update(client, user_id: str) -> None:
    """Create the essential daily-update task at workspace initialization.

    ADR-161: This is the heartbeat artifact. Every workspace gets one.
    """
    from services.task_workspace import TaskWorkspace
    from services.task_types import build_task_md_from_type
    from datetime import datetime, timezone, timedelta

    # next_run = tomorrow 09:00 UTC
    now = datetime.now(timezone.utc)
    next_run = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)

    # Insert tasks row with essential=true
    row = {
        "user_id": user_id,
        "slug": "daily-update",
        "mode": "recurring",
        "status": "active",
        "schedule": "daily",
        "next_run_at": next_run.isoformat(),
        "essential": True,
    }
    insert_result = client.table("tasks").insert(row).execute()
    if not insert_result.data:
        raise RuntimeError("Failed to insert daily-update task")

    # Write TASK.md via TaskWorkspace
    task_md = build_task_md_from_type(
        type_key="daily-update",
        title="Daily Update",
        slug="daily-update",
        schedule="daily",
        delivery="email",
        agent_slugs=["reporting"],
    )
    tw = TaskWorkspace(client, user_id, "daily-update")
    await tw.write_task(task_md)
```

### `api/services/primitives/manage_task.py`

Guard against deleting or archiving essential tasks:

```python
elif action == "archive":
    task = await _find_task(auth, task_slug, select="id, essential")
    if task.get("essential"):
        return {
            "success": False,
            "error": "essential_task",
            "message": "This task is essential to your workspace and cannot be archived. You can pause it instead."
        }
    # ... existing archive logic
```

The `pause` action is allowed against essential tasks — the user can explicitly opt out. The `update` action (for cadence, delivery) is also allowed.

### `api/services/task_pipeline.py`

Add an empty-state branch in the daily-update execution path:

```python
async def execute_task(client, user_id, task_slug):
    # ... existing context loading

    # ADR-161: Empty-state branch for daily-update
    if task_slug == "daily-update":
        is_empty = await _check_workspace_empty(client, user_id)
        if is_empty:
            # Skip LLM, emit deterministic template
            output = _build_empty_workspace_daily_update(user_id)
            await _save_and_deliver_empty_state(client, user_id, task_slug, output)
            return {"success": True, "task_slug": task_slug, "status": "delivered_empty"}

    # ... existing pipeline
```

The `_check_workspace_empty()` helper does a single SQL query (no LLM): are there other active tasks besides daily-update, AND are any context domain entities populated? If both are false, the workspace is empty.

The `_build_empty_workspace_daily_update()` is a pure Python function that returns a fixed HTML template:

```html
<h1>Your YARNNN workforce is ready</h1>
<p>Good morning. I'm <strong>Reporting</strong>, your synthesizer agent.
I'm here to give you a daily operational digest of what your workforce is doing.</p>
<p>Right now, there's nothing for me to report — your team hasn't been told
what to track yet. That's by design: I don't presume to know what matters
to you until you tell me.</p>
<p><a href="https://yarnnn.com/chat">Open a chat with me</a> and tell me
about your work. I'll set up tracking, kick off research, and tomorrow's
update will have something real to say.</p>
```

This is the minimum-viable empty state. Iteration on the wording is expected.

### `api/agents/tp_prompts/onboarding.py`

Remove the conditional daily-update creation block (currently around line 172):

```python
# DELETE this block (now handled by workspace_init Phase 5):
#   **Daily update:** Always create: `CreateTask(type_key="daily-update", ...)`
```

Replace with an awareness note:

```python
# REPLACE with:
#   **Daily update is already active.** Every workspace has a daily-update task
#   that runs each morning at 09:00 UTC and emails an operational digest. This
#   task is essential and cannot be removed. If the user wants to adjust it
#   (cadence, focus, pause), use ManageTask(action="update") or
#   ManageTask(action="pause"). Do NOT create a new daily-update — it already
#   exists from signup.
```

### `api/prompts/CHANGELOG.md`

A new entry documenting the prompt change.

---

## Documentation Changes

### `docs/architecture/SERVICE-MODEL.md`

Add a new subsection "The Heartbeat Artifact" under Execution Flow, describing:
- Daily-update as the floor
- The three layers of heartbeat (infrastructure cron, daily-update task, user experiential)
- Why this is structurally important to the autonomous-work bet

### `docs/architecture/FOUNDATIONS.md`

Extend Axiom 6 ("Autonomy Is the Product Direction") with a new subsection "The Floor: A System That Reaches You":

> The autonomous mode and the directed mode are peers. Neither is a prerequisite for the other. The system must be able to reach the user — to prove its existence — even before the user has directed any work. The daily-update task is the architectural commitment to this principle: every workspace receives a daily artifact, by default, from day one, with content that scales with workspace maturity. (See ADR-161.)

### `docs/architecture/registry-matrix.md`

Add a small note to the daily-update row in the task type catalog:

> `daily-update` is the **anchor task**. It is scaffolded at workspace initialization with `essential=true` and cannot be deleted. See ADR-161.

### `CLAUDE.md`

Add ADR-161 to the Key Architecture References list with a one-line summary.

### `docs/database/ACCESS.md`

Add a note about the new `tasks.essential` column.

---

## Canary Protocol

Before this code is committed to main, the developer (KVK) is the canary. The protocol:

1. **Migration applied to production first** via psql, against the live Supabase. The new column exists with `default false`, so all existing rows get `essential=false`.
2. **Backfill executed manually** for KVK's user_id only:
   - Insert one task row with `essential=true`, `slug='daily-update'`, `next_run_at=tomorrow 09:00 UTC`.
   - Write TASK.md via TaskWorkspace.
3. **Manual trigger** of the new task via `ManageTask(action="trigger")` or direct `execute_task("daily-update")` call.
4. **Verification:**
   - Email lands in KVK's inbox.
   - Empty-state branch fired (KVK's account currently has zero other active tasks and zero context entities).
   - The email content is the honest empty-state template, not a hallucinated digest.
   - The task appears in the database with `essential=true`.
5. **Only then** commit code, run the production-wide backfill, push to main.

The reason for this ordering: the migration is reversible (drop column), the manual backfill is reversible (delete one row), but a bad commit on main is harder to roll back. Verifying end-to-end on KVK's account before committing means the failure mode is contained to one user.

---

## Cost Implications

### Per-User Monthly Cost

| Workspace state | Daily-update cost/run | Runs/month | Monthly cost |
|---|---|---|---|
| **Empty** (no other tasks, no entities) | $0 (deterministic template) | 30 | **~$0** |
| **Sparse** (some entities, few runs) | ~$0.03 (small Sonnet call) | 30 | **~$0.90** |
| **Active** (full workforce running) | ~$0.05–0.15 (Sonnet with run_log context) | 30 | **~$1.50–4.50** |

For dormant users, the cost is effectively zero. For engaged users, the cost is bounded by the cost of summarizing their actual activity, which is itself small.

### System-Wide Cost Bound

Assuming N total users, of whom 60% are dormant and 40% are active:
- Dormant: 0.6N × $0 = $0
- Active: 0.4N × $3 = $1.20N

For 1,000 users: ~$1,200/month for the daily-update floor across the entire user base. This is well under the noise floor of any other infrastructure cost.

### What This Buys

- Zero dormant signups (every user receives daily proof of life).
- A canary (the developer's account is now perpetually testing the heartbeat).
- A foundation for ADR-160 (Task Tenure) — once tenure exists, every other task gets bounded, and the daily-update remains the only unbounded task. The architecture has a clean exception model.
- An always-honest output channel — the empty-state template is a *call to action*, not a fake digest. It surfaces the gap that existed and gives the user a single click to fill it.

---

## What This ADR Does NOT Do

This ADR is intentionally narrow. It does not:

- **Add task tenure or budgets.** That's ADR-160 (parked).
- **Change the task type registry.** `daily-update` already exists.
- **Change the inference cascade.** That's ADR-162 (Phase 2).
- **Restructure the surface.** That's ADR-163 (Phase 3).
- **Add per-task effectiveness telemetry.** Future ADR.
- **Make any other tasks essential.** Only `daily-update`. The principle is "one floor, not many."
- **Touch the agent roster.** The Reporting agent already exists from ADR-140.

The smallest possible change that makes the workforce visible to a brand-new user.

---

## Open Questions

1. **Should the empty-state template be customizable per user (e.g., based on inferred work context once any inference has run)?** Decision: not in v1. The template is fixed. ADR-162 will introduce inference improvements that may eventually feed the daily-update content, but the empty state itself stays deterministic for cost reasons.

2. **What happens if a user pauses the daily-update?** The task transitions to `paused`. The scheduler skips it. The user can resume via `ManageTask(action="resume")`. The system does not nag or auto-resume. The user's choice is respected. This is consistent with execution discipline #11 (the user is in charge of their own surface).

3. **Should the empty-state email include a tracking pixel or open-tracking?** Out of scope for ADR-161. Engagement telemetry will be addressed in ADR-160 (Task Tenure) when it lands.

---

## Revision History

| Date | Change |
|---|---|
| 2026-04-07 | v1 — Initial. Daily-update as essential anchor task. Empty-state branch. Workspace init Phase 5. Backfill protocol. |
