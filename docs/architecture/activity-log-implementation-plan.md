# Activity Log — Implementation Plan

**ADR**: ADR-063
**Status**: Ready to implement
**Last updated**: 2026-02-18

---

## Overview

Implement the `activity_log` table and wire it into all four write points, then read recent events into the TP working memory at session start.

Seven discrete steps. Each is independently testable.

---

## Step 1: Apply Migration

Run the migration against the Supabase database.

```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require" \
  -f supabase/migrations/060_activity_log.sql
```

**Verify**:
```bash
psql "..." -c "\d activity_log"
psql "..." -c "SELECT * FROM activity_log LIMIT 0;"  -- confirm table exists
```

---

## Step 2: Create `api/services/activity_log.py`

New module. Single public function: `write_activity()`. All write points import from here.

```python
# api/services/activity_log.py
"""
Activity Log — ADR-063

Append-only system provenance log. Records what YARNNN has done across all pipelines.
Written by: deliverable execution, platform sync, chat pipeline, TP memory tools.
Read by: working_memory.py (recent 10 events injected into TP session prompt).

Never called by users directly. All writes are service-role.
"""

import logging
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


async def write_activity(
    client,
    user_id: str,
    event_type: str,
    summary: str,
    event_ref: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Optional[str]:
    """
    Append an event to activity_log.

    Args:
        client: Supabase service-role client
        user_id: The user this event belongs to
        event_type: One of 'deliverable_run', 'memory_written', 'platform_synced', 'chat_session'
        summary: Human-readable one-liner (shown in working memory block)
        event_ref: UUID of related record (version_id, session_id, etc.) — optional
        metadata: Structured detail dict — optional

    Returns:
        activity_log row id, or None on error (non-fatal — caller should continue regardless)
    """
    if event_type not in {"deliverable_run", "memory_written", "platform_synced", "chat_session"}:
        logger.warning(f"[activity_log] Unknown event_type: {event_type}")
        return None

    try:
        row = {
            "user_id": user_id,
            "event_type": event_type,
            "summary": summary,
        }
        if event_ref:
            row["event_ref"] = str(event_ref)
        if metadata:
            row["metadata"] = metadata

        result = client.table("activity_log").insert(row).execute()
        inserted = result.data[0] if result.data else {}
        return inserted.get("id")

    except Exception as e:
        # Non-fatal: activity log failures should never block the primary operation
        logger.error(f"[activity_log] Failed to write event ({event_type}): {e}")
        return None


async def get_recent_activity(
    client,
    user_id: str,
    limit: int = 10,
    days: int = 7,
) -> list[dict]:
    """
    Fetch recent activity events for working memory injection.

    Args:
        client: Supabase client
        user_id: The user
        limit: Max rows to return (default 10, ~300 tokens in prompt)
        days: Lookback window in days (default 7)

    Returns:
        List of activity_log rows ordered by created_at DESC.
    """
    from datetime import datetime, timedelta, timezone
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    try:
        result = (
            client.table("activity_log")
            .select("event_type, event_ref, summary, metadata, created_at")
            .eq("user_id", user_id)
            .gte("created_at", since)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    except Exception as e:
        logger.error(f"[activity_log] Failed to fetch recent activity: {e}")
        return []
```

---

## Step 3: Write Point — Deliverable Execution

**File**: [api/services/deliverable_execution.py](../../api/services/deliverable_execution.py)

**Where**: After step 9 ("Update deliverable last_run_at"), before step 10 (full_auto governance).
Current context: `deliverable_execution.py` around line 542.

**Add** (after `client.table("deliverables").update(...).execute()` at line 542):

```python
# Activity log: record this deliverable run
try:
    from services.activity_log import write_activity
    status_label = final_status if 'final_status' in dir() else 'staged'
    deliverable_title = deliverable.get("title", "Deliverable")
    await write_activity(
        client=client,
        user_id=user_id,
        event_type="deliverable_run",
        summary=f"{deliverable_title} v{next_version} generated ({status_label})",
        event_ref=version_id,
        metadata={
            "deliverable_id": str(deliverable_id),
            "version_number": next_version,
            "strategy": strategy.strategy_name,
            "sources_count": len(gathered_result.sources_used),
        },
    )
except Exception:
    pass  # Non-fatal
```

Note: the `final_status` variable is set during step 10 (full_auto). Insert the activity write after step 10 so the status is accurate. Actual placement: after the `if governance == "full_auto"` block (around line 575), before the final `logger.info`.

**Correct placement** (after line 575, before `logger.info`):
```python
# Activity log: record this deliverable run (ADR-063)
try:
    from services.activity_log import write_activity
    deliverable_title = deliverable.get("title", "Deliverable")
    await write_activity(
        client=client,
        user_id=user_id,
        event_type="deliverable_run",
        summary=f"{deliverable_title} v{next_version} generated ({final_status})",
        event_ref=version_id,
        metadata={
            "deliverable_id": str(deliverable_id),
            "version_number": next_version,
            "strategy": strategy.strategy_name,
            "final_status": final_status,
        },
    )
except Exception:
    pass  # Non-fatal — never block execution
```

---

## Step 4: Write Point — Platform Sync

**File**: [api/workers/platform_worker.py](../../api/workers/platform_worker.py)

**Where**: After a successful platform sync batch completes for a resource. The sync functions (`_sync_slack`, `_sync_gmail`, `_sync_notion`, `_sync_calendar`) each return a result dict. The caller (main sync loop) processes results per resource.

Find the loop in `platform_worker.py` that iterates over selected sources and calls the per-platform sync. After a successful sync (no exception, `item_count > 0`), write:

```python
# Activity log: record platform sync (ADR-063)
try:
    from services.activity_log import write_activity
    item_count = sync_result.get("item_count", 0)
    resource_label = f"{platform}/{resource_name or resource_id}"
    await write_activity(
        client=client,
        user_id=user_id,
        event_type="platform_synced",
        summary=f"Synced {resource_label}: {item_count} items",
        metadata={
            "platform": platform,
            "resource_id": resource_id,
            "resource_name": resource_name,
            "item_count": item_count,
        },
    )
except Exception:
    pass  # Non-fatal
```

Write one row per resource (not one per user, not one per full sync job). This keeps the log granular enough to answer "when did you last sync #general?" but not so verbose that it floods the working memory.

---

## Step 5: Write Point — TP Memory Tools

**File**: `api/services/working_memory/tools.py` or wherever `create_memory` / `update_memory` TP tools are defined.

After a successful `upsert` into `user_context`, write:

```python
# Activity log: record memory write (ADR-063)
try:
    from services.activity_log import write_activity
    action = "Updated" if is_update else "Noted"
    await write_activity(
        client=client,
        user_id=user_id,
        event_type="memory_written",
        summary=f"{action}: {key} = {value[:80]}{'...' if len(value) > 80 else ''}",
        metadata={
            "key": key,
            "source": "tp_extracted",
            "action": "update" if is_update else "create",
        },
    )
except Exception:
    pass  # Non-fatal
```

---

## Step 6: Write Point — Chat Session (Optional, lower priority)

**File**: [api/routes/chat.py](../../api/routes/chat.py)

Chat session logging is lower priority because `recent_sessions` from `chat_sessions` partially covers this already. Implement last.

**Trigger**: When `chat_sessions.summary` is written (if/when a summariser is added). Alternatively, write a lightweight event when a session ends (the `done: True` signal at line 854 in chat.py):

```python
# Activity log: record session end (ADR-063)
# Only write if session had meaningful turns (e.g., > 1 user message)
if turn_count > 1:
    try:
        from services.activity_log import write_activity
        await write_activity(
            client=client,
            user_id=user_id,
            event_type="chat_session",
            summary=f"Chat session ({turn_count} turns)",
            event_ref=session_id,
            metadata={"turns": turn_count, "tools_used": tools_used},
        )
    except Exception:
        pass
```

This is intentionally minimal — no session summarisation required. A richer session summary can be a follow-up.

---

## Step 7: Read Point — Working Memory

**File**: [api/services/working_memory.py](../../api/services/working_memory.py)

**Changes**:
1. Add `MAX_ACTIVITY_EVENTS = 10` and `ACTIVITY_LOOKBACK_DAYS = 7` constants (after line 35)
2. Add `_get_recent_activity()` helper
3. Add `"recent_activity"` key to the `working_memory` dict in `build_working_memory()`

```python
# In build_working_memory() — add to working_memory dict:
working_memory = {
    "profile": _extract_profile(context_rows),
    "preferences": _extract_preferences(context_rows),
    "known": _extract_known(context_rows),
    "deliverables": await _get_active_deliverables(user_id, client),
    "platforms": await _get_connected_platforms(user_id, client),
    "recent_sessions": await _get_recent_sessions(user_id, client),
    "recent_activity": await _get_recent_activity(user_id, client),   # NEW
}
```

```python
async def _get_recent_activity(user_id: str, client: Any) -> list[dict]:
    """Fetch recent activity events for the working memory prompt block."""
    from services.activity_log import get_recent_activity
    try:
        return await get_recent_activity(
            client=client,
            user_id=user_id,
            limit=MAX_ACTIVITY_EVENTS,
            days=ACTIVITY_LOOKBACK_DAYS,
        )
    except Exception:
        return []
```

The `recent_activity` list is then rendered in the system prompt builder (wherever `working_memory` dict is serialized into the prompt string). The format should be:

```
### Recent activity
- 2026-02-18 09:00 · Weekly Digest v3 generated (staged)
- 2026-02-18 08:45 · Synced gmail/INBOX: 12 items
- 2026-02-17 14:30 · Chat session (8 turns)
- 2026-02-17 09:00 · Noted: prefers bullet points in reports
```

Find the system prompt builder that reads `working_memory` and add the new section there. Aim for ~300 tokens within the existing 2,000 token budget.

---

## Rollout Order

| Step | File | Type | Priority |
|---|---|---|---|
| 1 | `supabase/migrations/060_activity_log.sql` | Schema | Now |
| 2 | `api/services/activity_log.py` | New module | Now |
| 3 | `api/services/deliverable_execution.py` | Write point | High |
| 4 | `api/workers/platform_worker.py` | Write point | High |
| 7 | `api/services/working_memory.py` | Read point | After 3+4 have data |
| 5 | TP memory tools | Write point | Medium |
| 6 | `api/routes/chat.py` | Write point | Low |

Steps 3 and 4 first — they generate the most useful events (deliverable runs and syncs). Step 7 after production data exists so the prompt injection is meaningful on first use. Step 6 last — chat events are the lowest signal.

---

## Token Budget

Current working memory: ~2,000 tokens
New `recent_activity` section: ~300 tokens (10 events × ~30 tokens each)
Remaining budget: unchanged — the section replaces the underused `recent_sessions` block (sessions currently have no summaries, so the block renders empty).

Consider removing or collapsing `recent_sessions` once `recent_activity` is live, since deliverable runs and chat_session events cover the same ground with more signal.

---

## What This Does Not Change

- `filesystem_items` — unchanged
- `sync_registry` — unchanged (continues to track per-resource cursor/state)
- `deliverable_versions` — unchanged
- `session_messages` — unchanged
- `work_execution_log` — unchanged (step-level execution trace, ephemeral)
- Platform sync logic — only adds one INSERT call after a successful batch
- Deliverable execution logic — only adds one INSERT call after generation completes
