# ADR-055: Gmail Label-Based Sync

> **Status**: Accepted
> **Date**: 2026-02-12
> **Deciders**: Kevin (solo founder)
> **Related**: ADR-053 (Platform Sync Monetization), ADR-038 (Filesystem-as-Context), ADR-051 (Platform Context Page Patterns)

---

## Context

### The Problem

ADR-053 establishes that **synced sources are the monetization base layer**:
- Free tier: 1 Gmail label
- Starter: 5 Gmail labels
- Pro: 15 Gmail labels

But the current Gmail implementation doesn't support label-based sync:

**Current State:**
```
User connects Gmail → sees labels (INBOX/Payments, INBOX/MKTG, etc.)
User selects labels → nothing happens (selection is cosmetic)
Import runs → imports from "inbox" broadly, ignoring labels
Labels show "Not synced" → because they literally aren't synced
"Recent Context" section → shows emails from broad inbox import
```

**The Disconnect:**
- UI shows labels as selectable resources
- Backend doesn't sync per-label
- Sync status badges are meaningless
- Monetization based on label count is impossible to enforce

### The Requirement

Per ADR-053 and ADR-051:
1. Labels must be syncable resources (like Slack channels)
2. Sync status must be accurate per-label
3. Context must be shown within label rows
4. Label count limits must be enforceable

---

## Decision

### Implement Full Label-Based Sync for Gmail

#### 1. Backend: Label Import Support

**New resource_id format:**
```
label:<label_id>
```

**Import job modification** (`api/jobs/import_jobs.py`):
```python
# Detect label-based resource_id
if resource_id.startswith("label:"):
    label_id = resource_id.replace("label:", "")
    # Use Gmail API labelIds parameter
    query = f"after:{cutoff_date}"
    label_ids = [label_id]
    messages = google_client.list_gmail_messages(
        query=query,
        label_ids=label_ids,  # NEW: filter by label
        max_results=max_items
    )
```

**GoogleAPIClient enhancement** (`api/integrations/google/google_client.py`):
```python
async def list_gmail_messages(
    self,
    query: str = "",
    max_results: int = 100,
    label_ids: list[str] | None = None,  # NEW parameter
) -> list[dict]:
    """List Gmail messages with optional label filtering."""
    params = {"q": query, "maxResults": max_results}
    if label_ids:
        params["labelIds"] = label_ids
    # ... existing implementation
```

#### 2. Backend: Coverage Tracking per Label

**integration_coverage entries:**
```
user_id | provider | resource_id       | resource_name    | resource_type | coverage_state
--------|----------|-------------------|------------------|---------------|---------------
uuid    | gmail    | label:Label_123   | INBOX/Payments   | label         | covered
uuid    | gmail    | label:Label_456   | INBOX/MKTG       | label         | uncovered
```

**Update after sync:**
- `last_extracted_at` = sync timestamp
- `items_extracted` = email count
- `coverage_state` = "covered" | "partial" | "stale"

#### 3. Frontend: Context Integrated in Label Rows

**Before:**
```
[x] INBOX/Payments                         Not synced
[x] INBOX/MKTG                             Not synced
[ ] INBOX/Domain                           Not synced

---
Recent Context from Gmail
- Email 1 (Inbox, 3 days ago)
- Email 2 (Inbox, 3 days ago)
```

**After:**
```
[x] INBOX/Payments                         ✅ Synced • 12 emails
    └─ "Complete your launch..." (3 days ago)
    └─ "Welcome to PeerPush..." (3 days ago)
    └─ Show more...

[x] INBOX/MKTG                             ✅ Synced • 8 emails
    └─ "February newsletter..." (2 days ago)
    └─ Show more...

[ ] INBOX/Domain                           Not synced
```

**Key changes:**
- Remove separate "Recent Context" section
- Each label row expandable to show synced emails
- Sync badge reflects actual label sync state
- Content comes from `ephemeral_context` filtered by label

#### 4. API: Endpoint for Label Context

**New endpoint:**
```
GET /api/integrations/gmail/labels/{label_id}/context?limit=5
```

Returns:
```json
{
  "items": [
    {
      "id": "uuid",
      "content": "Email subject + snippet...",
      "source_timestamp": "2026-02-12T10:30:00Z",
      "metadata": {"from": "sender@email.com", "thread_id": "..."}
    }
  ],
  "total_count": 12,
  "last_synced_at": "2026-02-12T08:00:00Z"
}
```

#### 5. Import Trigger: Per-Label

**Current:** Single "Import from Gmail" button → imports inbox broadly

**New:** Import happens per selected label:
- User checks label → triggers import for that label
- Background sync respects label selection
- Unchecked labels don't get synced

---

## Implementation

### Phase 1: Backend - Label Import Support

1. **GoogleAPIClient** - Add `label_ids` parameter to `list_gmail_messages()`
2. **import_jobs.py** - Handle `label:<label_id>` resource_id format
3. **integration routes** - Update import trigger to accept label resource_id

### Phase 2: Backend - Coverage Tracking

1. **integration_coverage** - Ensure labels tracked as individual resources
2. **sync_registry** - Track last sync per label
3. **ephemeral_context** - Store label_id in metadata for filtering

### Phase 3: Frontend - Label Context Integration

1. **Remove** "Recent Context from Gmail" section
2. **Add** expandable context rows within each label
3. **Add** API call to fetch context per label
4. **Update** sync status badge to reflect actual state

### Phase 4: Sync Scheduler

1. **Background sync** - Iterate over selected labels, not just "inbox"
2. **Tier limits** - Enforce label count per tier (1/5/15)
3. **Frequency** - Sync labels at tier-appropriate frequency

---

## Database Changes

### ephemeral_context Metadata

Add `label_id` to Gmail entries:
```json
{
  "message_id": "...",
  "thread_id": "...",
  "from": "...",
  "to": "...",
  "labels": ["Label_123", "Label_456"],  // existing
  "label_id": "Label_123"  // NEW: primary label for this import
}
```

### integration_coverage

No schema changes needed. Existing `resource_id` field stores `label:<label_id>`.

---

## Consequences

### Positive

1. **Consistent with ADR-053** - Labels are countable, limitable resources
2. **Accurate sync status** - Users see real sync state per label
3. **Monetization enabled** - Label limits enforceable
4. **Better UX** - Context shown where it belongs (within labels)

### Negative

1. **More API calls** - One import per label instead of one broad import
2. **Migration needed** - Existing "inbox" imports don't map to labels

### Mitigations

- **API calls**: Gmail API allows 250 requests/second, not a concern
- **Migration**: Keep existing inbox imports, add label imports alongside

---

## Related Files

**Backend:**
- `api/integrations/google/google_client.py` - Gmail API client
- `api/jobs/import_jobs.py` - Import job processing
- `api/routes/integrations.py` - Import trigger endpoints
- `api/services/ephemeral_context.py` - Context storage

**Frontend:**
- `web/app/(authenticated)/context/[platform]/page.tsx` - Gmail context page
- `web/lib/api/client.ts` - API client

---

*This ADR enables label-based sync for Gmail, aligning with ADR-053 monetization model and ADR-051 platform context patterns.*
