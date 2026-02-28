# ADR-085: RefreshPlatformContent Primitive

**Status**: Implemented
**Date**: 2026-02-28
**Supersedes**: ADR-065 "live-first" platform content access pattern (partially)

## Context

TP's platform content access followed a 3-step model (ADR-065):
1. Live platform tools first (`platform_slack_*`, etc.)
2. Fallback to `Search(scope="platform_content")` for cached data
3. If cache empty → `Execute(action="platform.sync")` (fire-and-forget) → tell user to come back later

Step 3 was a dead end. The sync ran asynchronously — TP started a background job, told the user to check back, and stopped. For real-time questions like "I just got an email, can you help?" this broke the conversation flow.

## Decision

Add a `RefreshPlatformContent` primitive that performs a **synchronous, awaited** platform sync within the chat turn. This follows the **RAG cache-miss pattern**:

1. Check local store (`Search(scope="platform_content")`)
2. On miss/staleness → targeted upstream fetch (`RefreshPlatformContent`)
3. Write to store (via existing `_sync_platform_async()` pipeline)
4. Serve from store (`Search` again with fresh data)

### New content access model (replaces ADR-065 step 3):

1. `Search(scope="platform_content")` — primary query against synced data
2. If stale/empty → `RefreshPlatformContent(platform="slack")` — synchronous sync (~10-30s)
3. Re-query with `Search` — data is now fresh
4. Live platform tools (`platform_slack_*`) — for write operations, interactive lookups, CRUD

### What stays the same:

- Scheduler-based tier-gated cron syncs (ADR-077) continue unchanged
- Headless mode uses `freshness.sync_stale_sources()` for deliverable generation
- Frontend "Run sync" button on context pages continues calling REST endpoint
- All data flows through `platform_content` — TP never reads raw API responses

## Implementation

### Primitive definition

- **Name**: `RefreshPlatformContent`
- **Mode**: `["chat"]` only — headless uses `freshness.sync_stale_sources()`
- **Parameters**: `platform` (enum: slack, gmail, notion, calendar)
- **Staleness threshold**: 30 minutes — skips re-sync if content was fetched recently
- **Engine**: Calls `_sync_platform_async()` from `platform_worker.py` (same pipeline as scheduler)

### Singular implementation

`Execute(action="platform.sync")` removed — `RefreshPlatformContent` replaces it entirely. The Execute handler was fire-and-forget (started sync in background, returned immediately). RefreshPlatformContent awaits completion and returns a summary, making it strictly better for the TP conversation flow.

### Files

| File | Change |
|------|--------|
| `api/services/primitives/refresh.py` | NEW — tool definition + handler |
| `api/services/primitives/registry.py` | Register primitive |
| `api/services/primitives/search.py` | Update description (remove "live-first" directive) |
| `api/services/primitives/execute.py` | Remove `platform.sync` action |
| `api/agents/tp_prompts/platforms.py` | Update content access guidance |
| `api/agents/tp_prompts/behaviors.py` | Replace fire-and-forget Step 3 |
| `api/agents/tp_prompts/tools.py` | Add RefreshPlatformContent docs |

## Consequences

- TP can answer real-time questions about platform content without breaking conversation flow
- 30-minute staleness threshold prevents redundant syncs during rapid-fire questions
- No new API clients or sync logic — fully reuses existing worker pipeline
- Future platforms (Linear, Microsoft, etc.) automatically supported once added to `_sync_platform_async()`

## Known Concern: Dual Freshness Check Implementations

Two modules implement staleness checks via different mechanisms:

| Module | Queries | Threshold | Mode |
|--------|---------|-----------|------|
| `refresh.py` (this ADR) | `platform_content.fetched_at` | 30 minutes | Chat |
| `freshness.py` (ADR-049) | `sync_registry.last_synced_at` | 24 hours (configurable) | Headless |

Today these are both simple threshold comparisons and serve distinct modes — acceptable as-is. However, if freshness logic grows more complex (per-source staleness, exponential backoff on failure, tier-aware thresholds), the two implementations will diverge and become a maintenance risk.

**Recommendation**: If either implementation needs to become more sophisticated, extract a shared `is_platform_fresh(user_id, platform, threshold_minutes)` utility that both modules call. Do not pre-emptively abstract — wait until complexity actually materializes.