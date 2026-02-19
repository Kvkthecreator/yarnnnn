# ADR-061 Implementation Plan: Two-Path Architecture Consolidation

**Created**: 2026-02-16
**Target Completion**: 2026-02-23
**Status**: In Progress

---

## Overview

This plan implements ADR-061's Two-Path Architecture consolidation:
- **Path A (TP)**: Real-time conversational agent
- **Path B (Orchestrator)**: Async scheduled execution with Analysis + Execution phases

---

## Phase 1: Dead Code Cleanup

**Goal**: Remove unused agent code per ADR-061 audit findings.

### 1.1 Verify Dead Code (Day 1)

| File | Expected Status | Verification |
|------|-----------------|--------------|
| `api/agents/synthesizer.py` | Dead | Grep for imports/calls |
| `api/agents/report.py` | Dead | Grep for imports/calls |
| `api/agents/researcher.py` | Partial | Only `research_topic()` used |
| `api/agents/factory.py` | Simplify | Only DeliverableAgent needed |

```bash
# Verification commands
grep -r "SynthesizerAgent" api/ --include="*.py"
grep -r "ReportAgent" api/ --include="*.py"
grep -r "from agents.synthesizer" api/ --include="*.py"
grep -r "from agents.report" api/ --include="*.py"
grep -r "research_topic" api/ --include="*.py"
```

### 1.2 Remove Dead Agents (Day 1)

- [ ] Delete `api/agents/synthesizer.py`
- [ ] Delete `api/agents/report.py`
- [ ] Update `api/agents/__init__.py` to remove exports
- [ ] Update `api/agents/factory.py` to only support DeliverableAgent
- [ ] Verify tests still pass (if any agent tests exist)

### 1.3 Simplify Researcher (Day 1)

Keep only the `research_topic()` function needed by ResearchStrategy:

- [ ] Extract `research_topic()` to `api/services/web_research.py`
- [ ] Update `api/services/execution_strategies.py` imports
- [ ] Delete `api/agents/researcher.py` (class-based agent)

**Deliverable**: Cleaner agent directory with only:
- `base.py` - Shared infrastructure
- `thinking_partner.py` - Path A
- `deliverable.py` - Path B content generation
- `factory.py` - Simplified

---

## Phase 2: Analysis Phase Service

**Goal**: Implement conversation pattern detection as service function (not separate agent).

### 2.1 Service Function Skeleton (Day 2)

Create `api/services/conversation_analysis.py`:

```python
"""
Conversation Analysis Service - ADR-060/061

Detects patterns in user conversations and creates suggested deliverables.
Runs as part of unified_scheduler.py Analysis Phase (daily).
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class AnalystSuggestion:
    confidence: float  # 0.0 - 1.0
    deliverable_type: str
    title: str
    description: str
    suggested_frequency: str
    suggested_sources: list[dict]
    detection_reason: str
    source_sessions: list[str]

async def analyze_conversation_patterns(
    client,
    user_id: str,
    sessions: list[dict],
    existing_deliverables: list[dict],
    user_knowledge: list[dict],
) -> list[AnalystSuggestion]:
    """
    Analyze recent conversations for recurring patterns.

    Args:
        client: Supabase client
        user_id: User UUID
        sessions: Recent chat sessions (last 7 days)
        existing_deliverables: Current user deliverables (avoid duplicates)
        user_knowledge: Knowledge entries for context

    Returns:
        List of suggestions with confidence scores
    """
    # Implementation in 2.2
    pass

async def create_suggested_deliverable(
    client,
    user_id: str,
    suggestion: AnalystSuggestion,
) -> Optional[str]:
    """
    Create a deliverable with status='suggested' and analyst_metadata.

    Returns deliverable_id if created, None if duplicate detected.
    """
    # Implementation in 2.3
    pass
```

### 2.2 Pattern Detection Logic (Day 2-3)

Implement `analyze_conversation_patterns()`:

1. **Extract conversation summaries** from sessions
2. **Single LLM call** with structured output (JSON mode)
3. **Pattern matching** against known deliverable types
4. **Confidence scoring** based on:
   - Explicit frequency mentions ("weekly", "every Monday")
   - Repeated queries (same channel/topic 3+ times)
   - Audience mentions ("board", "team", "client")

Prompt structure:
```
Analyze these conversations for recurring work patterns.
For each pattern detected, provide:
- deliverable_type (from: slack_channel_digest, gmail_inbox_brief, status_report, etc.)
- confidence (0.0-1.0)
- suggested_frequency
- detection_reason

Return JSON array of suggestions.
```

### 2.3 Suggestion Creation (Day 3)

Implement `create_suggested_deliverable()`:

1. **Duplicate check**: Match deliverable_type + sources
2. **Create deliverable** with:
   - `status: 'active'` (deliverable itself)
   - Initial version with `status: 'suggested'`
   - `analyst_metadata` populated from suggestion
3. **Return deliverable_id** for tracking

### 2.4 Scheduler Integration (Day 3)

Update `api/jobs/unified_scheduler.py`:

```python
# In run_unified_scheduler(), add Analysis Phase

async def run_analysis_phase(supabase, now: datetime):
    """
    ADR-061: Analysis Phase - detect patterns in conversations.
    Runs daily (when minute < 5).
    """
    if now.minute >= 5:
        return  # Only run in first 5 minutes of hour

    # Get users with recent activity
    users = await get_active_users(supabase, days=7)

    analysis_count = 0
    suggestions_created = 0

    for user in users:
        try:
            sessions = await get_recent_sessions(supabase, user["id"], days=7)
            if len(sessions) < 3:  # Need minimum activity
                continue

            existing = await get_user_deliverables(supabase, user["id"])
            knowledge = await get_user_knowledge(supabase, user["id"])

            suggestions = await analyze_conversation_patterns(
                supabase, user["id"], sessions, existing, knowledge
            )

            for suggestion in suggestions:
                if suggestion.confidence >= 0.50:
                    result = await create_suggested_deliverable(
                        supabase, user["id"], suggestion
                    )
                    if result:
                        suggestions_created += 1

            analysis_count += 1

        except Exception as e:
            logger.warning(f"[ANALYSIS] Error for user {user['id']}: {e}")

    logger.info(f"[ANALYSIS] Processed {analysis_count} users, created {suggestions_created} suggestions")
```

**Deliverable**: Working analysis phase that creates suggested deliverables.

---

## Phase 3: TP Prompt Updates

**Goal**: Clarify TP's role boundary per ADR-061.

### 3.1 Add Work Boundary Section (Day 4)

Update `api/agents/tp_prompts/behaviors.py`:

```python
WORK_BOUNDARY = """
## Work Boundary

You are a conversational assistant (Path A), NOT a batch processor (Path B).

**DO:**
- Answer questions using Search, Read, Execute primitives
- Execute one-time platform actions (send Slack, create draft)
- Create deliverables when user explicitly asks
- Remember facts about user (Write to memory)

**DON'T:**
- Generate recurring deliverable content (orchestrator does that)
- Suggest automations mid-conversation unprompted
- Run extensive multi-step research (defer to deliverable for recurring needs)

**When user says "set up a weekly digest":**
- Create the deliverable configuration via Write primitive
- The backend orchestrator will generate content on schedule
- You do NOT generate the first version inline

This separation keeps conversations focused and responsive.
"""
```

### 3.2 Update Prompt Assembly (Day 4)

In `api/agents/thinking_partner.py`, ensure WORK_BOUNDARY is included in system prompt.

### 3.3 Update Prompt Changelog (Day 4)

Per claude.md protocol, update `api/prompts/CHANGELOG.md`:

```markdown
## [2026.02.16.1] - ADR-061 Work Boundary

### Changed
- behaviors.py: Added WORK_BOUNDARY section
- Expected behavior: TP no longer proactively suggests automations mid-conversation
- TP creates deliverable configs but doesn't generate content inline
```

**Deliverable**: Updated TP prompts with clear path boundary.

---

## Phase 4: Testing & Validation

**Goal**: Verify implementation works correctly.

### 4.1 Manual Testing (Day 5)

- [ ] Verify Analysis Phase runs on scheduler trigger
- [ ] Verify suggested deliverables appear with correct metadata
- [ ] Verify TP doesn't suggest automations mid-conversation
- [ ] Verify TP can still create deliverables when explicitly asked

### 4.2 Integration Points (Day 5)

- [ ] API endpoints for suggested deliverables work (`GET /deliverables/suggested`)
- [ ] Enable/dismiss actions update status correctly
- [ ] Frontend can display suggested deliverables (when UI ready)

---

## File Changes Summary

| Phase | Files Created/Modified |
|-------|----------------------|
| 1 | Delete: `synthesizer.py`, `report.py`. Modify: `factory.py`, `__init__.py` |
| 2 | Create: `services/conversation_analysis.py`. Modify: `unified_scheduler.py` |
| 3 | Modify: `tp_prompts/behaviors.py`, `thinking_partner.py`, `prompts/CHANGELOG.md` |
| 4 | No new files (testing) |

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Agent files reduced | 2 files deleted (synthesizer, report) |
| Analysis phase runs | Daily, logs user count + suggestions |
| Suggested deliverables created | For users with 3+ sessions/week |
| TP boundary respected | No automation suggestions mid-chat |

---

## Rollback Plan

If issues arise:
1. **Phase 1**: Revert git commits, restore deleted files
2. **Phase 2**: Disable analysis phase in scheduler (comment out call)
3. **Phase 3**: Revert prompt changes, update changelog

---

## Next Steps After This Plan

1. **Frontend**: Enhance `/deliverables` page with Suggested section (deferred)
2. **Notifications**: Weekly digest email with suggestions (Phase 3 of ADR-060)
3. **Learning loop**: Track acceptance rates to improve detection (Phase 4 of ADR-060)
