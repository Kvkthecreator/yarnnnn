# Phase 1-3 Integration Testing Guide

**Date**: 2026-02-20
**Scope**: Validation and testing for Phases 1-3 implementation
**Related**: ADR-069, ADR-070, ADR-071

---

## Automated Validation

### Quick Validation

Run the comprehensive validation script:

```bash
python3 scripts/validate_phase1_integration.py
```

This validates:
- ✅ Layer 4 content integration in manual signal processing
- ✅ Layer 4 content integration in automated cron
- ✅ ~~New deliverable types registered (deep_research, daily_strategy_reflection, intelligence_brief)~~ — **Deprecated by ADR-082**: these types are now absorbed into research_brief and status_report
- ✅ Memory extraction wired to approval endpoint
- ✅ Pattern detection scheduled at midnight UTC
- ✅ 5 pattern types implemented
- ✅ ~~TYPE_PROMPTS has 24 entries~~ — **Updated by ADR-082**: TYPE_PROMPTS now has 8 entries (active types only)
- ✅ Documentation complete (ADR-069, ADR-070, ADR-071)

---

## Manual Testing Scenarios

### 1. Manual Signal Processing with Layer 4 Content

**Objective**: Verify manual trigger includes recent deliverable content in reasoning

**Prerequisites**:
- User has active platform connections (Google Calendar, Gmail, Slack, or Notion)
- User has at least 1 existing deliverable with generated versions

**Test Steps**:
1. Navigate to Settings or Deliverables page
2. Click "Run Signal Processing Now" button
3. Check response payload

**Expected Result**:
- Signal processing completes successfully
- If `trigger_existing` action taken, it should be informed by recent deliverable content
- Response includes `actions_taken` array with reasoning results

**Verification**:
```bash
# Check logs for Layer 4 content in prompt
grep "Last output" logs/unified_scheduler.log

# Or inspect backend response
curl -X POST https://api.yarnnn.com/signal-processing/trigger \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

---

### 2. Memory Extraction from Deliverable Feedback

**Objective**: Verify approval with edits triggers memory extraction

**Prerequisites**:
- User has a staged deliverable version

**Test Steps**:
1. Navigate to Deliverables page
2. Open a staged version
3. Edit the content (e.g., shorten intro, change format)
4. Approve the version
5. Wait 5-10 seconds for async processing
6. Navigate to Context page → Memory tab

**Expected Result**:
- Memory entries appear with `source=feedback` if edits are significant
- Length preference memory if content length changed >30%
- Format preference memory if structural changes detected

**Example Memory Entries**:
```
Key: pattern:formatting_length
Value: "Prefers concise output; typically shortens generated content"
Source: feedback
Confidence: 0.7
```

**Database Verification**:
```sql
SELECT key, value, source, confidence
FROM user_context
WHERE user_id = 'USER_ID'
  AND source = 'feedback'
ORDER BY updated_at DESC
LIMIT 5;
```

---

### 3. Pattern Detection from Activity

**Objective**: Verify daily pattern detection runs and extracts behavioral patterns

**Prerequisites**:
- User has activity_log entries spanning multiple days
- At least 3 deliverable_run events

**Test Steps**:
1. Trigger pattern detection manually or wait until midnight UTC
2. Check `user_context` for new pattern-sourced entries
3. Verify 5 pattern types are being detected

**Expected Pattern Types**:

| Pattern Type | Key | Example Value |
|---|---|---|
| Day-of-week | `pattern:deliverable_day` | "Typically runs deliverables on Mondays" |
| Time-of-day | `pattern:deliverable_time` | "Typically runs deliverables in the afternoon (12pm-6pm)" |
| Type preference | `pattern:deliverable_type_preference` | "Frequently uses meeting_prep deliverables" |
| Edit location | `pattern:edit_location` | "Tends to edit intro sections when revising" |
| Formatting length | `pattern:formatting_length` | "Prefers concise output; typically shortens generated content" |

**Manual Trigger** (for testing):
```python
# In unified_scheduler.py, temporarily comment out midnight check
# if now.hour == 0 and now.minute < 5:  # Comment this line

# Then trigger scheduler manually
```

**Database Verification**:
```sql
SELECT key, value, source, confidence, created_at
FROM user_context
WHERE user_id = 'USER_ID'
  AND source = 'pattern'
ORDER BY created_at DESC
LIMIT 10;
```

---

### 4. New Deliverable Types (Phase 2)

**Objective**: Verify 3 new strategic intelligence types are fully functional

#### 4A. Deep Research Deliverable

**Test Steps**:
1. Via TP: "Create a deep research deliverable about quantum computing trends"
2. Or via UI: Create new deliverable, select type `deep_research`
3. Configure topic and sources
4. Trigger execution

**Expected Result**:
- Deliverable created with `deliverable_type=deep_research`
- Execution uses `ResearchStrategy` (web search via Anthropic native tool)
- Version content has 5 sections: Executive Summary, Key Findings, Detailed Analysis, Sources, Synthesis
- `source_snapshots` includes web search results

**Type Config Verification**:
```python
# Should return binding="research"
from api.routes.deliverables import get_type_classification
assert get_type_classification("deep_research")["binding"] == "research"
```

#### 4B. Daily Strategy Reflection Deliverable

**Test Steps**:
1. Via TP: "Set up a daily strategy reflection"
2. Or via UI: Create new deliverable, select type `daily_strategy_reflection`
3. Configure reflection focus
4. Trigger execution

**Expected Result**:
- Deliverable created with `deliverable_type=daily_strategy_reflection`
- Execution uses `CrossPlatformStrategy` (synthesizes across all platforms)
- Version content has 4 sections: Context Summary, Strategic Insights, Decision Points, Action Items
- `source_snapshots` includes calendar, gmail, slack, notion

#### 4C. Intelligence Brief Deliverable

**Test Steps**:
1. Via TP: "Create an intelligence brief for competitive analysis"
2. Or via UI: Create new deliverable, select type `intelligence_brief`
3. Configure brief type and focus areas
4. Trigger execution

**Expected Result**:
- Deliverable created with `deliverable_type=intelligence_brief`
- Execution uses `HybridStrategy` (research + platform grounding)
- Version content has 6 sections: Priority Signals, Situational Analysis, Market Intelligence, Operational Context, Strategic Implications, Watch List
- `source_snapshots` includes both web search and platform sources

---

### 5. Signal-Emergent Deliverables with Layer 4 Content

**Objective**: Verify signal processing uses recent deliverable content to make quality-aware decisions

**Prerequisites**:
- User has 1+ active deliverables with recent versions
- User has calendar events or signals

**Test Scenario A**: Content Staleness Detection

**Setup**:
1. Create a `meeting_prep` deliverable for "Weekly Team Standup"
2. Run it to generate version with content about internal team
3. Add new calendar event: "Client Meeting with Alice (external)"

**Test Steps**:
1. Trigger signal processing (manual or wait for cron)
2. Check processing result

**Expected Result**:
- Signal processing detects calendar event signal
- Reads recent `meeting_prep` deliverable content (400-char preview)
- LLM reasoning: "Existing meeting_prep is for internal standup, not Alice meeting"
- Action: `create_signal_emergent` (new one-time deliverable) instead of `trigger_existing`

**Verification**:
```sql
-- Check signal processing created NEW deliverable
SELECT id, title, origin, deliverable_type
FROM deliverables
WHERE user_id = 'USER_ID'
  AND origin = 'signal_emergent'
  AND deliverable_type = 'meeting_prep'
ORDER BY created_at DESC
LIMIT 1;
```

**Test Scenario B**: Content Coverage Detection

**Setup**:
1. Create `intelligence_brief` deliverable for "AI regulation trends"
2. Run it to generate version about AI regulation
3. Add new calendar event related to AI regulation (within existing coverage)

**Test Steps**:
1. Trigger signal processing
2. Check processing result

**Expected Result**:
- Signal processing reads recent `intelligence_brief` content
- LLM reasoning: "Recent deliverable (2 days ago) already covers this signal"
- Action: `no_action` (signal deduplicated by recent work)

---

### 6. TP Tool Integration

**Objective**: Verify TP can create new deliverable types via Write tool

**Test Cases**:

```
User: "Create a deep research deliverable about AI safety"
TP: Write(ref="deliverable:new", content={
  title: "AI Safety Research",
  deliverable_type: "deep_research",
  config: {topic: "AI safety"}
})
→ Expect: Deliverable created with type=deep_research
```

```
User: "Set up a daily strategy reflection"
TP: Write(ref="deliverable:new", content={
  title: "Daily Strategy Check-in",
  deliverable_type: "daily_strategy_reflection",
  frequency: "daily"
})
→ Expect: Deliverable created with type=daily_strategy_reflection
```

**Verification**:
- Check TP response acknowledges creation
- Check deliverables table has new row with correct type
- Check type_config matches expected binding (research, cross_platform, hybrid)

---

### 7. Documentation Consistency

**Objective**: Verify documentation aligns with implementation

**Checklist**:

- [ ] [four-layer-model.md](../architecture/four-layer-model.md) has bidirectional learning section
- [ ] [memory.md](../features/memory.md) lists 3 extraction sources
- [ ] [deliverables.md](../features/deliverables.md) mentions 3 origins (user_configured, analyst_suggested, signal_emergent)
- [ ] [ADR-069](../adr/ADR-069-layer-4-content-in-signal-reasoning.md) exists and describes Layer 4 integration
- [ ] [ADR-070](../adr/ADR-070-enhanced-activity-pattern-detection.md) exists and describes 5 pattern types
- [ ] [ADR-071](../adr/ADR-071-strategic-architecture-principles.md) exists and describes 8 strategic principles

**Manual Check**:
```bash
# Check for key terms in documentation
grep -r "bidirectional learning" docs/architecture/
grep -r "quality flywheel" docs/architecture/
grep -r "three extraction sources" docs/features/memory.md
grep -r "signal_emergent" docs/features/deliverables.md
```

---

## Performance Testing

### Signal Processing Latency

**Baseline**: Manual trigger should complete in <10 seconds for typical user

**Test**:
```bash
time curl -X POST https://api.yarnnn.com/signal-processing/trigger \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected**:
- With Layer 4 content (10 deliverables): 5-8 seconds
- Token usage: ~2,500-3,500 additional tokens (acceptable per ADR-069)

### Pattern Detection Performance

**Baseline**: Daily pattern detection should complete in <30 seconds per user

**Test**:
```python
import time
from services.memory import process_patterns
from services.supabase import get_service_client

start = time.time()
extracted = await process_patterns(
    client=get_service_client(),
    user_id="test-user-id"
)
elapsed = time.time() - start
print(f"Pattern detection: {extracted} patterns in {elapsed:.2f}s")
```

**Expected**:
- 90 days of activity_log (100-200 events): <5 seconds
- 5 pattern types detected on average per mature user

---

## Edge Cases

### 1. Deliverable with No Versions

**Scenario**: User created deliverable but never ran it

**Expected Behavior**:
- Signal processing query returns deliverable with `recent_content=None`
- Prompt formatting handles missing content gracefully (no preview shown)
- No crash or error

### 2. All Deliverables Are Stale

**Scenario**: User has deliverables but last version was >30 days ago

**Expected Behavior**:
- Signal processing includes content previews with "30 days ago" recency
- LLM reasoning may prefer `create_signal_emergent` over `trigger_existing`
- No special handling needed (staleness is input to reasoning)

### 3. Memory Extraction from Minimal Edits

**Scenario**: User approves version with only 2 characters changed

**Expected Behavior**:
- `process_feedback()` called but extracts nothing (edits too minimal)
- No new memory entries created
- Non-fatal, does not block approval

### 4. Pattern Detection with Insufficient Data

**Scenario**: User has only 1 deliverable_run event

**Expected Behavior**:
- Pattern detection runs but finds no patterns (thresholds not met)
- No memory entries created with `source=pattern`
- No error logged

---

## Rollback Plan

If Phase 1-3 integration causes issues:

### Quick Rollback (Manual Trigger Only)

1. Revert manual trigger endpoint to old query:
```python
# In api/routes/signal_processing.py:170-177
existing_deliverables_result = (
    supabase.table("deliverables")
    .select("id, title, deliverable_type, next_run_at, status")
    .eq("user_id", user_id)
    .in_("status", ["active", "paused"])
    .execute()
)
existing_deliverables = existing_deliverables_result.data or []
```

2. Deploy hotfix

### Full Rollback (All Phases)

```bash
# Revert to before Phase 1A
git revert d989c94  # Signal processing fix
git revert b3ae8f4  # Phase 3
git revert 655a88e  # Phase 3A
git revert 2eab875  # Phase 2
git revert 0e995d4  # Phase 1C
git revert fb4e62e  # Phase 1B part 2
git revert b7e4ee5  # Phase 1B part 1
git revert 27f8376  # Phase 1A

git push origin main
```

---

## Success Criteria

Phase 1-3 implementation is considered validated when:

- [ ] All 8 automated validation checks pass
- [ ] Manual signal processing includes Layer 4 content
- [ ] Memory extraction from approval creates `source=feedback` entries
- [ ] Daily pattern detection creates `source=pattern` entries
- [ ] All 3 new deliverable types execute successfully
- [ ] TP can create new deliverable types via Write tool
- [ ] Signal processing demonstrates quality-aware decision making (staleness/coverage)
- [ ] No performance regression (signal processing <10s, pattern detection <30s)
- [ ] Documentation matches implementation

---

## Next Steps After Validation

Once validation complete:

1. **User Acceptance Testing** (UAT)
   - Test with 3-5 beta users
   - Monitor logs for unexpected errors
   - Collect feedback on signal processing quality

2. **Production Monitoring**
   - Set up alerts for signal processing failures
   - Track pattern detection extraction rate
   - Monitor Layer 4 content token usage

3. **Feature Iteration**
   - Tune pattern detection thresholds based on real data
   - Add LLM-based edit location analysis (replace keyword heuristics)
   - Consider summarization for very long deliverables (>5,000 words)

---

## Related

- [ADR-069: Layer 4 Content Integration](../adr/ADR-069-layer-4-content-in-signal-reasoning.md)
- [ADR-070: Enhanced Activity Pattern Detection](../adr/ADR-070-enhanced-activity-pattern-detection.md)
- [ADR-071: Strategic Architecture Principles](../adr/ADR-071-strategic-architecture-principles.md)
- [Validation Script](../../scripts/validate_phase1_integration.py)
