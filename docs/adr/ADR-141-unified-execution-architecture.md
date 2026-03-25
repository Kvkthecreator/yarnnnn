# ADR-141: Unified Execution Architecture — Mechanical Scheduling, LLM Generation

> **Status**: Phase 1-3 Implemented (task pipeline + scheduler + all callers rewired; execution_strategies + agent_pulse deleted)
> **Date**: 2026-03-25
> **Authors**: KVK, Claude
> **Supersedes**: ADR-088 (Trigger Dispatch), ADR-126 (Agent Pulse — remaining Tier 1/2)
> **Evolves**: ADR-138 (Task model), ADR-140 (Workforce roster)
> **Preserves**: ADR-117 (Feedback distillation), ADR-118 (Output gateway), ADR-130 (Compose engine)

---

## Context

After ADR-138 (project collapse) and ADR-140 (workforce roster), the execution model is unclear. Multiple overlapping systems exist:

- `agent_pulse.py` — Tier 1/2 pulse with gates that reference dropped columns
- `trigger_dispatch.py` — dispatch logic that routes to execution
- `execution_strategies.py` — strategy pattern (Reporter/Analyst/Researcher) for context gathering
- `agent_execution.py` — 1600+ lines of execution logic with many hardcoded stubs
- Composer heartbeat — separate cron for workforce assessment
- Unified scheduler — queries tasks table but doesn't execute (stub)

These systems were built for the old project/PM model and haven't been cleanly rewired for the agent/task model. The naming is confusing: "TP headless mode" vs "Composer heartbeat" vs "agent pulse" are all variations of "the system does something without the user present."

### The principle: separate decision from execution

| Decision | Needs LLM? | Current | Should be |
|---|---|---|---|
| Is this task due? | No (SQL) | Agent pulse Tier 1 | Scheduler SQL check |
| Should agent generate? | No (task is due = yes) | Agent pulse Tier 2 (Haiku) | Eliminated — if due, run |
| What should agent produce? | Yes (Sonnet) | agent_execution.py | Task execution pipeline |
| Is this output good? | Maybe (Haiku) | Not implemented | Self-check (optional) |
| What tasks should exist? | Yes (TP) | Composer + inference | TP conversation only |
| Is the workspace healthy? | No (SQL) | Composer heartbeat | Mechanical health flags |

---

## Decision

### Three layers, clean separation

**Layer 1: Mechanical Backend (zero LLM cost)**

Cron-triggered, deterministic, SQL-based.

- **Platform sync**: check connection freshness → sync via API calls → write to `/knowledge/`
- **Task scheduling**: `SELECT * FROM tasks WHERE status='active' AND next_run_at <= now()` → trigger execution
- **Workspace cleanup**: delete expired `/working/` files
- **Health flags**: detect anomalies (missed cadences, zero runs in 7 days) → write to `/workspace/health_alerts.md`
- **Cadence calculation**: `next_run_at = last_run_at + interval` (pure math)

**Layer 2: Task Execution Pipeline (LLM cost = generation only)**

Mechanical pipeline triggered by Layer 1. No decision-making — just execution.

```
Scheduler triggers task
    → Read TASK.md (objective, criteria, output spec, agent slug)
    → Resolve agent (DB lookup by slug)
    → Read AGENT.md (identity, expertise)
    → Read agent memory/ (accumulated knowledge)
    → Search /knowledge/ (relevant workspace context)
    → Build execution prompt (task objective + agent identity + context)
    → Generate output (ONE Sonnet call, multi-tool-round)
    → Self-check against criteria (ONE Haiku call, optional)
    → Save output to /tasks/{slug}/outputs/{date}/
    → Compose HTML (render service call, non-fatal)
    → Append to memory/run_log.md
    → Write to /knowledge/ (accumulation)
    → Deliver per TASK.md config
    → Update tasks.last_run_at + calculate next_run_at
    → Write activity event
```

**Layer 3: TP Intelligence (LLM cost = orchestration)**

Runs only when user is present (chat) or on periodic heartbeat (every 6h).

- **Chat mode**: user-driven. Create agents, create tasks, adjust objectives, answer questions.
- **Heartbeat mode**: headless TP. Reads `/workspace/health_alerts.md`. Suggests actions. Processes pending feedback. Assesses workforce.
- **Multi-agent coordination**: TP chains tasks imperatively (TriggerTask with cross-context).

TP is the ONLY component that "thinks about" the system. Everything else is mechanical.

### Naming alignment

| Old (confusing) | New (clean) | What it is |
|---|---|---|
| TP chat mode | **TP** | User present, streaming, full primitives |
| TP headless mode | **Agent execution** | No user, task-triggered, generation pipeline |
| Composer heartbeat | **TP heartbeat** | Periodic headless TP (6h), reads health flags |
| Agent pulse Tier 1 | **Task scheduling gate** | SQL: is task due? |
| Agent pulse Tier 2 | **Dissolved** | No pre-generation assessment needed |
| Agent pulse Tier 3 | **Dissolved** | PM is gone (ADR-138) |
| trigger_dispatch | **Dissolved** | Scheduler triggers execution directly |
| execution_strategies | **Dissolved** | One pipeline reads TASK.md + AGENT.md |
| Composer assessment | **Health flags** | Mechanical anomaly detection |

### Unified scheduler (simplified)

```python
async def run_unified_scheduler():
    """Single cron job. All mechanical work."""

    # 1. Task execution — find and run due tasks
    due_tasks = query("SELECT * FROM tasks WHERE status='active' AND next_run_at <= now()")
    for task in due_tasks:
        await execute_task(client, task["user_id"], task["slug"])

    # 2. Platform sync — check and sync stale connections
    await run_platform_sync_check()

    # 3. Workspace cleanup — expire old /working/ files
    await cleanup_expired_workspace_files()

    # 4. Health flags — detect anomalies, write alerts
    await check_workspace_health()

    # 5. TP heartbeat — wake TP for users with pending flags (every 6h)
    if is_heartbeat_due():
        for user_id in get_users_with_health_flags():
            await run_tp_heartbeat(user_id)

    # 6. Session maintenance — rotate stale sessions, generate summaries
    await maintain_sessions()
```

### Cost model

| Action | LLM | Cost per execution |
|---|---|---|
| Check if task is due | None (SQL) | $0 |
| Execute task (generate) | Sonnet | ~$0.03-0.08 |
| Self-check output | Haiku (optional) | ~$0.001 |
| Compose HTML | None (render service) | $0 |
| TP heartbeat (every 6h) | Sonnet | ~$0.01 |
| User chat message | Sonnet | ~$0.01 |
| Health flag check | None (SQL) | $0 |

User with 5 weekly tasks: ~$0.25/week generation + $0.28/week heartbeats = **~$0.53/week**.

---

## What gets built

### New files

1. **`api/services/task_pipeline.py`** — the mechanical execution pipeline
   - `execute_task(client, user_id, task_slug)` — full pipeline from TASK.md to delivery
   - `build_task_prompt(task_md, agent_md, context)` — builds generation prompt
   - `self_check_output(output, criteria)` — optional Haiku quality gate
   - `calculate_next_run(schedule, last_run_at)` — cadence math

### Modified files

2. **`api/jobs/unified_scheduler.py`** — simplified to call `execute_task()` for due tasks
3. **`api/services/delivery.py`** — update to read delivery config from TASK.md (not agent)
4. **`api/services/agent_pipeline.py`** — retain prompt-building utilities, remove execution logic
5. **`api/agents/thinking_partner.py`** — heartbeat mode prompt injection

### Deleted files

6. **`api/services/agent_pulse.py`** — Tier 1/2 dissolved into scheduler SQL + task pipeline
7. **`api/services/trigger_dispatch.py`** — scheduler triggers directly
8. **`api/services/execution_strategies.py`** — one pipeline replaces strategy pattern
9. **`api/services/agent_execution.py`** — replaced by clean `task_pipeline.py`

### Retained files (no changes)

- `api/services/workspace.py` — AgentWorkspace, KnowledgeBase, TaskWorkspace
- `api/services/primitives/*.py` — all primitives stay (TP's toolbox)
- `api/services/delivery.py` — delivery service (updated to read from TASK.md)
- `api/services/feedback_distillation.py` — edits → preferences.md
- `api/services/context_inference.py` — onboarding context enrichment
- `render/` — output gateway service

---

## Impact on existing systems

### Activity Log

Current activity events that need updating:

| Event | Current source | New source | Change |
|---|---|---|---|
| `agent_generated` | agent_execution.py | task_pipeline.py | Update emit location |
| `agent_pulsed` | agent_pulse.py | **Dissolved** — no pulse events | Delete event type |
| `pm_coordination` | pm_coordination.py | **Deleted** (ADR-138) | Already gone |
| `agent_scheduled` | unified_scheduler.py | unified_scheduler.py | Rename to `task_executed` |

New events:
- `task_executed` — task slug, agent slug, output folder, duration, token usage
- `task_failed` — task slug, error message
- `health_flag` — flag type, affected agent/task

### Render Services

| Service | Impact | Changes |
|---|---|---|
| yarnnn-api | HIGH | task_pipeline.py replaces agent_execution.py. Scheduler rewired. |
| yarnnn-unified-scheduler | HIGH | Calls execute_task() instead of pulse dispatch |
| yarnnn-platform-sync | NONE | Platform sync is unchanged |
| yarnnn-mcp-server | LOW | May need agent lookup updates if execution changes agent state |
| yarnnn-render | NONE | Output gateway unchanged |

### Settings / Configuration

Current settings that need review:
- Work budget (`check_work_budget()`) — still applies, checked in task_pipeline.py
- Tier limits (agent count, source count) — unchanged
- Sync frequency — unchanged (platform sync is Layer 1)
- **No new env vars needed** — task execution uses same Anthropic API key, same Supabase client

### Frontend

- Activity page: update event types (`agent_pulsed` → dissolved, add `task_executed`)
- Agent detail: no changes (execution is task-level, not agent-level)
- Task detail: run history comes from `/tasks/{slug}/outputs/` (already works)
- Settings: no changes

---

## Implementation sequence

### Phase 1: Build task_pipeline.py
- New file with `execute_task()` pipeline
- Reads TASK.md + AGENT.md + knowledge
- Generates via Sonnet (reuse `generate_draft_inline()` or build clean)
- Saves output to task workspace
- Delivers per TASK.md config
- Updates scheduling

### Phase 2: Wire scheduler
- Replace stub with `execute_task()` calls
- Add health flag checks
- Add TP heartbeat trigger (every 6h)

### Phase 3: Delete legacy execution
- Delete: agent_pulse.py, trigger_dispatch.py, execution_strategies.py
- Gut: agent_execution.py (keep only utilities still referenced)
- Update activity_log.py event types

### Phase 4: TP heartbeat
- Headless TP mode with health-flag-aware prompt
- Reads /workspace/health_alerts.md
- Suggests actions to user (or auto-acts if authorized)

### Phase 5: Verify + cleanup
- End-to-end test: create task → scheduler picks up → agent generates → output delivered
- Verify all Render services
- Update docs

---

## Dependency analysis (verified)

### Safe to delete immediately
- `agent_pulse.py` — zero production callers. Dead code.
- `test_adr092_modes.py` — references agent_pulse.py only

### Cannot delete without rewiring
- `agent_execution.py` — `execute_agent_generation()` has 5 production callers:
  - `routes/agents.py` (POST /agents/{id}/run)
  - `routes/admin.py` (admin run endpoint)
  - `mcp_server/server.py` (MCP tool)
  - `services/primitives/execute.py` (Execute primitive)
  - `services/trigger_dispatch.py` (event dispatch)
  - Strategy: build `task_pipeline.py`, redirect callers one by one, then delete

- `execution_strategies.py` — called by `agent_execution.py:1280` for context gathering
  - Strategy: replace with task-aware context gathering in `task_pipeline.py`

- `trigger_dispatch.py` — called by `event_triggers.py:436` for Slack event routing
  - Strategy: event triggers call `execute_task()` directly, or route through scheduler

### Activity log events
- `agent_run` (agent_execution.py:1567) → rename to `task_executed`
- `agent_pulsed` (agent_pulse.py) → dissolve (dead code)
- `memory_written` (trigger_dispatch.py:130,194) → move to task_pipeline.py
- New: `task_executed`, `task_failed`, `health_flag`

### Render services impact
- **API**: HIGH — task_pipeline.py replaces agent_execution.py callers
- **Unified Scheduler**: HIGH — calls execute_task() instead of stub
- **Platform Sync**: NONE — unchanged
- **MCP Server**: LOW — update execute_agent_generation import
- **Output Gateway**: NONE — unchanged

### No new env vars needed

---

## Implementation Notes (2026-03-25)

### Phase 1-3: Implemented

**New files:**
- `api/services/task_pipeline.py` — complete pipeline with two entry points:
  - `execute_task(client, user_id, task_slug)` — task-first: reads TASK.md → resolves agent → gathers context → generates (Sonnet, multi-tool) → saves output → delivers → updates scheduling → writes activity. Used by scheduler.
  - `execute_agent_run(client, user_id, agent, trigger_context)` — agent-first: looks up assigned task, routes through `execute_task()`. Falls back to direct generation if no task. Used by manual runs, MCP, Execute primitive, event triggers.
  - `parse_task_md()` — structured parser for TASK.md
  - `gather_task_context()` — unified context gathering (replaces strategy pattern)
  - `build_task_execution_prompt()` — builds system + user prompt from task + agent identity
  - `_generate()` — headless generation loop (reuses `chat_completion_with_tools`)

**Modified files:**
- `api/jobs/unified_scheduler.py` — `execute_due_tasks()` calls `execute_task()` for each due task. Stub replaced with live execution.
- `api/routes/agents.py` — POST /agents/{id}/run → `execute_agent_run()`
- `api/routes/admin.py` — admin run endpoint → `execute_agent_run()`
- `api/mcp_server/server.py` — run_agent tool → `execute_agent_run()`
- `api/services/primitives/execute.py` — agent.generate action → `execute_agent_run()`
- `api/services/trigger_dispatch.py` — high dispatch → `execute_agent_run()`

**Deleted files:**
- `api/services/agent_pulse.py` — Tier 1/2 pulse dissolved into scheduler SQL + task pipeline.
- `api/services/execution_strategies.py` — strategy pattern replaced by `gather_task_context()`.

**Retained (legacy, no production callers to `execute_agent_generation()` remain):**
- `api/services/agent_execution.py` — helper functions still imported (`_fetch_skill_docs`, `_extract_contributor_assessment`, `_append_self_assessment`, `_generate_agent_card`, `get_next_run_number`, `create_version_record`, `update_version_for_delivery`, `SONNET_MODEL`, narration utilities). Will be dissolved into task_pipeline.py when stable.
- `api/services/trigger_dispatch.py` — still called by event_triggers.py for medium/low dispatch (observation accumulation). High dispatch now routes to `execute_agent_run()`.

### Deferred (Phase 4-5)

- Phase 4: TP heartbeat mode (reads health flags, periodic headless TP)
- Phase 5: Dissolve remaining `agent_execution.py` helpers into `task_pipeline.py`

**Activity events** — `task_executed` event used by both `execute_task()` and `execute_agent_run()`. Legacy `agent_pulsed` events no longer emitted (agent_pulse.py deleted).
