# ADR-070: Enhanced Activity Pattern Detection

**Status**: Accepted
**Date**: 2025-02-20
**Context**: ADR-064 Phase 1B completion

## Context

ADR-064 introduced implicit memory extraction from three sources: conversation, agent feedback, and activity patterns. The initial implementation of `process_patterns()` only detected day-of-week preferences (e.g., "Typically runs agents on Mondays").

The implementation brief specified that pattern detection must expand beyond this single heuristic to capture richer behavioral signals. The principle: **memory extraction should reflect actual user behavior patterns, not just when they work, but how they work**.

## Decision

Enhanced `_detect_activity_patterns()` in [services/memory.py](../../api/services/memory.py) to detect five first-class pattern types:

### 1. Day-of-Week Patterns
- **Detection**: One day has >50% of agent_run activity and ≥3 runs
- **Example**: `"Typically runs agents on Mondays"`
- **Key format**: `pattern:agent_day`

### 2. Time-of-Day Patterns
- **Detection**: Activity grouped into 4 time blocks (morning, afternoon, evening, late night)
- **Threshold**: One block has >50% of activity and ≥3 runs, with ≥5 total runs
- **Example**: `"Typically runs agents in the afternoon (12pm-6pm)"`
- **Key format**: `pattern:agent_time`

### 3. Agent Type Preferences
- **Detection**: One agent_type represents >60% of runs with ≥5 total runs
- **Example**: `"Frequently uses meeting_prep agents (primary workflow type)"`
- **Key format**: `pattern:agent_type_preference`
- **Purpose**: Signals primary workflow; useful for signal reasoning and onboarding recommendations

### 4. Edit Location Patterns
- **Detection**: Heuristic analysis of agent_approved event summaries for location keywords
- **Threshold**: One location (intro/body/conclusion) represents >60% of edits with ≥3 total edits
- **Example**: `"Tends to edit intro sections when revising agents"`
- **Key format**: `pattern:edit_location`
- **Note**: Currently uses keyword matching on summary text; future enhancement could use LLM-based diff analysis

### 5. Formatting Patterns (Length)
- **Detection**: Compares final_length vs draft_length in agent_approved metadata
- **Classification**: "shorter" if final < draft * 0.7, "longer" if final > draft * 1.3
- **Threshold**: ≥3 consistent edits in same direction
- **Examples**:
  - `"Prefers concise output; typically shortens generated content"`
  - `"Prefers detailed output; typically expands generated content"`
- **Key format**: `pattern:formatting_length`

## Enhanced Activity Log Metadata

To support these detections, activity_log writes now include richer metadata:

### agent_run events ([agent_execution.py:725](../../api/services/agent_execution.py#L725))
```python
metadata = {
    "agent_id": str(agent_id),
    "version_number": next_version,
    "agent_type": agent_type,  # NEW
    "strategy": strategy.strategy_name,
    "final_status": final_status,
    "delivery_error": delivery_error,
}
```

### agent_approved events ([agents.py:1960](../../api/routes/agents.py#L1960))
```python
metadata = {
    "agent_id": str(agent_id),
    "version_id": str(version_id),
    "agent_type": check.data.get("agent_type"),  # NEW
    "had_edits": bool(...),  # NEW
    "final_length": len(final_content),  # NEW (if had_edits)
    "draft_length": len(draft_content),  # NEW (if had_edits)
}
```

## Implementation

Changes span three files:

1. **[services/memory.py](../../api/services/memory.py)** (lines 367-524)
   - Expanded `_detect_activity_patterns()` from 30 lines to 158 lines
   - Five pattern detection functions (day, time, type, location, length)
   - Uses Counter for frequency analysis across all patterns
   - Maintains existing confidence=0.6 for pattern-sourced memories

2. **[routes/agents.py](../../api/routes/agents.py)** (lines 1946-1980)
   - Enhanced agent_approved activity log to include had_edits, final_length, draft_length, agent_type
   - Preserves existing memory feedback extraction (lines 1965-1980)

3. **[services/agent_execution.py](../../api/services/agent_execution.py)** (line 725)
   - Added agent_type to agent_run metadata

## Consequences

### Positive
- **Richer user profiles**: Memory layer now captures workflow preferences beyond just scheduling
- **Better signal reasoning**: LLM can use type preferences to guide create vs trigger decisions
- **Improved generation quality**: Formatting patterns inform draft length and structure
- **Foundation for learning**: Edit location patterns enable targeted prompt improvements
- **Non-breaking**: All changes are additive; existing pattern detection (day-of-week) preserved

### Trade-offs
- **Heuristic limitations**: Edit location detection uses keyword matching, not semantic analysis (acceptable for v1)
- **Metadata dependencies**: Pattern quality depends on consistent metadata writes (mitigated by try/except wrapping)
- **No retroactive detection**: Only detects patterns from activity logged after this change (acceptable - patterns emerge over time)

### Future Enhancements
- LLM-based edit location analysis (replace keyword heuristics with semantic diff analysis)
- Section-level formatting patterns (not just overall length)
- Cross-agent consistency patterns (e.g., "Always uses bullet points in weekly_standup but prose in board_update")
- Temporal patterns (morning agents are shorter than evening ones)

## Completion Criteria (Phase 1B)

✅ Pattern detection enhanced beyond single day-of-week rule
✅ Five first-class pattern types implemented
✅ Activity log metadata enriched for pattern detection
✅ No breaking changes to existing functionality
✅ Patterns written to user_context with source="pattern"

Phase 1B complete. Ready for Phase 1C: Type validation bug fix.

## References

- ADR-064: Implicit Memory Extraction (three write sources)
- ADR-063: Four-Layer Model (Activity = Layer 2)
- Implementation Brief Phase 1B: "Enhance pattern detection beyond the current single day-of-week rule"
