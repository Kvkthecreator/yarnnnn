# Analysis: Agent-Scoped Context

> **Status**: Exploration
> **Created**: 2026-02-06
> **Related**: ADR-005 (Unified Context), ADR-018 (Agent Pipeline), ADR-027 (Integration Reads)

---

## The Gap

YARNNN's current memory architecture has two scopes:

| Scope | Storage | Examples |
|-------|---------|----------|
| **User-scoped** | `project_id = NULL` | Style profiles, preferences, portable facts |
| **Project-scoped** | `project_id = uuid` | Project decisions, requirements, stakeholders |

**What's missing**: Context that accumulates *per agent* across versions.

---

## The Problem

A agent like "Weekly Status Report for Sarah" generates versions over time:

```
Version 1 → User edits heavily (adds more technical detail)
Version 2 → User edits moderately (still too formal)
Version 3 → User approves with minor tweaks
Version 4 → User approves as-is
```

**Where do these learnings live?**

Currently:
- Edit patterns are computed and stored in `agent_runs` (edit_distance_score, edit_categories)
- Feedback is stored as memories with `source_type='agent_feedback'`

**But**:
- These are scattered across tables
- No unified "what I've learned about *this specific agent*" context
- Each version re-discovers patterns that should persist

---

## What Agent-Scoped Context Would Contain

### 1. Learned Preferences (from feedback loop)

```
- "Sarah prefers bullet points over paragraphs"
- "Include explicit next steps section"
- "Technical detail level: high (v1 feedback)"
- "Don't use 'synergy' or 'leverage' (v2 deletion pattern)"
```

### 2. Accumulated Research

For a research brief agent:
```
- Prior findings that remain relevant
- Sources that proved valuable
- Topics already covered (avoid repetition)
- Emerging themes across versions
```

### 3. Recipient Model

Beyond static `recipient_context`:
```
- "Sarah responds well to data visualizations" (inferred from approvals)
- "Questions she's asked before" (from TP interactions about this agent)
- "Her current priorities" (may change over time)
```

### 4. Version Intelligence

```
- "Last version covered Q1 roadmap—this version should cover Q2"
- "Previous version was too long (1200 words → edited to 600)"
- "Format that worked: executive summary + details section"
```

---

## How This Differs from Existing Scopes

| Scope | Persistence | Portability | Example |
|-------|-------------|-------------|---------|
| **User** | Permanent | All projects | "I write casually on Slack" |
| **Project** | Project lifetime | Within project | "We use PostgreSQL" |
| **Agent** | Agent lifetime | Within agent | "Sarah likes bullets" |

**Key insight**: Agent context is *more specific* than project context but *more persistent* than a single version.

---

## Current State vs. Proposed

### Current Architecture

```
memories table
├── user_id (required)
├── project_id (nullable) → NULL = user-scoped, UUID = project-scoped
└── No agent_id

agent_runs table
├── Stores edit_distance_score, edit_categories
├── Stores feedback_notes
└── But these are per-version, not accumulated
```

### Potential Approaches

#### Option A: Add `agent_id` to memories

```sql
ALTER TABLE memories ADD COLUMN agent_id UUID REFERENCES agents(id);

-- Agent-scoped memories
INSERT INTO memories (user_id, project_id, agent_id, content, source_type, ...)
VALUES ('user', 'project', 'agent', 'Sarah prefers bullets', 'agent_learning', ...);
```

**Pros**: Extends existing architecture naturally
**Cons**: Adds third dimension to scope logic

#### Option B: Separate `agent_context` table

```sql
CREATE TABLE agent_context (
    id UUID PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES agents(id),
    context_type TEXT NOT NULL,  -- 'preference', 'research', 'recipient_model'
    content TEXT NOT NULL,
    confidence FLOAT,
    source_version_id UUID,  -- Which version taught us this
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

**Pros**: Clean separation, specific to agents
**Cons**: New table, new query patterns, doesn't inherit embedding search

#### Option C: Structured field on agents table

```sql
ALTER TABLE agents ADD COLUMN learned_context JSONB DEFAULT '{}';

-- Updated after each version approval
UPDATE agents SET learned_context = learned_context || '{"preferences": [...], "research": [...]}' WHERE id = ...;
```

**Pros**: Simple, no new table
**Cons**: No versioning, no embedding search, limited query flexibility

---

## Relationship to Feedback Loop

ADR-018 established the feedback loop:

```
User edits draft → Diff computed → Edit categories extracted → Stored
```

**Current storage**: `agent_runs.edit_categories` (per-version)

**Gap**: No *accumulation* across versions into persistent agent context.

### Proposed Enhancement

After version approval:
1. Compute diff (existing)
2. Extract edit categories (existing)
3. **NEW**: Run "preference extraction" agent
4. **NEW**: Store extracted preferences as agent-scoped context
5. Next version loads this context into agent prompt

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ENHANCED FEEDBACK LOOP                           │
└─────────────────────────────────────────────────────────────────────┘

User approves version (with edits)
        │
        ▼
┌───────────────────┐
│ Compute diff      │ ← Existing
│ Extract categories│
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Preference        │ ← NEW
│ Extraction Agent  │
│                   │
│ "What did we learn│
│  from these edits?│
│  What should we   │
│  remember for     │
│  next version?"   │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Store as          │ ← NEW
│ agent-scoped│
│ memory            │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Next generation   │
│ loads this context│
│ into prompt       │
└───────────────────┘
```

---

## Questions to Resolve

### 1. Scope Boundaries

If I learn "Sarah prefers bullets" from the status report agent, should this apply to:
- Only that agent? (strict agent scope)
- All agents for Sarah? (recipient scope)
- All status reports? (type scope)

**Hypothesis**: Start with strict agent scope. Let patterns emerge before generalizing.

### 2. Context Accumulation Strategy

How do we prevent unbounded growth?
- Cap at N learnings per agent?
- Decay old learnings?
- Agent summarizes/consolidates periodically?

### 3. Conflict Resolution

If agent context says "brief" but user style says "detailed", which wins?
- Agent context should override (more specific)
- Need clear hierarchy in prompt construction

### 4. Ad Hoc vs. Recurring

For one-off (ad hoc) agents, is agent-scoped context relevant?
- Less so—no version history to learn from
- Maybe still useful for multi-step workflows (gather → synthesize → refine)

---

## Connection to ADR-028 (Destination-First)

If agents become destination-first (see ADR-028), agent-scoped context gains new dimensions:

| Current Model | Destination-First Model |
|---------------|------------------------|
| "Sarah prefers bullets" | "Sarah-via-Slack prefers bullets" |
| "Include next steps" | "Slack posts should have threaded details" |
| N/A | "This channel expects Monday morning posts" |

**Insight**: Destination becomes part of the agent identity, and context accumulates per destination-agent pair.

---

## Recommendation

### Phase 1: Validate Need

Before building:
1. Track how often users make similar edits across versions
2. Identify if edit patterns persist or vary randomly
3. Check if users ask TP "remember this for next time"

### Phase 2: Simple Implementation

If validated:
1. Use Option A (add `agent_id` to memories)
2. Create "preference extraction" agent post-approval
3. Load agent-scoped memories in pipeline's context loading

### Phase 3: Sophistication

If working:
1. Add recipient-level rollup (learnings that apply to all agents for this recipient)
2. Add type-level rollup (learnings that apply to all status reports)
3. Add conflict resolution rules

---

## Open Questions for Future Work

1. How does this interact with "sources" configuration on agents?
2. Should agent context be visible/editable by users?
3. How to handle agent archival (delete context? preserve for analytics?)
4. Does this need its own embedding for semantic retrieval, or is keyword matching sufficient?

---

## References

- [ADR-005: Unified Context Model](../adr/ADR-005-unified-context-model.md)
- [ADR-018: Agent Pipeline](../adr/ADR-018-agent-pipeline.md)
- [ADR-027: Integration Read Architecture](../adr/ADR-027-integration-read-architecture.md)
- [ADR-028: Destination-First Agents](../adr/ADR-028-destination-first-agents.md)
