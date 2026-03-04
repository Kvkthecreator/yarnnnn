# ADR-088: Unified Input Processing & Work Serialization

**Status:** Proposed (Parked — superseded in part by ADR-091 `deliverable.acknowledge` action; un-park when event trigger volume justifies full graduated response routing)
**Date:** 2026-03-03
**Authors:** Kevin Kim, Claude (analysis)
**References:**
- [ADR-087: Deliverable Scoped Context](ADR-087-workspace-scoping-architecture.md) — the storage fields this ADR routes writes to
- [ADR-080: Unified Agent Modes](ADR-080-unified-agent-modes.md) — the two execution modes
- [ADR-068: Signal-Emergent Deliverables](ADR-068-signal-emergent-deliverables.md) — existing signal detection
- [ADR-089: Agent Autonomy](ADR-089-agent-autonomy-context-aware-triggers.md) — autonomous actions that build on this routing
- [Development Landscape](../analysis/workspace-architecture-landscape.md) — Step 2

---

## Context

YARNNN has five input types that can trigger work on a deliverable, handled by five separate code paths with no unified decision model:

| Input type | Current handler | Action |
|------------|----------------|--------|
| User messages | `POST /chat` → TP agent loop | Full conversation |
| Scheduled generation | `unified_scheduler.py` → headless | Full generation |
| Platform events | `event_triggers.py` → headless | Full generation (with cooldown) |
| Signal detection | `unified_scheduler.py` (hourly) | Create new deliverable OR ignore |
| Platform sync | `platform_sync_scheduler.py` | Write to platform_content (not deliverable-scoped) |

This scattered approach has two problems:

1. **No graduated response.** Every trigger either fires a full generation or is ignored. With `deliverable_memory` (ADR-087), a lighter action is possible: update the deliverable's memory without generating a full version.

2. **No concurrency coordination.** If two inputs target the same deliverable simultaneously, both write to `deliverable_memory` with no serialization. With one user and temporal separation this is safe, but it becomes a real risk as input frequency increases.

### What OpenClaw does

OpenClaw routes all inputs through a **Gateway** (unified routing) to a **Lane Queue** (serial execution per workspace). YARNNN doesn't need the full infrastructure, but it needs the **conceptual unification**: one decision point for "something happened relevant to this deliverable — what action should the agent take?"

---

## Decision

### Introduce `process_deliverable_input()`

A single function that all deliverable-relevant input paths call. It receives an input event and decides the action:

```python
async def process_deliverable_input(
    client,
    deliverable_id: str,
    input_type: str,       # 'schedule' | 'event' | 'signal' | 'heartbeat'
    input_data: dict,      # type-specific payload
    signal_strength: str   # 'high' | 'medium' | 'low'
) -> str:                  # 'generated' | 'memory_updated' | 'logged'
```

### Action routing

| Signal strength | Action | Cost | Example |
|----------------|--------|------|---------|
| **High** | Full generation (`execute_deliverable_generation()`) | Opus-level | Schedule fires, direct @mention, user-configured trigger |
| **Medium** | Memory update (append to `deliverable_memory`) | Haiku-level | New messages in monitored channel, tangential signal |
| **Low** | Log only (to `event_trigger_log`) | Zero LLM cost | Low-relevance activity, already-seen content |

Signal strength can be:
- **Rule-based:** Schedule and direct mentions = high. Platform events with cooldown = medium. Everything else = low.
- **Model-assessed:** Haiku classifies relevance given the deliverable's instructions and current memory. (Phase 2 of this ADR, after rule-based validates.)

### Callers

| Current code path | Change |
|-------------------|--------|
| `unified_scheduler.py` (scheduled generation) | Calls `process_deliverable_input(type='schedule', strength='high')` |
| `event_triggers.py` (platform events) | Calls `process_deliverable_input(type='event', strength=assessed)` |
| Signal processing (hourly in `unified_scheduler.py`) | For existing deliverables: calls `process_deliverable_input(type='signal', strength='medium')`. For new: still creates deliverable. |
| Future heartbeat | Calls `process_deliverable_input(type='heartbeat', strength='medium')` |

### Concurrency serialization

Within `process_deliverable_input()`, use **Postgres advisory locks** per deliverable for `deliverable_memory` writes:

```python
async with advisory_lock(client, deliverable_id):
    current = await get_deliverable_memory(client, deliverable_id)
    updated = merge_memory(current, new_data)
    await update_deliverable_memory(client, deliverable_id, updated)
```

This is lightweight (Postgres-native, no new infrastructure) and sufficient for current scale. If YARNNN grows to need true queuing, the advisory lock can be replaced with an async task queue without changing the caller interface.

---

## Implementation

### Phase 1: Unified routing (ADR-087 Phase 2)

- Create `api/services/input_router.py` with `process_deliverable_input()`
- Refactor `event_triggers.py` to call it instead of directly calling `execute_deliverable_generation()`
- Refactor scheduled generation in `unified_scheduler.py` to call it
- Add advisory lock for `deliverable_memory` writes
- Rule-based signal strength (high/medium/low based on input type)

### Phase 2: Model-assessed routing (after validation)

- Add Haiku-based relevance assessment for medium-strength signals
- The assessment prompt receives: deliverable title, instructions, current memory summary, incoming content
- Returns: relevance score + suggested observation (if medium) or generation trigger (if high)

---

## Consequences

### Positive
- One decision point for all deliverable-relevant inputs
- Graduated response: not everything triggers full generation
- Clear path to heartbeat and autonomous actions (ADR-089)
- Concurrency protection via advisory locks

### Negative
- Refactor of existing event trigger and scheduler code
- Advisory locks add latency (~1ms per lock acquisition, negligible)
- Model-assessed routing (Phase 2) adds Haiku cost per event

### Neutral
- `POST /chat` (user messages) does NOT go through this function — TP chat is a fundamentally different interaction pattern (streaming, multi-turn) that shouldn't be gated by input routing
- Platform sync unchanged — it writes to `platform_content`, not `deliverable_memory`

---

## References

- [OpenClaw Gateway Architecture](https://docs.openclaw.ai/cli/gateway) — the unified routing pattern
- [Pre-ADR Analysis Section 12](../analysis/workspace-architecture-analysis-2026-03-02.md) — OpenClaw deep-dive
- [event_triggers.py](../../api/services/event_triggers.py) — existing event matching
