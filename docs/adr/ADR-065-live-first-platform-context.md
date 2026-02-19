# ADR-065: Live-First Platform Context Access

**Status**: Accepted
**Date**: 2026-02-19
**Amends**: ADR-062 (Platform Context Architecture)
**Relates to**: ADR-063 (Four-Layer Model), ADR-050 (Platform Tools), ADR-038 (Filesystem-as-Context)

---

## Context

ADR-062 established that `filesystem_items` is a "conversational search cache" and that TP accesses platform content via `Search(scope="platform_content")` as its primary conversational path. Deliverable execution was already on live reads.

Operating experience has surfaced two failure modes with this model:

### Failure Mode 1: Empty-cache dead end

When a user asks about platform content and the sync cache is empty (first session, cold start, or sync never run), TP's sequence was:

1. `Search(scope="platform_content", query="...")` → `success=True, count=0` (empty cache)
2. `Execute(action="platform.sync", target="platform:slack")` → enqueues async job
3. `Search(query="")` → `success=False, error=missing_query` ← bug
4. `Search(query="...")` → still empty (sync takes 10-60s, not yet complete)

Result: user gets nothing. TP had live platform tools available the whole time and never used them.

### Failure Mode 2: Stale cache used without disclosure

When the cache is populated but old, TP returns content without telling the user the data is from a snapshot taken hours or days ago. The user has no signal that they may be working from stale information.

### The pivot

The codebase has moved away from "nightly cron populates cache, TP queries cache as primary path" — this model was appropriate when sync was the only access mechanism, but TP now has direct live platform tools (`platform_slack_list_channels`, `platform_gmail_search`, `platform_notion_search`, `platform_calendar_list_events`, etc.) that can answer most conversational queries immediately without touching the cache.

The right model mirrors Claude Code's MCP tool usage: **just call the tool directly**. The cache (`filesystem_items`) is a fallback for aggregation queries that live tools can't serve cheaply.

---

## Decision

### 1. Live platform tools are the primary path for conversational queries

When the user asks about content in a connected platform, TP's first action is a direct live tool call:

```
User: "What was discussed in #general this week?"
→ platform_slack_list_channels() to find #general channel ID (e.g., "C0123ABC")
→ platform_slack_get_channel_history(channel_id="C0123ABC", limit=100)
→ Summarize for user
```

Not:
```
→ Search(scope="platform_content", query="general this week")  ← wrong first move
```

This matches Claude Code's pattern: when you need to know something about a live system, you run a command against it — you don't query a stale index first.

### 2. `filesystem_items` is the fallback, not the primary

`Search(scope="platform_content")` is appropriate when:
- The query is aggregation-style across platforms (e.g., "what happened across Slack and Gmail this week?")
- A live tool call already failed or is unavailable
- The user explicitly asks to search synced content

When TP uses `filesystem_items` as the data source for a response, it **must disclose this**:

> "Based on content synced 3 hours ago..."
> "From the last sync on Feb 18..."

This is non-negotiable. The user must know when they're seeing a cached view.

### 3. If the cache is needed but empty: sync then wait

When `Search(scope="platform_content")` returns empty and no live tool can serve the query, the correct sequence is:

```
1. Execute(action="platform.sync", target="platform:slack")
2. Inform user: "Syncing your Slack content now. This takes ~30–60 seconds."
3. Wait in a loop — check sync status before re-querying:
   get_sync_status(platform="slack") → poll until fresh or timeout
4. Re-query once sync confirms completion
5. If still empty after sync: tell user there's no matching content
```

This is analogous to Claude Code waiting for a deploy before testing:
```
→ trigger deploy
→ wait 30s
→ check deploy status
→ run tests
```

**Never re-query immediately after triggering sync.** The job is asynchronous (Redis worker, 10–60s).

### 4. Memory (`user_context`) is not a search domain

`Search(scope="memory")` is removed from the valid search scopes TP uses. Memory is injected into the system prompt at session start via working memory — TP already has it. Searching it mid-conversation is redundant and reflects a misunderstanding of the layer separation.

The prior silent redirect (`scope="memory"` → `scope="platform_content"` in search.py) is removed. If TP needs to reference memory, it reads the working memory block already in its context.

---

## What Changes

| File | Change |
|---|---|
| `api/agents/tp_prompts/behaviors.py` | Add "Platform Content Access" section with live-first pattern, wait-loop, fallback disclosure rule |
| `api/services/primitives/search.py` | Remove silent `scope="memory"` redirect; add `synced_at` age to `platform_content` results |
| `docs/architecture/context-pipeline.md` | Update to reflect live-first model; clarify filesystem_items as fallback |
| `docs/architecture/tp-prompt-guide.md` | Add v6 entry |
| `api/prompts/CHANGELOG.md` | Record v6 changes |

---

## What Does Not Change

- `filesystem_items` schema — unchanged, cache is still populated and valid
- Platform sync pipeline — unchanged, background sync still runs on schedule
- Deliverable execution — already on live reads (ADR-062 confirmed this; not affected here)
- Working memory injection — unchanged; Memory and Activity layers injected at session start
- Live platform tool definitions — unchanged; tools already exist and work

---

## The Correct Mental Model

```
User asks about platform content
          │
          ▼
Do I have a live tool for this platform?
          │
    ┌─────┴─────┐
   Yes           No
    │             │
    ▼             ▼
Call live     Search(scope="platform_content")
platform         │
tool             ├─ Results found → use them, disclose cache age
    │            │
    │            └─ Empty → sync → wait → re-query
    │
    ▼
Answer user with live data (no disclosure needed — it's live)
```

---

## Reference Model

| Pattern | Claude Code equivalent |
|---|---|
| Live platform tool call | `Bash("git log --oneline")` — just run it |
| `filesystem_items` fallback | Reading a build cache — valid but may be stale |
| Sync → wait → re-query | Deploy → `sleep 30` → test |
| Fallback disclosure | Noting "this is from the build cache, not a fresh run" |

---

## Related

- [ADR-062](ADR-062-platform-context-architecture.md) — Prior model (filesystem_items as primary); this ADR amends its "conversational search" mandate
- [ADR-063](ADR-063-activity-log-four-layer-model.md) — Four-layer model (Memory / Activity / Context / Work)
- [ADR-050](ADR-050-mcp-gateway-architecture.md) — Platform tools (live API calls during conversation)
- [context-pipeline.md](../architecture/context-pipeline.md) — Updated to reflect this ADR
- [tp-prompt-guide.md](../architecture/tp-prompt-guide.md) — TP prompt versioning
