# Platform Integration Testing Runbook

> Verified 2026-02-23. Updated 2026-02-25 for ADR-077 sync overhaul expectations.

## Prerequisites

- Render API service deployed and live (`srv-d5sqotcr85hc73dpkqdg`)
- `SUPABASE_SERVICE_KEY` available (used as `X-Service-Key` header)
- Platform connections active. `selected_sources` auto-populated on first connect with smart defaults (ADR-079), customizable via source selection modal.
- SQL access via psql connection string (see `docs/database/ACCESS.md`)

## Admin Test Endpoints

All protected by `X-Service-Key` header matching `SUPABASE_SERVICE_KEY`.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/trigger-sync/{user_id}/{provider}` | POST | Trigger sync for a specific user+provider |
| `/api/admin/trigger-signal-processing/{user_id}` | POST | Run signal extraction + LLM triage |
| `/api/admin/sync-health` | GET | Cross-user sync registry health (requires admin JWT) |
| `/api/admin/pipeline-stats` | GET | Content layer + scheduler stats (requires admin JWT) |

## Per-Platform Sync Tests

### 1. Slack

```bash
curl -s -X POST "https://yarnnn-api.onrender.com/api/admin/trigger-sync/{USER_ID}/slack" \
  -H "X-Service-Key: {SERVICE_KEY}" | python3 -m json.tool
```

**Expected**: `{"success": true, "items_synced": N, "channels_synced": N}`
**ADR-077 changes**: Paginated history (1000 initial, 500 incremental), thread expansion (reply_count >= 2), system message filtering, user ID resolution to display names.
**Writes to**: `platform_content` with `platform="slack"`, `content_type="message"` or `"thread_reply"`
**Sync registry**: Entries per channel with `platform_cursor` (Slack `ts`)

### 2. Gmail + Calendar (Google)

```bash
curl -s -X POST "https://yarnnn-api.onrender.com/api/admin/trigger-sync/{USER_ID}/google" \
  -H "X-Service-Key: {SERVICE_KEY}" | python3 -m json.tool
```

**Expected**: `{"success": true, "items_synced": N, "gmail_sources": N, "calendar_sources": N}`
**Note**: The `google` provider auto-splits into Gmail and Calendar sub-syncs based on `landscape.resources[].metadata.platform`.
**ADR-077 changes**: Gmail paginated (200/label), concurrent fetch, 30-day initial window. Calendar wider window (-7d to +14d), paginated (200 events).
**Writes to**:
- `platform_content` with `platform="gmail"`, `content_type="email"`
- `platform_content` with `platform="calendar"`, `content_type="event"` (events from past 7 days + next 14 days)

### 3. Notion

```bash
curl -s -X POST "https://yarnnn-api.onrender.com/api/admin/trigger-sync/{USER_ID}/notion" \
  -H "X-Service-Key: {SERVICE_KEY}" | python3 -m json.tool
```

**Expected**: `{"success": true, "items_synced": N, "pages_synced": N, "pages_skipped": N, "pages_failed": N}`
**ADR-077 changes**: Recursive block fetch (depth=3, 500 blocks), database row querying, rate limiting (350ms between API calls).
**Writes to**: `platform_content` with `platform="notion"`, `content_type="page"`
**Sync registry**: Entries per page with `platform_cursor` (Notion `last_edited_time`)

## Signal Processing Test

Requires user to be on Starter or Pro tier (`workspaces.subscription_status`).

```bash
curl -s -X POST "https://yarnnn-api.onrender.com/api/admin/trigger-signal-processing/{USER_ID}" \
  -H "X-Service-Key: {SERVICE_KEY}" | python3 -m json.tool
```

**Expected**: `{"status": "completed", "extraction": {...}, "processing": {...}}`
**Extraction**: Shows which platforms were queried and total items found
**Processing**: Shows signals detected, actions taken, and LLM reasoning summary

## SQL Verification Queries

### Platform content counts
```sql
SELECT platform, content_type, COUNT(*) as rows,
  COUNT(DISTINCT resource_id) as resources
FROM platform_content
GROUP BY platform, content_type
ORDER BY platform;
```

### Sync registry state
```sql
SELECT platform, resource_id, resource_name, platform_cursor,
  item_count, last_synced_at
FROM sync_registry
ORDER BY platform;
```

### Activity log (sync events)
```sql
SELECT event_type, summary, created_at
FROM activity_log
WHERE event_type = 'platform_synced'
ORDER BY created_at DESC LIMIT 10;
```

### Daily token usage
```sql
SELECT get_daily_token_usage('{USER_ID}'::uuid) as daily_tokens;
```

### Token persistence check (after TP chat)
```sql
SELECT metadata->>'input_tokens', metadata->>'output_tokens', created_at
FROM session_messages sm
JOIN chat_sessions cs ON cs.id = sm.session_id
WHERE cs.user_id = '{USER_ID}' AND sm.role = 'assistant'
ORDER BY sm.created_at DESC LIMIT 5;
```

## Deliverable Delivery Test

Trigger a deliverable run to test the full pipeline: content generation → Resend email delivery → notification skip.

### Setup
```bash
# Set next_run_at to now (and optionally clear last_run_at to bypass freshness check)
psql "$CONN_STRING" -c "
UPDATE deliverables
SET next_run_at = NOW(), last_run_at = NULL
WHERE id = '{DELIVERABLE_ID}'
RETURNING id, title, next_run_at, destination;
"
```

### Wait for cron (up to 5 min), then verify
```sql
-- Check latest version
SELECT version_number, status, delivery_status, delivery_error,
       delivery_external_id, delivered_at
FROM deliverable_versions
WHERE deliverable_id = '{DELIVERABLE_ID}'
ORDER BY version_number DESC LIMIT 1;
```

### Expected behavior
- `delivery_status = 'delivered'`, `delivery_external_id` is a Resend message ID (UUID format)
- Email arrives with: title header → rendered markdown content → "View in Yarn" button → "Manage notifications" link
- **No separate notification email** (skipped for email-platform deliverables)
- Cron log shows: `"Skipped notification — content delivered via email"`

### Test results (2026-02-24)

| Test | Status | Details |
|------|--------|---------|
| Resend delivery (v5) | PASS | Content delivered via ResendExporter, external_id=fbf38403 |
| Email format | PASS | Title header + markdown content + "View in Yarn" footer |
| Notification skip | PASS | No redundant "ready" email — cron log confirms skip |
| Destination in query | PASS | `destination` column included in get_due_deliverables SELECT |

---

## Known Issues / Notes

1. **Calendar 0 events**: ADR-077 widened the window to -7d → +14d. If still 0, check the debug logs for `[PLATFORM_WORKER] Calendar {id}: API returned N events`.
2. **Gmail content**: RESOLVED (commit `011fb25`). Full body extraction now works — avg 5,760 chars per email. Title (subject) and author (sender) populated on all 17 emails.
3. **Google/Gmail alias**: `platform_connections.platform` stores `"google"` for the unified Google OAuth. The worker splits this into gmail + calendar sub-syncs. Signal extraction checks for any of `"google"`, `"gmail"`, `"calendar"` in `active_platforms`.
4. **Token persistence**: Only applies to TP messages created after deploy `d5a17a7` (2026-02-23 ~08:02 UTC). Earlier messages have null token fields.

## Test Results (2026-02-23)

| Test | Status | Details |
|------|--------|---------|
| Slack sync | PASS | 3 items from 2 channels |
| Gmail sync (via google) | PASS | 17 emails from INBOX, full body (avg 5,760 chars) |
| Calendar sync (via google) | PASS | 0 events (none in next 7 days) |
| Notion sync | PASS | 2 pages synced |
| Signal extraction | PASS | All 4 platforms queried, 22 items |
| Signal processing (LLM) | PASS | Haiku triage completed, 0 actions (correct for quiet period) |
| Gmail content quality | PASS | title, author, thread_id populated on all 17 emails |
| Token persistence SQL | PASS | `get_daily_token_usage()` returns 0 (no post-deploy messages yet) |
| Token budget enforcement | CODE VERIFIED | `check_daily_token_budget()` in chat.py, tested via function existence |
| TP signal.process Execute | DEPLOYED | `Execute(action="signal.process", target="system:signals")` added to primitives |
| Granular background jobs | PASS | 9 job types in system status (was 5), all have events in activity_log |
| Activity log CHECK constraint | PASS | Migration 080 adds 5 new event types, all insertable |
