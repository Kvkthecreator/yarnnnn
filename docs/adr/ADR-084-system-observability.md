# ADR-084: System Page Observability

**Status**: Implemented
**Date**: 2026-02-28
**Depends on**: ADR-053 (Tier Model), ADR-072 (Unified Content Layer), ADR-077 (Platform Sync Overhaul)

## Context

Over 24+ hours of debugging, platform syncs were silently failing due to (1) a missing Render cron (never provisioned) and (2) a nested `asyncio.run()` bug in `platform_sync_scheduler.py`. Both issues would have been immediately visible if the System page surfaced schedule-level observability — the user's timezone, expected schedule windows, and whether each window was hit or missed.

Currently the System page shows **what happened last** (last run time, status badge, items processed) but not **what should have happened and didn't**. For tier-based sync schedules (ADR-053), the expected cadence is deterministic — if a Starter user has 4x/day windows at 00:00/06:00/12:00/18:00 KST, a "missed" window is a clear signal of an infrastructure problem.

### Broken `next_sync_at` (Bug)

`api/routes/system.py` line 254 calculated `next_sync_at` as `last_sync + hours_between` using a hardcoded arithmetic map. This was wrong in two ways:
1. Missing `1x_daily` entry (defaulted to 6 hours instead of 24)
2. Doesn't use actual schedule windows — calculates from last sync time rather than the schedule

The correct approach: reuse `get_next_sync_time()` from `platform_limits.py` which already implements schedule-aware calculation.

## Decision

Extend the existing System page's Background Activity section with schedule-level observability. No new page sections, no new event handling.

### Backend Changes (`api/routes/system.py`)

1. **Fix `next_sync_at`**: Replace hardcoded arithmetic with `get_next_sync_time(sync_frequency, user_timezone)` from `platform_limits.py`

2. **Add `sync_schedule` to response**: New field on `SystemStatusResponse` containing:
   - User timezone (from `user_context` table)
   - Sync frequency label (human-readable)
   - Today's schedule windows with hit/miss status
   - Correct `next_sync_at`

3. **Add `schedule_description` to `BackgroundJobStatus`**: Static mapping of when each background job type is scheduled to run

4. **Window status logic**: Query today's `platform_synced` activity_log events (single DB call). For each schedule window, check if a sync event fell within the window. Return "completed", "missed", "upcoming", or "active".

### Frontend Changes (`web/app/(authenticated)/system/page.tsx`)

1. **Sync schedule observability bar**: At the top of Background Activity section, show timezone, frequency, next sync, and window status pills (green=completed, red=missed, gray=upcoming, blue=active)

2. **Schedule annotations**: Each background job row shows its expected schedule cadence as muted subtext

### Reused Existing Code

| Function | File | Usage |
|----------|------|-------|
| `SYNC_SCHEDULES` | `api/services/platform_limits.py` | Schedule window definitions |
| `get_next_sync_time()` | `api/services/platform_limits.py` | Correct next sync calculation |
| `_resolve_timezone()` | `api/services/platform_limits.py` | User timezone resolution |
| `SCHEDULE_WINDOW_MINUTES` | `api/services/platform_limits.py` | Window tolerance (10 min) |

## Files Modified

| File | Changes |
|------|---------|
| `docs/adr/ADR-084-system-observability.md` | **New** — this document |
| `api/routes/system.py` | Fix `next_sync_at`, add `ScheduleWindow` model, extend `SystemStatusResponse` with `sync_schedule`, add `schedule_description` to `BackgroundJobStatus`, add window status helper |
| `web/app/(authenticated)/system/page.tsx` | Add types, sync schedule observability bar, schedule annotations on job rows |
| `web/lib/api/client.ts` | Extend system status return type |

## Risks & Mitigations

- **Additional DB query**: One extra query to `activity_log` for today's `platform_synced` events. Bounded by 24 events max (hourly tier). Negligible cost.
- **Timezone mismatch**: Users without a timezone row in `user_context` default to UTC. Displayed timezone makes this visible.
- **Backward compatibility**: New fields are additive (`sync_schedule` is Optional, `schedule_description` is Optional). No breaking changes.

## Verification

1. `GET /api/system/status` returns `sync_schedule` with correct timezone and window statuses
2. `next_sync_at` on each platform matches actual schedule window (not `last_sync + hours`)
3. Past windows with `platform_synced` events = "completed"; past windows without = "missed"; future = "upcoming"
4. System page Background Activity shows observability bar with window pills
5. Existing `SyncStatusBanner` on context pages picks up corrected `next_sync_at` automatically
6. No regressions in existing Background Activity rendering
