# Context

> Layer 3 of 4 in the YARNNN four-layer model (ADR-063)

---

## What it is

Context is the current working material — what's in the user's platforms right now. Emails, Slack messages, Notion pages, calendar events. It is ephemeral, large, and lives on the platforms themselves. YARNNN accesses it in two ways: through a local cache for conversational search, and through live API calls for deliverable generation.

Context is never injected wholesale into the TP system prompt. It is fetched on demand, during a session, in response to a specific query or task.

**Analogy**: Context is the filesystem that Claude Code reads — source files exist on disk, but only the relevant ones are opened and read when needed. YARNNN's "disk" is the user's connected platforms.

---

## What it is not

- Not stable user knowledge — that is Memory (`user_context`)
- Not a log of YARNNN's actions — that is Activity (`activity_log`)
- Not generated output — that is Work (`deliverable_versions`)
- Not pre-loaded into the TP prompt — TP fetches it on demand

---

## Two access paths

Context is accessed in two distinct ways. They are completely independent.

### Path 1: Conversational Search (via `filesystem_items` cache)

When a user asks TP something like "what was discussed in #general this week?", TP calls `Search(scope="platform_content")`. This hits the `filesystem_items` table — a local cache of recent platform content — using an ILIKE text search.

The cache exists because fetching live from multiple platforms during a streaming response would be slow and composable cross-platform search would be impossible. The cache trades freshness for speed.

**Cache is populated by**: `platform_worker.py` on a schedule (Free: 2x/day, Starter: 4x/day, Pro: hourly). Each sync run reads from the platform APIs and writes to `filesystem_items` with a TTL.

**Cache is read by**: `api/services/primitives/search.py → _search_platform_content()` — ILIKE on `content` column.

**Cache is NOT used by**: deliverable execution. Deliverables always read live. This is documented as intended behaviour, not a gap.

### Path 2: Live Platform APIs (deliverable execution + TP tools)

Two sub-paths here, both making live API calls:

**Deliverable execution**: When a scheduled or on-demand deliverable runs, `deliverable_pipeline.py → fetch_integration_source_data()` decrypts credentials from `platform_connections` and calls the platform APIs directly. No cache is consulted. This ensures deliverables always reflect the state of platforms at the moment of generation.

**TP platform tools**: During a conversation, TP can make targeted live calls via dedicated tools:
- `platform_gmail_search` — searches Gmail directly
- `platform_notion_search` — searches Notion directly
- `platform_calendar_list_events` — lists calendar events
- `platform_slack_list_channels` — lists Slack channels
- `platform_slack_send_message`, `platform_gmail_create_draft`, etc. — action tools

These are distinct from Search — they are action-oriented and precise, not cross-platform content queries.

---

## Tables

### `filesystem_items` — Conversational search cache

| Column | Notes |
|---|---|
| `platform` | `slack`, `gmail`, `notion`, `calendar` |
| `resource_id` | Channel ID, label, page ID |
| `content` | Full message / email / page text |
| `content_type` | `message`, `email`, `page`, `event` |
| `expires_at` | TTL — 72 hours (Slack) or 168 hours (Gmail/Notion/Calendar) |

Upsert key: `(user_id, platform, resource_id, item_id)` — refreshed on each sync.

### `platform_connections` — OAuth credentials and settings

Stores encrypted OAuth tokens, sync preferences, selected sources, and last_synced_at per platform per user.

### `filesystem_documents` + `filesystem_chunks` — Uploaded documents

User-uploaded PDFs, DOCX, TXT, MD files are chunked, embedded, and stored in `filesystem_chunks`. Searchable via `Search(scope="document")` — semantic vector search, not ILIKE. Documents are Context, not Memory — they are working material, not standing instructions.

### `sync_registry` — Per-resource sync state

Tracks cursor and last_synced_at per `(user_id, platform, resource_id)`. Used by `platform_worker.py` to track sync progress across runs without re-reading content that hasn't changed.

---

## What each platform syncs

| Platform | Sync method | What is cached |
|---|---|---|
| Slack | MCPClientManager → `@modelcontextprotocol/server-slack` | Last 50 messages per selected channel |
| Gmail | `GoogleAPIClient` direct REST | Last 50 emails per selected label, 7-day window |
| Notion | `NotionAPIClient` direct REST | Full page content per selected page |
| Calendar | `GoogleAPIClient` direct REST | Next 7 days of events |

---

## Why the cache and live paths coexist

The cache and live API paths serve different purposes and cannot replace each other:

| | Cache (`filesystem_items`) | Live APIs |
|---|---|---|
| **Used for** | `Search(scope="platform_content")` during conversation | Deliverable execution, TP platform tools |
| **Latency** | Fast (local DB query) | Slower (external API round trip) |
| **Freshness** | Tier-dependent (2–24 hours stale possible) | Always current |
| **Cross-platform** | Single ILIKE query across all platforms | Separate call per platform |
| **Authoritative** | No — a cache, not source of truth | Yes — direct from platform |

Deliverables use live reads because they must be authoritative at the moment of generation. Conversational Search uses the cache because composable cross-platform text search during a streaming response requires a local index.

---

## Boundaries

| Question | Answer |
|---|---|
| Does TP get platform content in its system prompt? | No — Context is fetched on demand via Search or tools, never pre-loaded |
| Can Context be used as Memory? | No — platform content must be promoted explicitly. Automatic promotion was removed in ADR-059 |
| Is `filesystem_items` the source of truth? | No — platforms are. The cache is a convenience index |
| Does a stale cache affect deliverables? | No — deliverables always read live |
| Can a document upload add Memory entries? | Not automatically. "Promote document to Memory" is a deferred feature (ADR-062) |
| Why does `filesystem_items` exist if deliverables use live APIs? | Cache is for conversational search (ILIKE, cross-platform, low latency). Live APIs are for authoritative point-in-time reads. Neither can replace the other. |

---

## Related

- [ADR-062](../adr/ADR-062-platform-context-architecture-SUPERSEDED.md) — filesystem_items role and mandate
- [ADR-049](../adr/ADR-049-context-freshness-model-SUPERSEDED.md) — TTL and sync frequency
- [ADR-056](../adr/ADR-056-per-source-sync-implementation.md) — Per-source sync design
- [four-layer-model.md](../architecture/four-layer-model.md) — Architectural overview
- [context-pipeline.md](../architecture/context-pipeline.md) — Technical pipeline detail
- `api/workers/platform_worker.py` — sync worker
- `api/services/primitives/search.py` — `Search(scope="platform_content")`
- `api/services/deliverable_pipeline.py` — live reads for deliverable execution
