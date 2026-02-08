# ADR-031: Platform-Native Deliverable Architecture

> **Status**: Accepted
> **Created**: 2026-02-08
> **Updated**: 2026-02-08 (Decisions hardened from discourse)
> **Related**: ADR-028 (Destination-First), ADR-019 (Deliverable Types), ADR-030 (Context Extraction)
> **Analysis**: [platform-native-deliverables.md](../analysis/platform-native-deliverables.md)

---

## Context

YARNNN's current deliverable model treats platforms (Slack, Notion, Gmail) as:
1. **Input sources**: Places to extract context from
2. **Output destinations**: Places to export content to

This architecture is platform-agnostic by design—a status report is generated as markdown and converted for export. However, through building integration reads (ADR-027, ADR-030), a limitation emerged:

**The deliverable doesn't understand the platform it's interacting with.**

This manifests as:
- Generic outputs that don't feel native to their destination
- No event-driven triggers (only schedules)
- No write-back or response capabilities
- No platform-specific style application

---

## Decision

Evolve the deliverable model to be **platform-native**: deliverables that understand, respond to, and produce content native to their source and destination platforms.

### Core Principles

1. **Unified context, platform-aware output**: Keep the shared memory pool, but generate content shaped for destination platform
2. **Platforms inform reasoning, not just formatting**: Radical interpretation—platforms inform *what's worth saying*
3. **Event + schedule triggers**: Support platform events as triggers, not just cron schedules
4. **Native format generation**: Generate directly for platform formats, not markdown-then-convert
5. **Bidirectional flow**: Read from platforms, write to platforms, observe outcomes
6. **Ephemeral + persistent context**: Separate temporal platform data from long-term memory

---

## Key Decisions

### 1. Platform as Semantic Participant (Radical Interpretation)

**Decision**: Platforms inform *what's worth saying*, not just *how to say it*.

This means:
- **Slack digests** surface hot threads (high reply count), unanswered questions, decisions waiting
- **Gmail triage** identifies urgent senders, thread stalls, buried action items
- **Notion changelog** tracks meaningful edits (not typos), new sections, unresolved comments

Extraction prompts (ADR-030) should capture platform-specific signals, not just content.

### 2. Archetype Granularity (Hybrid)

**Decision**: Use hybrid approach for deliverable types.

**New types** for conceptually-distinct archetypes:
```python
deliverable_type: "slack_auto_reply" | "gmail_triage" | "slack_thread_synthesizer"
```

**Variants** for platform-specific versions of existing types:
```python
deliverable_type: "status_report"
platform_variant: "slack_digest"
```

### 3. Ephemeral Context Storage (Dedicated Table)

**Decision**: Use dedicated `ephemeral_context` table for time-bounded data.

- **General-purpose temporal layer**: Defined by lifespan, not by source
- Separate from `user_memories` table
- TTL-based cleanup
- Preserves source provenance and temporal attribution
- Prevents pollution of long-term memory

**Source categories** (not limited to platforms):
- Platform imports (Slack, Gmail, Notion)
- Calendar/schedule events
- Session context
- Time-bounded user notes
- Recent deliverable outputs

### 4. Implementation Sequence (Slack First, Vertical)

**Decision**: Go deep on Slack before expanding horizontally.

First archetype: **Slack Digest** (scheduled, read-only, low risk)
- Proves platform-native generation
- No event trigger infrastructure needed
- Validates the model before higher-risk archetypes

### 5. Deliverable-Specific Scoping

**Decision**: Each archetype has one primary trigger type and scoped targets.

| Archetype | Scope | Trigger | Max Governance |
|-----------|-------|---------|----------------|
| Slack Digest | Channel(s) | Scheduled | Full-auto |
| Slack Auto-Reply | Single channel/DMs | Event | Semi-auto (internal) |
| Gmail Triage | Label/search | Scheduled | Manual |
| Email Drafter | Thread/sender | Event | Manual |
| Notion Changelog | Page/database | Scheduled or Event | Full-auto |

### 6. Governance Ceilings

**Decision**: Governance has destination-derived ceilings.

```python
effective_governance = min(user_configured, destination_ceiling)
```

| Destination | Ceiling |
|-------------|---------|
| Internal Slack | full_auto |
| External Slack | semi_auto |
| Email to external | manual |
| Notion (internal) | full_auto |

---

## Architecture

### 1. Platform-Variant Deliverable Types

```python
class DeliverableTypeConfig(BaseModel):
    type: DeliverableType  # status_report, slack_auto_reply, etc.
    platform_variant: Optional[Literal["slack_digest", "email_summary", ...]] = None
    config: dict  # Type-specific config
```

When `platform_variant` is set:
- Generation prompt adjusts for platform idioms
- Output format is platform-native (Slack blocks, Notion blocks, email structure)
- Style profile for that platform is applied

### 2. Archetype-Specific Triggers

```python
# Scheduled archetype (Slack Digest)
class ScheduledTrigger(BaseModel):
    type: Literal["schedule"] = "schedule"
    schedule: ScheduleConfig  # daily, weekly, etc.
    skip_if: Optional[SkipCondition] = None  # e.g., message_count_below: 10

# Event archetype (Slack Auto-Reply)
class EventTrigger(BaseModel):
    type: Literal["event"] = "event"
    platform: Literal["slack", "gmail", "notion"]
    event_type: str  # mention_or_dm, unread_threshold, page_modified
    scope: dict  # channel_id, label, page_id
    cooldown: Optional[CooldownConfig] = None
```

### 3. Two-Tier Context Model

The context model separates data by **lifespan**, not by source. Ephemeral context is a general-purpose temporal layer; platform imports are one source category within it.

```python
class DeliverableContext(BaseModel):
    """Context assembled for deliverable generation"""

    # Time-bounded, source-attributed (TTL-based cleanup)
    # Sources: platform imports, calendar, session, time-bounded notes
    ephemeral: list[EphemeralContextItem]

    # Long-term user knowledge (no expiration)
    # Sources: user memories, promoted ephemeral, document extractions
    persistent: list[UserMemory]

    # Deliverable-specific learnings
    deliverable_learnings: list[DeliverableLearning]
```

### 4. Platform-Native Output

```python
class PlatformOutput(BaseModel):
    platform: str
    format_type: str  # blocks, email, page
    content: dict  # Platform-specific structure

    # Slack: {"blocks": [...], "thread_ts": "..."}
    # Gmail: {"subject": "...", "body": "...", "to": [...]}
    # Notion: {"title": "...", "blocks": [...]}
```

---

## Schema Changes

### Phase 1: Ephemeral Context & Platform Variants

```sql
-- Ephemeral context: general-purpose temporal data with TTL
-- Note: "platform" column is really "source_type" - includes non-platform sources
-- like "calendar", "session", "user_note" in addition to "slack", "gmail", "notion"
CREATE TABLE ephemeral_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,  -- Source type: slack, gmail, notion, calendar, session, user_note
    resource_id TEXT NOT NULL,  -- channel_id, label, page_id, event_id, session_id
    resource_name TEXT,
    content TEXT NOT NULL,
    content_type TEXT,  -- message, thread_summary, page_update, event, note
    platform_metadata JSONB,  -- Source-specific metadata (thread_ts, reactions, etc.)
    source_timestamp TIMESTAMPTZ,  -- When it happened at source
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,  -- TTL for cleanup

    -- Indexes for efficient querying
    INDEX idx_ephemeral_user_platform (user_id, platform),
    INDEX idx_ephemeral_expires (expires_at)
);

-- Platform style profiles
CREATE TABLE user_platform_styles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    style_profile JSONB NOT NULL,
    learned_from_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, platform)
);

-- Add platform_variant to deliverables
ALTER TABLE deliverables ADD COLUMN platform_variant TEXT;

-- Add governance_ceiling (system-enforced max)
ALTER TABLE deliverables ADD COLUMN governance_ceiling TEXT;
```

### Phase 2: Archetype-Specific Triggers

```sql
-- Archetype triggers (replaces generic schedule for some types)
CREATE TABLE deliverable_triggers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deliverable_id UUID REFERENCES deliverables(id) ON DELETE CASCADE,
    trigger_type TEXT NOT NULL,  -- 'schedule', 'event'
    platform TEXT,  -- NULL for schedule, 'slack'/'gmail'/'notion' for events
    event_config JSONB,  -- Event-specific: scope, thresholds, cooldowns
    skip_conditions JSONB,  -- When to skip even if triggered
    enabled BOOLEAN DEFAULT true,
    last_fired_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Trigger execution log
CREATE TABLE trigger_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger_id UUID REFERENCES deliverable_triggers(id),
    fired_at TIMESTAMPTZ DEFAULT now(),
    trigger_reason JSONB,  -- What condition was met
    skipped BOOLEAN DEFAULT false,
    skip_reason TEXT,
    version_id UUID REFERENCES deliverable_versions(id)
);
```

### Phase 3: Observe Loop

```sql
-- Export outcomes for feedback loop
ALTER TABLE export_log ADD COLUMN platform_metadata JSONB;  -- message_ts, etc.
ALTER TABLE export_log ADD COLUMN outcome JSONB;  -- reactions, replies, corrections
ALTER TABLE export_log ADD COLUMN outcome_observed_at TIMESTAMPTZ;
```

---

## Deliverable Archetypes

### Tier 1: Platform Monitors (Phase 2)

| Archetype | Type | Trigger | Governance Ceiling |
|-----------|------|---------|-------------------|
| **Slack Digest** | `status_report` variant | Scheduled | Full-auto |
| **Gmail Triage** | `gmail_triage` (new) | Scheduled | Manual |
| **Notion Changelog** | `notion_changelog` (new) | Scheduled/Event | Full-auto |

### Tier 2: Platform Responders (Phase 4+)

| Archetype | Type | Trigger | Governance Ceiling |
|-----------|------|---------|-------------------|
| **Slack Auto-Reply** | `slack_auto_reply` (new) | Event | Semi-auto (internal) |
| **Email Drafter** | `gmail_triage` variant | Event | Manual |

### Tier 3: Cross-Platform Synthesizers (Phase 6)

| Archetype | Type | Sources | Output |
|-----------|------|---------|--------|
| **Weekly Status** | `status_report` | Slack + Notion + Calendar | Multi-destination |
| **Project Brief** | `research_brief` variant | All platforms | Notion + Slack |

---

## Implementation Phases

### Phase 0: Foundation (Current) ✅
- Context extraction works (ADR-030)
- Destination-first deliverables work (ADR-028)
- Platform source visibility in UI

### Phase 1: Platform-Semantic Extraction
- Extend extraction prompts for platform-specific signals
- Add platform metadata to extractions (thread depth, reactions, etc.)
- Create `ephemeral_context` table
- **Deliverable**: Richer extracted context

### Phase 2: Slack Digest Archetype
- Implement Slack Digest as `status_report` with `platform_variant: "slack_digest"`
- Scheduled trigger with skip conditions
- Native Slack block output generation
- **Deliverable**: First working platform-native archetype

### Phase 3: Temporal Context Integration
- Generation pulls ephemeral + persistent context
- TTL-based cleanup job for ephemeral entries
- Platform provenance in generation prompts
- **Deliverable**: Digests feel "fresh"

### Phase 4: Event Trigger Infrastructure
- Polling service for platform activity
- Trigger evaluation and firing
- Cooldown enforcement
- **Deliverable**: Event-triggered archetypes possible

### Phase 5: Gmail Archetypes
- Gmail Triage (scheduled)
- Email Drafter (event-triggered, manual only)
- **Deliverable**: Gmail workflow value

### Phase 6: Cross-Platform Synthesizers
- Multi-source context assembly
- Project-to-resource mapping
- Multi-destination output
- **Deliverable**: Holy grail synthesis

---

## Trade-offs

### Benefits

1. **Higher quality outputs**: Platform-native content feels natural
2. **Reduced user effort**: Event triggers catch situations worth responding to
3. **Learning flywheel**: Observation loop improves over time
4. **Competitive differentiation**: Deep platform integration vs. generic AI writing
5. **Predictable behavior**: Archetype-specific triggers, not generic event handling

### Risks

1. **Complexity increase**: Each platform is its own integration surface
2. **Event trigger noise**: Too many triggers could overwhelm (mitigated by archetype scoping)
3. **Write-back risk**: Auto-posting requires trust (mitigated by governance ceilings)
4. **Platform API dependency**: Changes to Slack/Gmail/Notion APIs affect us

### Mitigations

1. **Vertical implementation**: Prove Slack before expanding
2. **Archetype scoping**: Specific triggers, not generic event handling
3. **Governance ceilings**: System-enforced limits on automation
4. **Abstraction layer**: Platform interactions through adapter pattern

---

## Relationship to Prior ADRs

### ADR-028 (Destination-First)

This ADR **extends** ADR-028:
- Destination informs generation, not just export
- Governance ceilings derived from destination characteristics
- Event triggers complement schedule triggers

### ADR-030 (Context Extraction)

This ADR **builds on** ADR-030:
- Extraction enhanced for platform-specific signals
- Source metadata enables platform-aware generation
- Ephemeral context layer for temporal data

### ADR-019 (Deliverable Types)

This ADR **extends** ADR-019:
- New types for conceptually-distinct archetypes
- Variants for platform-specific versions of existing types
- Type-specific trigger and governance defaults

---

## Success Metrics

| Metric | Phase 2 Target | Phase 4 Target |
|--------|----------------|----------------|
| Platform fit score | 70%+ | 85%+ |
| Style match rate | 60%+ | 75%+ |
| Event trigger adoption | N/A | 30%+ |
| User time per deliverable | -20% | -50% |

---

## Conclusion

Platform-native deliverables represent a significant evolution of YARNNN's value proposition—from "AI that writes content" to "AI that understands and participates in your workflow across platforms."

Key decisions:
1. **Radical interpretation**: Platforms inform reasoning, not just formatting
2. **Hybrid typing**: New types + variants preserve existing system
3. **Ephemeral storage**: Dedicated table for temporal context
4. **Slack first**: Vertical implementation to prove model
5. **Archetype scoping**: Specific triggers, predictable behavior
6. **Governance ceilings**: User control preserved

---

## References

- [Analysis: Platform-Native Deliverables](../analysis/platform-native-deliverables.md)
- [ADR-028: Destination-First Deliverables](./ADR-028-destination-first-deliverables.md)
- [ADR-019: Deliverable Types System](./ADR-019-deliverable-types.md)
- [ADR-030: Context Extraction Methodology](./ADR-030-context-extraction-methodology.md)
- [Integration-First Onboarding](../design/INTEGRATION_FIRST_ONBOARDING.md)
