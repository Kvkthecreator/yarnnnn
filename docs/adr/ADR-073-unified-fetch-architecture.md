# ADR-073: Unified Fetch Architecture

**Status**: Accepted
**Date**: 2026-02-23
**Supersedes**: Portions of ADR-068 (signal extraction via live APIs)
**Relates to**: ADR-072 (Unified Content Layer), ADR-056 (Per-Source Sync), ADR-053 (Platform Sync as Monetization Base Layer)

---

## Context

Audit of the codebase (2026-02-23) revealed **three independent subsystems** making live platform API calls with no coordination:

| Subsystem | Entry Point | Writes to `platform_content`? | Source Filtering | Time Window |
|-----------|-------------|-------------------------------|------------------|-------------|
| Platform Sync | `platform_sync_scheduler.py` → `platform_worker.py` | Yes | `selected_sources` | Hardcoded per platform |
| Signal Extraction | `unified_scheduler.py` → `signal_extraction.py` | No (discards after LLM triage) | Partial (Slack/Notion yes, Gmail/Calendar no) | Hardcoded per platform |
| Deliverable Execution | `unified_scheduler.py` → `deliverable_pipeline.py` | No (in-memory cache) | Deliverable config | Configurable |

Additionally, deliverable execution reads from `platform_content` AND live-fetches, merging both into the LLM prompt — two data paths for one operation.

### Problems

1. **Triple fetch**: The same Gmail API gets called by sync, signal extraction, and deliverable execution within the same hour.
2. **Inconsistent filtering**: Gmail signal extraction ignores `selected_sources` and queries `in:inbox`. Calendar signal extraction has no source filtering.
3. **Data discard**: Signal extraction fetches content, passes summaries to Haiku, then discards everything. The raw data is lost — no accumulation.
4. **Unwired retention**: `mark_content_retained()` is defined but never called. `cleanup_expired_content()` is defined but not in any scheduler. The content lifecycle is incomplete.
5. **Monetization bypass**: Signal processing runs hourly for all users regardless of tier, bypassing the sync frequency lever (ADR-053).

## Decision

### Single Fetch Path

**Platform sync is the only subsystem that calls external platform APIs.**

```
┌─────────────────────────────────────────────────────────────────┐
│ FETCH LAYER (singular)                                          │
│                                                                 │
│ platform_sync_scheduler → platform_worker                       │
│   - One fetch per platform per source per sync cycle            │
│   - Writes ALL content to platform_content                      │
│   - Full content (not summaries, not snippets)                  │
│   - content_hash dedup prevents duplicate rows                  │
│   - TTL-based expiry for ephemeral content                      │
│   - Tier-gated frequency (ADR-053)                              │
│   - This is the ONLY subsystem that talks to external APIs      │
│                                                                 │
│ Signal extraction and deliverable execution do NOT call APIs.   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ writes to
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ CONTENT LAYER (platform_content — single source of truth)       │
│                                                                 │
│ - Immutable store of fetched content                            │
│ - content_hash prevents duplicate writes                        │
│ - TTL expires unreferenced content automatically                │
│ - Retention marks what downstream consumers used                │
│ - cleanup_expired_content runs periodically                     │
│ - ALL downstream consumers read from here                       │
└──────────────┬───────────────────────┬──────────────────────────┘
               │ reads                 │ reads
               ▼                       ▼
┌──────────────────────────┐ ┌────────────────────────────────────┐
│ SCHEDULING HEURISTICS    │ │ SEMANTIC LAYER                     │
│                          │ │                                    │
│ Rules + freshness checks │ │ LLM reasoning over content:        │
│ against platform_content │ │ - TP chat (user-initiated)         │
│ metadata. No LLM calls.  │ │ - Deliverable execution (system)   │
│                          │ │                                    │
│ Decides WHEN to invoke   │ │ Marks consumed content as retained │
│ the semantic layer.       │ │ via mark_content_retained()        │
└──────────────────────────┘ └────────────────────────────────────┘
```

### Fetch Hardening Requirements

#### Per-Platform Specifications

| Platform | API | Source Filter | Time Window | Items per Source | Sync Token Support |
|----------|-----|---------------|-------------|------------------|--------------------|
| **Slack** | MCP `get_channel_history` | `selected_sources` (all selected) | Last 2 days | 50 messages/channel | `oldest` param (last fetched ts) |
| **Gmail** | Google `list_messages` + `get_message` | `selected_sources` (per-label) | Last 7 days | 50 per label (full message) | `historyId` for delta sync |
| **Calendar** | Google `list_calendar_events` | `selected_sources` (per-calendar) | Next 7 days | 50 per calendar | `syncToken` for delta sync |
| **Notion** | Notion `get_page` + `get_page_content` | `selected_sources` (page IDs) | Full page (no time window) | 1 page = 1 item | `last_edited_time` comparison |

#### Sync Token / Incremental Sync (Near-Term)

Store a sync cursor per resource in `sync_registry`. On each sync cycle:

1. Read cursor from `sync_registry` for this `(user_id, platform, resource_id)`
2. Pass cursor to API call (e.g., Gmail `historyId`, Calendar `syncToken`, Slack `oldest`)
3. Fetch only changes since cursor
4. Write new content to `platform_content`
5. Update cursor in `sync_registry`

Fallback: if cursor is missing or stale (>TTL), do a full fetch for the configured time window.

#### Credential Handling (Already Hardened — Phase 1)

All platforms use `TokenManager.decrypt()` consistently (commit `2851612`):
- Slack: `credentials_encrypted` → JSON with `bot_token`, `team_id`
- Gmail/Calendar: `refresh_token_encrypted` → refresh token → `GoogleAPIClient._get_access_token()` (with 1-hour caching)
- Notion: `credentials_encrypted` → access token (no expiry)

Google API calls use `_request_with_retry` with:
- `httpx.Timeout(30.0, connect=10.0)` on all calls
- Exponential backoff (1s, 2s, 4s) on 429/5xx
- 3 max retries

#### Deduplication

Two-level strategy:
1. **Fetch-level**: Sync tokens prevent re-fetching unchanged content from APIs
2. **Store-level**: `content_hash` upsert on `(user_id, platform, resource_id, item_id, content_hash)` prevents duplicate rows when content hasn't changed

#### Error Handling and Success/Fail

Per-source-per-cycle tracking:
- Each source sync writes to `activity_log` (event_type: `platform_synced`)
- Metadata includes: items fetched, items new (vs dedup), errors, sync token used
- Failed sources don't block other sources for the same user
- Failed syncs preserve the previous cursor (retry next cycle with same window)

### Webhooks (Deferred — Future Optimization)

Gmail push notifications, Slack Events API, and Notion webhooks would replace polling with push-based updates. This eliminates the fetch-then-compare pattern entirely.

**Deferred because**:
- Requires publicly accessible endpoint with signature verification
- Retry handling and delivery guarantees differ per platform
- Current polling architecture must be proven and stable first
- Single-fetch consolidation is prerequisite regardless

When pursued, webhooks write to `platform_content` through the same store path — they replace the trigger mechanism (push vs poll) but not the storage layer.

### Retention Lifecycle (Wire Existing Functions)

1. **Deliverable execution**: After synthesis, call `mark_content_retained(content_ids, reason='deliverable_execution', ref=version_id)`. The `platform_content_ids` are already captured in `deliverable_pipeline.py:3723` — just need to pass to retain function.
2. **TP sessions**: When TP reads platform content during chat, call `mark_content_retained(content_ids, reason='tp_session', ref=session_id)`.
3. **Cleanup**: Add `cleanup_expired_content()` to unified scheduler (hourly). Deletes non-retained content past TTL.
4. **Versioning**: When `content_hash` differs for the same `(resource_id, item_id)`, the upsert creates a new row (different hash = different unique key). Previous version remains until TTL expiry or cleanup. For explicit version tracking, use the existing `version_of` FK column.

### Signal Processing Transformation

The current `signal_extraction.py` + `signal_processing.py` LLM triage pipeline is replaced by scheduling heuristics:

**Rule-based triggers** (no LLM call):
- Calendar: "Event with >2 external attendees in next 4 hours" → trigger `meeting_prep` deliverable
- Content freshness: "New platform_content arrived for this deliverable's sources since last run" → trigger execution
- Staleness: "Deliverable hasn't run in >2x its configured frequency" → trigger execution

**What this removes**:
- `signal_extraction.py` live API calls (replaced by reading `platform_content`)
- `signal_processing.py` Haiku LLM triage call (replaced by scheduling rules)
- The hourly per-user LLM cost for signal classification

**What this preserves**:
- Signal-emergent deliverable creation (a scheduling rule can still create a new deliverable)
- Deduplication via `signal_history` (same mechanism, different trigger)
- `activity_log` tracking of scheduling decisions

### Monetization (Scoped Separately — ADR-074)

The fetch architecture provides natural monetization control points:

**Data handling layer**:
- Sync frequency (tier-gated: Free=2x/day, Starter=4x/day, Pro=hourly)
- Number of sources per platform (tier-gated: Free=1, Starter=5, Pro=20)
- Number of platform connections

**Compute layer**:
- Number of LLM-consuming operations per period (TP sessions + deliverable runs)
- Token usage per operation

Enforcement at fetch level means downstream consumers (TP, deliverables) are automatically scoped — they can only access what was fetched and stored.

Detailed monetization scoping is a separate concern requiring its own ADR.

### Observability (Scoped Separately — Documented in `docs/features/`)

The singular fetch path enables single-point instrumentation:

**Fetch layer**: Per-sync-cycle logging of what was fetched, from which sources, how many items, new vs duplicate, errors
**Content layer**: When fetched, when retained (by what), when expired
**Consumer layer**: What content was consumed by which deliverable/TP session

Detailed observability design is a separate concern requiring its own feature documentation and potentially its own ADR.

---

## Consequences

### Positive
- Single source of truth for platform data (`platform_content`)
- API calls happen once, not three times
- Monetization enforcement at fetch level automatically gates all downstream consumers
- Content accumulates — nothing is fetched and discarded
- Sync tokens reduce API call volume over time
- Observability instrumentable at one point

### Negative
- Content freshness depends on sync frequency — Free users see up to 12-hour-old data
- Calendar time-sensitivity may require more aggressive sync for Pro tier
- Removing Haiku triage means scheduling rules need to be well-designed to avoid unnecessary Sonnet calls

### Migration Path

1. ~~Wire `mark_content_retained` and `cleanup_expired_content` into existing pipeline~~ **Done** (2026-02-23, commit d300394)
2. ~~Add sync token support to `platform_worker.py` per-platform~~ **Done** (2026-02-23) — Slack `oldest`, Gmail date cursor, Calendar `syncToken`, Notion `last_edited_time`
3. ~~Modify signal processing to read `platform_content` instead of live APIs~~ **Done** (2026-02-23, commit d300394) — `signal_extraction.py` rewritten to read from `platform_content`
4. Replace LLM signal triage with scheduling heuristics — **Proposed** in ADR-074
5. ~~Remove `fetch_integration_source_data` from deliverable execution~~ **Done** (2026-02-23, commit d300394) — execution strategies read from `platform_content`
6. ~~Remove `signal_extraction.py` live API calls~~ **Done** (2026-02-23, commit d300394)
7. Instrument fetch layer for observability — **Deferred**

---

## References

- ADR-072: Unified Content Layer & TP Execution Pipeline
- ADR-056: Per-Source Sync Implementation
- ADR-053: Platform Sync as Monetization Base Layer
- ADR-068: Signal-Emergent Deliverables (partially superseded)
- `docs/integrations/PLATFORM-INTEGRATIONS.md` (updated alongside this ADR)
