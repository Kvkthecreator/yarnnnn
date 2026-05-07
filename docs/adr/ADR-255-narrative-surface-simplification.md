# ADR-255: Narrative Surface Simplification

> **Status**: Proposed
> **Date**: 2026-05-07
> **Authors**: KVK, Claude
> **Amends**: ADR-252 (chat routing), ADR-253 D5 (heartbeat triggers — cron: now implemented)
> **Dimensional classification**: **Channel** (Axiom 6) primary — the narrative surface gets cleaner; **Trigger** (Axiom 4) secondary — Reviewer cron heartbeat wired; **Mechanism** (Axiom 5) tertiary — dispatch path complexity reduced

---

## Context

Post-ADR-252/253/254, the system has the right directional architecture — three-party narrative, Reviewer as primary intelligence, deterministic execution router, heartbeat-driven Reviewer wakeup. But accumulated implementation layers from the early "optimistic placeholder" design create ongoing fragility and complexity:

1. **`cron:` heartbeat triggers declared but not implemented** — `_autonomy.yaml` declares `cron: "10 8 * * 1-5"` for the Reviewer's morning proactive wakeup but the scheduler only evaluates `after:` triggers. Dead config.

2. **signal-evaluator fires trade-proposal off the dispatcher path** — bypasses CAS claim, `execution_events` recording, and audit trail. Off-path execution.

3. **`response_stream` is 300-line nested generator** — six levels of nesting with three distinct dispatch paths interleaved. Every bug in chat routing requires navigating this structure.

4. **Optimistic streaming placeholder** — frontend adds empty `assistant` message before first SSE event, then must clean it up when Reviewer handles the turn. Created `reviewerHandledTurn` flag, `REMOVE_LAST_MESSAGE` action, double `loadScopedHistory()` calls. All compensating for one wrong assumption.

5. **`TPContext` is a legacy name** — "Thinking Partner" was retired by ADR-247. The context manages the narrative stream (all roles, all parties). Wrong name, wrong mental model.

6. **`get_or_create_task_session` is dead code** — no callers post-ADR-231 task abstraction sunset.

---

## Decisions

### D1: Implement `cron:` heartbeat triggers in the scheduler

The unified scheduler already runs every 5 minutes. At each tick, after processing due recurrence declarations, scan `heartbeat_triggers` for each active user's `_autonomy.yaml` for `cron:` entries that are due (same `compute_next_run_at` logic as recurrences). When due, fire `heartbeat_turn(trigger_slug="cron:{cron_expr}")`.

This gives the Reviewer its proactive morning wakeup — Simons reads the fresh morning scan at 08:10 ET and posts to the narrative without the operator asking. The `cron:` trigger is a declared commitment to regular Reviewer presence.

Implementation: `_fire_cron_heartbeats(supabase, active_user_ids, now)` in `unified_scheduler.py`. Reads `_autonomy.yaml` per user, finds `cron:` entries in `heartbeat_triggers`, uses `croniter` to check if due since last run, fires asynchronously.

### D2: Fix signal-evaluator off-path trade-proposal dispatch

`trading_signal_evaluator._fire_trade_proposal()` calls `invocation_dispatcher.dispatch()` directly — bypassing the scheduler's CAS claim, `execution_events` recording, and spend ceiling check. This is an off-path invocation.

**Fix**: replace `_fire_trade_proposal()` with a narrative entry: write `role='system'` entry noting "Signal fired — trade-proposal will be evaluated at next scheduler tick." The scheduler's next 5-minute tick picks up `trade-proposal` if it's due. No off-path dispatch.

If the operator needs immediate trade-proposal execution, the Reviewer's heartbeat_turn() (which fires after signal_evaluation completes) can include that as a directive.

### D3: Chat route — three clean dispatch functions, no optimistic placeholder

Extract `response_stream()` into three clean async functions:

```python
async def _dispatch_execution_turn(auth, session_id, request, router_result)
    # Writes system_agent narration from router_result → done SSE. No LLM.

async def _dispatch_reviewer_turn(auth, session_id, request, history)
    # Calls address_turn() → writes reviewer message → done SSE.
    # No streaming placeholder. Yields reviewer_response SSE then done immediately.

async def _dispatch_system_agent_turn(auth, session_id, request, history, ...)
    # Full LLM stream → tool events → system_agent message → done SSE.
```

`response_stream` becomes a clean dispatcher:
```python
async def response_stream():
    await _write_user_message(...)
    
    router_result = await route_execution(auth, request.content)
    if router_result:
        async for e in _dispatch_execution_turn(...): yield e
        return
    
    if _reviewer_triggered(request.content):
        async for e in _dispatch_reviewer_turn(...): yield e
        return
    
    async for e in _dispatch_system_agent_turn(...): yield e
```

**Optimistic placeholder removed**: frontend only adds a message on first `content` SSE event — not at stream start. This eliminates `reviewerHandledTurn`, `REMOVE_LAST_MESSAGE`, and double `loadScopedHistory()`. Single clean path: SSE events arrive → update message in place.

### D4: `TPContext` → `NarrativeContext`

The context manages the **narrative** — the single chat-shaped log of every invocation (FOUNDATIONS Axiom 9). It is not "the Thinking Partner's context."

All-or-nothing rename in one commit:
- `web/contexts/TPContext.tsx` → `web/contexts/NarrativeContext.tsx`
- `TPProvider` → `NarrativeProvider`
- `TPContextValue` → `NarrativeContextValue`
- `useTP()` → `useNarrative()`
- All 46 import sites updated

DB slugs (`thinking_partner`), class names (`YarnnnAgent`), Python internals — unchanged per GLOSSARY exceptions.

### D5: Remove `get_or_create_task_session` dead code

`get_or_create_task_session` has no callers post-ADR-231 (tasks dissolved into recurrence declarations). Delete the function (~80 lines). `_load_task_context` has a live caller (surface content loading for task-detail view) — preserved.

---

## Implementation plan

### Commit 1 — D1: Cron heartbeat triggers in scheduler
- `api/jobs/unified_scheduler.py`: `_fire_cron_heartbeats()` function + call after `dispatch_due_invocations()`

### Commit 2 — D2: Signal evaluator off-path fix
- `api/services/back_office/trading_signal_evaluator.py`: replace `_fire_trade_proposal()` with narrative entry

### Commit 3 — D3: Chat route refactor + placeholder removal
- `api/routes/chat.py`: extract 3 dispatch functions, remove optimistic placeholder path
- `web/contexts/NarrativeContext.tsx` (formerly TPContext): remove `reviewerHandledTurn`, `REMOVE_LAST_MESSAGE` — simplified stream handler
- `web/types/desk.ts`: remove `REMOVE_LAST_MESSAGE` from TPAction

### Commit 4 — D4: TPContext → NarrativeContext rename
- `web/contexts/TPContext.tsx` → `web/contexts/NarrativeContext.tsx`
- All 46 import sites

### Commit 5 — D5: Dead code + docs
- Delete `get_or_create_task_session`
- ADR-255 → Implemented, CLAUDE.md entry

---

## What this does NOT change

- The three-party narrative model (ADR-247) — unchanged
- Reviewer keyword trigger logic — unchanged
- Execution router patterns — unchanged
- Back-office cron chain (outcome-reconcil → calibration → reflection) — correctly cron-based, unchanged
- `narrative-digest` and `proposal-cleanup` — correctly cron-based, unchanged
- The Reviewer's `after:` heartbeat triggers — unchanged, working
