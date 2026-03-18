# ADR-056: Per-Source Sync Implementation

> **Status**: Accepted
> **Date**: 2026-02-12
> **Deciders**: Kevin (solo founder)
> **Related**: ADR-053 (Platform Sync Monetization), ADR-055 (Gmail Label-Based Sync)

---

## Context

### The Gap

ADR-053 establishes per-source sync as the **monetization base layer**:

| Tier | Slack Channels | Gmail Labels | Notion Pages | Calendars |
|------|----------------|--------------|--------------|-----------|
| Free | 1 | 1 | 1 | 1 |
| Starter | 5 | 5 | 5 | 3 |
| Pro | 20 | 15 | 25 | 10 |

**The Promise**: Users select specific sources, only those sources are synced, tier limits are enforced.

**The Reality**: After comprehensive audit, critical gaps exist:

| Platform | Per-Source Sync? | Actual Behavior | Gap |
|----------|------------------|-----------------|-----|
| Slack | **No** | Hardcoded `[:10]` channels | Ignores `selected_sources` |
| Gmail | **No** | Broad inbox fetch | ADR-055 not implemented |
| Notion | **No** | Top 20 recent pages | Ignores `selected_sources` |
| Calendar | **Missing** | No sync function exists | Not implemented at all |

### Root Cause

The enforcement chain is broken:

```
Route stores selected_sources ✓
  ↓
Scheduler calls worker with provider only ✗ (no selected_sources passed)
  ↓
Worker loads integration but ignores landscape.selected_sources ✗
  ↓
Worker syncs hardcoded limits (10 channels, 20 pages, broad inbox) ✗
```

**Key file**: `api/workers/platform_worker.py`
- Line 79-89: Loads full integration (includes landscape) but never uses it
- Line 153: `channels[:10]` hardcoded, not `selected_sources`
- Line 213: Gmail `list_messages()` has no label filtering
- Line 258-259: Notion `query=""` fetches recent, not selected

### Monetization Impact

This breaks monetization entirely:
- Free user selects 1 channel, sync fetches 10 channels
- User gets 10x more context than tier promises
- No upgrade incentive since limits aren't visible
- Can't charge based on label/channel/page count

---

## Decision

### Implement Full Per-Source Sync for All Platforms

#### 1. Worker: Accept and Use Selected Sources

**api/workers/platform_worker.py**

Update `sync_platform()` signature:
```python
def sync_platform(
    user_id: str,
    provider: str,
    selected_sources: list[str] | None = None,  # NEW
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
) -> dict:
```

If `selected_sources` not passed, extract from integration.landscape:
```python
integration = result.data
landscape = integration.get("landscape", {})
selected = selected_sources or landscape.get("selected_sources", [])
```

#### 2. Slack: Filter by Selected Channels

**Current** (`_sync_slack`):
```python
for channel in channels[:10]:  # Hardcoded
```

**New**:
```python
selected_channel_ids = set(selected_sources)
for channel in channels:
    if channel["id"] not in selected_channel_ids:
        continue  # Skip unselected
    # ... sync channel
```

#### 3. Gmail: Implement Label-Based Sync (ADR-055)

**Current** (`_sync_gmail`):
```python
messages = await gmail.list_messages(max_results=50)  # Broad inbox
```

**New**:
```python
# selected_sources format: ["label:Label_123", "label:Label_456"]
for source in selected_sources:
    if source.startswith("label:"):
        label_id = source.replace("label:", "")
        messages = await gmail.list_messages(
            max_results=50,
            label_ids=[label_id],  # Filter by label
        )
        for msg in messages:
            await _store_ephemeral_context(
                ...
                resource_id=f"label:{label_id}",  # Track per-label
                metadata={...,"label_id": label_id},
            )
```

#### 4. Notion: Filter by Selected Pages

**Current** (`_sync_notion`):
```python
pages = await manager.search_notion(..., query="")  # Top 20 recent
```

**New**:
```python
selected_page_ids = set(selected_sources)
for page_id in selected_page_ids:
    page = await manager.get_notion_page(page_id=page_id)
    if page:
        await _store_ephemeral_context(...)
```

#### 5. Calendar: Implement Sync Function

**Add new function** (`_sync_calendar`):
```python
async def _sync_calendar(client, user_id: str, integration: dict, selected_sources: list[str]) -> dict:
    """Sync Google Calendar events."""
    from integrations.providers.calendar import CalendarClient

    calendar = CalendarClient(
        access_token=integration.get("access_token"),
        refresh_token=integration.get("refresh_token"),
    )

    items_synced = 0
    for calendar_id in selected_sources:
        events = await calendar.list_events(
            calendar_id=calendar_id,
            time_min=datetime.now(timezone.utc) - timedelta(days=7),
            time_max=datetime.now(timezone.utc) + timedelta(days=30),
        )
        for event in events:
            await _store_ephemeral_context(
                client=client,
                user_id=user_id,
                source_type="calendar",
                resource_id=event.get("id"),
                resource_name=event.get("summary", "Untitled event"),
                ...
            )
            items_synced += 1

    return {"items_synced": items_synced}
```

#### 6. Scheduler: Pass Selected Sources to Worker

**api/jobs/platform_sync_scheduler.py**

Update job enqueue to include selected sources:
```python
# When enqueueing platform sync
landscape = integration.get("landscape", {})
selected_sources = landscape.get("selected_sources", [])

job = queue.enqueue(
    sync_platform,
    user_id=user_id,
    provider=provider,
    selected_sources=selected_sources,  # Pass through
)
```

#### 7. Resource ID Format Standardization

| Platform | Format | Example |
|----------|--------|---------|
| Slack | `{channel_id}` | `C123ABC456` |
| Gmail | `label:{label_id}` | `label:Label_123` |
| Notion | `{page_id}` | `abc123-def456-...` |
| Calendar | `{calendar_id}` | `primary` or `abc@group.calendar.google.com` |

---

## Implementation Plan

### Phase 1: Worker Foundation (Required for all platforms)

1. Update `sync_platform()` signature to accept `selected_sources`
2. Extract selected sources from integration if not passed
3. Pass selected sources to each provider sync function
4. Add logging to track which sources are synced

**Files**: `api/workers/platform_worker.py`

### Phase 2: Slack Channel Filtering

1. Change `channels[:10]` to filter by `selected_sources`
2. Log skipped channels (for debugging)
3. Update sync count to reflect actual synced channels

**Files**: `api/workers/platform_worker.py:_sync_slack()`

### Phase 3: Gmail Label-Based Sync (ADR-055 Implementation)

1. Add `label_ids` parameter to `GmailClient.list_messages()`
2. Loop over selected labels in `_sync_gmail()`
3. Store `label:{label_id}` as resource_id
4. Add `label_id` to metadata

**Files**:
- `api/integrations/providers/gmail.py`
- `api/workers/platform_worker.py:_sync_gmail()`

### Phase 4: Notion Page Filtering

1. Change from `search_notion(query="")` to explicit page fetch
2. Add `get_notion_page(page_id)` to MCP client
3. Loop over selected page IDs

**Files**:
- `api/integrations/core/client.py`
- `api/workers/platform_worker.py:_sync_notion()`

### Phase 5: Calendar Sync Implementation

1. Create `CalendarClient` class (if not exists)
2. Implement `_sync_calendar()` function
3. Add calendar case to worker dispatch
4. Register with scheduler

**Files**:
- `api/integrations/providers/calendar.py` (new or update)
- `api/workers/platform_worker.py`

### Phase 6: Scheduler Integration

1. Update scheduler to pass `selected_sources` to worker
2. Ensure landscape is loaded when enqueueing

**Files**: `api/jobs/platform_sync_scheduler.py`

---

## Verification Criteria

After implementation, these must be true:

1. **Slack**: Free user selects 1 channel → only that channel synced
2. **Gmail**: Free user selects 1 label → only that label's emails synced
3. **Notion**: Free user selects 1 page → only that page synced
4. **Calendar**: Free user selects 1 calendar → only that calendar's events synced
5. **Logs**: Worker logs show which sources were synced vs skipped
6. **Context**: `ephemeral_context.resource_id` matches selected source format

---

## Testing Plan

### Manual Verification

1. Set user to Free tier in database
2. Select exactly 1 source per platform
3. Trigger sync via scheduler or manually
4. Verify only 1 source appears in `ephemeral_context`
5. Change to Starter, add 5 sources, verify all 5 sync

### Automated Tests

```python
def test_slack_respects_selected_sources():
    # Setup: User with 10 channels, only 2 selected
    # Act: Run sync
    # Assert: Only 2 channels in ephemeral_context

def test_gmail_syncs_by_label():
    # Setup: User with label:Label_123 selected
    # Act: Run sync
    # Assert: All emails have resource_id="label:Label_123"
```

---

## Consequences

### Positive

1. **Monetization works** - Tier limits actually enforced
2. **Accurate sync status** - UI reflects reality
3. **Upgrade incentive** - Users hit limits, see value in upgrading
4. **ADR-053 alignment** - Per-source sync is the monetization layer

### Negative

1. **Migration needed** - Existing synced data has wrong resource_ids
2. **More API calls** - Per-source instead of bulk fetch
3. **Calendar work** - Net-new implementation required

### Mitigations

- **Migration**: Keep existing data, new syncs use correct format
- **API calls**: Platforms have generous rate limits
- **Calendar**: Builds on existing Google OAuth, minimal new code

---

## Related Files

**Core Worker:**
- `api/workers/platform_worker.py` - Main sync implementation

**Provider Clients:**
- `api/integrations/core/client.py` - MCP client manager
- `api/integrations/providers/gmail.py` - Gmail client
- `api/integrations/providers/calendar.py` - Calendar client (new/update)

**Scheduler:**
- `api/jobs/platform_sync_scheduler.py` - Tier-based scheduling

**Limits:**
- `api/services/platform_limits.py` - Tier definitions (already correct)

**Frontend (no changes needed for this ADR):**
- Frontend already shows source selection UI
- Will reflect correct sync status once backend fixed

---

## See Also

- [ADR-053: Platform Sync Monetization](ADR-053-platform-sync-monetization.md) - Monetization model
- [ADR-055: Gmail Label-Based Sync](ADR-055-gmail-label-based-sync.md) - Gmail-specific design
- [LIMITS.md](../monetization/LIMITS.md) - Limit definitions and enforcement

---

*This ADR closes the gap between ADR-053's per-source monetization promise and the actual backend implementation.*
