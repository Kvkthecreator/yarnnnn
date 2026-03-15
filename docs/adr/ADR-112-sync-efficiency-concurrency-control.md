# ADR-112: Sync Efficiency & Concurrency Control

**Status**: Accepted (docs complete, implementation pending)
**Date**: 2026-03-15
**Depends on**: ADR-053 (Tier Model), ADR-056 (Per-Source Sync), ADR-073 (Sync Tokens), ADR-077 (Platform Sync Overhaul), ADR-085 (RefreshPlatformContent)

## Context

Platform sync (ADR-077) works correctly but has two structural inefficiencies discovered during system page audit (2026-03-15):

### Problem 1: No "nothing changed" fast-path

The current flow always iterates every selected source and makes per-source API calls, even when a platform has zero new content:

```
Scheduler tick → _needs_sync() checks cooldown → iterate ALL sources →
  per-source delta fetch → store content → update sync_registry
```

For a Pro user with 20 Slack channels, this means 20+ API calls every hour even if nothing happened. Delta detection (ADR-073 cursors) already minimizes *what* is fetched per source, but doesn't skip the source iteration itself.

### Problem 2: TOCTOU race in scheduler dedup

The scheduler runs every 5 minutes (`*/5 * * * *`). `_needs_sync()` uses a cooldown (`SCHEDULE_WINDOW_MINUTES = 10` in `platform_limits.py`) to prevent duplicate syncs. But this creates a Time-Of-Check-Time-Of-Use race:

1. Cron fires at `:00`, `_needs_sync()` returns True, sync starts (takes 30s)
2. Cron fires at `:05`, `_needs_sync()` checks `sync_registry.last_synced_at` — still shows the *previous* sync time because the `:00` sync hasn't finished yet
3. Second sync starts → duplicate `platform_synced` activity log entries, wasted API calls

The `SCHEDULE_WINDOW_MINUTES = 10` is a timing hack that *usually* prevents this but isn't architecturally sound.

### Problem 3: No concurrency guard between sync paths

Three paths can trigger a platform sync:

| Path | Entry point | Checks cooldown? | Concurrency guard? |
|------|------------|-------------------|--------------------|
| Scheduled | `platform_sync_scheduler.py` → `_sync_platform_async()` | Yes (`_needs_sync()`) | None |
| Frontend "Sync Now" | `POST /integrations/{provider}/sync` → `BackgroundTasks` | **No** | None |
| TP chat | `RefreshPlatformContent` primitive → `_sync_platform_async()` | 30-min staleness check | None |

If a user clicks "Sync Now" while a scheduled sync is running, both execute simultaneously. This is *functionally safe* (content_hash dedup on `platform_content` prevents duplicate rows) but wastes API quota and produces duplicate activity log entries.

## Decision

Three optimization layers, ordered by implementation priority:

### Layer 1: Sync lock on `platform_connections` (fixes Problems 2 & 3)

Add `sync_in_progress` (boolean) and `sync_started_at` (timestamptz) columns to `platform_connections`. These represent the actual execution boundary — sync operates per-platform per-user.

**Acquire lock before sync:**
```python
# Atomically set lock if not already held (or stale)
UPDATE platform_connections
SET sync_in_progress = true, sync_started_at = NOW()
WHERE user_id = :uid AND platform = :platform
  AND (sync_in_progress = false OR sync_started_at < NOW() - INTERVAL '10 minutes')
RETURNING id;
```

If no row returned → sync already in progress → skip (scheduled) or return "sync in progress" (manual).

**Release lock after sync (success or failure):**
```python
UPDATE platform_connections
SET sync_in_progress = false, sync_started_at = NULL
WHERE user_id = :uid AND platform = :platform;
```

**Stale lock timeout**: 10 minutes. If `sync_started_at` is older than 10 minutes, the previous sync is assumed crashed and the lock is force-acquired. This matches the maximum expected sync duration for a heavily-loaded account.

**Behavior by sync path:**

| Path | On lock conflict |
|------|-----------------|
| Scheduled sync | Skip silently (another sync is running, next cron tick will pick up) |
| Frontend "Sync Now" | Return `{"status": "sync_already_in_progress"}` — UX shows existing sync |
| TP `RefreshPlatformContent` | Return tool message "Sync already in progress, data will be fresh shortly" |

**Removes**: `SCHEDULE_WINDOW_MINUTES = 10` constant — no longer needed.

### Layer 2: Platform-level heartbeat fast-path (fixes Problem 1)

Before iterating sources, make ONE lightweight API call per platform to check if anything changed since last sync:

| Platform | Heartbeat check | Cost | "No change" signal |
|----------|----------------|------|--------------------|
| Slack | `conversations.list` (exclude_members, limit=1 per channel with `latest` ts) | 1 API call | All channel `latest` timestamps unchanged vs `sync_registry.platform_cursor` |
| Gmail | `users.getProfile` → `historyId` | 1 API call | `historyId` unchanged since last sync (monotonically increasing) |
| Calendar | `events.list` with `syncToken` | 1 API call | Empty response (Google's native incremental sync) |
| Notion | `search` with `last_edited_time` > last sync, `page_size=1` | 1 API call | 0 results |

**If heartbeat shows no change:**
- Skip entire source iteration
- Update `sync_registry.last_synced_at` for all sources (confirms "checked, nothing new")
- Log `platform_synced` with `items_synced: 0` and `metadata: {"heartbeat": true}`
- Total cost: ~100ms + 1 API call vs 5-30s + N API calls

**Heartbeat cursor storage**: Store the platform-level cursor (e.g., Gmail `historyId`, Slack channel `latest` map) in `platform_connections.settings` under a `sync_cursor` key. This is distinct from per-resource cursors in `sync_registry.platform_cursor`.

**Fallback**: If heartbeat check fails (API error, rate limit), fall through to full source iteration. Heartbeat is an optimization, not a gate.

### Layer 3: Per-source skip hints (optional, deferred)

When heartbeat indicates *some* change but not *all* sources changed, use heartbeat response to skip unchanged sources. Example: Slack heartbeat returns `latest` ts per channel — only iterate channels whose `latest` > `sync_registry.platform_cursor`.

**Deferred because**: Layer 2 already eliminates the most expensive case (zero-change syncs). Per-source skipping adds complexity for marginal gain. Revisit when accounts have 50+ sources.

## Architectural Precedent

This follows the same pattern as ADR-085 (RefreshPlatformContent):

> **RAG cache-miss pattern**: Check local store → on miss/staleness → targeted upstream fetch → serve from store.

The heartbeat is the "check local store" step applied at the platform level. If the heartbeat confirms freshness, we skip the "upstream fetch" entirely. The sync lock ensures only one fetch runs at a time, preventing the "thundering herd" equivalent.

## Interaction with Existing Sync Architecture

**What stays unchanged:**
- ADR-077 three-phase model (landscape → delta → extraction) — heartbeat is a new Phase 0
- ADR-073 platform-native cursors — still used for per-source delta detection when heartbeat indicates changes
- ADR-056 per-source sync — source iteration logic unchanged
- `sync_registry` as per-resource truth — heartbeat doesn't replace it, just gates access to it
- Content dedup via `content_hash` on `platform_content` — safety net preserved
- ADR-085 `RefreshPlatformContent` — same worker pipeline, now respects sync lock
- Tier-based frequency (`_needs_sync()` cooldowns) — preserved as first gate before lock acquisition

**What changes:**
- `SCHEDULE_WINDOW_MINUTES` removed (replaced by sync lock)
- `platform_connections` gains `sync_in_progress` + `sync_started_at` columns
- `platform_connections.settings` gains `sync_cursor` for platform-level heartbeat state
- `platform_worker.py` gains heartbeat check before source iteration
- `platform_sync_scheduler.py` acquires/releases sync lock around `_sync_platform_async()`
- Manual sync endpoints check sync lock before dispatching

## Dual Freshness Check Note (from ADR-085)

ADR-085 flagged the dual freshness implementations (`refresh.py` 30-min threshold vs `freshness.py` 24-hour threshold). This ADR does NOT unify them — they serve distinct purposes:

- `refresh.py` guards chat-turn syncs (short threshold, user-facing latency)
- `freshness.py` guards headless agent syncs (long threshold, background execution)

The sync lock (Layer 1) naturally coordinates between them — both paths acquire the same lock, preventing overlap regardless of which freshness check triggered the sync.

## Migration

```sql
-- Migration: Add sync concurrency control to platform_connections
ALTER TABLE platform_connections ADD COLUMN IF NOT EXISTS sync_in_progress boolean DEFAULT false;
ALTER TABLE platform_connections ADD COLUMN IF NOT EXISTS sync_started_at timestamptz;
```

## Files to Modify (Implementation)

| File | Change |
|------|--------|
| `supabase/migrations/109_sync_concurrency_control.sql` | Add columns |
| `api/workers/platform_worker.py` | Heartbeat check (Phase 0), lock acquire/release |
| `api/jobs/platform_sync_scheduler.py` | Lock acquire before `_sync_platform_async()`, release after |
| `api/routes/integrations.py` | Check lock in `trigger_platform_sync`, return status if locked |
| `api/services/primitives/refresh.py` | Check lock, return message if sync in progress |
| `api/services/platform_limits.py` | Remove `SCHEDULE_WINDOW_MINUTES` |
| `api/integrations/core/slack_client.py` | Add lightweight `get_channel_latest()` for heartbeat |
| `api/integrations/core/google_client.py` | Add `get_gmail_history_id()`, calendar syncToken check |
| `api/integrations/core/notion_client.py` | Add `check_recent_changes()` for heartbeat |

## Risks & Mitigations

- **Stale lock (crashed sync)**: 10-minute timeout auto-releases. Chosen to exceed max observed sync duration (~45s for heavy accounts) with generous margin.
- **Heartbeat API changes**: Each heartbeat is a standard, stable API call (profile, list, search). Wrapped in try/except with fallthrough to full sync.
- **Clock skew**: Lock uses DB-side `NOW()` not application time. All comparisons server-side.
- **Race on lock acquisition**: The UPDATE ... WHERE ... RETURNING pattern is atomic in Postgres. Two concurrent acquires on the same row: one wins, one gets empty result.

## Verification

After implementation:
1. Scheduled sync with no platform changes → heartbeat skips source iteration, completes in <1s
2. Two cron ticks 5 min apart → second skips due to lock, zero duplicate activity_log entries
3. "Sync Now" during scheduled sync → returns "sync in progress" (no duplicate execution)
4. TP `RefreshPlatformContent` during scheduled sync → returns "sync in progress" message
5. Crashed sync (kill process mid-sync) → next tick after 10 min auto-recovers
