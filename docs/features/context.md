# Context

> Layer 3 of 4 in the YARNNN four-layer model (ADR-063)
> **Updated**: 2026-02-20 — ADR-072 unified content layer

---

## What it is

Context is the unified content layer — platform content with retention-based accumulation. Emails, Slack messages, Notion pages, calendar events. Content that proves significant (referenced by deliverables, signal processing, or TP sessions) is retained indefinitely. Unreferenced content expires after TTL.

Context is never injected wholesale into the TP system prompt. It is fetched on demand, during a session, via TP primitives (`Search`, `FetchPlatformContent`, `CrossPlatformQuery`).

**Analogy**: Context is the filesystem that Claude Code reads — source files exist on disk, but only the relevant ones are opened and read when needed. YARNNN's "disk" is the user's connected platforms, with significant content accumulating over time.

---

## What it is not

- Not stable user knowledge — that is Memory (`user_context`)
- Not a log of YARNNN's actions — that is Activity (`activity_log`)
- Not generated output — that is Work (`deliverable_versions`)
- Not pre-loaded into the TP prompt — TP fetches it on demand

---

## The `platform_content` table (ADR-072)

All platform content flows through a single table with retention semantics:

```
platform_content
├── Ephemeral content (retained=false, expires_at set)
│   └── Written by platform sync, expires after TTL
│
└── Retained content (retained=true, expires_at NULL)
    └── Marked significant by deliverable execution, signal processing, or TP sessions
```

### Two writers

**Platform Sync** (`platform_worker.py`):
- Runs continuously on tier-appropriate frequency
- Writes with `retained=false`, `expires_at=NOW()+TTL`
- Knows nothing about significance — just syncs

**Signal Processing** (`signal_extraction.py`):
- Reads live APIs for time-sensitive signals
- Writes significant content with `retained=true`
- Sets `retained_reason='signal_processing'`

### Retention marking

When content is consumed by a downstream system, it's marked retained:

| Consumer | When | Sets |
|---|---|---|
| Deliverable execution | After synthesis | `retained=true`, `retained_reason='deliverable_execution'`, `retained_ref=version_id` |
| TP session | After semantic search hit | `retained=true`, `retained_reason='tp_session'`, `retained_ref=session_id` |
| Signal processing | When identified as significant | `retained=true`, `retained_reason='signal_processing'` |

---

## Table Schema

### `platform_content` — Unified content layer

| Column | Notes |
|---|---|
| `platform` | `slack`, `gmail`, `notion`, `calendar` |
| `resource_id` | Channel ID, label, page ID, calendar ID |
| `resource_name` | Human-readable name |
| `item_id` | Unique item identifier from platform |
| `content` | Full text content |
| `content_type` | `message`, `email`, `page`, `event` |
| `content_hash` | SHA-256 for deduplication on re-fetch |
| `content_embedding` | vector(1536) for semantic search |
| `fetched_at` | When fetched from platform |
| `retained` | When true, content never expires |
| `retained_reason` | `deliverable_execution`, `signal_processing`, `tp_session` |
| `retained_ref` | FK to the record that marked this retained |
| `expires_at` | NULL if retained=true, otherwise TTL |

**Unique constraint**: `(user_id, platform, resource_id, item_id, content_hash)`

### TTL by platform (for unreferenced content)

| Platform | Expiry |
|---|---|
| Slack | 7 days |
| Gmail | 14 days |
| Notion | 30 days |
| Calendar | 1 day |

### `platform_connections` — OAuth credentials and settings

Stores encrypted OAuth tokens, sync preferences, selected sources, and last_synced_at per platform per user.

### `filesystem_documents` + `filesystem_chunks` — Uploaded documents

User-uploaded PDFs, DOCX, TXT, MD files are chunked, embedded, and stored in `filesystem_chunks`. Searchable via `Search(scope="document")` — semantic vector search. Documents are Context, not Memory — they are working material, not standing instructions.

### `sync_registry` — Per-resource sync state

Tracks cursor and last_synced_at per `(user_id, platform, resource_id)`. Used by `platform_worker.py` to track sync progress across runs.

---

## How content is accessed

**TP primitives** are the single access path:
- `Search(scope="platform_content")` — semantic search via pgvector embeddings
- `FetchPlatformContent` — targeted retrieval by resource
- `CrossPlatformQuery` — multi-platform search

**Deliverable execution** (ADR-072) uses TP in headless mode — same primitives, same search capabilities.

**Signal processing** reads live APIs for time-sensitive signals, then marks corresponding `platform_content` records as retained.

---

## What each platform syncs

| Platform | Sync method | What is stored |
|---|---|---|
| Slack | MCPClientManager → `@modelcontextprotocol/server-slack` | Last 50 messages per selected channel |
| Gmail | `GoogleAPIClient` direct REST | Last 50 emails per selected label, 7-day window |
| Notion | `NotionAPIClient` direct REST | Full page content per selected page |
| Calendar | `GoogleAPIClient` direct REST | Next 7 days of events |

---

## The accumulation moat

Content that proves significant accumulates indefinitely. Over time, `platform_content` contains:
- Recent ephemeral content (TTL-bounded, most expires unused)
- Accumulated significant content (never expires, the compounding moat)

This is how YARNNN builds intelligence over time. A user with 6 months of deliverable history has a rich archive of content that mattered.

**Key insight**: Don't accumulate everything. Don't expire everything. **Accumulate what proved significant.**

---

## Boundaries

| Question | Answer |
|---|---|
| Does TP get platform content in its system prompt? | No — Context is fetched on demand via primitives, never pre-loaded |
| Can Context be used as Memory? | No — platform content must be promoted explicitly. Automatic promotion was removed in ADR-059 |
| Is `platform_content` the source of truth? | No — platforms are. `platform_content` is a working cache with retention semantics |
| Does a stale cache affect deliverables? | No — deliverables use TP primitives which query `platform_content` with retention-aware filtering |
| Can a document upload add Memory entries? | Not automatically. "Promote document to Memory" is a deferred feature |
| What replaces `filesystem_items`? | `platform_content` (ADR-072). The old table was dropped in migration 077. |

---

## Related

- [ADR-072](../adr/ADR-072-unified-content-layer-tp-execution-pipeline.md) — Unified content layer and TP execution pipeline
- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Four-layer model
- [four-layer-model.md](../architecture/four-layer-model.md) — Architectural overview
- [context-pipeline.md](../architecture/context-pipeline.md) — Technical pipeline detail
- `api/services/platform_content.py` — Unified content service
- `api/workers/platform_worker.py` — sync worker
- `api/services/primitives/search.py` — `Search(scope="platform_content")`
