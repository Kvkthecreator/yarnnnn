# ADR-088: Trigger Dispatch

**Status:** Phase 1 Implemented (2026-03-04) — schedule + event call sites. Signal medium path deferred to Phase 2 (requires signal_processing.py changes, combine with ADR-089 un-parking).

**Note on ADR-091:** `agent.acknowledge` (ADR-091) is a chat-driven write path — the user supervises via TP, the agent records an observation. This ADR is about the background path: cron + webhook + signal triggers routing through a single decision point. Parallel paths, not substitutes.

**When to un-park:** When over-reactive full generations from event triggers (Problem 1) or context staleness between scheduled runs (Problem 2) becomes felt in practice. Technical prerequisites are satisfied (ADR-087 fully implemented).

**Date:** 2026-03-03 (v1), 2026-03-04 (v2 — renamed to Trigger Dispatch, restructured around dispatch_trigger())
**Authors:** Kevin Kim, Claude (analysis)
**References:**
- [ADR-087: Agent Scoped Context](ADR-087-workspace-scoping-architecture.md) — `agent_memory` is the write target for medium-strength dispatch
- [ADR-089: Agent Autonomy](ADR-089-agent-autonomy-context-aware-triggers.md) — autonomous context updates that flow through dispatch
- [ADR-068: Signal-Emergent Agents](ADR-068-signal-emergent-agents.md) — signal processing, the third dispatch caller
- [ADR-080: Unified Agent Modes](ADR-080-unified-agent-modes.md) — headless mode used for both high and medium dispatch actions
- [ADR-083: Remove RQ Worker](ADR-083-remove-rq-worker.md) — inline execution model this ADR builds on

---

## Problem

Three separate backend paths all funnel to `execute_agent_generation()` with no shared decision logic:

| Caller | Trigger origin | Current action |
|--------|---------------|----------------|
| `unified_scheduler.py` → `process_agent()` | Cron (every 5min, schedule-based) | Full generation |
| `event_triggers.py` → `execute_event_triggers()` | Platform webhook (Slack, Gmail) | Full generation |
| `unified_scheduler.py` → `run_signal_processing()` | Cron (hourly signal scan) | Full generation OR nothing |

This is binary: every trigger either fires a full version generation or is ignored. Two consequences:

**1. Over-reaction.** A Slack mention in a monitored channel fires a full generation. Sometimes the right action is "note this" — not "generate a new version." Cooldowns mitigate frequency but don't change the action type.

**2. Context staleness.** Between scheduled generations, relevant platform content accumulates but `agent_memory` doesn't update. The next generation sees a batch of context at once rather than incrementally accumulated observations. Signal processing against existing agents currently does nothing — that path is absent.

---

## Decision

### Introduce `dispatch_trigger()` in `api/services/trigger_dispatch.py`

A single function that all background trigger paths call. Receives a trigger and decides the action based on signal strength:

```python
async def dispatch_trigger(
    client,
    agent: dict,
    trigger_type: str,        # 'schedule' | 'event' | 'signal'
    trigger_context: dict,    # type-specific payload (passed through to execution)
    signal_strength: str,     # 'high' | 'medium' | 'low'
) -> str:                     # 'generated' | 'memory_updated' | 'logged'
```

### Action routing

| Signal strength | Action | Cost | Used for |
|----------------|--------|------|---------|
| `high` | `execute_agent_generation()` | Full LLM cost | Schedule fires, direct @mention |
| `medium` | Append observation to `agent_memory` | Haiku-level | Platform event in monitored source, signal against existing agent |
| `low` | Log only (`activity_log`) | Zero LLM cost | Low-relevance activity, already-seen content |

### Signal strength assignment — Phase 1, rule-based

| Trigger | Strength | Rationale |
|---------|----------|-----------|
| `schedule` | always `high` | User configured this schedule — honor it |
| `event` (webhook match) | `medium` | Something happened; accumulate context, let schedule generate |
| `signal` → new agent | `high` | Signal warranted creating this agent; generate immediately |
| `signal` → existing agent | `medium` | Relevant signal; note it for the next generation |

The key behavior change: **event triggers shift from `high` to `medium` by default.** Schedule is the only path that always produces a full version. Events feed memory, not versions directly.

### Caller changes — 3 call sites, surgical

```python
# unified_scheduler.py → process_agent()
# Before:
result = await execute_agent_generation(client, user_id, agent, trigger_context)
# After:
result = await dispatch_trigger(client, agent, 'schedule', trigger_context, 'high')

# event_triggers.py → execute_event_triggers()
# Before:
result = await execute_agent_generation(client, user_id, agent, trigger_context)
# After:
result = await dispatch_trigger(client, agent, 'event', trigger_context, 'medium')

# unified_scheduler.py → run_signal_processing() — existing agent path (currently absent)
# New:
result = await dispatch_trigger(client, agent, 'signal', trigger_context, 'medium')
```

Everything else is unchanged: scheduler cron cadence, webhook handler normalization, `event_triggers.py` matching and cooldown logic, `execute_agent_generation()` itself.

### Concurrency

Medium-strength actions (memory writes) use a Postgres advisory lock per agent inside `dispatch_trigger()`:

```python
async with advisory_lock(client, agent_id):
    current = await get_agent(client, agent_id)
    updated_memory = append_observation(current["agent_memory"], observation)
    await update_agent_memory(client, agent_id, updated_memory)
```

Lightweight, Postgres-native, no new infrastructure. Replaceable with async task queue if needed later without changing the caller interface.

---

## What dispatch_trigger is NOT

- **Not a scheduler.** `unified_scheduler.py` and `platform_sync_scheduler.py` remain the cron entrypoints, unchanged.
- **Not a queue.** No Redis, no RQ, no message broker. Inline execution per ADR-083.
- **Not a TP chat path.** `POST /chat` is entirely separate — streaming, session-scoped, full primitives. It does not go through dispatch.
- **Not a new agent.** Medium-strength dispatch uses a direct Haiku API call to extract an observation string — it does not invoke the headless agent loop.

---

## Implementation Phases

### Phase 1: Rule-based dispatch — IMPLEMENTED (2026-03-04)

- Created `api/services/trigger_dispatch.py` with `dispatch_trigger()`
- High path: delegates to `execute_agent_generation()`, passes result through
- Medium path: builds observation from trigger_context, appends to `agent_memory.observations` (capped at 20), writes `activity_log` event_type `memory_written`
- Low path: writes `activity_log` event_type `scheduler_heartbeat`, no LLM cost
- Concurrency: optimistic read-modify-write (safe at single-user scale; no advisory lock needed)
- Updated 2 call sites:
  - `event_triggers.py` → `execute_event_triggers()`: `dispatch_trigger(..., 'medium')`
  - `unified_scheduler.py` → `process_agent()`: `dispatch_trigger(..., 'high')`
- Signal call site deferred: `trigger_existing` action already advances schedule (high equivalent). True medium-strength signal path requires new action type in `signal_processing.py` — deferred to Phase 2.

No schema changes. No new tables.

### Phase 2: Model-assessed signal strength

Replace rule-based `signal_strength` at call sites with a Haiku classification step inside `dispatch_trigger()`:

```python
signal_strength = await _assess_signal_strength(
    client, agent, trigger_context
)
# Prompt receives: agent title + instructions + current memory summary + incoming event content
# Returns: 'high' | 'medium' | 'low'
```

Phase 1 callers pass `signal_strength` explicitly. Phase 2 makes it optional, falling back to model-assessed when omitted. No caller interface change required for Phase 1 code.

---

## Consequences

### Positive
- Single decision point for all background trigger paths — one place to reason about "what should happen when X fires"
- Event triggers accumulate context rather than generating immediately — scheduled generations become better-informed
- Clear path to ADR-089 autonomous actions: medium-strength dispatch is the same mechanism, just called from new trigger origins
- Concurrency protection for `agent_memory` writes

### Negative
- Event-triggered immediate generation no longer happens by default — users relying on webhook-triggered versions get output at the next scheduled run instead. Mitigated by: schedule triggers remain `high`, manual runs always available.
- Haiku cost per medium-strength event (Phase 2 model-assessed path only; Phase 1 rule-based medium is still Haiku but for observation extraction, not routing)

### Neutral
- `POST /chat` unchanged — TP chat is not a dispatch concern
- Platform sync unchanged — writes to `platform_content`, not `agent_memory`
- `execute_agent_generation()` unchanged — still the `high` path, called by dispatch rather than directly

---

## References

- [event_triggers.py](../../api/services/event_triggers.py) — existing event matching and cooldown infrastructure
- [unified_scheduler.py](../../api/jobs/unified_scheduler.py) — schedule + signal callers
- [agent_execution.py](../../api/services/agent_execution.py) — the `high` path (`execute_agent_generation`)
