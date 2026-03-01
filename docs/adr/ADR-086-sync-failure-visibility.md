# ADR-086: Sync Failure Visibility

**Status**: Implementing
**Date**: 2026-03-01
**References**: ADR-084 (System Observability), ADR-077 (Platform Sync Overhaul)

## Problem

Platform syncs can silently fail due to expired OAuth tokens, rate limits, or API errors. The sync infrastructure already tracks errors (`sync_registry.last_error`, `activity_log` metadata), but neither the Context pages nor the System page surfaces them to users. This led to 24+ hours of undetected sync failures during development.

## Decision

Surface sync errors in two existing locations:

1. **Context pages** (per-platform): Add error count to `SyncStatusBanner`, add `'error'` health state to `PlatformSyncActivity` source health table, categorize raw errors into user-friendly messages.

2. **System page** (schedule observability): Add `"failed"` window status to `_build_todays_windows()` when activity_log events contain `metadata.error`.

## Scope

- Backend: Extend `sync-status` endpoint with error fields, extend system schedule windows
- Frontend: Error banner, error health badges, error categorization utility, failed window pills
- No new pages, tables, or cron jobs

## Key Design Choices

- **Error categorization on frontend**: Raw errors are technical strings (e.g., "Token refresh failed: 400 Bad Request"). Map to user-friendly categories client-side via `web/lib/sync-errors.ts`.
- **Errors take priority over timing**: In `SyncStatusBanner`, error state renders before lag/healthy states.
- **Existing data**: `sync_registry.last_error` written by worker via `freshness.py`, `LandscapeResource.last_error` already typed — no new data collection needed.

## Files Modified

- `api/routes/integrations.py` — sync-status endpoint error fields
- `api/routes/system.py` — failed window status
- `web/lib/sync-errors.ts` — error categorization (new)
- `web/lib/api/client.ts` — type extensions
- `web/components/context/SyncStatusBanner.tsx` — error banner
- `web/components/context/PlatformSyncActivity.tsx` — error health state
- `web/app/(authenticated)/context/{slack,gmail,notion,calendar}/page.tsx` — wire errorCount
- `web/app/(authenticated)/system/page.tsx` — failed window pill color
