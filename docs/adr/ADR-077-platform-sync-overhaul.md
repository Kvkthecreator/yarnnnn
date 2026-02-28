# ADR-077: Platform Sync Overhaul

**Status**: Implemented
**Date**: 2026-02-25
**Depends on**: ADR-053 (Tier Model), ADR-056 (Per-Source Sync), ADR-072 (Unified Content Layer), ADR-073 (Sync Tokens), ADR-076 (Direct API Clients)

## Context

Platform sync was technically operational but producing extremely thin content (33 total items across 4 platforms for the primary test user). The core flow worked, but captured insufficient content to build the accumulation moat described in ADR-072.

**Root causes identified:**

1. **Scheduler status filter bug** — `platform_sync_scheduler.py` filtered `status = "connected"` but all active connections stored `status = "active"`. Scheduled syncs never ran.
2. **No pagination** — All platform fetches capped at a single API page (50-100 items).
3. **Slack noise** — No subtype filtering (system messages stored as content). No thread expansion.
4. **Narrow source limits** — Free tier: 2 sources/platform. Combined with scheduler bug = near-zero content.
5. **Short TTLs** — Slack 7d, Calendar 1d. Content expired before it could be referenced.
6. **Calendar 0 items** — Forward-only time window (`now → +7d`), no debug logging to diagnose failures.

## Decision

Overhaul all four platform sync implementations following a unified three-phase model:

### Three-Phase Sync Model

**Phase 1 — Landscape (structural discovery):** Discover all available resources with full pagination. Store in `platform_connections.landscape`.

**Phase 2 — Delta detection:** For each selected source, determine what changed since last cursor using platform-native mechanisms (Slack `oldest` ts, Gmail `after:` date, Calendar `syncToken`, Notion `last_edited_time`).

**Phase 3 — Content extraction:** Fetch full content for delta items with pagination, thread expansion (Slack), recursive block fetch (Notion). Store in `platform_content` with deduplication.

### Per-Platform Specifications

#### Slack
- **Pagination**: `get_channel_history_paginated()` via `has_more` + `response_metadata.next_cursor` (1000 initial, 500 incremental)
- **Thread expansion**: `get_thread_replies()` for messages with `reply_count >= 2`, max 20 threads/channel/sync
- **User resolution**: `resolve_users()` batch resolves IDs → display names
- **Noise filtering**: Skip system subtypes (`bot_message`, `channel_join`, `channel_leave`, etc.)
- **Landscape**: `list_channels_paginated()` via cursor (up to 1000 channels)

#### Gmail
- **Pagination**: `list_gmail_messages_paginated()` via `nextPageToken` (200 messages/label)
- **Concurrent fetch**: `asyncio.gather` with `Semaphore(10)` for individual message GETs
- **Initial window**: 30 days (was 7)
- **Cursor**: Date-based (`after:YYYY/MM/DD`) — simpler than historyId, works with content_hash dedup

#### Notion
- **Recursive blocks**: `get_page_content_full()` recursively fetches nested blocks with `has_children` expansion (max_depth=3, max_blocks=500)
- **Database support**: `query_database()` fetches rows, then syncs each as a page
- **Rate limiting**: 350ms inter-request delay (Notion 3 req/sec limit)
- **Landscape**: `search_paginated()` via `start_cursor`/`has_more` (up to 500 resources)
- **Block types**: Extended to handle `table_row`, `bookmark`, `embed`, `divider`

#### Calendar
- **Wider window**: `-7d → +14d` (past meetings = useful context, future = prep)
- **Pagination**: `nextPageToken` support in `list_calendar_events()` (up to 200 events)
- **Negative relative times**: `_parse_relative_time()` now supports `-7d` syntax
- **Richer content**: Event content now includes time, attendees, organizer
- **Debug logging**: Explicit log of API response item count per calendar

### Tier Limits (Widened)

| Platform | Free (was) | Free (new) | Starter (was) | Starter (new) | Pro |
|----------|-----------|-----------|--------------|--------------|-----|
| Slack    | 2         | 5         | 5            | 15           | ∞   |
| Gmail    | 2         | 5         | 5            | 10           | ∞   |
| Notion   | 2         | 10        | 5            | 25           | ∞   |
| Calendar | ∞         | ∞         | ∞            | ∞            | ∞   |

**Rationale**: API fetch costs are not the primary pricing driver (deliverables and token budget are). Wider source limits enable the accumulation moat thesis (ADR-072) to function — content must exist before it can be retained and referenced.

### TTL Changes

| Platform | Was    | Now     |
|----------|--------|---------|
| Slack    | 7 days | 14 days |
| Gmail    | 14 days| 30 days |
| Notion   | 30 days| 90 days |
| Calendar | 1 day  | 2 days  |

**Rationale**: Longer TTLs give downstream systems more time to reference and retain content. The hourly cleanup job handles expiry; table size is bounded by source limits + TTL ceiling.

## Files Modified

| File | Changes |
|------|---------|
| `api/jobs/platform_sync_scheduler.py` | Fix status filter: `.in_("status", ["connected", "active"])` |
| `api/integrations/core/slack_client.py` | Add `get_channel_history_paginated`, `get_thread_replies`, `resolve_users`, `list_channels_paginated` |
| `api/integrations/core/google_client.py` | Add `list_gmail_messages_paginated`, paginated `list_calendar_events`, negative relative time support |
| `api/integrations/core/notion_client.py` | Add `search_paginated`, `get_page_content_full`, `_fetch_blocks_recursive`, `query_database` |
| `api/workers/platform_worker.py` | Rewrite `_sync_slack`, `_sync_gmail`, `_sync_notion`, `_sync_calendar`; extend `_extract_text_from_notion_blocks`; update TTLs |
| `api/services/platform_limits.py` | Widen source limits for Free and Starter tiers |
| `api/services/landscape.py` | Use `list_channels_paginated` (Slack) and `search_paginated` (Notion) |

## Risks & Mitigations

- **Slack rate limits**: Thread expansion capped at 20/channel/sync
- **Notion rate limits (3 req/sec)**: 350ms inter-request delay
- **Gmail concurrent fetch**: Semaphore(10) prevents thundering herd
- **Increased content volume**: Existing cleanup job handles TTL expiry; source limits bound table size
- **Backward cursor compatibility**: All cursor formats unchanged (Slack ts, Gmail date, Calendar syncToken, Notion last_edited_time)

## Deployment Notes

### Render Cron Provisioning (2026-02-27)

The `platform-sync` cron was defined in `render.yaml` but **never provisioned on Render** during initial deployment. The Render Blueprint sync did not create it automatically. This meant:

- All scheduled platform syncs silently never ran
- The only syncs that occurred were manual "Refresh Data" button clicks from the UI
- The ADR-077 overhaul code was correct and deployed, but the scheduler entry point was never invoked

**Resolution**: Provisioned `yarnnn-platform-sync` cron via Render API (`crn-d6gdvi94tr6s73b6btm0`):
- Schedule: `*/5 * * * *`
- Command: `cd api && python -m jobs.platform_sync_scheduler`
- Region: Singapore
- 9 env vars configured (matching `render.yaml` spec)

### Concurrent Fix: `working_memory.py`

`api/services/working_memory.py` line 444 referenced `updated_at` on `integration_import_jobs`, which doesn't exist (ADR-058 schema). Changed to `created_at`. This was causing 400 errors on MCP server context queries.

### First Validation (2026-02-27, test user kvkthecreator@gmail.com)

| Platform | Items Synced | Notes |
|----------|-------------|-------|
| Slack    | 7           | Incremental (recent messages since last manual sync) |
| Google   | 73          | 34 emails + 39 calendar events |
| Notion   | 0           | No changes since last manual sync |

All `platform_connections.last_synced_at` updated. `activity_log` entries written for each `platform_synced` event. Content total: 335 → 377 items.

### Google Split Sync Fix (2026-02-28)

The worker had separate `provider=="gmail"`, `provider=="calendar"`, and `provider=="google"` branches. Since `platform_connections` stores `platform="gmail"` for the single Google OAuth row, the scheduler always passed `provider="gmail"` — which only called `_sync_gmail()`, never `_sync_calendar()`. The `provider=="google"` branch (which correctly splits sources by `metadata.platform`) was dead code for scheduled syncs.

**Fix**: Unified all three branches into one `provider in ("gmail", "calendar", "google")` path that always does the split-sync. Worker now normalizes the DB lookup (`gmail/calendar/google` all query the `"gmail"` row) and splits `selected_sources` by landscape `metadata.platform`. This applies to both scheduled syncs (scheduler) and on-demand syncs (Refresh Data button).

Also fixed downstream consumers:
- `working_memory.py`: Synthesizes a "calendar" entry from the "gmail" DB row so TP sees both platforms
- `project_tools.py`: `list_integrations` now returns both gmail and calendar items
- `platform_tools.py`: Calendar tools load when gmail is connected
- `integrations.py` landscape endpoint: Filters resources by `metadata.platform` per requested domain, fixes `sync_registry` query to use correct platform value, wraps `discover_landscape()` in error handling
- `landscape.py`: Token decryption wrapped in error handling

## Verification

After deployment:
1. ✅ Scheduled syncs should appear in `activity_log` without manual "Refresh Data"
2. ✅ `SELECT platform, content_type, COUNT(*) FROM platform_content WHERE user_id = '...' GROUP BY platform, content_type` should show significantly more content
3. ✅ Slack: system messages filtered, threads expanded
4. ✅ Gmail: >50 emails per label (pagination working)
5. ✅ Notion: nested block content captured, database rows synced
6. ✅ Calendar: events appear with wider time range
