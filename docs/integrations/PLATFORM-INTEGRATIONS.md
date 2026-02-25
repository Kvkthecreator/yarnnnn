# Platform Integrations Architecture

> Backend infrastructure documentation for YARNNN platform integrations.
> Updated 2026-02-23 per ADR-073 (Unified Fetch Architecture).

## Overview

YARNNN integrates with four external platforms. All platform data flows through a **single fetch path** that writes to `platform_content` (ADR-072). All downstream consumers (TP, deliverables, scheduling heuristics) read from `platform_content` — they do not call external APIs.

| Platform | OAuth Provider | Transport | Fetch → `platform_content` | TP Tools (Real-Time) | Deliverable Source | Deliverable Export |
|----------|---------------|-----------|---------------------------|---------------------|-------------------|-------------------|
| Slack | slack | MCP Gateway | Yes | Yes | Yes (reads `platform_content`) | Yes |
| Gmail | google | Direct API | Yes | Yes | Yes (reads `platform_content`) | Yes |
| Calendar | google | Direct API | Yes | Yes | Yes (reads `platform_content`) | Yes |
| Notion | notion | Direct API | Yes | Yes | Yes (reads `platform_content`) | Yes |

## Tier Limits (ADR-053)

| Gate | Free | Starter | Pro |
|------|------|---------|-----|
| Platform connections | All 4 | All 4 | All 4 |
| Sources per platform | 2 | 5 | Unlimited |
| Sync frequency | 1x/day (8am) | 4x/day | Hourly |
| Active deliverables | 2 | 5 | Unlimited |
| Signal processing | Off | On | On |
| TP daily token budget | 50k | 250k | Unlimited |
| Calendar source selection | N/A (all calendars) | N/A | N/A |

**Primary cost gates** (ordered by cost impact):
1. **Signal processing** — Haiku + potential Sonnet spend per user per cycle; off for free tier
2. **Daily token budget** — TP conversations consume tokens; direct mapping to Anthropic API spend
3. **Active deliverables** — Each deliverable run consumes Sonnet tokens
4. **Sources per platform** — More sources = more API calls and storage
5. **Sync frequency** — More frequent syncs = more API calls

**Enforcement locations**:
- Source limits: `platform_limits.py` → `check_source_limit()`, `validate_sources_update()`
- Token budget: `chat.py` → `check_daily_token_budget()` via SQL RPC `get_daily_token_usage()`
- Signal processing: `unified_scheduler.py` (skip free), `signal_processing.py` route (403)
- Deliverable limits: `signal_processing.py` service → `check_deliverable_limit()`
- Sync frequency: `platform_limits.py` → `SYNC_SCHEDULES`, checked in scheduler

---

## Data Flow Architecture (ADR-073)

```
┌─────────────────────────────────────────────────────────────────────┐
│ FETCH LAYER (singular — only subsystem calling external APIs)       │
│                                                                     │
│ platform_sync_scheduler.py (cron */5, tier-gated)                   │
│   └─ platform_worker.py                                             │
│        ├─ _sync_slack()     → MCP Gateway → Slack API               │
│        ├─ _sync_gmail()     → GoogleAPIClient → Gmail API v1        │
│        ├─ _sync_calendar()  → GoogleAPIClient → Calendar API v3     │
│        └─ _sync_notion()    → NotionAPIClient → Notion API          │
│                                                                     │
│ Writes ALL content to platform_content table.                       │
│ Content starts ephemeral (retained=false, TTL set).                 │
│ Tier gates: Free=1x/day, Starter=4x/day, Pro=hourly (ADR-053).     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ writes to
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│ CONTENT LAYER (platform_content — single source of truth)           │
│                                                                     │
│ Storage:   store_platform_content(), batch writers                   │
│ Readers:   get_platform_content(), get_content_for_deliverable(),   │
│            get_content_summary_for_generation(),                     │
│            search_platform_content() (pgvector semantic search)      │
│ Retention: mark_content_retained() when content is consumed         │
│ Cleanup:   cleanup_expired_content() removes TTL-expired rows       │
│ Freshness: has_fresh_content_since() for scheduling decisions       │
└──────────┬──────────────────┬────────────────────┬──────────────────┘
           │                  │                    │
           ▼                  ▼                    ▼
   TP Chat (Sonnet)    Deliverable Exec     Scheduling Heuristics
   (real-time,         (Sonnet synthesis,    (rules + freshness,
    user-initiated)     system-triggered)     no LLM — decides
                                              WHEN to trigger)
```

### TP Real-Time Tools (Separate Path)

TP tools (Slack send message, Gmail send/draft, Calendar create/update/delete) are **write operations** that go directly to platform APIs. These are not part of the fetch pipeline — they are user-initiated actions through TP, not data retrieval.

Read-oriented TP tools (search, list) should migrate to reading from `platform_content` where feasible. Some real-time reads (e.g., checking current calendar availability for scheduling) may continue to use live APIs where freshness is critical.

```
TP Write Tools: platform_tools.py → direct platform APIs (Slack, Gmail, Calendar, Notion)
TP Read Context: working_memory.py → platform_content table
```

---

## Per-Platform Specifications

### Slack (MCP Gateway)

**OAuth Config**: [oauth.py](../../api/integrations/core/oauth.py)
```
Scopes: chat:write, channels:read, channels:history, channels:join,
        groups:read, groups:history, users:read, im:write
```

**Credential Storage**: `credentials_encrypted` → JSON `{bot_token, team_id}`
**Decryption**: `TokenManager.decrypt()` → `json.loads()`
**Token Expiry**: Slack bot tokens do not expire.

**Fetch Spec (platform_worker)**:

| Aspect | Value |
|--------|-------|
| Source filter | `landscape.selected_sources` — auto-populated by member count desc (ADR-078) |
| Time window | All recent messages (no time filter currently — sync token will add `oldest` param) |
| Items per source | 50 messages per channel |
| Content stored | Full message text, user, ts, reactions, thread metadata |
| Content type | `message`, `thread_parent`, `thread_reply` |
| TTL | 7 days |
| Sync token | Slack `oldest` param — store last fetched `ts` per channel in `sync_registry` |

**TP Tools** (defined in [platform_tools.py](../../api/services/platform_tools.py)):
- `platform_slack_send_message` — Send DM to user
- `platform_slack_list_channels` — List available channels

---

### Gmail (Direct API)

**OAuth Config**: Part of unified Google OAuth
```
Scopes: gmail.readonly, gmail.send, gmail.compose, gmail.modify
```

**Credential Storage**: `refresh_token_encrypted`
**Decryption**: `TokenManager.decrypt()` → refresh token → `GoogleAPIClient._get_access_token()` (1-hour cache)
**Token Expiry**: Access tokens expire in 1 hour. Refresh handled automatically with caching.

**Fetch Spec (platform_worker)**:

| Aspect | Value |
|--------|-------|
| Source filter | `landscape.selected_sources` — auto-populated with INBOX, SENT, STARRED, IMPORTANT, then user labels (ADR-078) |
| Time window | Last 7 days (recency filter) |
| Items per source | 50 messages per label (full message fetch via `get_message`) |
| Content stored | Subject + body snippet (up to 10,000 chars), headers, thread_id |
| Content type | `email` |
| TTL | 14 days |
| Sync token | Gmail `historyId` — store per label in `sync_registry`, use `history.list` for delta |

**TP Tools**:
- `platform_gmail_search` — Search messages with Gmail query syntax
- `platform_gmail_get_thread` — Get full email thread
- `platform_gmail_send` — Send email
- `platform_gmail_create_draft` — Create draft for user review

---

### Calendar (Direct API)

**OAuth Config**: Shares Google OAuth with Gmail
```
Scopes: calendar.readonly, calendar.events.readonly, calendar.events
```

**Credential Storage**: Same as Gmail (`refresh_token_encrypted` on `google` platform connection)
**Token Expiry**: Same as Gmail.

**Fetch Spec (platform_worker)**:

| Aspect | Value |
|--------|-------|
| Source filter | `landscape.selected_sources` — ALL calendars auto-selected, unlimited in all tiers (ADR-078) |
| Time window | Next 7 days |
| Items per source | 50 events per calendar |
| Content stored | Title, description, location, start/end, attendees, htmlLink |
| Content type | `event` |
| TTL | 1 day (events are time-sensitive; re-fetched each cycle) |
| Sync token | Calendar `syncToken` — store per calendar in `sync_registry` |

**Note**: Calendar's short TTL (1 day) means Pro users (hourly sync) see near-real-time event data. Free users (1x/day) may see stale event info. This is an intentional monetization lever. Calendar source selection is disabled (calendars=-1) — all visible calendars sync.

**TP Tools**:
- `platform_calendar_list_events` — List upcoming events with time filters
- `platform_calendar_get_event` — Get event details with attendees
- `platform_calendar_create_event` — Create new calendar events
- `platform_calendar_update_event` — Modify existing events
- `platform_calendar_delete_event` — Delete events (with confirmation)

---

### Notion (Direct API)

**OAuth Config**: Notion's built-in OAuth (no scopes needed)

**Credential Storage**: `credentials_encrypted` → access token
**Decryption**: `TokenManager.decrypt()`
**Token Expiry**: Notion OAuth tokens do not expire.

**Why Direct API (not MCP)**:
- `@notionhq/notion-mcp-server` requires internal `ntn_...` integration tokens, not OAuth tokens
- Notion's hosted MCP manages its own OAuth sessions — no way to inject ours
- `NotionAPIClient` handles all Notion REST operations with our OAuth tokens

**Fetch Spec (platform_worker)**:

| Aspect | Value |
|--------|-------|
| Source filter | `landscape.selected_sources` — auto-populated by last_edited desc, deprioritizing Untitled (ADR-078) |
| Time window | Full page content (no time window — pages are documents, not streams) |
| Items per source | 1 page = 1 item (page metadata + all content blocks) |
| Content stored | Full plain text extraction from all block types |
| Content type | `page` |
| TTL | 30 days |
| Sync token | `last_edited_time` comparison — skip re-fetch if page hasn't changed |

**TP Tools**:
- `platform_notion_search` — Search pages/databases
- `platform_notion_create_comment` — Add comments

---

## OAuth Provider Mapping

| Frontend Display | Backend `platform` Column | OAuth Flow | Notes |
|-----------------|--------------------------|------------|-------|
| Slack | `slack` | Slack OAuth | Separate OAuth provider |
| Gmail | `google` | Google OAuth | Single Google OAuth grants Gmail + Calendar |
| Calendar | `google` | Google OAuth | Same connection as Gmail, no separate OAuth |
| Notion | `notion` | Notion OAuth | Separate OAuth provider |

**Legacy Note**: Older records may have `gmail` as the platform value. Backend handles both `google` and `gmail` for Google-sourced integrations.

---

## Token Management

### Token Types

| Platform | Storage Column | Token Type | Expiry |
|----------|---------------|------------|--------|
| Slack | `credentials_encrypted` | Bot token (JSON) | Never |
| Gmail | `refresh_token_encrypted` | OAuth refresh token | Never (access token: 1 hour) |
| Calendar | `refresh_token_encrypted` | Same as Gmail | Same as Gmail |
| Notion | `credentials_encrypted` | OAuth access token | Never |

### Google Token Caching (Phase 1 Hardening)

Google access tokens are cached in-memory per refresh token:
```
GoogleAPIClient._token_cache: dict[refresh_token → (access_token, expires_at_monotonic)]
```

- Cache TTL: refresh 60 seconds before expiry
- Cache scope: per-process (acceptable for single-instance Render deployment)
- All API calls use `_request_with_retry` with `httpx.Timeout(30.0, connect=10.0)`
- Retry: exponential backoff (1s, 2s, 4s) on 429/5xx, 3 max attempts

---

## Sync Pipeline

### Trigger

`platform_sync_scheduler.py` runs every 5 minutes (Render cron). Checks which users are due for sync based on tier:

| Tier | Sync Frequency | Min Interval Between Syncs |
|------|---------------|---------------------------|
| Free | 1x daily (8am) | 20 hours |
| Starter | 4x daily | 4 hours |
| Pro | Hourly | 45 minutes |

### Execution Flow

```
platform_sync_scheduler.py
  → get_users_due_for_sync(): query platform_connections, check tier, check last_synced_at
  → process_user_sync(): for each due user
      → _get_selected_sources(): read landscape.selected_sources per provider
      → sync_platform(): call platform_worker per provider
          → _sync_{slack,gmail,notion,calendar}(): fetch from API
              → _store_platform_content(): upsert to platform_content table
          → update last_synced_at on platform_connections
          → write activity_log event (platform_synced)
```

### Deduplication Strategy

1. **Fetch-level (sync tokens)**: Only request changes since last sync cursor. Reduces API call volume.
2. **Store-level (content_hash)**: Upsert on `(user_id, platform, resource_id, item_id, content_hash)`. Same content = no new row. Changed content = new row (previous version remains until TTL).

### Content Lifecycle (ADR-072)

```
Fetched → Stored (ephemeral, TTL set)
              ↓
         Consumed by deliverable/TP → mark_content_retained()
              ↓
         Retained (no TTL, persists)

         OR

         Not consumed → TTL expires → cleanup_expired_content() deletes
```

---

## Environment Variables

```bash
# Slack
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=

# Notion
NOTION_CLIENT_ID=
NOTION_CLIENT_SECRET=

# Google (Gmail + Calendar)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Encryption
INTEGRATION_ENCRYPTION_KEY=  # Required — missing raises ValueError at startup
```

---

## Key Files

| Concern | File |
|---------|------|
| Sync scheduler | `api/jobs/platform_sync_scheduler.py` |
| Sync worker | `api/workers/platform_worker.py` |
| Content storage (ADR-072) | `api/services/platform_content.py` |
| Google API client | `api/integrations/core/google_client.py` |
| Notion API client | `api/integrations/core/notion_client.py` |
| MCP client (Slack) | `api/integrations/core/client.py` |
| Token management | `api/integrations/core/tokens.py` |
| OAuth flows | `api/integrations/core/oauth.py` |
| TP platform tools | `api/services/platform_tools.py` |
| Tier limits | `api/services/platform_limits.py` |
| Freshness tracking | `api/services/freshness.py` |

---

## Adding New Platforms

With ADR-073, new platforms follow a single pattern:

1. **OAuth**: Add provider config to `oauth.py`
2. **API Client**: Create `integrations/core/{platform}_client.py`
3. **Sync Worker**: Add `_sync_{platform}()` to `platform_worker.py`
4. **Content Storage**: Define content_type, TTL, and sync token strategy
5. **TP Tools** (optional): Add to `platform_tools.py` for real-time user actions
6. **Delivery** (optional): Add exporter for write-back operations

All read operations by TP and deliverables automatically work via `platform_content` — no per-platform integration needed for reads.

---

## Related Documentation

- [ADR-073: Unified Fetch Architecture](../adr/ADR-073-unified-fetch-architecture.md) — current architecture
- [ADR-072: Unified Content Layer](../adr/ADR-072-unified-content-layer-tp-execution-pipeline.md) — `platform_content` schema
- [ADR-056: Per-Source Sync](../adr/ADR-056-per-source-sync-implementation.md) — selected_sources model
- [ADR-053: Platform Sync as Monetization](../adr/ADR-053-platform-sync-monetization.md) — tier-based sync frequency
- [Phase 1 Technical Debt](../development/PHASE-1-TECHNICAL-DEBT.md) — credential/resilience hardening
