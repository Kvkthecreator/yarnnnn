# Architecture: Agent Execution Model

**Status:** Canonical
**Date:** 2026-03-25 (rewritten for ADR-141: Unified Execution Architecture)
**Supersedes:** Previous version (pulse-driven execution, strategy pattern, PM coordination)
**Codifies:** ADR-141 (Unified Execution Architecture), ADR-138 (Agents as Work Units), ADR-140 (Workforce Roster)
**Related:**
- [execution-loop.md](execution-loop.md) — **the accumulation cycle** (how run N feeds run N+1 — awareness, tracker, feedback actuation)
- [ADR-141: Unified Execution Architecture](../adr/ADR-141-unified-execution-architecture.md) — governing ADR
- [ADR-138: Agents as Work Units](../adr/ADR-138-agents-as-work-units.md) — task model
- [ADR-140: Agent Workforce Model](../adr/ADR-140-agent-workforce-model.md) — roster model
- [FOUNDATIONS.md](FOUNDATIONS.md) — axioms governing the system (Axiom 5: user-as-supervisor)

> **This doc describes the three-layer architecture** (what the layers are, what triggers exist, what code runs). For the cycle-to-cycle accumulation mechanics — awareness.md handoff, entity tracker rebuild, system verification, feedback actuation, and how context compounds across runs — see [execution-loop.md](execution-loop.md).

---

## The Core Principle: Control Plane / Data Plane

**TP is the control plane. Tasks are the data plane.**

- **TP** (chat or heartbeat) is the only component that creates, modifies, or reprioritizes tasks — changing schedules, adjusting objectives, assigning agents, pausing/resuming work. TP is the only thing that *thinks*.
- **The scheduler** is a dumb executor — reads `tasks.next_run_at <= now` and runs them. No opinions, no LLM, no decisions.
- **The task pipeline** is a mechanical generation engine — reads TASK.md, resolves agent, gathers context, generates, delivers. Same pipeline regardless of trigger source.

This means: TP changes the data (task definitions), the scheduler reads the data and executes. All intelligence about *what should happen* lives in TP. All execution of *what was decided* lives in the pipeline.

### Three Layers

**Layer 1 — Mechanical Backend** (zero LLM cost): Cron-triggered, deterministic, SQL-based.
**Layer 2 — Task Pipeline** (Sonnet per task): Reads TASK.md + AGENT.md → gathers context → generates → delivers.
**Layer 3 — TP Intelligence** (user-driven): Chat mode + periodic heartbeat. The only component that "thinks about" the system.

---

## Trigger Taxonomy

All triggers end in the same `execute_task()` pipeline. The trigger source determines *when*, not *how*.

| Trigger | Source | Latency | How it works |
|---------|--------|---------|-------------|
| **Scheduled** | Cron (5-min cycle) | ≤5 min | Scheduler queries `next_run_at <= now`, calls `execute_task()` |
| **User-initiated** | Chat / UI button | Instant | TP or route calls `execute_task()` directly (bypasses scheduler) |
| **Event-driven** | Slack webhook etc. | Instant | `trigger_dispatch` → `execute_agent_run()` → `execute_task()` |

### Why 5-minute cron + instant manual (not faster cron)

The scheduler cron runs every 5 minutes. This is deliberate:

- **Scheduled tasks** (daily briefing, weekly digest) don't need sub-minute precision. ±5 min is invisible.
- **User-initiated runs** ("run this now") bypass the scheduler entirely — they call `execute_task()` inline. Instant.
- **Faster cron** (1-min) would only help if user-initiated runs went through the scheduler queue, which they don't.
- **Cost**: The cron itself is zero LLM cost (SQL query). The only scaling concern is Composer heartbeat (Haiku, ~$0.001/user/cycle), which 5-min keeps bounded at ~$0.30/user/day for Pro.

The hybrid is correct: mechanical cadence for scheduled work, instant execution for interactive work.

### How TP "moves up the queue"

When a user says "run my research briefing now":
1. TP can call `ManageTask(task_slug=..., action="trigger")` → routes through `_handle_trigger` → `execute_task()` → instant
2. TP can set `tasks.next_run_at = now()` via `ManageTask(action="update")` → scheduler picks it up within 5 min

Both are valid. Option 1 is the default for interactive "run now" semantics.

---

## Layer 1: Mechanical Scheduling

`api/jobs/unified_scheduler.py` — runs every 5 minutes via Render cron.

```
Cron fires (every 5 min)
├── 1. Task execution: SELECT * FROM tasks WHERE status='active' AND next_run_at <= now
│   └── For each due task → execute_task(client, user_id, task_slug)
├── 2. Platform content cleanup (hourly)
├── 3. Workspace ephemeral cleanup (hourly)
├── 4. Import jobs (continuous)
├── 5. Composer heartbeat (Pro: continuous, Free: daily)
├── 6. Memory extraction (nightly)
└── 7. Scheduler heartbeat event
```

No LLM calls. No decision-making. Pure SQL queries and dispatch.

---

## Layer 2: Task Pipeline

`api/services/task_pipeline.py` — the generation pipeline.

### Two internal phases (ADR-182)

**Phase A — Mechanical Context Assembly** (zero LLM): steps 1-6 below. Pure SQL reads against `workspace_files` + DB lookups. Materializes all predictable context into the generation prompt. For `produces_deliverable` tasks, this includes prior output and output inventory — the agent receives everything it needs without tool rounds.

**Phase B — LLM Synthesis**: step 7-8. For `produces_deliverable` tasks: reduced tool surface (`WriteFile` + `RuntimeDispatch` only), 0-1 tool rounds. For `accumulates_context` tasks: full headless tool set, standard tool rounds (agent writes to domain files during execution).

### Task-first entry: `execute_task(client, user_id, task_slug)`

Used by scheduler for due tasks.

```
execute_task(client, user_id, task_slug)
├── Phase A — Mechanical Context Assembly (zero LLM):
│   ├── 1. Read TASK.md (objective, criteria, output spec, agent slug)
│   ├── 2. Resolve agent (DB lookup by slug)
│   ├── 2b. ADR-164 dispatch: if agent.role == 'thinking_partner' → _execute_tp_task() (back office path, skips LLM)
│   ├── 3. Check work budget
│   ├── 4. Create agent_runs record
│   ├── 5. Read AGENT.md + agent memory + preferences
│   └── 6. Gather context (domain files, entity trackers, prior output, agent workspace)
├── Phase B — LLM Synthesis:
│   ├── 7. Build prompt (task objective + agent identity + pre-gathered context)
│   └── 8. Generate (Sonnet — reduced tools for deliverable, full for accumulation)
├── Post-generation:
│   ├── 9. Save output to /tasks/{slug}/outputs/ + /agents/{slug}/outputs/
│   ├── 10. Write to /knowledge/ (accumulation)
│   ├── 11. Compose HTML (render service, non-fatal)
│   ├── 12. Deliver per TASK.md config
│   ├── 13. Update tasks.last_run_at + calculate next_run_at
│   ├── 14. Post-generation: self-observation, agent reflection (ADR-149), agent card
│   └── 15. Work units only (ADR-164: task_executed activity_log write removed — agent_runs row is authoritative)
```

**Back office dispatch (ADR-164)**: when step 2 resolves the assigned agent and finds `role == 'thinking_partner'`, control hands off to `_execute_tp_task()` which reads the TASK.md `## Process` section for an `executor: <dotted.path>` directive, imports the module, calls its `run(client, user_id, task_slug)` async function, writes the structured output to the standard outputs folder, updates `next_run_at`, and returns. Back office tasks bypass steps 3-15 entirely — no credit check, no LLM, no agent_runs row. See [ADR-164](../adr/ADR-164-back-office-tasks-tp-as-agent.md).

### Agent-first entry: `execute_agent_run(client, user_id, agent, trigger_context)`

Used by manual runs (POST /agents/{id}/run), MCP, and `trigger_dispatch.py` (event triggers). The ADR-168 Commit 2 cleanup removed the `Execute` primitive as a caller — TP-initiated triggers now flow through `ManageTask(action="trigger")` instead.

```
execute_agent_run(client, user_id, agent)
├── 1. Look up agent's assigned task (scan TASK.md files)
├── 2a. If task found → execute_task(client, user_id, task_slug)
└── 2b. If no task → _execute_direct() (taskless generation)
```

### Context Gathering (Phase A — Mechanical)

Replaces the old strategy pattern (PlatformBound/CrossPlatform/Analyst/Research).

One function: `gather_task_context()`. Zero LLM cost. Reads from:
1. Task awareness (`awareness.md` — execution state across cycles)
2. Source scope (selected platform sources per task)
3. Domain tracker + entity files (objective-matched from `context_reads`/`context_writes`)
4. Accumulated context domains (`/workspace/context/`)
5. Agent identity + playbooks (`ws.load_context()`)
6. User notes (`notes.md`)
7. Prior output + output inventory (ADR-182 — `outputs/latest/output.md` + file listing)

No strategy selection. No scope-based routing. One path.

### Generation (Phase B — LLM)

Reuses the headless agent loop pattern:
- Model: Sonnet
- Tools: **output_kind-aware** (ADR-182):
  - `produces_deliverable`: reduced set (`WriteFile` + `RuntimeDispatch`), 0-1 tool rounds — all reads pre-gathered
  - `accumulates_context`: full headless primitives, standard tool rounds — agent writes to domain files
  - `external_action`: full headless + platform tools
- Safety: narration stripping, short-output retry, max-tokens handling

---

## Layer 3: TP Intelligence

The only component that "thinks about" the system.

### Chat mode (user-present)
- Streaming, full primitives, session-scoped
- Creates agents, creates tasks, adjusts objectives, answers questions
- Entry point: `/api/chat` → `thinking_partner.py`

### Heartbeat mode (periodic, deferred)
- Headless TP, reads health flags
- Suggests actions, processes pending feedback, assesses workforce
- Triggered by Composer heartbeat in scheduler

---

## The Boundary in Code

```python
# Layer 1: Scheduler (zero LLM)
# api/jobs/unified_scheduler.py
due_tasks = await get_due_tasks(supabase)           # SQL query
success, failed = await execute_due_tasks(supabase, due_tasks)  # dispatch

# Layer 2: Task pipeline (Sonnet per task)
# api/services/task_pipeline.py
result = await execute_task(client, user_id, task_slug)
#   → parse_task_md() → resolve agent → gather_task_context()
#   → build_task_execution_prompt() → _generate() → save → deliver

# Layer 3: TP (user-present or periodic heartbeat)
# api/agents/thinking_partner.py
# Creates tasks, monitors health, chains multi-agent work
```

---

## Mode-Gated Primitives

Primitives declare which modes they are available in via two explicit registries (`CHAT_PRIMITIVES`, `HEADLESS_PRIMITIVES`) in `api/services/primitives/registry.py`.

**Canonical reference:** [primitives-matrix.md](primitives-matrix.md) — substrate × mode × capability-tag matrix for the full primitive surface. That doc is maintained alongside code (ADR-168). This file used to duplicate a smaller version of the matrix and drifted by ~6 weeks across ADR-146, ADR-148, ADR-149, ADR-151, ADR-153, ADR-155, and ADR-168. Point new readers at the matrix doc, not this paragraph.

---

## Key Files

| Concern | File |
|---------|------|
| Scheduler (Layer 1) | `api/jobs/unified_scheduler.py` |
| Task pipeline (Layer 2) | `api/services/task_pipeline.py` |
| Task workspace | `api/services/task_workspace.py` |
| Agent workspace | `api/services/workspace.py` |
| TP (Layer 3) | `api/agents/thinking_partner.py` |
| Primitive registry | `api/services/primitives/registry.py` |
| LLM interface | `api/services/anthropic.py` |
| Delivery | `api/services/delivery.py` |
| Activity log | `api/services/activity_log.py` |

---

## What Was Deleted (ADR-141)

| File | Concept | Replacement |
|------|---------|-------------|
| `agent_pulse.py` | 3-tier pulse (sense→decide) | Scheduler SQL query (is task due?) |
| `execution_strategies.py` | Strategy pattern (5 strategies) | `gather_task_context()` — one function |
| `ROLE_PULSE_CADENCE` | Per-role pulse cadence | Task schedule (`tasks.schedule` + `next_run_at`) |
| PM coordination | PM agent Tier 3 pulse | TP absorbs coordination (ADR-138) |
| Composer per-agent assessment | Pulse-based health signals | Task execution events in activity_log |

---

## Cost Model

| Action | LLM | Cost per execution | With ADR-182 |
|--------|-----|-------------------|---|
| Check if task is due | None (SQL) | $0 | $0 |
| Mechanical context assembly | None (SQL) | $0 | $0 |
| Execute produces_deliverable | Sonnet | ~$0.05-0.12 (multi-round) | ~$0.03-0.06 (single-round) |
| Execute accumulates_context | Sonnet | ~$0.05-0.08 | ~$0.05-0.08 (unchanged) |
| Compose HTML | None (render service) | $0 | $0 |
| User chat message | Sonnet | ~$0.01 | ~$0.01 |

User with 5 weekly produces_deliverable tasks: ~$0.15-0.30/week (with ADR-182) vs ~$0.25-0.60/week (current).

---

## Anti-Patterns

**Using LLM to decide whether to generate**
If a task is due (next_run_at <= now), run it. No Haiku pre-assessment. The schedule IS the decision. The old pulse model (Tier 2 Haiku agent reflection) was dissolved because it added cost without changing the outcome — if a task is scheduled, it should run.

**Making the scheduler "smart"**
The scheduler is a dumb loop: query → execute → update next_run_at. All intelligence about what tasks should exist, what their schedules should be, and whether they should be paused belongs in TP (Layer 3). The scheduler never decides — it only executes what TP has already decided.

**Routing user-initiated runs through the scheduler queue**
When a user says "run this now," call `execute_task()` directly. Don't set `next_run_at = now` and wait for the 5-min cron. The scheduler queue is for autonomous scheduled work; interactive requests deserve instant execution.

**Separate execution paths for different agent types**
One pipeline (`execute_task`) for all agents. Context gathering adapts to scope, but the pipeline is the same.

**Agent-level scheduling**
Scheduling lives on tasks, not agents. An agent can have multiple tasks with different cadences. Mode (recurring/goal/reactive) is a property of the work, not the worker.
