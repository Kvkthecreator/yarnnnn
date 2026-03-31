# Activity

> Layer 2 of 4 in the YARNNN four-layer model (ADR-063)
> Two-tier scoping model (ADR-129)

---

## What it is

Activity is the system provenance log — a record of what YARNNN has done. It answers the question "what happened recently?" rather than "what do I know about the user?" (Memory) or "what's on the platforms right now?" (Context).

Every time YARNNN completes something meaningful — runs an agent, syncs a platform, pulses an agent, assembles a project output — it appends a row to `activity_log`. The log is append-only. Nothing is updated or deleted.

**Analogy**: Activity is YARNNN's git commit log. It records what was done, when, and what the outcome was. It is not the output itself (that is Work) and not the content (that is Context).

---

## Two-Tier Scoping Model (ADR-129)

Activity serves two distinct scopes:

### Tier 1 — Workspace Activity (macro)

User-level operational events. "What did my system do today?" Surfaces on the global `/activity` page as a supervision dashboard.

### Tier 2 — Project Activity (micro)

Project-scoped events from three substrates:
1. **Activity events** — `activity_log` rows with `project_slug` in metadata
2. **Conversation** — `session_messages` via project sessions (ADR-125)
3. **Workspace changes** — `workspace_files` timestamps and folder structure

These merge into a unified project timeline via `mergeTimeline()` in the Meeting Room (ADR-124).

---

## What it is not

- Not platform content — that is Context (`platform_content`)
- Not generated output — that is Work (`agent_runs`, workspace output folders)
- Not stable user knowledge — that is Memory (`user_memory`)
- Not a replacement for `agent_runs` or `session_messages` — those hold full records; Activity holds lightweight event summaries
- Not a separate table per project — the same `activity_log` table serves both tiers via metadata filtering

---

## Table: `activity_log`

Append-only. Written by service role only (no user-facing INSERT).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK -> auth.users |
| `event_type` | TEXT | Constrained enum (see below) |
| `event_ref` | UUID | FK to related record (run_id, session_id, etc.) |
| `summary` | TEXT | Human-readable one-liner for prompt injection |
| `metadata` | JSONB | Structured event detail; project events include `project_slug` |
| `created_at` | TIMESTAMPTZ | Auto |

**RLS**: Users can SELECT their own rows. No INSERT/UPDATE/DELETE via user-facing clients — service role only.

---

## Event Type Registry

### Workspace-level events (Tier 1)

| event_type | Written by | When | Scope |
|---|---|---|---|
| `platform_synced` | `platform_worker.py` | After sync batch completes | Platform |
| `content_cleanup` | `unified_scheduler.py` | After expired content removal | Platform |
| `integration_connected` | `routes/integrations.py` | After OAuth connection | Platform |
| `integration_disconnected` | `routes/integrations.py` | After OAuth disconnection | Platform |
| `composer_heartbeat` | `unified_scheduler.py` | After Composer assessment cycle | Composer |
| `agent_bootstrapped` | `onboarding_bootstrap.py` | After auto-created agent on platform connect | Composer |
| `project_scaffolded` | `project_registry.py` | After project scaffolded via registry | Composer |
| `duty_promoted` | `composer.py` | After Composer promoted agent duty | Composer |
| `memory_written` | `memory.py` | After nightly memory extraction | Memory |
| `session_summary_written` | `unified_scheduler.py` | After session summary generation | Memory |
| `chat_session` | `chat.py` | At end of each chat turn | Chat |
| `scheduler_heartbeat` | `unified_scheduler.py` | Every 5 min execution cycle | System |

### Task-level events (Tier 2)

These events carry `task_slug` in their JSONB `metadata` field.

**Task lifecycle events** (ADR-138/149):

| event_type | Written by | When |
|---|---|---|
| `task_created` | `primitives/task.py` | Task created via CreateTask |
| `task_executed` | `task_pipeline.py` | After task execution completes |
| `task_triggered` | `primitives/manage_task.py` | Manual trigger via ManageTask |
| `task_paused` | `primitives/manage_task.py` | Task paused |
| `task_resumed` | `primitives/manage_task.py` | Task resumed |
| `task_evaluated` | `primitives/manage_task.py` | TP evaluated output quality (ADR-149) |
| `task_steered` | `primitives/manage_task.py` | TP wrote steering notes (ADR-149) |
| `task_completed` | `primitives/manage_task.py` | Task marked complete (ADR-149) |

**Agent lifecycle events:**

| event_type | Written by | When |
|---|---|---|
| `agent_run` | `agent_execution.py` | After agent version generated |
| `agent_approved` | `routes/agents.py` | When user approves a run |
| `agent_rejected` | `routes/agents.py` | When user rejects a run |

**Note:** PM coordination events (`pm_pulsed`, `project_heartbeat`, etc.) are from the dissolved project layer (ADR-138). They remain in the `VALID_EVENT_TYPES` set for historical data but are no longer written by current code.

---

## How Activity is written

Each write point is a single `write_activity()` call from `api/services/activity_log.py`. All calls are wrapped in `try/except pass` — a log failure is never allowed to block the primary operation.

The `VALID_EVENT_TYPES` frozenset in `activity_log.py` is the canonical constraint — any event_type not in that set is rejected with a warning log.

```
agent_execution.py
  -> version delivered
  -> write_activity("agent_run", summary="Weekly Digest v3 delivered", metadata={agent_id, project_slug, ...})

agent_pulse.py
  -> pulse decision made
  -> write_activity("agent_pulsed", summary="Observed: no new content", metadata={action, reason, tier, ...})

platform_worker.py
  -> sync batch returns successfully
  -> write_activity("platform_synced", summary="Synced gmail: 12 items", ...)

unified_scheduler.py
  -> agent generation triggered
  -> write_activity("agent_scheduled", summary="Scheduled: Weekly Digest", metadata={agent_id, ...})
```

---

## How Activity is read

### Working memory injection (TP prompt)

`working_memory.py -> _get_recent_activity()` fetches the last 10 events within the last 7 days and includes them in the working memory dict. They are rendered by `format_for_prompt()` as a "Recent activity" block:

```
### Recent activity
- 2026-03-22 09:00 . Weekly Digest v3 generated (staged)
- 2026-03-22 08:45 . Synced gmail: 12 items
- 2026-03-21 14:30 . PM checked on contributors - 2 fresh, 1 overdue
- 2026-03-21 09:00 . Agent pulsed: observe (no new content)
```

This block consumes approximately 300 tokens of the 2,000 token working memory budget.

### Global activity page (`/activity`)

`/api/memory/activity` returns up to 200 events from the last 30 days. Frontend groups by date and provides category filters (Agents, Projects, Memory, Sync, Chat, System). `EVENT_CONFIG` maps each event_type to label, icon, color, and category. Expandable metadata detail panel renders event-specific structured data.

### Project activity (`/api/projects/{slug}/activity`)

Returns project-scoped events filtered by `PROJECT_EVENT_TYPES` + `metadata->>project_slug`. Merged with `session_messages` via `mergeTimeline()` in the Meeting Room tab, sorted by timestamp to create a unified chronological stream.

---

## What Activity enables

**TP grounding**: TP can answer "when did you last run my digest?" or "what happened in last night's sync?" from working memory, without a live database lookup mid-conversation.

**Supervision**: The global activity page provides an auditable trail of what YARNNN has done across the workspace — platform operations, Composer decisions, memory extraction.

**Project intelligence**: Project timelines show agent thinking (pulse decisions), PM coordination (steering, assessment, assembly), and conversation — making agent intelligence visible between output deliveries.

**Cold-start awareness**: On a brand-new account, the activity block is empty. TP knows it has no history. This is better than silence — it's an explicit signal.

---

## Boundaries

| Question | Answer |
|---|---|
| Can users write to Activity directly? | No — service role only |
| Is Activity deleted when an agent is deleted? | No — the log is immutable |
| Does Activity replace `agent_runs`? | No — `agent_runs` holds the full generated content; Activity holds the summary event |
| Does Activity replace `session_messages`? | No — `session_messages` holds the full conversation; Activity holds the lightweight event |
| What happens if a write_activity() call fails? | The calling operation continues — the log write is non-fatal by design |
| How are project events filtered? | Via `metadata->>project_slug` JSONB filtering, not a dedicated column |
| Is there a separate table per project? | No — one table, two conceptual tiers via metadata |

---

## Volume expectations

- Agent runs: ~1-3/day per project
- Agent pulse events: ~4-48/day per agent (varies by role cadence, ADR-126)
- PM pulse events: ~48/day per project (30-min cadence)
- Platform syncs: ~4-8/day per user
- Memory writes: occasional (nightly extraction)
- Chat turns: ~5-20/day per active user

Typical: ~50-200 rows/day per active user (increased from ~20-40 due to pulse events). No TTL — rows accumulate over time. At this volume, the table stays manageable indefinitely.

---

## Frontend Configuration

### EVENT_CONFIG (global activity page)

Master lookup in `web/app/(authenticated)/activity/page.tsx`. Maps each `event_type` to:
- `label` — human-readable name
- `icon` — Lucide icon component
- `color` — Tailwind color class
- `category` — filter group (Agents, Projects, Memory, Sync, Chat, System)

### ACTIVITY_EVENT_CONFIG (project timeline)

Project-specific config in `web/app/(authenticated)/projects/[slug]/page.tsx`. Uses personified labels (e.g., "Check-in" instead of "project_heartbeat"). `formatActivitySummary()` transforms raw metadata into narrative text per event type.

### FILTER_CATEGORIES / CATEGORY_EVENT_TYPES

Category-based filtering on the global activity page. User selects a category chip -> events filtered to matching event_type array.

---

## Related

- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Activity layer design and implementation
- [ADR-124](../adr/ADR-124-project-meeting-room.md) — Meeting Room (activity events as inline chat cards)
- [ADR-125](../adr/ADR-125-project-native-session-architecture.md) — Project-scoped sessions
- [ADR-126](../adr/ADR-126-agent-pulse.md) — Agent Pulse (high-frequency activity source)
- [ADR-129](../adr/ADR-129-activity-scoping-two-tier-model.md) — Two-tier scoping model
- [Four-Layer Model](../architecture/four-layer-model.md) — Architectural overview
- `api/services/activity_log.py` — `write_activity()`, `get_recent_activity()`, `VALID_EVENT_TYPES`
- `api/services/working_memory.py` — `_get_recent_activity()`, prompt injection
- `supabase/migrations/060_activity_log.sql` — Schema
