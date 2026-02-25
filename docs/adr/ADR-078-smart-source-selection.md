# ADR-078: Smart Source Auto-Selection

**Status**: Implemented
**Date**: 2026-02-25
**Depends on**: ADR-077 (Platform Sync Overhaul), ADR-053 (Tier Model)

## Context

ADR-077 hardened sync mechanics — pagination, thread expansion, system message filtering, wider time windows. But production results showed nearly identical content volume because the **source selection scope** hadn't changed.

The test user had 252 available resources across 4 platforms but only 6 selected (2 Slack channels, 1 Gmail label, 1 calendar, 2 Notion pages). That's 2.4% surface area coverage. The accumulation moat (ADR-072) cannot build on 2.4%.

The root cause: source selection is fully manual. After OAuth connect, users see an empty checklist and must explicitly pick sources. Most users select minimally and never return to expand.

API fetch costs are negligible — the real cost gates are LLM calls (deliverables, signals), not platform API reads. Broadening content capture has near-zero marginal cost.

## Decision

### 1. Smart auto-selection on first connect

When landscape is first discovered and `selected_sources` is empty, auto-select the most valuable sources up to tier limit using platform-specific heuristics:

| Platform | Heuristic | Rationale |
|----------|-----------|-----------|
| Slack | Sort by `num_members` desc | Busiest channels = most context |
| Gmail | INBOX → SENT → STARRED → IMPORTANT → user labels (skip SPAM/TRASH/CATEGORY_*) | Priority labels first, skip noise |
| Calendar | ALL calendars (unlimited tier) | Tiny data volume, 2-day TTL, high signal value |
| Notion | Sort by `last_edited` desc, deprioritize "Untitled" | Recently active pages = most relevant |

### 2. Calendar: always all

Calendar has `calendars: -1` (unlimited) in all tiers. Auto-select every calendar the user has access to. Calendar events are short text with 2-day TTL — the data volume is negligible.

### 3. Backfill for existing users

Admin endpoint `POST /admin/backfill-sources/{user_id}` expands existing users' selections to tier limits using the same heuristics. Preserves existing selections and adds new ones.

### 4. Frontend unchanged

The source selection modal reads `selected_sources` from the API. Pre-selected defaults show up as checked boxes — the user can still uncheck or rearrange. No frontend code changes needed.

## Implementation

**`api/services/landscape.py`**:
- `compute_smart_defaults(provider, resources, max_sources)` — pure function, no side effects
- Called by `discover_landscape()` result handler and `refresh_landscape()` when `selected_sources` is empty

**`api/routes/integrations.py`**:
- Landscape endpoint calls `compute_smart_defaults` when `existing_selected` is empty after discovery

**`api/routes/admin.py`**:
- `POST /admin/backfill-sources/{user_id}` — merges smart defaults with existing selections up to tier limit

## Production Results

Test user (kvkthecreator@gmail.com) before and after backfill:

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Selected sources | 6 | 50 | 8.3x |
| Slack messages | 3 | 199 | 66x |
| Gmail emails | 30 | 70 | 2.3x |
| Calendar events | 1 | 41 | 41x |
| Notion pages | 2 | 25 | 12.5x |
| **Total content** | **36** | **335** | **9.3x** |

## Consequences

- New users get meaningful content from first sync without manual curation
- Existing users can be backfilled via admin endpoint
- Users retain full control — auto-selections are pre-checked, not locked
- API cost impact is negligible (platform reads, not LLM calls)
- `platform_content` table grows faster — existing TTL cleanup handles this
