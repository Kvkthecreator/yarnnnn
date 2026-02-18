# ADR-064: Unified Memory Service

**Status**: Accepted
**Date**: 2026-02-18
**Amends**: ADR-059 (Simplified Context Model)
**Relates to**: ADR-063 (Four-Layer Model), ADR-049 (Context Freshness)

---

## Context

ADR-059 established `user_context` as the single Memory store, replacing the complex knowledge_* inference pipeline. It defined two write paths:

1. **User directly** — via Context page UI
2. **TP during conversation** — via `create_memory` / `update_memory` tools

The tool-based approach has problems:

- **Explicit tool calls add friction**: TP must recognize "this is worth remembering" and call a tool, which appears in the conversation as a visible action
- **Categorization overhead**: TP must pick `entry_type` (fact/instruction/preference) and generate a sanitized key
- **TP-centric scope**: Only conversations feed memory — but YARNNN has multiple signal sources (deliverable feedback, activity patterns, platform sync)

### Learning from Claude Code

Claude Code's memory model is **implicit**:
- Claude saves notes without announcing it
- Memory accumulates as a side effect of work
- User can review via `/memory` but doesn't see writes happen

The key insight: **memory formation should be invisible to the user.** They state preferences naturally; the system remembers.

### YARNNN's broader scope

Unlike Claude Code (a CLI for coding), YARNNN has multiple surfaces that generate learnable signals:

| Source | Signal Example |
|--------|----------------|
| TP conversation | "I prefer bullet points" |
| Deliverable feedback | User always edits the intro paragraph |
| Deliverable runs | Weekly digest runs every Monday 9am |
| Platform sync | Calendar shows recurring 1:1 with Sarah |

Memory extraction should be a **backend orchestration concern**, not a TP tool.

---

## Decision: Unified Memory Service

Replace explicit TP memory tools with a backend service that:
1. Receives signals from multiple pipelines
2. Extracts learnable facts at pipeline boundaries
3. Writes to `user_context` (existing table, unchanged schema)

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Signal Sources                          │
├────────────────┬────────────────┬────────────────┬──────────┤
│  Chat Pipeline │  Deliverable   │  Activity Log  │  Future  │
│  (session end) │  (user edits)  │  (patterns)    │  ...     │
└───────┬────────┴───────┬────────┴───────┬────────┴────┬─────┘
        │                │                │             │
        └────────────────┴────────────────┴─────────────┘
                                │
                                ▼
                 ┌──────────────────────────┐
                 │     Memory Service       │
                 │   api/services/memory.py │
                 │                          │
                 │  - process_conversation()│
                 │  - process_feedback()    │
                 │  - process_patterns()    │
                 │  - get_for_prompt()      │
                 └──────────────┬───────────┘
                                │
                                ▼
                 ┌──────────────────────────┐
                 │     user_context         │
                 │     (unchanged)          │
                 └──────────────────────────┘
```

### When extraction runs

Aligned with existing backend orchestration patterns:

| Source | Trigger | Method |
|--------|---------|--------|
| Chat | Session end (timeout or explicit close) | `process_conversation()` |
| Deliverable | User approves edited version | `process_feedback()` |
| Activity | Background job (daily, via unified_scheduler) | `process_patterns()` |

No real-time extraction during conversation. Extract once at pipeline boundaries, like deliverable execution.

### Extraction approach

**v1: Simple**
- **Conversation**: Single LLM call at session end: "What facts about this user are worth remembering?"
- **Deliverable feedback**: Diff analysis — what did user consistently change?
- **Activity patterns**: Rule-based — if user runs X every Monday, note it

**Future**: More sophisticated ML-based extraction, but keep the interface stable.

---

## What Changes

### Delete

| File | Reason |
|------|--------|
| `api/services/extraction.py` | Replaced by `memory.py` |
| `create_memory` tool | TP no longer writes memory explicitly |
| `update_memory` tool | User edits via UI only |
| `delete_memory` tool | User deletes via UI only |
| `suggest_project_for_memory` tool | Project scoping removed in ADR-059 |

### Create

| File | Purpose |
|------|---------|
| `api/services/memory.py` | Unified memory service |

### Modify

| File | Change |
|------|--------|
| `api/routes/chat.py` | Call `memory.process_conversation()` at session end |
| `api/services/working_memory.py` | Use `memory.get_for_prompt()` |
| `api/services/project_tools.py` | Remove memory tools from tool list and handlers |
| `api/agents/thinking_partner.py` | Remove memory tool instructions from prompt |
| `docs/features/memory.md` | Document new implicit model |

---

## Memory Service Interface

```python
# api/services/memory.py

class MemoryService:
    """
    Unified memory extraction and persistence.

    Replaces explicit TP memory tools with implicit extraction
    at pipeline boundaries.
    """

    async def process_conversation(
        self,
        client,
        user_id: str,
        messages: list[dict],
        session_id: str,
    ) -> int:
        """
        Extract memories from a completed TP conversation.

        Called at session end (timeout or explicit close).
        Uses LLM to identify facts worth remembering.

        Returns: Number of memories written
        """

    async def process_feedback(
        self,
        client,
        user_id: str,
        deliverable_id: str,
        original: str,
        edited: str,
    ) -> int:
        """
        Learn from user edits to deliverable output.

        Called when user approves an edited version.
        Analyzes diff to identify consistent patterns.

        Returns: Number of memories written
        """

    async def process_patterns(
        self,
        client,
        user_id: str,
    ) -> int:
        """
        Analyze activity_log for behavioral patterns.

        Called by unified_scheduler (daily job).
        Rule-based pattern detection.

        Returns: Number of memories written
        """

    async def get_for_prompt(
        self,
        client,
        user_id: str,
        token_budget: int = 2000,
    ) -> str:
        """
        Format memories for system prompt injection.

        Called by working_memory.py at session start.
        Returns formatted string for TP system prompt.
        """
```

---

## TP Behavior Change

**Before**: TP had `create_memory` tool, had to decide what to remember, called tool explicitly.

**After**: TP converses naturally. Memory is extracted at session end by backend. TP is unaware of memory writes.

**Prompt change**: Remove memory tool instructions. Add passive note:

```
## About memory

I remember things you've told me across sessions. You don't need to ask me to remember —
if you state a preference or fact, I'll note it for next time.

You can view and edit what I remember in the Context page.
```

---

## Alignment with Existing Patterns

### unified_scheduler.py

Memory pattern extraction runs as a daily job, same pattern as:
- Deliverable execution (check due, execute)
- Import job processing (check pending, process)

```python
# In unified_scheduler.py main()

# Existing
await process_due_deliverables(client)
await process_import_jobs(client)

# New
await process_memory_patterns(client)  # calls memory.process_patterns() per user
```

### activity_log integration

Memory writes still logged to `activity_log` with event_type `memory_written`:

```python
# In memory.py after writing to user_context
await write_activity(
    client=client,
    user_id=user_id,
    event_type="memory_written",
    summary=f"Noted: {content[:60]}...",
    metadata={"key": key, "source": "conversation"}
)
```

---

## What Stays the Same

- `user_context` table schema — unchanged
- User direct edits via Context page — unchanged
- `get_recent_activity()` — unchanged
- Four-layer model (Memory/Activity/Context/Work) — Memory layer mechanics change, concept unchanged
- Working memory prompt format — unchanged, just sourced from `memory.get_for_prompt()`

---

## Migration

1. Create `api/services/memory.py` with service class
2. Update `chat.py` to call `process_conversation()` at session end
3. Remove memory tools from `project_tools.py` (definitions + handlers + TOOL_HANDLERS map)
4. Update TP prompt in `thinking_partner.py`
5. Delete `api/services/extraction.py`
6. Update `working_memory.py` to use `memory.get_for_prompt()`
7. Add daily pattern extraction to `unified_scheduler.py`
8. Update `docs/features/memory.md`
9. Update `CLAUDE.md`
10. Update `api/prompts/CHANGELOG.md`

---

## Known Tradeoffs

### No real-time memory confirmation

User won't see "I'll remember that" during conversation. This is intentional — memory should be invisible. User can review in Context page.

If we find users want confirmation, we can add a subtle indicator (not a tool call, just a note).

### Session-end extraction has latency

If session ends abruptly (browser close), extraction may not run. Mitigate by:
- Frontend sends session-end signal on beforeunload
- Backend has session timeout that triggers extraction

### LLM cost at session end

One extraction call per session adds cost. Mitigate by:
- Only extract if session has meaningful user content
- Use fast model (Haiku) for extraction
- Skip if session is < N messages

---

## Related

- [ADR-059](ADR-059-simplified-context-model.md) — `user_context` table design
- [ADR-063](ADR-063-activity-log-four-layer-model.md) — Activity layer, four-layer model
- [ADR-049](ADR-049-context-freshness.md) — Session philosophy (API coherence, not memory)
- [docs/features/memory.md](../features/memory.md) — User-facing memory documentation
