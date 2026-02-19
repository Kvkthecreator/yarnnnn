# Context Pipeline Architecture

How platform data flows from OAuth connection through to the TP system prompt and deliverable execution.

> **Last updated**: 2026-02-19 (ADR-065 — live-first platform context; filesystem_items as fallback)

---

## Conceptual Model: Four Layers

Yarnnn operates on four distinct layers. The terminology is intentional and should be used consistently across code, docs, and conversation.

```
┌─────────────────────────────────────────────────────────────┐
│  MEMORY  (user_context)                                      │
│  What TP knows about you — stable, explicit, small          │
│  Injected into every TP session (working memory block)      │
└─────────────────────────────────────────────────────────────┘
         Written by: user directly (Context page); Memory Service nightly cron

┌─────────────────────────────────────────────────────────────┐
│  ACTIVITY  (activity_log)                                    │
│  What YARNNN has done — system provenance, append-only      │
│  Recent events injected into every TP session               │
└─────────────────────────────────────────────────────────────┘
         Written by: deliverable pipeline, platform sync,
                     memory service (session end)

┌─────────────────────────────────────────────────────────────┐
│  CONTEXT  (filesystem_items + live platform APIs)           │
│  What's in your platforms right now — ephemeral, large      │
│  Accessed on demand: Search (cache) or live fetch           │
└─────────────────────────────────────────────────────────────┘
         Written by: background sync worker (cache),
                     live API calls at execution time

┌─────────────────────────────────────────────────────────────┐
│  WORK  (deliverables + deliverable_versions)                 │
│  What TP produces — structured, versioned, exported         │
│  Always generated from live Context reads                   │
└─────────────────────────────────────────────────────────────┘
         Written by: deliverable execution pipeline
```

### Reference models

| | Claude Code | Clawdbot | Yarnnn |
|---|---|---|---|
| **Memory** | CLAUDE.md | SOUL.md / USER.md | `user_context` |
| **Activity** | Git commit log | Script execution log | `activity_log` |
| **Context** | Source files (read on demand) | Local filesystem | `filesystem_items` + live APIs |
| **Work** | Build output | Script output | `deliverable_versions` |
| **Execution** | Shell / Bash | Skills | Deliverable pipeline (live reads) |

---

## Two Independent Data Paths

A common source of confusion: the platform sync pipeline and the deliverable execution pipeline both talk to the same upstream platforms (Slack, Gmail, Notion, Calendar) but are **completely independent systems** with different purposes.

```
Platform Sync (platform_worker.py)
  → Reads platform APIs on a schedule
  → Writes to filesystem_items (TTL cache)
  → Purpose: power conversational Search

Deliverable Execution (deliverable_execution.py)
  → Reads platform APIs live at generation time
  → Never reads filesystem_items
  → Purpose: produce authoritative, current content
```

Scheduled deliverables run entirely on live reads. `filesystem_items` is not consulted. This is by design and correct — deliverables should reflect the state of platforms at the moment of generation, not a cached snapshot.

---

## Memory Layer: user_context

**Table**: `user_context`
**ADR**: ADR-059

A single flat key-value store for everything TP knows *about the user*. Replaces the prior four-table inference pipeline (`knowledge_profile`, `knowledge_styles`, `knowledge_domains`, `knowledge_entries`).

| Key pattern | Meaning | Example |
|---|---|---|
| `name`, `role`, `company`, `timezone` | Profile fields | `role = "Head of Growth"` |
| `tone_{platform}`, `verbosity_{platform}` | Style preferences | `tone_slack = "casual"` |
| `fact:...` | Noted facts | `fact:prefers bullet points` |
| `instruction:...` | Standing instructions | `instruction:always include TL;DR` |
| `preference:...` | Stated preferences | `preference:no jargon in reports` |

**Written by**:
- User directly via the Context page (Profile, Styles, Entries sections)
- Backend Memory Service via nightly cron and pipeline hooks (ADR-064):
  - `process_conversation()` — nightly cron (midnight UTC), processes prior day's sessions in batch
  - `process_feedback()` — triggered when user approves an edited deliverable version
  - `process_patterns()` — daily background job (activity_log analysis)

**Never written by**: TP directly during conversation. The explicit `create_memory` / `update_memory` tools were removed in ADR-064. Conversation memory extraction is a **batch nightly job**, not a real-time session-end hook. A preference stated today is available in working memory the next morning.

**Read by**: `working_memory.py → build_working_memory()` — assembled into the system prompt block injected at the start of every TP session (~2,000 token budget).

### Working memory format

```
### About you
{name, role, company, timezone}

### Your preferences
{tone_*, verbosity_*, preference:*}

### What you've told me
{fact:*, instruction:*}

### Active deliverables
{title, destination, sources, schedule — max 5}

### Connected platforms
{name, status, last_synced, freshness}
```

---

## Context Layer: filesystem_items

**Table**: `filesystem_items`
**ADR**: ADR-049, ADR-062

An internal cache of recent platform content. Short TTL. Exists specifically to serve `Search(scope="platform_content")` during conversational TP sessions.

### What it is and is not

- **Is**: A fallback search index for conversational queries that live platform tools can't serve cheaply (e.g., cross-platform aggregation)
- **Is not**: The primary path for platform content access — live platform tools are. Is not a source of truth. Is not used by deliverable execution.

**ADR-065**: The prior model treated `filesystem_items` as TP's primary platform content path. This has been revised. TP uses live platform tools first; `filesystem_items` is a fallback. When fallback is used, TP discloses the cache age to the user.

### Sync frequency (ADR-053)

| Tier | Frequency | Min interval |
|---|---|---|
| Free | 2x/day | 6 hours |
| Starter | 4x/day | 4 hours |
| Pro | Hourly | 45 minutes |

Triggered by `unified_scheduler.py` → `platform_sync_scheduler.py` → `platform_worker.py` every 5 minutes.

### What each platform extracts

| Platform | Method | What is stored |
|---|---|---|
| Slack | MCPClientManager → `@modelcontextprotocol/server-slack` | Last 50 messages per selected channel |
| Notion | `NotionAPIClient` direct REST (fixed 580f378) | Full page content per selected page |
| Gmail | `GoogleAPIClient` direct REST | Last 50 emails per selected label, 7-day window |
| Calendar | `GoogleAPIClient` direct REST | Next 7 days of events |

### TTL

| Platform | Expiry |
|---|---|
| Slack | 72 hours |
| Notion | 168 hours |
| Gmail | 168 hours |
| Calendar | 168 hours |

### Upsert key

`(user_id, platform, resource_id)` — one row per source+resource, refreshed on each sync.

### Known issue: Notion sync

`_sync_notion()` in `platform_worker.py` currently uses `MCPClientManager` which spawns `@notionhq/notion-mcp-server` via `npx`. This server requires internal integration tokens (`ntn_...`), not OAuth tokens. Notion content is likely **not landing in `filesystem_items`** — the sync is silently failing.

**Fix**: Replace with direct `NotionAPIClient.get_page_content()` calls, identical to the landscape discovery fix already applied. This is the correct and ready fix; it is now a prioritised bug.

---

## Context Layer: Live Platform APIs (Deliverable Execution)

When a deliverable runs (scheduled or on-demand), data is fetched **live** from platform APIs at execution time. No cache is consulted.

**Entry point**: `deliverable_pipeline.py → fetch_integration_source_data()`

**Flow**:
```
unified_scheduler.py (every 5 min)
  → get_due_deliverables()
  → execute_deliverable_generation()   [deliverable_execution.py]
  → get_execution_strategy()           [execution_strategies.py]
  → strategy.gather_context()
  → fetch_integration_source_data()    [deliverable_pipeline.py]
  → _fetch_gmail_data() / _fetch_slack_data() / _fetch_notion_data() / _fetch_calendar_data()
  → Live API call using decrypted credentials from platform_connections
```

Credentials are decrypted from `platform_connections` at execution time. Google tokens are refreshed automatically if expired. No user session is required — scheduled deliverables run fully headless.

---

## Work Layer: Deliverables

**Tables**: `deliverables`, `deliverable_versions`

The output of TP's execution pipeline. Every generation run produces a new `deliverable_version`. Versions are reviewed by the user and exported to the platform destination (Slack channel, Gmail draft, Notion page, etc.).

Deliverables carry their own source configuration — which channels, labels, pages, or calendars to read from. Source references live on the deliverable, not on any domain or grouping abstraction (knowledge_domains was removed in ADR-059 for this reason).

---

## Live Platform Tools (Conversational)

TP has platform tools for direct, action-oriented platform operations during conversation. These are distinct from both the sync cache and deliverable execution:

| Tool | Platform | Method |
|---|---|---|
| `platform_slack_send_message` | Slack | MCP Gateway → Slack API |
| `platform_slack_list_channels` | Slack | MCP Gateway → Slack API |
| `platform_notion_search` | Notion | Direct NotionAPIClient |
| `platform_notion_create_comment` | Notion | Direct NotionAPIClient |
| `platform_gmail_search` | Gmail | GoogleAPIClient |
| `platform_gmail_create_draft` | Gmail | GoogleAPIClient |
| `platform_calendar_list_events` | Calendar | GoogleAPIClient |
| `platform_calendar_create_event` | Calendar | GoogleAPIClient |

These are action calls TP makes on behalf of the user during a chat turn. They are **not** how context flows into TP — that is the working memory block and Search.

---

## What TP Has at Session Start

At the start of every TP session, the working memory block is assembled from **Memory only** (user_context + active deliverables + platform connection status). Raw platform content is **not** pre-injected.

TP accesses platform content during a session in two ways, with a defined priority order (ADR-065):

1. **Primary: Live platform tools** — `platform_gmail_search`, `platform_slack_list_channels`, `platform_notion_search`, etc. Direct API calls. Always current. Used first.
2. **Fallback: `Search(scope="platform_content")`** — hits `filesystem_items` cache (ILIKE text search). Used when live tools can't serve the query (cross-platform aggregation, live tool unavailable). When used, TP **must disclose the cache age** to the user.

**If the cache is needed but empty**: TP triggers `Execute(action="platform.sync")`, informs the user ("takes ~30–60 seconds, ask again once done"), then stops. There is no in-conversation polling tool available — sync is async. The user re-engages after the job completes; the cache will be populated by then.

---

## Document Uploads

Uploaded documents are processed into `filesystem_chunks` (chunked, embedded, indexed). They are searchable via `Search(scope="document")`. Documents do **not** automatically extract into Memory (`user_context`).

**Intentional oversight**: there is a legitimate future use case for "promote document to Memory" — where a user wants a style guide, brief, or set of standing instructions to always be present in working memory rather than just searchable. This should be implemented as an explicit user action, not automatic extraction. It is deferred pending architectural hardening.

---

## Connection Mechanisms

Three different connection mechanisms exist — understanding the distinction prevents confusion:

| Mechanism | Location | Used for |
|---|---|---|
| **MCP Gateway** | `mcp-gateway/` (Node.js) + `api/services/mcp_gateway.py` | TP live Slack tool calls during chat |
| **MCPClientManager** | `api/integrations/core/client.py` | Background Slack + Notion sync (platform_worker) |
| **Direct API clients** | `api/integrations/core/notion_client.py`, `google_client.py` | Notion discovery, Gmail/Calendar sync and TP tools |

---

## Known Gaps (as of 2026-02-19)

1. **Notion sync fixed** — `_sync_notion()` now uses `NotionAPIClient` directly (580f378). Resolved.

2. **Document-to-Memory extraction removed** — Documents populate filesystem_chunks only. Intentional for now; "promote to Memory" is a deferred feature.

3. **filesystem_items not used by execution** — documented here as intended behaviour, not a gap. Prevents confusion about the mirror's purpose.

4. **Live-first access model (ADR-065)** — TP now uses live platform tools as the primary path for conversational platform queries. `filesystem_items` is fallback only. TP must disclose when a response is generated from cached content. See [ADR-065](../adr/ADR-065-live-first-platform-context.md).
