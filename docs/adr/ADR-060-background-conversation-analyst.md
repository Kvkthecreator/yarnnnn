# ADR-060: Background Conversation Analyst Architecture

**Date**: 2026-02-16
**Status**: Proposed
**Supersedes**: None
**Relates to**: ADR-045 (Deliverable Orchestration), ADR-049 (Context Freshness), ADR-057 (Onboarding)

---

## Context

### The Problem

Users have conversations with Thinking Partner (TP) that contain implicit work patterns:
- "I need to update the board monthly on our progress"
- "Can you summarize what happened in #engineering this week?"
- "I should probably track competitor funding news"

Currently, TP can create deliverables mid-conversation, but this creates friction:
1. **Interrupts flow**: User is thinking, not configuring
2. **Blurs responsibility**: Is TP a conversational assistant or work orchestrator?
3. **Timing problem**: Research shows 62% of mid-task suggestions are dismissed

### Evidence Base

External research conducted (2026-02-16):

| Finding | Source | Implication |
|---------|--------|-------------|
| 52% engagement at workflow boundaries vs 62% dismissal mid-task | Developer interaction research | Post-conversation > in-conversation |
| No product does fully automatic creation | Linear, Granola, Superhuman, Otter | All require explicit trigger or confirmation |
| Viva Topics retired (2025) | Microsoft | Automatic extraction without tight UX fails |
| 21% of AI summaries contain errors | Meeting assistant research | Confidence thresholds + human review required |
| 64% delete apps with 5+ notifications/week | UX research | Batch digest > per-event notifications |

### Architectural Insight

Claude Code's success comes from clear separation:
- **Conversational agent**: Explores, reads, answers, executes
- **Background systems**: Caching, tool management, context handling

YARNNN should mirror this: TP for conversation, background systems for work orchestration.

---

## Decision

### Principle: Separation of Concerns

**TP becomes a pure conversational agent:**
- Search (internal + web)
- Read user context
- Answer questions
- Execute platform actions
- Remember facts about user
- **NOT**: Create deliverables mid-conversation

**Background Conversation Analyst handles work detection:**
- Runs asynchronously (not during conversation)
- Analyzes conversation patterns
- Creates "suggested" deliverables
- User manages via frontend, not chat

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ User's Live Experience                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐                                           │
│  │ Thinking Partner │ ← Pure conversational agent               │
│  │                  │   Claude Code-like: explore, answer,      │
│  │                  │   search, execute                         │
│  └──────────────────┘                                           │
│                                                                 │
│  Conversations stored in chat_sessions / session_messages       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ (async, not blocking)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Background Orchestration                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  unified_scheduler.py (daily cron)                              │
│           │                                                     │
│           ▼                                                     │
│  ┌──────────────────┐                                           │
│  │ Conversation     │ ← Analyzes recent conversations           │
│  │ Analyst Agent    │   Detects: patterns, recurring needs,     │
│  │                  │   implicit deliverable requests           │
│  └────────┬─────────┘                                           │
│           │                                                     │
│           │ confidence > 60%                                    │
│           ▼                                                     │
│  ┌──────────────────┐                                           │
│  │ Suggested        │ ← status: "suggested"                     │
│  │ Deliverables     │   Not auto-enabled                        │
│  └──────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ User Notification                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  On visit to /deliverables:                                     │
│    → Badge/indicator for new suggestions                        │
│    → "Suggested" section at top                                 │
│    → One-click: enable, edit, dismiss                           │
│                                                                 │
│  Weekly email digest:                                           │
│    → "Here's what we noticed this week"                         │
│    → Links to review suggestions                                │
│    → Not per-suggestion (avoids spam)                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Frequency Model

| Activity | Frequency | Channel |
|----------|-----------|---------|
| Analyst runs | Daily | Background (silent) |
| Suggestions created | As detected | `status: "suggested"` in DB |
| In-app notification | On visit | Badge in `/deliverables` |
| Email digest | Weekly | Rollup of week's suggestions |
| Deliverable outputs | Per schedule | Separate email cadence |

**Rationale**: Analyst is write-heavy, notify-light. Users who visit daily see suggestions immediately; others get weekly rollup. Avoids notification fatigue.

---

## Schema Changes

### Deliverable Version Status

Add `"suggested"` to version status enum:

```sql
-- Migration: 0XX_suggested_deliverable_status.sql
ALTER TABLE deliverable_versions
DROP CONSTRAINT IF EXISTS deliverable_versions_status_check;

ALTER TABLE deliverable_versions
ADD CONSTRAINT deliverable_versions_status_check
CHECK (status IN ('generating', 'staged', 'reviewing', 'approved', 'rejected', 'suggested'));

-- Index for quick filtering
CREATE INDEX idx_versions_suggested
ON deliverable_versions(user_id, status)
WHERE status = 'suggested';
```

### Suggested Version Metadata

```sql
-- In deliverable_versions.metadata (JSONB)
{
  "analyst_confidence": 0.75,
  "detected_pattern": "weekly_status_to_board",
  "source_sessions": ["session-uuid-1", "session-uuid-2"],
  "detection_reason": "User mentioned 'monthly board update' in 2 conversations"
}
```

---

## Analyst Agent Design

### Input

```python
class AnalystInput:
    user_id: str
    sessions: list[ChatSession]  # Last 7 days of conversations
    existing_deliverables: list[Deliverable]  # To avoid duplicates
    user_knowledge: list[KnowledgeEntry]  # User preferences
```

### Output

```python
class AnalystSuggestion:
    confidence: float  # 0.0 - 1.0
    deliverable_type: str  # e.g., "status_report", "slack_channel_digest"
    title: str
    description: str
    suggested_frequency: str
    suggested_sources: list[Source]
    detection_reason: str
    source_sessions: list[str]
```

### Confidence Thresholds

| Confidence | Action |
|------------|--------|
| >= 0.70 | Create as "suggested", include in weekly digest |
| 0.50 - 0.69 | Create as "suggested", lower priority in UI |
| < 0.50 | Log for analytics, do not create |

### Pattern Detection Examples

| User Says | Detected Pattern | Suggested Deliverable |
|-----------|------------------|----------------------|
| "I update the board monthly" | Explicit frequency + audience | Monthly Board Update (status_report) |
| "What happened in #engineering?" (3x) | Repeated channel query | Weekly #engineering Digest (slack_channel_digest) |
| "Track Acme Corp news" | Competitor monitoring | Weekly Competitive Brief (research_brief) |
| "Summarize my unread emails" | Email triage pattern | Daily Inbox Brief (gmail_inbox_brief) |

---

## TP Prompt Changes

Remove deliverable creation from TP's active responsibilities:

```python
# In tp_prompts/behaviors.py - ADD

ANALYST_BOUNDARY = """
## Work Detection Boundary

You are a conversational assistant, NOT a work orchestrator.

**DO:**
- Answer questions about user's context
- Execute one-time platform actions (send Slack, create draft)
- Help user understand their data
- Remember facts for future conversations

**DON'T:**
- Suggest creating recurring deliverables mid-conversation
- Ask "Would you like me to set up a weekly report?"
- Proactively offer automation during chat

If user explicitly asks to create a deliverable, help them.
But don't suggest it - that's the Analyst's job (runs in background).

This separation keeps conversations focused and reduces interruption.
"""
```

---

## Frontend Changes

### /deliverables Page Enhancement

```
┌─────────────────────────────────────────────────────────────────┐
│ Deliverables                                        [+ Create]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 💡 Suggested (3 new)                              [Dismiss all] │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │                                                             │ │
│ │ Weekly #engineering Digest                                  │ │
│ │ Based on your recent conversations        [Enable] [Edit] [×]│ │
│ │                                                             │ │
│ │ Monthly Board Update                                        │ │
│ │ You mentioned "board updates" twice       [Enable] [Edit] [×]│ │
│ │                                                             │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Active (2)                                                  │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │ Weekly Status Report          Every Mon 9am    [Pause] [Edit]│ │
│ │ Daily Inbox Brief             Every day 8am    [Pause] [Edit]│ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### User Actions

| Action | Effect |
|--------|--------|
| Enable | Moves to Active, schedules first run |
| Edit | Opens deliverable editor with pre-filled values |
| Dismiss (×) | Removes suggestion, logs for learning |
| Dismiss all | Clears suggestions section |

---

## Implementation Phases

### Phase 1: Schema + API Foundation ✅ (2026-02-16)
- [x] Add `status: "suggested"` migration (`051_suggested_deliverable_status.sql`)
- [x] Add `analyst_metadata` column to `deliverable_versions`
- [x] API endpoints: `GET /deliverables/suggested`, `POST .../enable`, `DELETE .../dismiss`
- [x] Frontend types: `SuggestedVersion`, `AnalystMetadata`, updated `VersionStatus`
- [x] API client methods: `listSuggested`, `enableSuggested`, `dismissSuggested`
- [ ] Enhance `/deliverables` page with Suggested section (deferred - needs full CRUD revamp)
- [ ] Track dismissals for future learning

### Phase 2: Conversation Analyst Agent
- [ ] Create `ConversationAnalystAgent` class
- [ ] Add to `unified_scheduler.py` (daily trigger)
- [ ] Implement pattern detection logic
- [ ] Create suggested deliverables with metadata

### Phase 3: Notification Layer
- [ ] Add in-app badge for new suggestions
- [ ] Weekly email digest via Resend
- [ ] User preference: opt-out of suggestion emails

### Phase 4: Learning Loop (Future)
- [ ] Track acceptance/dismissal rates per pattern type
- [ ] Adjust confidence thresholds based on user behavior
- [ ] Personalize detection based on user's deliverable history

---

## Migration Path

### For Existing Users

No breaking changes:
- Existing deliverables continue working
- TP can still create deliverables if user explicitly asks
- Suggestions are additive, not replacing manual creation

### For New Users (ADR-057 Onboarding)

Onboarding flow unchanged:
- New users still guided through first deliverable creation
- Analyst starts working after first week of conversations
- Suggestions augment, not replace, explicit setup

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Too many suggestions | Medium | High | Confidence threshold (60%+); weekly digest not daily |
| Wrong suggestions | Medium | Medium | Easy dismiss; feedback loop for learning |
| Users ignore suggestions | Medium | Low | Measure acceptance rate; iterate on detection |
| TP feels "dumber" | Low | Medium | TP is more focused, not less capable |
| Privacy concerns | Low | High | Transparent: "Based on your conversations" |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Suggestion acceptance rate | > 30% | Enabled / (Enabled + Dismissed) |
| Time to first deliverable | < 7 days | For users with suggestions |
| Suggestion precision | > 70% | Enabled suggestions that run > 2 times |
| Notification opt-out rate | < 20% | Users disabling weekly digest |

---

## Open Questions

1. **Analyst trigger**: Daily cron vs. after N conversations vs. after session end?
   - **Proposed**: Daily cron (simpler), can refine later

2. **Duplicate detection**: How to avoid suggesting what user already has?
   - **Proposed**: Match on deliverable_type + sources before creating

3. **Analyst model**: Claude Sonnet (fast) or Opus (better reasoning)?
   - **Proposed**: Sonnet for cost efficiency; upgrade if precision suffers

4. **Opt-out granularity**: Global opt-out or per-pattern-type?
   - **Proposed**: Global for Phase 1; per-type if users request

---

## Related ADRs

- **ADR-045**: Deliverable Orchestration Redesign (execution strategies)
- **ADR-049**: Context Freshness Model (no history compression philosophy)
- **ADR-057**: Streamlined Onboarding (new user flow)
- **ADR-058**: Knowledge Base Architecture (user preferences storage)
