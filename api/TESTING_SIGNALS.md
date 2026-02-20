# Testing Signal Processing (ADR-068)

This guide explains how to test the signal processing implementation without waiting for the scheduled cron execution.

## Quick Test (Production)

The fastest way to test signal processing with your production data:

```bash
# Using Render CLI (requires render CLI installed)
render run python api/test_signal_processing.py kvkthecreator@gmail.com
```

This will:
1. Extract signals from your live Google Calendar and Gmail
2. Run LLM reasoning over the signals
3. Create signal-emergent deliverables (if warranted)
4. Show detailed logs of the entire process

## Test Filters

You can test specific signal types:

```bash
# Test all signal types (default)
render run python api/test_signal_processing.py kvkthecreator@gmail.com --filter all

# Test only calendar signals (hourly cron behavior)
render run python api/test_signal_processing.py kvkthecreator@gmail.com --filter calendar_only

# Test only silence signals (daily cron behavior)
render run python api/test_signal_processing.py kvkthecreator@gmail.com --filter non_calendar
```

## Local Testing

If you want to run the test locally (requires environment variables):

```bash
# Set environment variables
export SUPABASE_URL="your_supabase_url"
export SUPABASE_SERVICE_KEY="your_service_role_key"
export ANTHROPIC_API_KEY="your_anthropic_key"
export GOOGLE_CLIENT_ID="your_google_oauth_client_id"
export GOOGLE_CLIENT_SECRET="your_google_oauth_client_secret"

# Run test
cd api
python test_signal_processing.py kvkthecreator@gmail.com
```

## Expected Output

Successful test run will show:

```
============================================================
SIGNAL PROCESSING TEST
============================================================
User: kvkthecreator@gmail.com
Filter: all
Time: 2026-02-20T00:37:20.043680+00:00
============================================================

2026-02-20 09:37:20 - __main__ - INFO - ✓ Found user: kvkthecreator@gmail.com (id: xxx)
2026-02-20 09:37:20 - __main__ - INFO - ✓ Platform connections: 2
2026-02-20 09:37:20 - __main__ - INFO -   - gmail: active
2026-02-20 09:37:20 - __main__ - INFO -   - slack: active

============================================================
EXTRACTING SIGNALS (filter=all)
============================================================

2026-02-20 09:37:25 - __main__ - INFO - ✓ Signal extraction complete:
2026-02-20 09:37:25 - __main__ - INFO -   - Calendar signals: 3
2026-02-20 09:37:25 - __main__ - INFO -   - Silence signals: 2
2026-02-20 09:37:25 - __main__ - INFO -   - Has signals: True

2026-02-20 09:37:25 - __main__ - INFO - Calendar signals:
2026-02-20 09:37:25 - __main__ - INFO -   - 'Team Sync' in 4.2h (event_id: abc123, attendees: 5)
2026-02-20 09:37:25 - __main__ - INFO -   - 'Client Demo' in 28.5h (event_id: def456, attendees: 3)

============================================================
GATHERING CONTEXT
============================================================

2026-02-20 09:37:26 - __main__ - INFO - ✓ User context entries: 15
2026-02-20 09:37:26 - __main__ - INFO - ✓ Recent activity entries: 8
2026-02-20 09:37:26 - __main__ - INFO - ✓ Existing deliverables: 2

============================================================
PROCESSING SIGNALS (LLM reasoning)
============================================================

2026-02-20 09:37:28 - __main__ - INFO - ✓ Signal processing complete:
2026-02-20 09:37:28 - __main__ - INFO -   - Actions proposed: 2
2026-02-20 09:37:28 - __main__ - INFO -   - Reasoning: User has two upcoming meetings...

2026-02-20 09:37:28 - __main__ - INFO - Proposed actions:
2026-02-20 09:37:28 - __main__ - INFO -   - create_signal_emergent: meeting_prep (confidence: 0.85)
2026-02-20 09:37:28 - __main__ - INFO -     Title: Meeting Prep: Team Sync
2026-02-20 09:37:28 - __main__ - INFO -     Signal context: {'event_id': 'abc123', ...}

============================================================
EXECUTING ACTIONS
============================================================

2026-02-20 09:37:30 - __main__ - INFO - ✓ Execution complete:
2026-02-20 09:37:30 - __main__ - INFO -   - Deliverables created: 2

2026-02-20 09:37:30 - __main__ - INFO - Created deliverables:
2026-02-20 09:37:30 - __main__ - INFO -   - Meeting Prep: Team Sync (meeting_prep) [active] - uuid
2026-02-20 09:37:30 - __main__ - INFO -   - Meeting Prep: Client Demo (meeting_prep) [active] - uuid

============================================================
TEST COMPLETE
============================================================
```

## Verifying Results

After running the test, you can verify the created deliverables:

1. **Check the database**:
   ```sql
   SELECT id, title, deliverable_type, origin, status, created_at
   FROM deliverables
   WHERE user_id = '<your_user_id>'
   AND origin = 'signal_emergent'
   ORDER BY created_at DESC
   LIMIT 10;
   ```

2. **Check signal_history for deduplication**:
   ```sql
   SELECT signal_type, signal_ref, last_triggered_at, deliverable_id
   FROM signal_history
   WHERE user_id = '<your_user_id>'
   ORDER BY last_triggered_at DESC;
   ```

3. **Check deliverable versions** (if execution completed):
   ```sql
   SELECT dv.id, d.title, dv.status, dv.created_at
   FROM deliverable_versions dv
   JOIN deliverables d ON d.id = dv.deliverable_id
   WHERE d.user_id = '<your_user_id>'
   AND d.origin = 'signal_emergent'
   ORDER BY dv.created_at DESC
   LIMIT 10;
   ```

## Troubleshooting

**No signals detected:**
- Check that you have active platform connections (gmail, slack)
- Verify you have upcoming calendar events with external attendees
- For silence signals, check you have Gmail threads in INBOX with no reply in 5+ days

**Signal extracted but no actions proposed:**
- LLM may have determined confidence < 0.60
- Check existing deliverables - type deduplication may have filtered the action
- Review the reasoning output for LLM's decision

**Deduplication blocking:**
- Check signal_history table for recent triggers
- Deduplication windows: meeting_prep (24h), silence_alert (7d), contact_drift (14d)
- Wait for window to expire or manually delete from signal_history

**Environment variable errors:**
- Ensure all required env vars are set (see top of this document)
- For Render, use `render run` to inherit production environment
- For local, export vars or create .env file in parent directory

## Scheduled Execution

The actual cron runs at these frequencies:

- **Calendar signals**: Every hour (`:00-:04` minutes)
- **Silence/drift signals**: Daily at 7:00 AM UTC

To monitor production cron execution, check Render logs or unified_scheduler output.
