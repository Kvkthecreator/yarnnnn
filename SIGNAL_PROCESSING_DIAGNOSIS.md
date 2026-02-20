# Signal Processing Diagnosis Report

**Date**: 2026-02-20
**Issue**: Signal processing running hourly but failing due to OAuth errors

---

## Problem Summary

Signal processing IS running hourly as designed (commit `bc0b9d5`), but failing to extract signals due to:

1. **Google OAuth Token Refresh Failure** (Critical)
2. **Slack Deliverable Type Missing** (Minor)
3. **Notion Signals Not Tested** (Unknown status)

---

## Findings from Render Logs

### ✅ What's Working

- **Scheduler Frequency**: ✅ Running every 5 minutes as configured
- **Signal Processing Trigger**: ✅ Hourly execution (top of each hour, :00-:04)
- **Memory Extraction**: ✅ Working (processed 1 session at midnight)
- **Platform Connections**: ✅ 3 active (gmail, slack, notion)

### ❌ What's Broken

#### 1. Google Calendar/Gmail Signal Extraction

**Error**:
```
WARNING: Calendar signal extraction failed for 2abf3f96-118b-4987-9d95-40f2d9be9a18: Token refresh failed
```

**Root Cause**:
- `GoogleAPIClient._get_access_token()` calls Google OAuth token refresh endpoint
- Google returns non-200 status (likely 400 or 401)
- Possible reasons:
  - Refresh token revoked by user
  - Refresh token expired (Google refresh tokens CAN expire if unused for 6 months)
  - OAuth app credentials mismatch
  - Scopes changed

**Location**: `api/integrations/core/google_client.py:52-78`

**Impact**:
- ❌ Calendar signals not detected
- ❌ Gmail silence signals not detected

#### 2. Phase 2 Deliverable Types Not in Database Constraint (FIXED ✅)

**Error**:
```
Database constraint violation for deliverable type: deep_research (or daily_strategy_reflection, intelligence_brief)
```

**Root Cause**:
- Phase 2 strategic intelligence types added to code but missing from database CHECK constraint
- Migration 064 included Wave 1 types but not Phase 2 types
- Database rejected INSERT for new deliverable types

**Location**: `supabase/migrations/064_deliverable_type_constraint.sql`

**Fix Applied** (Migration 075):
- Added `deep_research`, `daily_strategy_reflection`, `intelligence_brief` to constraint
- Migration applied to production: 2026-02-20
- Commit: `cbba6d2`

**Impact**:
- ✅ FIXED: Phase 2 deliverable types can now be created
- All 3 strategic intelligence types validated at database level

#### 3. Notion Signals

**Status**: No evidence in logs (not tested yet)

---

## Database State

### Platform Connections (User: 2abf3f96-118b-4987-9d95-40f2d9be9a18)

| Platform | Status | Token Type | Token Length | Created |
|---|---|---|---|---|
| gmail | active | refresh_token | 228 chars | 2026-02-19 05:42 |
| slack | active | access_token | 164 chars | 2026-02-18 23:44 |
| notion | active | access_token | 164 chars | 2026-02-19 04:34 |

**Observations**:
- Gmail has `refresh_token_encrypted` (good - required for long-lived access)
- Slack/Notion have `credentials_encrypted` only (OAuth 2.0 access tokens)
- No `last_synced_at` for any platform (sync may never have run)

---

## Solution Plan

### Fix 1: Reconnect Google/Gmail OAuth (User Action Required)

**Why**: Refresh token may be revoked/expired

**Steps**:
1. Go to Settings → Integrations
2. Click "Reconnect" on Google/Gmail integration
3. Complete OAuth flow
4. New refresh token will be stored
5. Test manual signal processing

**Alternative**: Check Google OAuth consent screen settings
- Verify app is not in "Testing" mode with 7-day token expiry
- Ensure scopes include:
  - `https://www.googleapis.com/auth/gmail.readonly`
  - `https://www.googleapis.com/auth/calendar.readonly`

### Fix 2: Add Missing Phase 2 Types to Database Constraint ✅ APPLIED

**Status**: ✅ RESOLVED (Migration 075 applied)

**File**: `supabase/migrations/075_phase2_strategic_types.sql`

**What was done**:
- Added `deep_research`, `daily_strategy_reflection`, `intelligence_brief` to deliverable_type CHECK constraint
- Constraint now includes all 27 valid deliverable types
- Applied to production database: 2026-02-20
- Commit: `cbba6d2`

### Fix 3: Add Logging for Token Refresh Errors (Code Improvement)

**File**: `api/integrations/core/google_client.py`

**Line 74-75**, enhance error message:
```python
if response.status_code != 200:
    error_detail = response.text
    logger.error(f"[GOOGLE_CLIENT] Token refresh failed: status={response.status_code}, detail={error_detail}")
    raise RuntimeError(f"Token refresh failed: {response.text}")
```

This will help diagnose future OAuth issues faster.

### Fix 4: Verify Notion Signal Extraction (Testing)

**Steps**:
1. Ensure Notion connection is valid
2. Create a Notion page and don't edit for 14+ days (or backdate a page)
3. Trigger manual signal processing
4. Check logs for Notion signal detection

---

## Verification Steps

### After OAuth Reconnect:

1. **Check Render Logs**:
   ```
   # Should see SUCCESS instead of WARNING
   [SIGNAL] Hourly calendar check: 1 users with active platforms
   [SIGNAL_EXTRACTION] user=... calendar=2, silence=1, slack=0, notion=0
   ```

2. **Check Database**:
   ```sql
   SELECT * FROM deliverables
   WHERE origin = 'signal_emergent'
   ORDER BY created_at DESC
   LIMIT 5;
   ```

3. **Test Manual Trigger**:
   - Go to Settings → Integrations
   - Click "Scan Now" under Proactive Signal Detection
   - Should complete without OAuth errors

---

## Architecture Notes

### Signal Extraction Flow

```
unified_scheduler.py (every 5 min)
  ├─ Hourly (if now.minute < 5):
  │   ├─ extract_signal_summary(filter="calendar_only")
  │   │   └─ _extract_calendar_signals()
  │   │       └─ GoogleAPIClient.list_calendar_events()
  │   │           └─ _get_access_token() ← FAILS HERE
  │   └─ extract_signal_summary(filter="non_calendar")  ← NEW (bc0b9d5)
  │       ├─ _extract_silence_signals()
  │       │   └─ GoogleAPIClient.list_gmail_messages() ← FAILS HERE
  │       ├─ _extract_slack_signals()
  │       │   └─ MCPClientManager.get_client("slack")
  │       └─ _extract_notion_signals()
  │           └─ NotionAPIClient.get_page()
  └─ Daily (if now.hour == 0): ← REMOVED (bc0b9d5)
      └─ process_patterns(), process_conversation()
```

### OAuth Token Lifecycle

**Google (Gmail/Calendar)**:
- Uses OAuth 2.0 with refresh tokens
- Access tokens expire after 1 hour
- Refresh tokens used to get new access tokens
- Refresh tokens CAN expire if:
  - User revokes access
  - App is in "Testing" mode (7-day expiry)
  - Token unused for 6 months
  - User changes password

**Slack**:
- Uses MCP Slack server
- OAuth handled by MCP client
- Access tokens are long-lived (no refresh needed)

**Notion**:
- Uses direct API client
- Internal integration token (no OAuth expiry)

---

## Status Summary

| Component | Status | Action Required |
|---|---|---|
| Signal scheduling | ✅ Fixed | None (bc0b9d5 deployed) |
| Calendar signals | ✅ Fixed | User reconnected OAuth 2026-02-20 |
| Gmail signals | ✅ Fixed | User reconnected OAuth 2026-02-20 |
| Slack signals | ✅ Working | None (slack_channel_digest in constraint) |
| Notion signals | ❓ Unknown | Test with stale page |
| Phase 2 types constraint | ✅ Fixed | Migration 075 applied (cbba6d2) |
| Layer 4 integration | ✅ Working | None (verified in code) |
| Hourly frequency | ✅ Working | None (verified in logs) |

---

## Related

- Commit `bc0b9d5`: Changed non-calendar signals from daily to hourly
- Commit `ae28e3e`: Implemented Slack and Notion signal detection
- ADR-068: Signal-emergent deliverables
- File: `api/integrations/core/google_client.py:52-78` (OAuth refresh)
- File: `api/services/signal_extraction.py` (Signal extractors)
- File: `api/jobs/unified_scheduler.py:1016,1139` (Scheduling logic)
