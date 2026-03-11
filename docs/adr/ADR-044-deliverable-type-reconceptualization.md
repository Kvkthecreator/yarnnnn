# ADR-044: Agent Type Reconceptualization

**Date**: 2026-02-11
**Status**: Amended by ADR-082 (Agent Type Consolidation — type surface reduced to 8 active types)
**Supersedes**: ADR-019 (Agent Types System) - conceptual direction
**Relates to**: ADR-031 (Platform-Native), ADR-034 (Emergent Domains), DECISION-001 (Platform Sync), ADR-082 (Type Consolidation)

---

## Context

### Legacy Model (ADR-019)

The original agent type system was **format-centric**:

```
status_report, stakeholder_update, research_brief, meeting_summary, custom
```

These types describe **output shape**, not:
- Where the value comes from (which platform context)
- How fresh the context needs to be (temporal requirements)
- Whether the agent should emerge vs. be declared
- Whether platforms inform reasoning or just formatting

### New Reality

Our architecture has evolved:

1. **Platforms are THE context** (ADR-031, ADR-043)
   - Real-time sync for fresh data
   - Platform signals inform *what's worth saying*
   - Source selection with limits per platform

2. **On-demand sync model** (DECISION-001)
   - Fresh context at generation time
   - Freshness thresholds matter (< 1h vs > 24h)
   - Cost implications of sync frequency

3. **Emergent domains** (ADR-034)
   - Domains emerge from agent source patterns
   - TP discovers context boundaries organically
   - Suggests: agents themselves might emerge

4. **Platform-native generation** (ADR-031)
   - Slack digests surface hot threads, not just summarize
   - Gmail triage identifies urgent vs. routine
   - Each platform has unique signal characteristics

### The Gap

Current types don't capture:

| Aspect | ADR-019 Model | Reality |
|--------|---------------|---------|
| Context source | Implicit/any | Platform-specific matters |
| Freshness | Assumed | Critical (stale context = bad output) |
| Discovery | User declares | TP could propose |
| Platform signals | Format only | Reasoning & selection |
| Composition | Single type | Can combine (research + slack) |

---

## Decision

Reconceptualize agent types as a **two-dimensional classification** with **emergent discovery support**.

### Dimension 1: Context Binding

How the agent relates to platform context:

| Binding | Description | Examples |
|---------|-------------|----------|
| **Platform-bound** | Primary value from single platform's signals | Slack digest, Gmail triage, Notion changelog |
| **Cross-platform** | Synthesizes across multiple platforms | Weekly standup (Slack + Notion + Calendar) |
| **Research/Discovery** | Builds context through agentic discovery | Competitive analysis, market research |
| **Hybrid** | Research + platform grounding | "Research competitors, grounded in #product discussions" |

### Dimension 2: Temporal Pattern

How the agent relates to time:

| Pattern | Description | Freshness Requirement |
|---------|-------------|----------------------|
| **Reactive** | Triggered by platform events | Real-time / < 1h |
| **Scheduled** | Regular cadence (daily/weekly) | Fresh at generation (sync on-demand) |
| **On-demand** | User-triggered when needed | Fresh at generation |
| **Emergent** | TP discovers need, proposes creation | Varies by discovered need |

### Dimension 3: Emergence Support

Agents can be:

| Mode | Description |
|------|-------------|
| **Declared** | User explicitly creates via wizard/TP |
| **Proposed** | TP suggests based on observed patterns |
| **Auto-created** | TP creates with user confirmation (future) |

---

## New Type System

### Platform-Bound Types

These are **platform-specific by design**. The platform isn't just a source—it's the organizing principle.

#### Slack-Bound

| Type | Value Proposition | Key Signals |
|------|-------------------|-------------|
| `slack_digest` | "What happened while you were away" | Hot threads, decisions made, questions unanswered |
| `slack_standup_synthesis` | Aggregate team standups into summary | Standup patterns, blockers, patterns across people |
| `slack_decision_log` | Track decisions made in channels | "We decided", reactions, thread conclusions |
| `slack_question_roundup` | Unanswered questions needing attention | Questions without resolution, @ mentions without reply |

**Platform-specific signals used**:
- Thread depth & reply velocity
- Reaction patterns (👀 vs ✅)
- Time-to-response
- @ mention patterns
- Channel cross-references

#### Gmail-Bound

| Type | Value Proposition | Key Signals |
|------|-------------------|-------------|
| `gmail_triage` | Prioritized inbox summary | Sender importance, thread age, action-required language |
| `gmail_thread_summary` | Summarize long email threads | Thread length, participant changes, decision points |
| `gmail_followup_tracker` | Emails awaiting response | Sent emails without reply, promised follow-ups |

**Platform-specific signals used**:
- Sender history & relationship
- Thread length & participant count
- Labels as semantic markers
- Response time patterns

#### Notion-Bound

| Type | Value Proposition | Key Signals |
|------|-------------------|-------------|
| `notion_changelog` | What changed in your docs | Edit significance, new sections, resolved comments |
| `notion_stale_page_alert` | Docs that need updating | Age vs. reference frequency, broken links |
| `notion_decision_tracker` | Decisions documented in pages | Decision callouts, status changes |

**Platform-specific signals used**:
- Edit frequency & recency
- Comment resolution status
- Page link graph
- Database property changes

### Cross-Platform Types

These synthesize across platforms. They're about the **synthesis task**, not the platform.

| Type | Description | Typical Sources |
|------|-------------|-----------------|
| `status_report` | Progress update for stakeholder | Slack + Notion + Calendar |
| `weekly_digest` | "What happened this week" across work | All connected platforms |
| `project_brief` | Current state of a project | Slack channels + Notion pages + relevant emails |
| `meeting_prep` | Context for upcoming meeting | Calendar + related Slack threads + relevant docs |
| `handoff_document` | Context transfer for coverage | All context for a project/domain |

**Cross-platform types require**:
- Multiple platform sources selected
- Domain-scoped context (ADR-034)
- Synthesis reasoning (what connects the data)

### Research/Discovery Types

These build context through agentic work, not just platform extraction.

| Type | Description | Agentic Actions |
|------|-------------|-----------------|
| `competitive_analysis` | Research on competitors | Web search, news monitoring, product analysis |
| `market_landscape` | Overview of market/industry | Industry research, trend identification |
| `topic_deep_dive` | Comprehensive research on topic | Multi-source research, synthesis |
| `preparation_brief` | Research for upcoming event/meeting | Context gathering, question preparation |

**Discovery types require**:
- Clear research objective
- Agentic research capability (web search, etc.)
- Synthesis of discovered information

### Hybrid Composition

Types can be **composed** with platform grounding:

```
research_brief + slack_grounding =
  "Research competitors, incorporating insights from #product discussions"

competitive_analysis + gmail_grounding =
  "Competitive analysis, including relevant customer feedback emails"
```

**Composition pattern**:
```typescript
interface AgentConfig {
  primary_type: string;  // The core agent type
  platform_grounding?: {
    platform: "slack" | "gmail" | "notion";
    sources: string[];  // Channel IDs, labels, page IDs
    grounding_instruction?: string;  // How to incorporate
  }[];
}
```

---

## Emergent Agent Discovery

### TP as Agent Proposer

The TP should recognize opportunities to create agents:

**Trigger patterns**:

| Pattern | Example | Proposed Agent |
|---------|---------|---------------------|
| Repeated requests | "Summarize Slack for me" 3x | Propose `slack_digest` |
| Context need | "What did we decide about X?" often | Propose `slack_decision_log` |
| Preparation patterns | Meeting on calendar + relevant context | Propose `meeting_prep` |
| Stakeholder mentions | Mentions of same recipient | Propose `status_report` to that person |

**TP behavior**:

```
User: "Can you catch me up on what happened in #engineering this week?"

TP: [Provides catch-up summary]

    I notice you've asked me this a few times. Would you like me to
    set up a weekly Slack digest for #engineering? I can generate
    it every Monday morning before you start work.

    [Set up weekly digest] [Not now]
```

### Emergence Mechanics

```python
# TP tracks patterns that suggest agent value
class AgentPatternDetector:
    patterns = [
        {
            "trigger": "repeated_platform_summary_request",
            "count_threshold": 3,
            "time_window_days": 14,
            "proposed_type": "platform_digest",
            "proposal_message": "I notice you often ask for {platform} summaries..."
        },
        {
            "trigger": "meeting_context_gathering",
            "context": "calendar_event_upcoming",
            "proposed_type": "meeting_prep",
            "proposal_message": "You have a meeting with {participants} coming up..."
        },
        # ... more patterns
    ]
```

---

## Freshness Requirements

### Platform-Bound Types

| Type | Freshness Requirement | Sync Behavior |
|------|----------------------|---------------|
| `slack_digest` | < 1h for "current" feel | Sync on generation |
| `gmail_triage` | < 30m for inbox accuracy | Sync on generation |
| `notion_changelog` | < 4h acceptable | Sync if stale |

### Cross-Platform Types

| Type | Freshness Requirement | Sync Behavior |
|------|----------------------|---------------|
| `status_report` | < 4h for accuracy | Sync stale sources only |
| `meeting_prep` | < 1h (meeting is soon) | Sync all sources |
| `weekly_digest` | < 24h acceptable | Use cached where fresh |

### Freshness UX

```
Pre-generation check:
┌─────────────────────────────────────────────────────────────┐
│ Data Sources for "Weekly Status"                            │
├─────────────────────────────────────────────────────────────┤
│ 💬 Slack: #engineering, #product                            │
│    ● Last synced 2 hours ago                                │
│                                                             │
│ 📧 Gmail: INBOX, Important                                  │
│    ⚠️ Last synced 26 hours ago   [Refresh]                  │
│                                                             │
│ Some sources are stale. Generate anyway or refresh first?   │
│                                                             │
│ [Generate with stale data]  [Refresh all, then generate]    │
└─────────────────────────────────────────────────────────────┘
```

---

## Migration from ADR-019 Types

| ADR-019 Type | New Classification |
|--------------|-------------------|
| `status_report` | Cross-platform: `status_report` |
| `stakeholder_update` | Cross-platform: `status_report` (variant) |
| `research_brief` | Research: `topic_deep_dive` or `competitive_analysis` |
| `meeting_summary` | Platform-bound: `slack_standup_synthesis` or Cross-platform: `meeting_recap` |
| `custom` | Preserved as escape hatch |

**Migration approach**:
- Existing agents keep `agent_type` field
- Add `type_classification` field for new system
- Gradual migration as users edit agents

---

## Data Model Changes

```sql
-- Extend agents table
ALTER TABLE agents ADD COLUMN type_classification JSONB;
-- {
--   "binding": "platform_bound" | "cross_platform" | "research" | "hybrid",
--   "temporal_pattern": "reactive" | "scheduled" | "on_demand" | "emergent",
--   "primary_platform": "slack" | "gmail" | "notion" | null,
--   "platform_grounding": [
--     {"platform": "slack", "sources": ["C123"], "instruction": "..."}
--   ],
--   "freshness_requirement_hours": 4
-- }

-- Emergent agent tracking
CREATE TABLE agent_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    proposed_type TEXT NOT NULL,
    proposed_config JSONB NOT NULL,
    trigger_pattern TEXT NOT NULL,  -- What triggered the proposal
    trigger_evidence JSONB,  -- Evidence that triggered it
    status TEXT DEFAULT 'pending',  -- pending, accepted, dismissed
    created_at TIMESTAMPTZ DEFAULT now(),
    responded_at TIMESTAMPTZ
);

-- Track repeated patterns
CREATE TABLE user_interaction_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    pattern_type TEXT NOT NULL,
    pattern_data JSONB NOT NULL,
    occurrence_count INTEGER DEFAULT 1,
    first_seen_at TIMESTAMPTZ DEFAULT now(),
    last_seen_at TIMESTAMPTZ DEFAULT now(),
    proposed_agent_id UUID REFERENCES agent_proposals(id),

    UNIQUE(user_id, pattern_type, pattern_data)
);
```

---

## Frontend Scaffolding Implications

### Type Selection Redesign

Replace flat type list with **binding-first selection**:

```
Step 1: What kind of agent?
┌─────────────────────────────────────────────────────────────┐
│ 📊 Platform Monitor                                         │
│    Stay on top of a specific platform                       │
│    Examples: Slack digest, Gmail triage, Notion changelog   │
├─────────────────────────────────────────────────────────────┤
│ 🔗 Cross-Platform Synthesis                                 │
│    Combine context from multiple sources                    │
│    Examples: Weekly status, Project brief, Meeting prep     │
├─────────────────────────────────────────────────────────────┤
│ 🔍 Research & Discovery                                     │
│    Build understanding through research                     │
│    Examples: Competitive analysis, Market landscape         │
├─────────────────────────────────────────────────────────────┤
│ ✨ Custom                                                    │
│    Describe what you need                                   │
└─────────────────────────────────────────────────────────────┘
```

### Platform-Bound Flow

```
Step 2 (Platform Monitor selected):

Which platform?
┌──────────┐  ┌──────────┐  ┌──────────┐
│  Slack   │  │  Gmail   │  │  Notion  │
│ 💬       │  │ 📧       │  │ 📝       │
└──────────┘  └──────────┘  └──────────┘

Step 3 (Slack selected):

What do you want to monitor?
┌─────────────────────────────────────────────────────────────┐
│ 📋 Channel Digest                                           │
│    "What happened while you were away"                      │
├─────────────────────────────────────────────────────────────┤
│ 📌 Decision Log                                             │
│    Track decisions made in your channels                    │
├─────────────────────────────────────────────────────────────┤
│ ❓ Unanswered Questions                                      │
│    Questions that need your attention                       │
└─────────────────────────────────────────────────────────────┘

Step 4: Select channels (respects limits from ADR-043)
```

### Emergent Agent UI

TP can propose agents inline:

```
┌─────────────────────────────────────────────────────────────┐
│ 💡 Agent Suggestion                                   │
├─────────────────────────────────────────────────────────────┤
│ I notice you often ask for Slack catch-ups on Mondays.      │
│                                                             │
│ Would you like me to automatically generate a weekly        │
│ digest of #engineering and #product every Monday at 8am?    │
│                                                             │
│ [Set this up]  [Customize]  [Not interested]                │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Type Classification Metadata
- [ ] Add `type_classification` JSONB to agents
- [ ] Define classification schema
- [ ] Backfill existing agents with inferred classification
- [ ] Update agent creation to capture classification

### Phase 2: Platform-Bound Type Refinement
- [ ] Implement platform-specific signal extraction (beyond ADR-030)
- [ ] Create dedicated generation prompts for each platform-bound type
- [ ] Add freshness checking to generation flow
- [ ] Platform-bound type selection in wizard

### Phase 3: Emergent Agent Discovery
- [ ] Track user interaction patterns in TP
- [ ] Implement pattern detection for proposal triggers
- [ ] Create proposal UI component
- [ ] TP behavior for suggesting agents

### Phase 4: Hybrid Composition
- [ ] Platform grounding configuration in wizard
- [ ] Generation prompt composition for hybrid types
- [ ] UI for adding platform grounding to research types

---

## Success Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| Agent adoption by type | Track distribution | Validates type usefulness |
| Emergent proposal acceptance | > 30% | Proposals are valuable |
| Freshness-related regenerations | < 10% | Freshness UX works |
| Platform-bound output quality | > 70% approval | Platform signals improve output |
| Time to first agent | < 3 min | Simplified flow |

---

## Open Questions

1. **Should emergent proposals be dismissable permanently?**
   - Leaning: Yes, with "Don't suggest this type again" option

2. **Can users create their own platform-bound types?**
   - Leaning: Not in v1, use custom type with platform grounding

3. **How do we handle platform types when platform disconnected?**
   - Agent becomes "stale" with reconnect prompt

---

## Related

- ADR-019: Agent Types System (superseded direction)
- ADR-031: Platform-Native Agents
- ADR-034: Emergent Context Domains
- ADR-043: Platform Settings Frontend
- DECISION-001: Platform Sync Strategy
