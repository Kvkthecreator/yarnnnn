# Activity

> Workspace-level event log — narrowed role after ADR-163 and ADR-164
> Originally Layer 2 of 4 in the YARNNN four-layer model (ADR-063)

---

## What it is

`activity_log` is the system's workspace-level event log — a record of events that are *not* naturally captured by the `tasks` or `agent_runs` tables. It answers "what workspace-level things have happened recently?" (platform connections, chat session boundaries, user feedback events).

As of **ADR-164**, activity_log's role has narrowed significantly. The nine task-lifecycle event types that used to be written here were redundant denormalizations of data already captured in `agent_runs` rows and `tasks` table state. They have been **deleted**. Activity_log now holds only workspace-level events that don't have a natural home in the task substrate.

As of **ADR-163**, the dedicated `/activity` page has been **deleted**. User-visible activity surfacing moved to:
- **Per-task activity** → `/work/{slug}` task detail (run history sourced from `agent_runs`)
- **Per-agent activity** → `/agents/{id}` identity + health card
- **Workspace-wide recent activity** → Chat briefing dashboard (sourced from `agent_runs` + remaining `activity_log` workspace events)
- **Diagnostic events** → Settings → System Status (scheduler heartbeats)

**Analogy**: Activity_log is YARNNN's workspace-level event journal — a small, focused record of things that aren't "a task ran" or "an agent produced output." It is NOT the authoritative record of task execution (that's `agent_runs` + `tasks`).

---

## What it is not (post ADR-164)

- **Not a task execution log** — `agent_runs` is the authoritative execution record. Task state transitions (paused, resumed, completed) are captured by the `tasks` table's `status` column and `last_run_at`/`next_run_at` timestamps.
- **Not the source of truth for "what did a task do"** — that lives in `/tasks/{slug}/outputs/{date}/output.md` and the task's run log.
- **Not a replacement for `agent_runs` or `session_messages`** — those hold full records; Activity holds lightweight event summaries only for workspace-level events.
- **Not accumulated workspace context** — that lives in `/workspace/context/`.
- **Not stable user knowledge** — that is Memory (`user_memory`).

---

## Table: `activity_log`

Append-only. Written by service role only (no user-facing INSERT).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK -> auth.users |
| `event_type` | TEXT | Constrained enum (see below) |
| `event_ref` | UUID | FK to related record (session_id, etc.) |
| `summary` | TEXT | Human-readable one-liner |
| `metadata` | JSONB | Structured event detail |
| `created_at` | TIMESTAMPTZ | Auto |

**RLS**: Users can SELECT their own rows. No INSERT/UPDATE/DELETE via user-facing clients — service role only.

---

## Event Type Registry (Post ADR-164)

### Workspace-level events (still written)

| event_type | Written by | When | Purpose |
|---|---|---|---|
| `integration_connected` | `routes/integrations.py` | After OAuth connection | Platform lifecycle |
| `integration_disconnected` | `routes/integrations.py` | After OAuth disconnection | Platform lifecycle |
| `chat_session` | `routes/chat.py` | At end of each chat turn | Session boundary marker |
| `memory_written` | `services/memory.py` | After UpdateContext writes | Memory audit |
| `scheduler_heartbeat` | `jobs/unified_scheduler.py` | Hourly | System health marker |

### Feedback events (still written)

| event_type | Written by | When |
|---|---|---|
| `agent_feedback` | `services/feedback_distillation.py` | When user edits/corrects an agent output |
| `agent_approved` | `routes/agents.py` | When user approves a run |
| `agent_rejected` | `routes/agents.py` | When user rejects a run |

### Task-lifecycle events (DELETED per ADR-164)

These event types **are no longer written** by any code path. They were redundant denormalizations of authoritative state already in `agent_runs` and `tasks`. Historical rows remain queryable; new writes have been removed.

| event_type | Authoritative source | Why removed |
|---|---|---|
| `task_executed` | `agent_runs` row per run | Run record IS the execution log |
| `task_triggered` | `agent_runs` row + `tasks.last_run_at` | Trigger is a run, captured there |
| `task_paused` | `tasks.status = 'paused'` + `updated_at` | Current state is authoritative |
| `task_resumed` | `tasks.status = 'active'` + `next_run_at` | Current state is authoritative |
| `task_completed` | `tasks.status = 'completed'` | Current state is authoritative |
| `task_evaluated` | `/tasks/{slug}/memory/feedback.md` (ADR-149) | Evaluation lives in task memory |
| `task_steered` | `/tasks/{slug}/memory/steering.md` (ADR-149) | Steering lives in task memory |
| `task_created` | `tasks` row + `/tasks/{slug}/TASK.md` | Creation record is the row + charter |
| `agent_run` | `agent_runs` row | The row IS the record |

**Historical drift (pre-ADR-164):** `VALID_EVENT_TYPES` in `activity_log.py` may still include these types for backward-compatible querying of old data. They are no longer written. Further housekeeping can remove them from the enum once historical rows are no longer needed.

---

## How Activity is written

Each write point is a `write_activity()` call from `api/services/activity_log.py`. All calls are wrapped in `try/except pass` — a log failure never blocks the primary operation.

```
routes/integrations.py
  -> OAuth connection succeeds
  -> write_activity("integration_connected", summary="Connected Slack", metadata={platform, ...})

routes/chat.py
  -> Chat turn completes
  -> write_activity("chat_session", ...)

unified_scheduler.py
  -> Hourly diagnostic
  -> write_activity("scheduler_heartbeat", summary="Scheduler healthy", metadata={tasks_found, ...})
```

---

## How Activity is read (post ADR-163)

### Working memory injection (TP prompt)

`working_memory.py` can still inject recent workspace-level events into TP's compact index (ADR-159) if a future signal needs it, but the primary "what's been happening" signal TP sees comes from `tasks` + `agent_runs` state, not from activity_log.

### Chat briefing dashboard (ADR-163)

The Chat home page's "Recent activity" feed unions:
1. Recent `agent_runs` rows (task executions, the majority of user-visible activity)
2. Recent `activity_log` rows of the remaining workspace event types (OAuth, chat, feedback)

This produces a coherent "what happened recently" feed without the denormalization of task lifecycle events.

### `/activity` page — DELETED (ADR-163)

The top-level activity page is gone. Users who want to see "everything that happened" navigate through per-entity surfaces or the Chat briefing.

---

## What activity_log enables (post ADR-164)

**Workspace event audit**: Platform OAuth lifecycle, chat session boundaries, user feedback events — things that don't naturally belong to a task or agent_run.

**Diagnostic telemetry**: Scheduler heartbeat writes provide a quick "is the cron alive" signal without requiring a separate metrics pipeline.

**Cold-start awareness**: On a brand-new account, activity_log is empty. Combined with empty `agent_runs`, TP knows the workspace is fresh.

---

## Boundaries

| Question | Answer |
|---|---|
| Can users write to Activity directly? | No — service role only |
| Does Activity replace `agent_runs`? | No — `agent_runs` is the authoritative task execution record |
| Does Activity replace `tasks`? | No — `tasks` is the authoritative work unit record |
| Is Activity deleted when an agent is deleted? | No — the log is immutable; rows may reference dead entities |
| What happens if a `write_activity()` call fails? | The calling operation continues — the log write is non-fatal by design |

---

## Volume expectations (post ADR-164)

Activity_log volume dropped significantly after ADR-164 deleted the nine task-lifecycle writes. New per-user daily estimate:

- Integration events: occasional (OAuth connect/disconnect, ~0-2/week)
- Chat sessions: ~5-20/day per active user
- Memory writes: ~2-10/day during active conversations
- Feedback events: ~0-5/day depending on user engagement
- Scheduler heartbeats: 24/day (hourly, one per active workspace)

Typical: **~10-30 rows/day per active user** (was ~20-60 pre-ADR-164). No TTL — rows accumulate over time.

---

## Related

- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Original activity layer design (role since narrowed)
- [ADR-149](../adr/ADR-149-task-lifecycle-architecture.md) — Task lifecycle primitives (evaluation/steering now written to task memory files, not activity_log)
- [ADR-159](../adr/ADR-159-filesystem-as-memory.md) — Working memory compact index (TP prompt)
- [ADR-163](../adr/ADR-163-surface-restructure.md) — Surface restructure, /activity page deleted
- [ADR-164](../adr/ADR-164-back-office-tasks-tp-as-agent.md) — Task-lifecycle events deleted as redundant; back office tasks visible via `agent_runs` and `/work` surface
- `api/services/activity_log.py` — `write_activity()`, `VALID_EVENT_TYPES`
- `api/services/working_memory.py` — `format_compact_index()` (ADR-159)
