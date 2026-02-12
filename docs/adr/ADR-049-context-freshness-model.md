# ADR-049: Context Freshness Model

> **Status**: Accepted
> **Created**: 2026-02-12
> **Deciders**: Kevin (solo founder)
> **Related**: ADR-038 (Single Storage Layer), ADR-039 (Unified Context Surface), ADR-048 (Direct MCP Access)

---

## Context

### The Core Insight

Claude Code's context model works because the **filesystem is static and recoverable**:
- Files don't disappear between sessions
- History is disposable - you can always re-read files
- Each session starts fresh with current state

YARNNN's context comes from **dynamic platform sources** (Slack, Notion, Gmail). We previously tried to manage this through session history and memory extraction. This created complexity around:
- History compression
- Session rollup
- Memory vs history boundaries

### The Reframe

Instead of history management, we need **context freshness management**.

```
Claude Code Model:
  Filesystem (static) → [git pull] → Updated filesystem → Analysis

YARNNN Equivalent:
  Platform state → [targeted sync] → ephemeral_context → Analysis + Generation
```

The platforms ARE our filesystem. Syncing IS our git pull. Each deliverable generation should work with **current state**, not accumulated history.

---

## Decision

### 1. Context Freshness, Not History Compression

**We do NOT need:**
- Session summarization/rollup
- History compression when context overflows
- Memory extraction to reduce history

**We DO need:**
- Source snapshot tracking on deliverables
- Freshness metadata on synced content
- Targeted sync before generation

### 2. Deliverable-Anchored Source Tracking

Each `deliverable_version` records what sources were used and when:

```json
{
  "source_snapshots": [
    {
      "platform": "slack",
      "resource_id": "C123ABC",
      "resource_name": "#product-updates",
      "synced_at": "2026-02-05T09:00:00Z",
      "platform_cursor": "1707123456.000100",
      "item_count": 47
    },
    {
      "platform": "notion",
      "resource_id": "abc123-def456",
      "resource_name": "Board Notes",
      "synced_at": "2026-02-05T09:00:00Z",
      "last_edited_at": "2026-02-03T14:00:00Z"
    }
  ]
}
```

This is the "git commit" equivalent - immutable record of what state was used.

### 3. Freshness Metadata on ephemeral_context

The `ephemeral_context` table tracks current sync state:

```json
{
  "sync_metadata": {
    "synced_at": "2026-02-05T09:00:00Z",
    "platform_cursor": "1707123456.000100",
    "item_count": 47,
    "source_latest_at": "2026-02-04T18:30:00Z"
  }
}
```

This enables freshness checks without re-querying platforms.

### 4. Freshness Check Before Generation

When `Execute(action="deliverable.generate")` is called:

1. **Load deliverable sources** from config
2. **Check freshness** - compare ephemeral_context.sync_metadata with platform state
3. **Sync if stale** - targeted sync of only stale sources
4. **Generate with fresh context**
5. **Record snapshots** - store source_snapshots on new version

```python
async def check_source_freshness(deliverable, auth) -> dict:
    """Compare last sync with current platform state."""
    sources = deliverable.get("sources", [])
    stale = []

    for source in sources:
        # Get current sync state from ephemeral_context
        synced = await get_sync_metadata(auth, source["platform"], source["resource_id"])

        # Get platform's current state (lightweight metadata call)
        current = await get_platform_resource_state(auth, source["platform"], source["resource_id"])

        if current["latest_at"] > synced.get("source_latest_at", "1970-01-01"):
            stale.append({
                **source,
                "synced_at": synced.get("synced_at"),
                "current_latest": current["latest_at"]
            })

    return {"fresh": len(stale) == 0, "stale_sources": stale}
```

### 5. Simplified Session Model

Sessions are for **API coherence only**, not context memory:

| Aspect | Old Model | New Model |
|--------|-----------|-----------|
| Purpose | Context continuity | API coherence (tool_use blocks) |
| History | Compressed/rolled up | Simple truncation (last N messages) |
| Scope | Daily with accumulation | Daily, stateless |
| "Where we left off" | Session history | Deliverable state |

**Token budget**: Replace `MAX_HISTORY_MESSAGES = 30` with token-based limit (~50k tokens for history).

**No compression needed**: If user needs prior context, they ask "remind me about my board update" and TP reads deliverable state fresh.

---

## Architecture

### The Two Concerns (Separated)

```
ephemeral_context (mutable)
├── What's synced now
├── sync_metadata: {synced_at, cursor, item_count}
└── Items from platforms

deliverable_versions.source_snapshots (immutable)
├── What was used at generation time
├── Exact sync timestamps
└── Enables "what changed since last time"
```

Deliverable owns **"what I used"** (audit trail).
ephemeral_context owns **"what's current"** (for freshness checks).

### Flow: Deliverable Generation

```
User: "Generate my board update"
                ↓
TP: Execute(action="deliverable.generate", target="deliverable:uuid")
                ↓
    ┌─────────────────────────────────────┐
    │ 1. Load deliverable config          │
    │    - sources: [slack:#updates, ...]  │
    │    - style, template, recipients     │
    └─────────────────────────────────────┘
                ↓
    ┌─────────────────────────────────────┐
    │ 2. Check freshness                  │
    │    - For each source:               │
    │      - Get ephemeral_context state  │
    │      - Compare with platform state  │
    │    - Result: [stale sources]        │
    └─────────────────────────────────────┘
                ↓
    ┌─────────────────────────────────────┐
    │ 3. Sync stale sources (targeted)    │
    │    - Only sync what's needed        │
    │    - Update ephemeral_context       │
    └─────────────────────────────────────┘
                ↓
    ┌─────────────────────────────────────┐
    │ 4. Generate with fresh context      │
    │    - Read from ephemeral_context    │
    │    - Apply style/template           │
    └─────────────────────────────────────┘
                ↓
    ┌─────────────────────────────────────┐
    │ 5. Record version with snapshots    │
    │    - Store source_snapshots         │
    │    - Immutable audit trail          │
    └─────────────────────────────────────┘
```

### Flow: Session (Chat)

```
User opens /dashboard
        ↓
┌─────────────────────────────────────┐
│ Get or create daily session         │
│ Load last N messages (token budget) │
└─────────────────────────────────────┘
        ↓
User: "What's in my board update?"
        ↓
┌─────────────────────────────────────┐
│ TP reads deliverable state fresh    │
│ (Not from session history)          │
│ Read(ref="deliverable:uuid")        │
└─────────────────────────────────────┘
        ↓
TP: "Your Board Update has 3 versions..."
```

---

## Implementation

> **Status**: ✅ Completed 2026-02-12

### Phase 1: Schema Updates ✅

Migration: `042_context_freshness.sql`

- Added `source_snapshots JSONB` to `deliverable_versions`
- Added `sync_metadata JSONB` to `ephemeral_context`
- Created `sync_registry` table for tracking current sync state per source
- Added helper functions for sync state management

### Phase 2: Freshness Check Service ✅

Created `api/services/freshness.py`:
- `check_deliverable_freshness(client, user_id, deliverable)` - check if sources are fresh
- `get_sync_state(client, user_id, platform, resource_id)` - get current sync state
- `update_sync_registry(...)` - update sync state after storing context
- `record_source_snapshots(client, version_id, sources_used)` - record what was used
- `sync_stale_sources(client, user_id, stale_sources)` - targeted sync via job queue
- `compare_with_last_generation(...)` - "what changed since last generation"

### Phase 3: Update Generation Flow ✅

Modified `api/services/deliverable_execution.py`:
1. Freshness check before generation
2. Targeted sync of stale sources
3. Record source_snapshots on new version

Updated `api/services/ephemeral_context.py`:
- `store_slack_context_batch` updates sync_registry after storing
- `store_gmail_context_batch` updates sync_registry after storing
- `store_notion_context` updates sync_registry after storing

### Phase 4: Token-Based Session History ✅

Updated `api/routes/chat.py`:
- `MAX_HISTORY_TOKENS = 50000` (replaced message count)
- `estimate_message_tokens(message)` - token estimation for messages
- `truncate_history_by_tokens(messages, max_tokens)` - token-based truncation
- Updated `build_history_for_claude()` to use token budget
- Documented that sessions are API coherence only (not context memory)

---

## Consequences

### Positive

1. **Aligned with Claude Code model** - Context is "filesystem", sync is "git pull"
2. **Explicit freshness** - Always know what state was used
3. **Targeted sync** - No blanket updates, cost-efficient
4. **Simplified sessions** - No compression complexity
5. **Audit trail** - source_snapshots enable "what changed" analysis

### Negative

1. **Schema migration** - Need to add columns to existing tables
2. **Platform metadata calls** - Freshness check adds API calls
3. **Learning curve** - Team needs to understand freshness model

### Mitigations

- Platform metadata calls are lightweight (just timestamps, not content)
- Can cache freshness state for short periods
- Clear documentation of the model

---

## Future Considerations

### Focus Mode (Deferred)

Single surface is correct for now. Future enhancement: user explicitly says "let's work on [deliverable]" and UI/context narrows to that deliverable's domain.

### Auto-Update Jobs (Deferred)

Current model: sync triggered by deliverable generation.
Future: background jobs that pre-sync high-frequency sources.

This would update ephemeral_context proactively, so generation finds fresh data without waiting.

---

## See Also

- [ADR-038: Single Storage Layer](ADR-038-single-storage-layer.md)
- [ADR-039: Unified Context Surface](ADR-039-unified-context-surface.md)
- [ADR-048: Direct MCP Access](ADR-048-direct-mcp-access.md)
- [ADR-006: Session and Message Architecture](ADR-006-session-message-architecture.md)
