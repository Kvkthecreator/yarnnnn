# Implementation Plan: ADR-060 Amendment 001

**Date**: 2026-02-17
**Estimated Steps**: 6
**Dependencies**: ADR-060-amendment-001-behavioral-pattern-detection.md (approved)

---

## Pre-Implementation Checklist

- [ ] Amendment ADR reviewed and approved
- [ ] No conflicting changes in `conversation_analysis.py`
- [ ] Test user available for validation

---

## Step 1: Database Migration - Cold Start Tracking

**File**: `supabase/migrations/054_analyst_cold_start_tracking.sql`

```sql
-- Track whether user has received cold start message
ALTER TABLE user_notification_preferences
ADD COLUMN IF NOT EXISTS analyst_cold_start_sent BOOLEAN DEFAULT false;

COMMENT ON COLUMN user_notification_preferences.analyst_cold_start_sent IS
'ADR-060 Amendment 001: Whether user has received the analyst cold start message explaining the feature.';
```

**Validation**: Run migration, verify column exists.

---

## Step 2: Add User Stage Detection

**File**: `api/services/conversation_analysis.py`

Add function after imports:

```python
async def get_user_stage(client, user_id: str) -> str:
    """
    Determine user maturity stage for analysis thresholds.

    Stages:
    - onboarding: < 7 days old OR < 3 sessions (skip analysis)
    - exploring: 3-10 sessions, no deliverables (high threshold)
    - active: 10+ sessions OR 1+ deliverables (normal threshold)
    - power_user: 5+ deliverables (normal + gap analysis future)
    """
    from datetime import datetime, timezone

    try:
        # Check account age
        user_result = client.auth.admin.get_user_by_id(user_id)
        if not user_result or not user_result.user:
            return "exploring"  # Default to exploring if can't determine

        created_at = user_result.user.created_at
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        account_age_days = (datetime.now(timezone.utc) - created_at).days

        # Check session count (all time)
        session_result = (
            client.table("chat_sessions")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        session_count = session_result.count or 0

        # Check deliverable count
        deliverable_result = (
            client.table("deliverables")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .in_("status", ["active", "paused"])
            .execute()
        )
        deliverable_count = deliverable_result.count or 0

        # Determine stage
        if account_age_days < 7 or session_count < 3:
            return "onboarding"
        elif deliverable_count >= 5:
            return "power_user"
        elif deliverable_count >= 1 or session_count >= 10:
            return "active"
        else:
            return "exploring"

    except Exception as e:
        logger.warning(f"[ANALYSIS] Failed to determine user stage: {e}")
        return "exploring"  # Safe default


# Stage-based confidence thresholds
STAGE_THRESHOLDS = {
    "onboarding": None,   # Skip analysis entirely
    "exploring": 0.70,    # High confidence only
    "active": 0.50,       # Normal threshold
    "power_user": 0.50,   # Normal (gap analysis in future)
}
```

**Validation**: Call `get_user_stage()` for test user, verify returns "onboarding" or "exploring".

---

## Step 3: Rewrite Analyst Prompt

**File**: `api/services/conversation_analysis.py`

Replace `ANALYSIS_SYSTEM_PROMPT`:

```python
ANALYSIS_SYSTEM_PROMPT = """You are analyzing user conversation BEHAVIOR patterns across multiple sessions.

**Your goal**: Detect implicit recurring information needs - NOT explicit scheduling requests.

## What to Look For (Cross-Session Behavioral Patterns)

1. **Repeated Topic Queries** (3+ sessions)
   - User asks about the same subject/entity across different sessions
   - Example: "#engineering channel" mentioned in sessions 1, 3, and 5
   - Suggests: Automated digest for that topic/channel

2. **Platform Resource Interest** (2+ occurrences)
   - Same Slack channel, email folder, or Notion page queried multiple times
   - Example: "What's new in #daily-work?" asked in 2 sessions
   - Suggests: Platform-specific recurring digest

3. **Temporal Information Needs** (2+ occurrences)
   - Phrases indicating time-based catchup: "yesterday", "this week", "catch me up", "what happened"
   - Example: "What happened in Slack while I was out?"
   - Suggests: Recurring summary deliverable

4. **Context Re-establishment** (2+ sessions)
   - User repeatedly explains the same background information
   - Example: "I'm working on Project X for Client Y" restated in multiple sessions
   - Suggests: This should be stored context or deliverable template

## What NOT to Look For

- **Explicit scheduling language**: "every Monday", "weekly", "monthly"
  (Users who say this would create deliverables themselves)
- **One-time queries**: Single questions about a topic
- **Exploration/testing**: Questions about system capabilities, feature discovery
- **System status checks**: "Is my Slack connected?", "What documents do I have?"

## Confidence Scoring (Behavioral Evidence)

- **0.80+**: Clear cross-session repetition (3+ instances of same pattern)
- **0.60-0.79**: Moderate pattern (2 instances with supporting context)
- **0.40-0.59**: Weak signal, needs more data to confirm
- **< 0.40**: No actionable pattern detected

## Output Format

Return a JSON array of suggestions. Each suggestion:
```json
{
  "confidence": 0.75,
  "deliverable_type": "slack_channel_digest",
  "title": "Weekly #engineering Digest",
  "description": "Summary of key discussions and decisions from #engineering",
  "suggested_frequency": "weekly",
  "suggested_sources": [{"type": "slack", "channel": "engineering"}],
  "detection_reason": "User asked about #engineering activity in 3 separate sessions over the past week"
}
```

Return empty array `[]` if:
- No behavioral patterns detected with confidence >= 0.40
- Conversations are exploratory/testing behavior
- Insufficient cross-session data

**Important**: Focus on BEHAVIOR across sessions, not keywords within sessions."""
```

**Validation**: Run test script with existing user data, verify different output format.

---

## Step 4: Update Analysis Function with Stage Logic

**File**: `api/services/conversation_analysis.py`

Modify `run_analysis_for_user()`:

```python
async def run_analysis_for_user(
    client,
    user_id: str,
) -> tuple[int, str]:
    """
    Run full analysis pipeline for a single user.

    Args:
        client: Supabase client
        user_id: User UUID

    Returns:
        Tuple of (suggestions_created, user_stage)
    """
    # Check user stage first
    stage = await get_user_stage(client, user_id)

    if stage == "onboarding":
        logger.info(f"[ANALYSIS] Skipping {user_id}: onboarding stage")
        return 0, stage

    # Get threshold for this stage
    threshold = STAGE_THRESHOLDS.get(stage, 0.50)

    # Gather inputs
    sessions = await get_recent_sessions(client, user_id, days=7)
    if len(sessions) < 2:
        return 0, stage

    existing = await get_user_deliverables(client, user_id)
    knowledge = await get_user_knowledge(client, user_id)

    # Analyze
    suggestions = await analyze_conversation_patterns(
        client, user_id, sessions, existing, knowledge
    )

    # Create suggestions that meet stage-appropriate threshold
    created = 0
    for suggestion in suggestions:
        if suggestion.confidence >= threshold:
            result = await create_suggested_deliverable(client, user_id, suggestion)
            if result:
                created += 1

    return created, stage
```

**Validation**: Run with test user, verify stage detection and threshold application.

---

## Step 5: Add Cold Start Notification

**File**: `api/services/notifications.py`

Add function:

```python
async def notify_analyst_cold_start(
    db_client,
    user_id: str,
) -> bool:
    """
    Send one-time cold start message explaining the analyst feature.

    Only sent once per user, tracked in user_notification_preferences.

    Returns True if sent, False if already sent or error.
    """
    # Check if already sent
    try:
        pref_result = (
            db_client.table("user_notification_preferences")
            .select("analyst_cold_start_sent")
            .eq("user_id", user_id)
            .execute()
        )

        if pref_result.data and pref_result.data[0].get("analyst_cold_start_sent"):
            return False  # Already sent

    except Exception:
        pass  # Continue - will try to send

    message = (
        "I've started analyzing your conversations to detect patterns that could "
        "benefit from automation. I haven't found any recurring needs yet, but as "
        "you use YARNNN more, I'll suggest deliverables when I notice you repeatedly "
        "asking about the same topics or resources."
    )

    result = await send_notification(
        db_client=db_client,
        user_id=user_id,
        message=message,
        channel="email",
        urgency="low",
        context={"type": "analyst_cold_start"},
        source_type="system",
    )

    # Mark as sent
    if result.status == "sent":
        try:
            db_client.table("user_notification_preferences").upsert({
                "user_id": user_id,
                "analyst_cold_start_sent": True,
            }, on_conflict="user_id").execute()
        except Exception as e:
            logger.warning(f"[NOTIFICATION] Failed to mark cold start sent: {e}")

    return result.status == "sent"
```

**Validation**: Call function for test user, verify email sent and flag set.

---

## Step 6: Update Scheduler with Cold Start Logic

**File**: `api/jobs/unified_scheduler.py`

In the Analysis Phase section, after creating suggestions:

```python
# After the suggestion creation loop:
# ADR-060 Amendment 001: Send cold start if no suggestions and not sent before
if analysis_suggestions == 0 and user_stage not in ["onboarding"]:
    try:
        from services.notifications import notify_analyst_cold_start
        cold_start_sent = await notify_analyst_cold_start(supabase, user_id)
        if cold_start_sent:
            logger.info(f"[ANALYSIS] Sent cold start notification to {user_id}")
    except Exception as cold_err:
        logger.warning(f"[ANALYSIS] Cold start notification failed: {cold_err}")
```

Also update the return value handling from `run_analysis_for_user()` to capture stage.

**Validation**: Run scheduler, verify cold start sent for users with 0 suggestions.

---

## Post-Implementation Checklist

- [ ] Run migration on production database
- [ ] Deploy updated code
- [ ] Verify next 6 AM UTC run logs show stage detection
- [ ] Check test user receives cold start email (if applicable)
- [ ] Monitor suggestion rates over 7 days

---

## Rollback Plan

If behavioral detection produces too many false positives:
1. Revert `ANALYSIS_SYSTEM_PROMPT` to keyword-based version
2. Keep user stage logic (useful regardless)
3. Raise thresholds: `exploring: 0.85, active: 0.70`

No database rollback needed - columns are additive.
