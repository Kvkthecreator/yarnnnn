# ADR-052: Platform Context Surface

> **Status**: Accepted
> **Date**: 2026-02-12
> **Deciders**: Kevin (solo founder)
> **Related**: ADR-038 (Filesystem-as-Context), ADR-039 (Unified Context Surface)

---

## Context

ADR-038 established that platform content IS the context - stored in `ephemeral_context` table, not extracted into a separate memories layer. ADR-039 designed the unified Context page with cards showing sync status.

However, the current `/context/[platform]` page has a "Recent Context" section that:
1. Queries `api.userMemories.list()` - which returns user-stated facts from `memories` table
2. Shows "No context extracted" even when channels ARE synced
3. Doesn't show actual synced content from `ephemeral_context`

This creates confusion: users see synced channels but "no context" - when the synced messages ARE the context.

### The Real Problem

Per ADR-038, the architecture is:
- `memories` table = User-stated facts ONLY (preferences, schedules, stated information)
- `ephemeral_context` table = Platform content (Slack messages, Gmail emails, Notion pages)

The frontend incorrectly conflates these. "Recent Context from Slack" should show synced Slack messages, not user memories.

## Decision

**Replace the "Recent Context" section with actual synced content from `ephemeral_context`.**

### API Changes

Add a new endpoint to fetch ephemeral context by platform:

```
GET /api/integrations/{provider}/context?limit=20
```

Returns:
```json
{
  "items": [
    {
      "id": "uuid",
      "content": "Message text...",
      "content_type": "message|thread_parent|email|page",
      "resource_name": "#engineering",
      "source_timestamp": "2026-02-12T10:30:00Z",
      "metadata": {
        "user": "U123",
        "ts": "1234567890.123456",
        "signals": { "thread_reply_count": 5 }
      }
    }
  ],
  "total_count": 142,
  "freshest_at": "2026-02-12T10:30:00Z"
}
```

### Frontend Changes

1. **Replace `recentMemories` state** with `platformContext` state
2. **Call new endpoint** instead of `api.userMemories.list()`
3. **Platform-specific rendering**:
   - **Slack**: Show messages with user, timestamp, thread indicators
   - **Gmail**: Show email snippets with from/subject
   - **Notion**: Show page titles with last edited
   - **Calendar**: Show events (though these are typically queried on-demand)

### Section Rename

- **Before**: "Recent Context from Slack"
- **After**: "Synced Content" (or just show in the channel cards themselves)

### What Gets Removed

1. `recentMemories` state and API call in `/context/[platform]/page.tsx`
2. Legacy `api.userMemories.list()` filtering by platform
3. Confusing "No context extracted" empty state

### Platform-Specific Display

| Platform | Content Type | Display Format |
|----------|--------------|----------------|
| **Slack** | Messages | `[timestamp] <user> message text` with thread/reaction indicators |
| **Gmail** | Emails | `From: sender | Subject: title | snippet...` |
| **Notion** | Pages | `Page title | Last edited: date` |
| **Calendar** | Events | On-demand - no sync display needed |

## Consequences

### Positive

- **Accurate representation** - Shows actual synced content, not wrong data type
- **User understanding** - Users see what TP knows about their platforms
- **ADR alignment** - Properly implements ADR-038 filesystem-as-context model
- **Removes confusion** - No more "no context" when channels are synced

### Negative

- **API change** - New endpoint needed
- **Frontend refactor** - Replace `recentMemories` with new data model

### Neutral

- **User memories still exist** - Facts remain in `/context?source=facts` per ADR-039
- **No migration needed** - Data already in `ephemeral_context`

## Implementation

### Phase 1: Backend (This ADR)
1. Add `GET /api/integrations/{provider}/context` endpoint
2. Return ephemeral_context filtered by platform
3. Include metadata for rich display

### Phase 2: Frontend (This ADR)
1. Replace `recentMemories` with `platformContext`
2. Platform-specific content cards
3. Remove legacy empty states

### Phase 3: Future Enhancement
1. Inline content preview in channel/label cards
2. Click to expand full context
3. Search within synced content

---

## References

- [ADR-038: Filesystem-as-Context](ADR-038-filesystem-as-context.md)
- [ADR-039: Unified Context Surface](ADR-039-unified-context-surface.md)
- `api/services/ephemeral_context.py` - Existing service
