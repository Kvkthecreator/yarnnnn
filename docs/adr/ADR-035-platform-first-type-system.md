# ADR-035: Platform-First Deliverable Type System

> **Status**: Superseded by [ADR-082](ADR-082-deliverable-type-consolidation.md) — type system consolidated from 27 to 8 active types
> **Created**: 2025-02-09
> **Related**: ADR-019 (Deliverable Types), ADR-031 (Platform-Native Deliverables), ADR-032 (Platform-Native Frontend)

---

## Context

ADR-019 established a type system for deliverables (status_report, stakeholder_update, etc.) focused on **output format**. ADR-031 introduced platform-native deliverables focused on **platform semantics**. However, these remain conceptually separate:

- ADR-019 types are destination-agnostic (a "status report" is the same whether going to Slack or Email)
- ADR-031 archetypes are platform-specific but lack concrete implementation taxonomy

Users think in terms of **workflows**, not abstract types:
- "Summarize my Slack channels weekly" (not "create a status_report with slack_digest variant")
- "Draft my standup from yesterday's activity" (not "configure a meeting_summary")

We need a unified type system that:
1. Presents types as **platform-native workflows**
2. Maps to underlying generation infrastructure
3. Supports phased rollout by risk profile
4. Enables competitive differentiation

---

## Decision

Replace the current type selector with a **platform-first workflow taxonomy** organized by:
1. **Data flow direction** (pull vs push, internal vs external)
2. **Risk profile** (determines rollout wave)
3. **Platform specificity** (single-platform vs cross-platform)

### Type Taxonomy

#### Wave 1: Internal Single-Platform (Low Risk, High Value)

These types keep data within the same platform or deliver to the user themselves. Safe for aggressive automation.

| Type ID | Display Name | Flow | Trigger | Governance Ceiling |
|---------|--------------|------|---------|-------------------|
| `slack_channel_digest` | Channel Digest | Slack → Slack | Scheduled | full_auto |
| `slack_standup` | Daily Standup | Slack → Slack | Scheduled | full_auto |
| `gmail_inbox_brief` | Inbox Brief | Gmail → Gmail Draft | Scheduled | manual |
| `notion_page_summary` | Page Summary | Notion → Notion | Scheduled | full_auto |

#### Wave 2: Cross-Platform Internal (Medium Risk, Core Differentiator)

These types synthesize across platforms but stay internal. Draft mode required.

| Type ID | Display Name | Flow | Trigger | Governance Ceiling |
|---------|--------------|------|---------|-------------------|
| `weekly_status` | Weekly Status Update | Slack + Gmail → Gmail Draft | Scheduled | manual |
| `meeting_prep` | Meeting Prep Brief | Gmail + Slack → Gmail Draft | Scheduled | manual |
| `decision_log` | Decision Capture | Slack → Notion | Scheduled | semi_auto |
| `team_pulse` | Team Pulse | Slack → Slack/Email | Scheduled | semi_auto |

#### Wave 3: External-Facing (Higher Risk, Manual Only)

These types produce content for external audiences. Strict manual governance.

| Type ID | Display Name | Flow | Trigger | Governance Ceiling |
|---------|--------------|------|---------|-------------------|
| `stakeholder_brief` | Stakeholder Brief | Internal → Gmail Draft | Scheduled | manual |
| `client_update` | Client Update | Internal → Gmail Draft | Scheduled | manual |
| `project_changelog` | Project Changelog | Multi-source → Notion | Scheduled | manual |

---

## Type Definitions

### Wave 1 Types

#### `slack_channel_digest`

**Purpose**: Summarize activity from busy channel(s) to a quieter destination.

**Use Cases**:
- Engineering channel → Leadership channel (weekly)
- All-hands channel → Executive summary (daily)
- Support channel → Team digest (daily)

**Configuration**:
```typescript
interface SlackChannelDigestConfig {
  source_channels: string[];           // Channel IDs to monitor
  destination_channel: string;         // Where to post digest
  focus: 'highlights' | 'decisions' | 'questions' | 'all';
  include_threads: boolean;            // Expand thread replies
  mention_threshold: number;           // Min reactions/replies to highlight
  max_items: number;                   // Cap items in digest
}
```

**Extraction Signals** (ADR-030 enhancement):
- Thread depth (conversations worth highlighting)
- Reaction count (community signal)
- Unanswered questions (gaps to surface)
- Decision language ("we decided", "going with", "approved")

**Default Scope**:
- `recency_days`: 1 (daily) or 7 (weekly)
- `max_items`: 200
- `include_threads`: true

---

#### `slack_standup`

**Purpose**: Auto-generate standup from yesterday's Slack activity.

**Use Cases**:
- Personal standup draft from your messages
- Team standup compilation from team channel

**Configuration**:
```typescript
interface SlackStandupConfig {
  source_mode: 'personal' | 'team';
  source_channels?: string[];          // For team mode
  user_filter?: string;                // For personal: your Slack user ID
  format: 'bullet' | 'narrative';
  sections: {
    done: boolean;                     // What was accomplished
    doing: boolean;                    // What's in progress
    blockers: boolean;                 // What's blocking
  };
}
```

**Extraction Signals**:
- Completion language ("done", "shipped", "merged", "finished")
- Progress language ("working on", "in progress", "reviewing")
- Blocker language ("stuck on", "waiting for", "blocked by")

**Default Scope**:
- `recency_days`: 1
- `max_items`: 100

---

#### `gmail_inbox_brief`

**Purpose**: Daily triage of what needs attention in your inbox.

**Use Cases**:
- Morning briefing of overnight emails
- End-of-day summary of unread items
- Priority flagging for busy inboxes

**Configuration**:
```typescript
interface GmailInboxBriefConfig {
  source_labels: string[];             // Labels to scan (default: INBOX)
  include_sent: boolean;               // Include sent items for context
  priority_senders: string[];          // Always highlight these senders
  categorize_by: 'sender' | 'thread' | 'urgency';
  max_items: number;
}
```

**Extraction Signals**:
- Thread stalls (no reply in X days)
- Action language ("please", "can you", "need", "by [date]")
- Priority senders (VIPs defined by user)
- Unread count per thread

**Default Scope**:
- `recency_days`: 1
- `max_items`: 50
- `include_sent`: true

---

#### `notion_page_summary`

**Purpose**: Summarize child pages or database entries to parent.

**Use Cases**:
- Project page summarizing sub-tasks
- Meeting notes summarizing action items
- Documentation summarizing changes

**Configuration**:
```typescript
interface NotionPageSummaryConfig {
  source_page_id: string;              // Parent page to scan
  include_children: boolean;           // Summarize child pages
  include_databases: boolean;          // Summarize linked databases
  focus: 'changes' | 'status' | 'all';
  output_location: 'same_page' | 'new_page';
}
```

**Extraction Signals**:
- Recent edits (last modified)
- Status properties (if database)
- Completion properties (checkboxes, status)
- Comment threads

**Default Scope**:
- `max_depth`: 2
- `max_pages`: 10

---

### Wave 2 Types

#### `weekly_status`

**Purpose**: Cross-platform synthesis for weekly status updates.

**Use Cases**:
- IC weekly update to manager
- Team status to leadership
- Project status to stakeholders

**Configuration**:
```typescript
interface WeeklyStatusConfig {
  sources: {
    slack_channels?: string[];
    gmail_labels?: string[];
    notion_pages?: string[];
  };
  audience: 'manager' | 'leadership' | 'team' | 'stakeholders';
  sections: {
    summary: boolean;
    accomplishments: boolean;
    blockers: boolean;
    next_week: boolean;
    metrics?: boolean;
  };
  detail_level: 'brief' | 'standard' | 'detailed';
  destination: {
    platform: 'gmail' | 'slack' | 'notion';
    target: string;                    // Email address, channel, page
  };
}
```

**Extraction Signals**:
- Accomplishment language across platforms
- Meeting outcomes from Slack
- Email threads with external stakeholders
- Notion task completions

**Default Scope**:
- `recency_days`: 7
- `max_items`: 300 (across all sources)

---

#### `meeting_prep`

**Purpose**: Context brief before important meetings.

**Use Cases**:
- 1:1 prep with direct reports
- External meeting prep (client context)
- Interview prep (candidate research)

**Configuration**:
```typescript
interface MeetingPrepConfig {
  meeting_type: 'one_on_one' | 'external' | 'team' | 'interview';
  context_person?: string;             // Who the meeting is with
  sources: {
    slack_dms?: boolean;               // Recent DMs with this person
    slack_channels?: string[];         // Relevant channels
    gmail_threads?: string[];          // Email history
    notion_pages?: string[];           // Related docs
  };
  sections: {
    context_summary: boolean;          // Recent interactions
    topics_to_discuss: boolean;        // Suggested agenda
    open_items: boolean;               // Unresolved from last time
    talking_points: boolean;           // Prepared points
  };
}
```

**Extraction Signals**:
- Recent interactions with person
- Unresolved threads/questions
- Commitments made ("I'll", "will do", "action item")
- Sentiment signals

**Default Scope**:
- `recency_days`: 14 (for 1:1s), 30 (for quarterly)
- `max_items`: 100

---

#### `decision_log`

**Purpose**: Capture decisions from Slack to Notion knowledge base.

**Use Cases**:
- Engineering decisions → Architecture docs
- Product decisions → PRD updates
- Team agreements → Team wiki

**Configuration**:
```typescript
interface DecisionLogConfig {
  source_channels: string[];
  destination_database: string;        // Notion database ID
  decision_signals: string[];          // Custom decision phrases
  capture_context: boolean;            // Include surrounding discussion
  auto_categorize: boolean;            // AI categorization
}
```

**Extraction Signals**:
- Decision language ("decided", "agreed", "going with", "approved")
- Voting/polling outcomes
- Thread conclusions
- @mentions of decision-makers

**Default Scope**:
- `recency_days`: 7
- `max_items`: 50
- `include_threads`: true

---

#### `team_pulse`

**Purpose**: Synthesize team health signals from activity patterns.

**Use Cases**:
- Manager awareness of team morale
- Leadership team health dashboard
- Org-wide engagement signals

**Configuration**:
```typescript
interface TeamPulseConfig {
  source_channels: string[];
  team_members?: string[];             // Specific people to track
  signals: {
    activity_levels: boolean;          // Message volume trends
    response_times: boolean;           // How quickly people reply
    sentiment: boolean;                // Positive/negative language
    collaboration: boolean;            // Cross-person interactions
  };
  alert_thresholds?: {
    activity_drop_percent?: number;    // Alert if activity drops X%
    sentiment_threshold?: number;      // Alert if sentiment below X
  };
}
```

**Extraction Signals**:
- Message volume over time
- Response latency patterns
- Sentiment analysis
- Collaboration graphs

**Default Scope**:
- `recency_days`: 7
- Compare to previous period

---

### Wave 3 Types

#### `stakeholder_brief`

**Purpose**: Executive summary for investors, board, or advisors.

**Configuration**:
```typescript
interface StakeholderBriefConfig {
  audience_type: 'investor' | 'board' | 'advisor' | 'executive';
  sources: {
    slack_channels?: string[];
    notion_pages?: string[];
    gmail_labels?: string[];
  };
  sections: {
    executive_summary: boolean;
    highlights: boolean;
    challenges: boolean;
    metrics?: boolean;
    asks?: boolean;
  };
  sensitivity: 'confidential' | 'internal';
  formality: 'formal' | 'professional';
}
```

**Governance**: Always `manual` - must be reviewed before send.

---

#### `client_update`

**Purpose**: Professional updates to external clients.

**Configuration**:
```typescript
interface ClientUpdateConfig {
  client_name: string;
  project_context?: string;
  sources: {
    internal_channels?: string[];      // Internal discussion
    client_threads?: string[];         // Client email threads
    project_pages?: string[];          // Project documentation
  };
  sections: {
    progress_summary: boolean;
    deliverables_status: boolean;
    next_steps: boolean;
    blockers_needing_input: boolean;
  };
  tone: 'formal' | 'professional' | 'friendly';
}
```

**Governance**: Always `manual` - external audience.

---

#### `project_changelog`

**Purpose**: Track and communicate project progress across workstreams.

**Configuration**:
```typescript
interface ProjectChangelogConfig {
  project_name: string;
  sources: {
    slack_channels?: string[];
    notion_databases?: string[];       // Task/issue tracking
    github_repos?: string[];           // Code changes (future)
  };
  sections: {
    summary: boolean;
    completed: boolean;
    in_progress: boolean;
    upcoming: boolean;
    blockers: boolean;
  };
  audience: 'internal' | 'stakeholders' | 'public';
  format: 'narrative' | 'bullet' | 'changelog';
}
```

---

## UI Presentation

### Type Selection (Full-Screen Wizard Step 2)

Organize types by **workflow pattern**, not technical category:

```
┌─────────────────────────────────────────────────────────────────┐
│  What do you want YARNNN to create?                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 STAY INFORMED                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ 🔷 Channel      │  │ 📧 Inbox        │  │ 📝 Page         │ │
│  │    Digest       │  │    Brief        │  │    Summary      │ │
│  │                 │  │                 │  │                 │ │
│  │ Slack → Slack   │  │ Gmail → Draft   │  │ Notion → Notion │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  📝 COMMUNICATE UPDATES                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ 📋 Weekly       │  │ 🎯 Daily        │  │ 👥 Team         │ │
│  │    Status       │  │    Standup      │  │    Pulse        │ │
│  │                 │  │                 │  │                 │ │
│  │ Multi → Email   │  │ Slack → Slack   │  │ Slack → Slack   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  🧠 CAPTURE KNOWLEDGE                                           │
│  ┌─────────────────┐  ┌─────────────────┐                      │
│  │ 📌 Decision     │  │ 📖 Meeting      │  ┌─────────────────┐ │
│  │    Log          │  │    Prep         │  │ ✨ Custom       │ │
│  │                 │  │                 │  │                 │ │
│  │ Slack → Notion  │  │ Multi → Draft   │  │ Define your own │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  ──────────────────────────────────────────────────────────────│
│  🔒 EXTERNAL COMMUNICATIONS                     Coming Soon     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Stakeholder     │  │ Client          │  │ Project         │ │
│  │ Brief           │  │ Update          │  │ Changelog       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Type Card Details

Each type card shows:
- **Icon**: Platform-specific or workflow icon
- **Name**: User-friendly workflow name
- **Flow indicator**: Source → Destination platforms
- **Badge**: "New", "Popular", or "Coming Soon"

On hover/focus:
- **Description**: 1-2 sentence explanation
- **Example**: "Summarizes #engineering for #leadership-updates weekly"

---

## Backend Integration

### Type Registry

```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel

class DeliverableTypeWave(str, Enum):
    WAVE_1 = "wave_1"  # Internal single-platform
    WAVE_2 = "wave_2"  # Cross-platform internal
    WAVE_3 = "wave_3"  # External-facing

class GovernanceCeiling(str, Enum):
    FULL_AUTO = "full_auto"
    SEMI_AUTO = "semi_auto"
    MANUAL = "manual"

class TypeDefinition(BaseModel):
    id: str
    display_name: str
    description: str
    wave: DeliverableTypeWave
    source_platforms: list[str]
    destination_platforms: list[str]
    governance_ceiling: GovernanceCeiling
    default_scope: dict
    extraction_signals: list[str]
    config_schema: dict  # JSON Schema for type-specific config
    prompt_template: str
    enabled: bool = True

TYPE_REGISTRY: dict[str, TypeDefinition] = {
    "slack_channel_digest": TypeDefinition(
        id="slack_channel_digest",
        display_name="Channel Digest",
        description="Summarize busy Slack channels to a quieter destination",
        wave=DeliverableTypeWave.WAVE_1,
        source_platforms=["slack"],
        destination_platforms=["slack"],
        governance_ceiling=GovernanceCeiling.FULL_AUTO,
        default_scope={"recency_days": 7, "max_items": 200, "include_threads": True},
        extraction_signals=["thread_depth", "reactions", "decisions", "questions"],
        config_schema={...},
        prompt_template="slack_channel_digest_v1",
    ),
    # ... other types
}
```

### Prompt Templates

Each type has a dedicated prompt template with platform-specific instructions:

```python
PROMPT_TEMPLATES = {
    "slack_channel_digest_v1": """
You are creating a Slack channel digest for {destination_channel}.

SOURCE CHANNELS: {source_channels}
TIME PERIOD: Last {recency_days} days
FOCUS: {focus}

PLATFORM SIGNALS TO PRIORITIZE:
- Threads with {mention_threshold}+ replies or reactions (high engagement)
- Unanswered questions (gaps worth surfacing)
- Decision language ("we decided", "agreed", "going with")
- @mentions of key stakeholders

EXTRACTED CONTENT:
{extracted_context}

USER MEMORIES (persistent context):
{user_memories}

FORMAT: Slack message blocks (mrkdwn)
- Use bullet points for highlights
- Bold key decisions
- Link to original threads where relevant
- Keep total length under 2000 characters

Generate the digest now:
""",

    "weekly_status_v1": """
You are creating a weekly status update for {audience}.

SOURCES:
- Slack: {slack_summary}
- Gmail: {gmail_summary}
- Notion: {notion_summary}

TIME PERIOD: {start_date} to {end_date}

SECTIONS TO INCLUDE:
{sections_list}

DETAIL LEVEL: {detail_level}

USER'S COMMUNICATION STYLE:
{style_profile}

FORMAT: {output_format}

Generate the status update now:
""",
}
```

---

## Migration Path

### From ADR-019 Types

| Old Type | New Type | Migration |
|----------|----------|-----------|
| `status_report` | `weekly_status` | Map config, preserve sources |
| `meeting_summary` | `meeting_prep` or `slack_standup` | Based on config |
| `stakeholder_update` | `stakeholder_brief` | Direct mapping |
| `research_brief` | `custom` (for now) | Keep as custom |
| `custom` | `custom` | No change |

### Database Changes

```sql
-- Add wave tracking to deliverables
ALTER TABLE deliverables ADD COLUMN type_wave TEXT;

-- Add enabled flag for feature gating
ALTER TABLE deliverables ADD COLUMN type_enabled BOOLEAN DEFAULT true;

-- Index for wave-based queries
CREATE INDEX idx_deliverables_wave ON deliverables(type_wave);
```

---

## Rollout Strategy

### Phase 1: Wave 1 Types (Week 1-2)
1. Implement type registry with Wave 1 types
2. Build full-screen wizard with type selection
3. Create prompt templates for Wave 1
4. Ship with Wave 2/3 shown as "Coming Soon"

### Phase 2: Wave 2 Types (Week 3-4)
1. Enable `weekly_status` and `meeting_prep`
2. Add cross-platform source selection UI
3. Implement synthesis prompts
4. Monitor adoption and quality

### Phase 3: Wave 3 Types (Week 5+)
1. Enable external-facing types
2. Add governance warnings
3. Implement approval workflows if needed

---

## Success Metrics

| Metric | Wave 1 Target | Wave 2 Target |
|--------|---------------|---------------|
| Type selection rate (vs Custom) | 70%+ | 80%+ |
| First-run acceptance | 50%+ | 60%+ |
| Weekly active deliverables | +30% | +50% |
| User-reported time savings | 2+ hrs/week | 4+ hrs/week |

---

## Relationship to Prior ADRs

### ADR-019 (Deliverable Types)
- **Supersedes** the generic type system
- Preserves `custom` as escape hatch
- Migration path for existing deliverables

### ADR-031 (Platform-Native Deliverables)
- **Implements** the archetype vision
- Concrete type definitions for each archetype
- Extraction signals from ADR-030 enhanced

### ADR-032 (Platform-Native Frontend)
- **Aligns** wizard with platform-first UX
- Full-screen surface for type selection
- Platform context panel integration

---

## Open Questions

1. **Should Custom require explicit unlock?**
   - Option A: Always available but de-emphasized
   - Option B: Unlock after creating 2+ typed deliverables
   - Recommendation: Option A initially, measure usage

2. **How to handle type changes?**
   - Recommendation: Allow change, clear type-specific config, preserve sources/schedule

3. **Should Wave 2/3 be visible before enabled?**
   - Recommendation: Yes, "Coming Soon" creates anticipation and signals roadmap

---

## References

- [ADR-019: Deliverable Types System](./ADR-019-deliverable-types.md)
- [ADR-031: Platform-Native Deliverables](./ADR-031-platform-native-deliverables.md)
- [ADR-032: Platform-Native Frontend Architecture](./ADR-032-platform-native-frontend-architecture.md)
- [ADR-030: Context Extraction Methodology](./ADR-030-context-extraction-methodology.md)
