# Architecture: Agent Execution Model

**Status:** Canonical
**Date:** 2026-03-25 (rewritten for ADR-141: Unified Execution Architecture)
**Supersedes:** Previous version (pulse-driven execution, strategy pattern, PM coordination)
**Codifies:** ADR-141 (Unified Execution Architecture), ADR-138 (Agents as Work Units), ADR-140 (Workforce Roster)
**Related:**
- [ADR-141: Unified Execution Architecture](../adr/ADR-141-unified-execution-architecture.md) — governing ADR
- [ADR-138: Agents as Work Units](../adr/ADR-138-agents-as-work-units.md) — task model
- [ADR-140: Agent Workforce Model](../adr/ADR-140-agent-workforce-model.md) — roster model
- [Supervision Model](supervision-model.md) — the complementary UI/UX framing

---

## The Core Principle

Three layers, clean separation. Mechanical scheduling (zero LLM), generation pipeline (Sonnet per task), TP intelligence (user-present + periodic heartbeat).

**Layer 1 — Mechanical Backend** (zero LLM cost): Cron-triggered, deterministic, SQL-based.
**Layer 2 — Task Pipeline** (Sonnet per task): Reads TASK.md + AGENT.md → gathers context → generates → delivers.
**Layer 3 — TP Intelligence** (user-driven): Chat mode + periodic heartbeat. The only component that "thinks about" the system.

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

### Task-first entry: `execute_task(client, user_id, task_slug)`

Used by scheduler for due tasks.

```
execute_task(client, user_id, task_slug)
├── 1. Read TASK.md (objective, criteria, output spec, agent slug)
├── 2. Resolve agent (DB lookup by slug)
├── 3. Check work budget
├── 4. Create agent_runs record
├── 5. Read AGENT.md + agent memory + preferences
├── 6. Gather context (knowledge base + agent workspace)
├── 7. Build prompt (task objective + agent identity + context)
├── 8. Generate (Sonnet, multi-tool-round headless loop)
├── 9. Save output to /tasks/{slug}/outputs/ + /agents/{slug}/outputs/
├── 10. Write to /knowledge/ (accumulation)
├── 11. Compose HTML (render service, non-fatal)
├── 12. Deliver per TASK.md config
├── 13. Update tasks.last_run_at + calculate next_run_at
├── 14. Post-generation: self-observation, self-assessment, agent card
└── 15. Activity log (task_executed) + work units
```

### Agent-first entry: `execute_agent_run(client, user_id, agent, trigger_context)`

Used by manual runs (POST /agents/{id}/run), MCP, Execute primitive, event triggers.

```
execute_agent_run(client, user_id, agent)
├── 1. Look up agent's assigned task (scan TASK.md files)
├── 2a. If task found → execute_task(client, user_id, task_slug)
└── 2b. If no task → _execute_direct() (taskless generation)
```

### Context Gathering

Replaces the old strategy pattern (PlatformBound/CrossPlatform/Analyst/Research).

One function: `gather_task_context()`. Reads from:
1. Agent workspace (AGENT.md, thesis, memory, observations) via `ws.load_context()`
2. Knowledge base (`/knowledge/` — includes platform content synced by platform sync)
3. User memories (`/memory/notes.md`)

No strategy selection. No scope-based routing. One path.

### Generation

Reuses the headless agent loop pattern:
- Model: Sonnet
- Tools: mode-gated headless primitives (Search, Read, List, WebSearch, GetSystemState)
- Tool rounds: scope-aware (platform=2, cross_platform=3, knowledge=3, research=6, autonomous=8)
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

Primitives declare which modes they are available in. One registry.

| Primitive | Chat | Headless |
|-----------|------|----------|
| Search, Read, List, GetSystemState, WebSearch | ✓ | ✓ |
| RefreshPlatformContent | ✓ | ✓ |
| Write, Edit, Execute, Clarify, SaveMemory | ✓ | |
| CreateTask, ReadTask, UpdateTask | ✓ | |
| RuntimeDispatch | | ✓ |

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

| Action | LLM | Cost per execution |
|--------|-----|-------------------|
| Check if task is due | None (SQL) | $0 |
| Execute task (generate) | Sonnet | ~$0.03-0.08 |
| Compose HTML | None (render service) | $0 |
| User chat message | Sonnet | ~$0.01 |
| Composer heartbeat | Haiku | ~$0.001 |

User with 5 weekly tasks: ~$0.25/week generation + $0.03/week heartbeats = **~$0.28/week**.

---

## Anti-Patterns

**Using LLM to decide whether to generate**
If a task is due (next_run_at <= now), run it. No Haiku pre-assessment. The schedule IS the decision.

**Separate execution paths for different agent types**
One pipeline (`execute_task`) for all agents. Context gathering adapts to scope, but the pipeline is the same.

**Agent-level scheduling**
Scheduling lives on tasks, not agents. An agent can have multiple tasks with different cadences. Mode (recurring/goal/reactive) is a property of the work, not the worker.
