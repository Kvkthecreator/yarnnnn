# ADR-060 Amendment 001: Behavioral Pattern Detection

**Date**: 2026-02-17
**Status**: Proposed
**Amends**: ADR-060 (Background Conversation Analyst Architecture)

---

## Context

### Original Design Flaw

ADR-060's pattern detection focused on **explicit scheduling language**:

```
"I update the board monthly" → Monthly Board Update
"every week" → weekly frequency
"for my manager" → audience-based suggestion
```

**Problem**: If a user explicitly says "I need a weekly report for my manager", they would just... create it. The analyst was looking for patterns that users would self-service.

### Case Study Analysis

Real user data (2 sessions, 14 messages) over 2 days:
- Session 1: PDF upload test, questions about document content
- Session 2: PDF questions, capability discovery, Slack connection check

**Current analyst output**: 0 suggestions (correct for wrong reasons)

The analyst correctly produced no suggestions, but the detection logic wouldn't have found patterns even with more data because:
1. It looks for explicit frequency keywords ("every week", "daily")
2. It looks for audience mentions ("for the board")
3. These phrases indicate users who would create deliverables manually

### TP vs Orchestrator Architecture Reality

Per ADR-061, we have clear separation:
- **TP**: On-the-fly, conversational, ad-hoc requests
- **Orchestrator**: Scheduled, recurring, automated outputs

Users will naturally use TP for exploration and one-off tasks. The analyst should detect **behavioral patterns that indicate latent recurring needs** - not transcribe explicit requests.

---

## Decision

### Shift from Keyword Detection to Behavioral Analysis

**Before** (explicit patterns):
| User Says | Detection |
|-----------|-----------|
| "I update the board monthly" | ✓ Frequency + audience |
| "What's in #engineering?" (once) | ✗ No pattern |

**After** (behavioral patterns):
| Behavior Across Sessions | Detection |
|--------------------------|-----------|
| Asked about #engineering in 3 different sessions | ✓ Repeated topic |
| Always requests bullet point summaries | ✓ Format preference |
| Keeps re-explaining project context | ✓ Context re-establishment |
| Asked "what happened yesterday" twice | ✓ Temporal information need |

### Pattern Categories

| Category | Signal | Minimum Threshold | Example Suggestion |
|----------|--------|-------------------|-------------------|
| **Repeated Topic** | Same subject/entity across 3+ sessions | 3 sessions | "#engineering Digest" |
| **Platform Query** | Same platform resource queried 2+ times | 2 queries | "Daily Inbox Brief" |
| **Temporal Need** | "yesterday", "this week", "recent" patterns | 2 occurrences | "Weekly Activity Summary" |
| **Format Consistency** | Repeated output structure requests | 3 requests | Template suggestion |
| **Context Re-establishment** | Same background info repeated | 2 sessions | Profile/deliverable setup |

### User Maturity Model

Not all users should receive suggestions immediately.

| Stage | Criteria | Analyst Behavior |
|-------|----------|------------------|
| **Onboarding** | < 7 days OR < 3 sessions | Skip analysis entirely |
| **Exploring** | 3-10 sessions, no deliverables | Analyze but require high confidence (0.70+) |
| **Active** | 10+ sessions OR 1+ deliverables | Normal analysis (0.50+ threshold) |
| **Power User** | 5+ deliverables | Look for coverage gaps |

### Cold Start Communication

When analysis runs but finds nothing, send a one-time acknowledgment:

```
"I analyzed your recent conversations but didn't detect patterns that would
benefit from automation yet. As you use YARNNN more, I'll look for recurring
information needs and suggest deliverables when appropriate."
```

This is NOT sent every analysis cycle - only once per user until:
- A suggestion is eventually made, OR
- User has 10+ sessions with no suggestions (then remind again)

---

## Implementation Changes

### 1. Analyst Prompt Rewrite

Replace `ANALYSIS_SYSTEM_PROMPT` with behavioral focus:

```python
ANALYSIS_SYSTEM_PROMPT = """You are analyzing user conversation BEHAVIOR patterns, not keywords.

**What to look for (cross-session patterns):**

1. **Repeated Topics**: Same subject mentioned across 3+ sessions
   - e.g., User asked about #engineering in sessions 1, 3, and 5
   - Suggests: automated digest of that topic

2. **Platform Resource Queries**: Same channel/inbox/folder queried multiple times
   - e.g., "What's new in #daily-work?" asked twice
   - Suggests: platform-specific digest

3. **Temporal Information Needs**: Phrases like "yesterday", "this week", "catch me up"
   - e.g., "What happened in Slack yesterday?" patterns
   - Suggests: recurring summary

4. **Re-established Context**: User repeatedly explains the same background
   - e.g., "I'm working on Project X for Client Y" in multiple sessions
   - Suggests: this should be a deliverable template or profile entry

**What NOT to look for:**
- Explicit scheduling language ("every Monday", "weekly") - user would self-service
- One-time queries or exploration behavior
- System/feature testing conversations

**Confidence scoring (behavioral):**
- 0.80+: Clear cross-session repetition (3+ instances)
- 0.60-0.79: Moderate pattern (2 instances with related context)
- 0.40-0.59: Weak signal, needs more data
- <0.40: No actionable pattern

**Output JSON array or empty []:**
"""
```

### 2. Add User Stage Detection

```python
async def get_user_stage(client, user_id: str) -> str:
    """Determine user maturity stage for analysis thresholds."""
    # Check account age
    user_result = client.auth.admin.get_user_by_id(user_id)
    account_age_days = (datetime.now() - user_result.user.created_at).days

    # Check session count (all time)
    session_count = client.table("chat_sessions").select("id", count="exact").eq("user_id", user_id).execute().count

    # Check deliverable count
    deliverable_count = client.table("deliverables").select("id", count="exact").eq("user_id", user_id).in_("status", ["active", "paused"]).execute().count

    if account_age_days < 7 or session_count < 3:
        return "onboarding"
    elif deliverable_count >= 5:
        return "power_user"
    elif deliverable_count >= 1 or session_count >= 10:
        return "active"
    else:
        return "exploring"
```

### 3. Stage-Based Thresholds

```python
STAGE_THRESHOLDS = {
    "onboarding": None,  # Skip analysis
    "exploring": 0.70,   # High confidence only
    "active": 0.50,      # Normal threshold
    "power_user": 0.50,  # Normal + gap analysis
}
```

### 4. Cold Start Notification

Track in `user_notification_preferences`:
```sql
ALTER TABLE user_notification_preferences
ADD COLUMN analyst_cold_start_sent BOOLEAN DEFAULT false;
```

---

## Files to Modify

| File | Change |
|------|--------|
| `api/services/conversation_analysis.py` | Rewrite `ANALYSIS_SYSTEM_PROMPT`, add `get_user_stage()`, adjust thresholds |
| `api/jobs/unified_scheduler.py` | Add stage check before analysis, cold start notification |
| `api/services/notifications.py` | Add `notify_analyst_cold_start()` function |
| `supabase/migrations/054_analyst_cold_start_tracking.sql` | Add tracking column |

---

## Risks

| Risk | Mitigation |
|------|------------|
| Behavioral analysis misses patterns | Log all analysis runs for manual review; iterate on prompt |
| Users never reach analysis threshold | Cold start message explains feature exists |
| Too few suggestions overall | Track suggestion rate per user stage; adjust thresholds |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Analysis runs with 0 suggestions | ~100% (keyword-based) | < 70% for active users |
| Suggestion acceptance rate | N/A | > 30% |
| False positive rate (dismissed quickly) | N/A | < 20% |

---

## Open Questions

1. **Gap analysis for power users**: Should analyst suggest filling gaps (e.g., "You have Slack digest but not Gmail brief")?
   - **Proposed**: Defer to Phase 2; focus on behavioral patterns first

2. **Cross-session topic clustering**: Should we pre-cluster topics before LLM analysis?
   - **Proposed**: Start with LLM-only; add clustering if token costs high

3. **Re-analysis cooldown**: How long after dismissal before re-suggesting similar pattern?
   - **Proposed**: 30 days; track dismissal reasons
