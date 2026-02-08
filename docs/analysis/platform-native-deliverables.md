# Platform-Native Deliverables: A Conceptual Analysis

> **Status**: Refined
> **Date**: 2026-02-08
> **Updated**: 2026-02-08 (Decisions hardened from discourse)
> **Related**: ADR-028 (Destination-First), ADR-019 (Deliverable Types), ADR-030 (Context Extraction)

---

## Executive Summary

This analysis explores the evolution of YARNNN's deliverable model from **generic task execution** to **platform-native automation**. The core insight: deliverables that are deeply aware of their source platforms (Slack, Notion, Gmail) can deliver fundamentally more value than platform-agnostic content generation.

**Key Decision**: YARNNN will pursue the **radical interpretation** of platform awareness—platforms inform *what's worth saying*, not just how to say it. This means understanding platform-specific signals (hot threads, unanswered questions, urgent senders) as first-class inputs to deliverable generation.

---

## The Tension Identified

### Current State: Platform-Agnostic Deliverables

The existing deliverable types (status report, stakeholder update, research brief, etc.) are **platform-agnostic**:

```
User Input → AI Processing → Content Output → (Optional) Platform Export
```

This design was intentional—it maximizes flexibility. A "status report" can be exported to Slack, Notion, email, or downloaded. The deliverable doesn't care where it goes.

### The Observed Gap

Through building integration reads (ADR-027) and context extraction (ADR-030), a pattern emerged:

1. **Context is platform-specific**: Slack discussions have a different texture than Notion documents or email threads
2. **User mental models are platform-linked**: "The project status is in Slack" or "The decisions are in Notion"
3. **Outputs want to be platform-native**: A Slack thread summary should feel like a Slack message, not a generic markdown document

The current model treats platforms as **plumbing** (input sources, output destinations) rather than **semantic participants** in the deliverable workflow.

---

## Decision: Platform as Semantic Participant

We chose the **radical interpretation** over the conservative one:

| Approach | Description | Decision |
|----------|-------------|----------|
| **Conservative** | Platforms inform *format and style* only | ❌ Leaves value on the table |
| **Radical** | Platforms inform *what's worth saying* | ✅ Chosen |

This means:
- **Slack digests** surface hot threads (high reply count), unanswered questions (messages ending in `?` with no replies), decisions waiting (@mentions without resolution)
- **Gmail triage** identifies urgent senders (based on response time patterns), thread stalls (awaiting response for N days), action items buried in threads
- **Notion changelog** tracks meaningful edits (not just typos), new sections, unresolved comments

The LLM already has this capability—we structure the extraction prompts and platform data to enable it.

**Implementation implication**: Extraction prompts (ADR-030) should capture platform-specific signals, not just content. We may need to extend block types or add platform-specific metadata.

---

## Two-Layer Context Model

### Layer 1: Unified Context Pool (Keep This)

All extracted context flows into a shared memory pool:
- User memories are platform-agnostic after extraction
- Cross-platform synthesis is possible ("connect the Notion doc to the Slack discussion")
- Deduplication and conflict resolution happens in one place

**This remains.** The user's knowledge isn't siloed by platform—their understanding of a project spans tools.

### Layer 2: Platform-Aware Deliverables (The Evolution)

This is where the current design is **flat**. Deliverables should be:

| Dimension | Current (Generic) | Evolved (Platform-Native) |
|-----------|-------------------|---------------------------|
| **Trigger** | Schedule-based | Event-driven from platforms |
| **Context** | Pull from any source | Platform-specific patterns |
| **Output** | Markdown content | Native platform formats |
| **Style** | Inferred from destination | Learned from platform usage |
| **Actions** | Export button | Write-back to platform |

---

## Two-Tier Context for Generation

To avoid muddling long-term memory with temporal platform data, deliverable generation uses two context tiers:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Deliverable Context                         │
│                                                                 │
│  ┌─────────────────────────────────────┐                       │
│  │  Ephemeral Context (Temporal)       │                       │
│  │  - Last N days from sources         │                       │
│  │  - Platform provenance preserved    │                       │
│  │  - Stored in ephemeral_context table│                       │
│  │  - Used for "what happened recently"│                       │
│  └─────────────────────────────────────┘                       │
│                        +                                        │
│  ┌─────────────────────────────────────┐                       │
│  │  Persistent Context (Memory)        │                       │
│  │  - User memories (preferences, facts)│                      │
│  │  - Deliverable-scoped learnings     │                       │
│  │  - Used for "what I always know"    │                       │
│  └─────────────────────────────────────┘                       │
│                        ↓                                        │
│  ┌─────────────────────────────────────┐                       │
│  │  Generation                          │                       │
│  └─────────────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

**Key distinction**:
- **Ephemeral context**: Stored separately, time-bounded, platform-attributed, cleaned up after TTL
- **Persistent context**: The current memory system, plus per-deliverable accumulated learnings

**Decision**: Use dedicated `ephemeral_context` table (Option 2), not fetch-fresh or mixed storage.

---

## Conceptual Framework: The Workday Graph

Consider how a professional's day actually flows:

```
Morning: Check Slack → catch up on team discussions
         Read email → external stakeholder updates
         Skim Notion → project doc changes

Midday:  Slack DM → quick sync with designer
         Update Notion → capture decision from call
         Draft email → reply to client

Evening: Review Slack threads → what did I miss?
         Write status update → synthesize the day
```

The user's work **graph** spans platforms. But each platform has:
- **Native interaction patterns** (thread replies, page comments, email threading)
- **Information density** (Slack is ephemeral, Notion is persistent)
- **Relationship context** (Slack = internal team, Email = external stakeholders)

A platform-native deliverable understands this graph, not just the content.

---

## Deliverable-Specific Scoping

**Key insight**: Deliverables should be specific enough that trigger behavior is predictable.

Instead of broad "Slack automation", each archetype has:
1. **Scoped target**: Specific channel, label, page (not "all of Slack")
2. **Trigger type**: Event-based OR scheduled (rarely both)
3. **Governance ceiling**: Maximum autonomy level allowed for this archetype

| Archetype | Scope | Trigger Type | Max Governance |
|-----------|-------|--------------|----------------|
| Slack Auto-Reply | Single channel or DMs | Event (mention/DM) | Semi-auto (internal), Manual (external) |
| Slack Digest | Channel or set of channels | Scheduled | Full-auto (it's just a summary) |
| Gmail Triage | Label or search | Scheduled | Manual (drafts only) |
| Email Drafter | Specific thread or sender | Event (new email) | Manual |
| Notion Changelog | Single page or database | Event (modification) or Scheduled | Full-auto |

This gives us:
- **Batching**: Event-triggered deliverables are batched by their scope, not globally
- **Thresholds**: Defined per-archetype (e.g., Slack digest only fires if >10 messages)
- **Cooldowns**: Per-deliverable, not per-platform

---

## Evolved Deliverable Archetypes

### Category 1: Platform Monitors

These deliverables **watch** a platform and produce intelligence.

| Archetype | Platform | Trigger | Output |
|-----------|----------|---------|--------|
| **Slack Digest** | Slack | Daily/weekly schedule | Summary of key discussions, decisions, action items |
| **Inbox Triage** | Gmail | Scheduled | Categorized emails, suggested responses, urgency flags |
| **Notion Changelog** | Notion | Page modification or schedule | What changed, who changed it, why it matters |
| **Thread Synthesizer** | Slack | Thread length threshold | Synthesize long threads into decisions + action items |

### Category 2: Platform Responders

These deliverables **respond** within a platform context.

| Archetype | Platform | Trigger | Output |
|-----------|----------|---------|--------|
| **Slack Auto-Reply** | Slack | @mention or DM | Contextual response using personal style + memory |
| **Email Drafter** | Gmail | Email in "needs response" label | Draft reply with appropriate tone and context |
| **Notion Commenter** | Notion | @mention in page | Add clarifying comment or answer question |

### Category 3: Cross-Platform Synthesizers

These deliverables **connect** context across platforms.

| Archetype | Sources | Output |
|-----------|---------|--------|
| **Weekly Status** | Slack + Notion + Calendar | Synthesized progress report |
| **Project Brief** | Slack threads + Notion pages + Email threads | Executive summary of project state |
| **Meeting Prep** | Calendar event + related Slack + Notion docs | Pre-meeting context package |
| **Handoff Doc** | All platform activity for project | Comprehensive handoff for team member |

---

## Archetype Granularity (Hybrid Approach)

**Decision**: Use hybrid approach for archetype typing.

Platform-native archetypes that are **conceptually new** (auto-reply, triage) get new types:
```python
deliverable_type: "slack_auto_reply" | "gmail_triage" | "slack_thread_synthesizer"
```

Archetypes that are **platform-specific versions of existing types** use variants:
```python
deliverable_type: "status_report"
platform_variant: "slack_digest"
```

This preserves the existing type system while enabling platform-native specialization.

---

## Trigger Model Evolution

### Current: Schedule-Only

```python
DeliverableSchedule = {
    "type": "weekly",
    "day": "monday",
    "hour": 9
}
```

### Evolved: Event + Schedule (Per-Archetype)

Each archetype has one primary trigger type:

```python
# Slack Digest: Scheduled
trigger = {
    "type": "schedule",
    "schedule": {"type": "daily", "hour": 18},
    "skip_if": {"message_count_below": 10}  # Skip if nothing to report
}

# Slack Auto-Reply: Event-based
trigger = {
    "type": "event",
    "event": {
        "platform": "slack",
        "type": "mention_or_dm",
        "channel": "C123456"
    },
    "cooldown": {"per_thread": "4h", "per_channel": "1h"}
}
```

**Key design choice**: Triggers are archetype-specific, not generic. This makes behavior predictable.

---

## Governance as Destination-Influenced

Governance is deliverable-scoped but with destination-derived ceilings:

```python
class Deliverable:
    governance: GovernanceLevel  # User-configured
    governance_ceiling: GovernanceLevel  # System-enforced

    @property
    def effective_governance(self) -> GovernanceLevel:
        return min(self.governance, self.governance_ceiling)
```

**Ceiling derivation**:
- Internal Slack channel → ceiling: `full_auto`
- External Slack channel (shared with clients) → ceiling: `semi_auto`
- Email to external → ceiling: `manual`
- Notion page (internal) → ceiling: `full_auto`

---

## Platform-Specific Output Formats

### Current: Markdown → Export Conversion

```
Generate markdown → Convert to Slack mrkdwn → Post
```

### Evolved: Native Format Generation

The AI generates **directly for the platform**:

| Platform | Native Patterns | Generation Considerations |
|----------|-----------------|---------------------------|
| **Slack** | Blocks, threads, emoji reactions, @mentions | Short messages, actionable, thread-friendly |
| **Gmail** | Threading, signatures, CC semantics | Formal, complete sentences, clear subject lines |
| **Notion** | Blocks, databases, properties, links | Structured, navigable, interconnected |

Example: A Slack digest should:
- Use bullet points (Slack-native)
- Include emoji for scanability
- Link to original threads
- End with a call to action

---

## Bidirectional Flow Architecture

```
     ┌──────────────────────────────────────────────────────────────┐
     │                        YARNNN                                 │
     │                                                               │
     │   Context Pool ←──────── Read ─────────┐                     │
     │        │                                │                     │
     │        │                                │                     │
     │        ▼                                │                     │
     │   Deliverable ─────────→ Write ─────────┼──→ Platform        │
     │        │                                │    (Slack/Notion/  │
     │        │                                │     Gmail)         │
     │        └──────── Observe ───────────────┘                    │
     │                 (reactions,                                   │
     │                  replies,                                     │
     │                  edits)                                       │
     └──────────────────────────────────────────────────────────────┘
```

**Observe loop** (Phase 4): After posting to Slack, track:
- Did people react? (👍 = good, 😕 = confusing)
- Did anyone reply with corrections?
- Was the thread continued?

---

## Implementation Phasing

### Phase 0: Foundation (Current State) ✅
- Context extraction works (ADR-030)
- Destination-first deliverables work (ADR-028)
- Platform source visibility in UI

### Phase 1: Platform-Semantic Extraction
- Extend extraction prompts to capture platform-specific signals
- Add platform metadata to memories (thread depth, reaction counts, etc.)
- Preserve temporal attribution for ephemeral context
- **Deliverable**: Richer extracted context, no new deliverable types yet

### Phase 2: Platform-Native Archetypes (Slack First)
- Implement **Slack Digest** (scheduled, read-only, low risk) — **First archetype**
- Implement **Slack Auto-Reply** (event-triggered, scoped to channel)
- Define archetype config schema, trigger types, governance ceilings
- **Deliverable**: Two working Slack-native archetypes, end-to-end

### Phase 3: Temporal Context Layer
- Create `ephemeral_context` table for time-bounded platform data
- Deliverable generation pulls both ephemeral + persistent context
- TTL-based cleanup for ephemeral entries
- **Deliverable**: Digests feel "fresh" without polluting long-term memory

### Phase 4: Gmail Archetypes
- Gmail Triage (scheduled inbox summary)
- Email Drafter (event-triggered, manual governance only)
- **Deliverable**: Gmail workflow value

### Phase 5: Notion Archetypes
- Notion Changelog (scheduled or event-triggered)
- Notion integration tends toward read-heavy, write-light
- **Deliverable**: Notion awareness in context and outputs

### Phase 6: Cross-Platform Synthesizers
- Weekly Status pulling from all platforms
- Project-to-resource mapping (explicit or inferred)
- **Deliverable**: The "holy grail" multi-platform synthesis

---

## Integration with Existing Architecture

### Deliverable Types (ADR-019)

Platform-native archetypes **extend, not replace** existing types:

| Existing Type | Platform-Native Extensions |
|---------------|---------------------------|
| `status_report` | Slack Status Digest (variant), Email Weekly Summary (variant) |
| `stakeholder_update` | Email Investor Update (variant), Notion Board Memo (variant) |
| `research_brief` | Notion Research Page (variant), Slack Key Findings Post (variant) |
| `meeting_summary` | Notion Meeting Notes (variant), Slack Thread Summary (variant) |

New conceptually-distinct archetypes get new types:
| New Type | Description |
|----------|-------------|
| `slack_auto_reply` | Event-triggered contextual responses |
| `gmail_triage` | Inbox categorization and draft suggestions |
| `slack_thread_synthesizer` | Long thread → decision summary |

### Destination-First (ADR-028)

Platform-native deliverables align with destination-first:
- Destination informs not just export, but **generation**
- Style inference becomes **platform-style inference**
- Governance levels remain applicable, with destination-derived ceilings

### Context Extraction (ADR-030)

Platform-native deliverables **consume** extraction methodology:
- Source metadata (`platform`, `resource_name`) informs deliverable
- Block types can be filtered by relevance to deliverable type
- Freshness guarantees enable event-driven triggers

---

## Success Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Platform fit score** | % of deliverables exported without style edits | >70% |
| **Event trigger accuracy** | User acceptance of event-triggered runs | >80% |
| **Response quality** | Auto-responses approved without edit | >60% |
| **Time saved** | Reduction in user effort per deliverable | 50%+ |
| **Trust delegation** | Users enabling auto modes | 30%+ by month 3 |

---

## Conclusion

The evolution from generic deliverables to platform-native automation represents a significant but natural progression of YARNNN's vision. Key principles:

1. **Keep the unified context pool** — Cross-platform synthesis is core value
2. **Platforms inform reasoning, not just formatting** — Radical interpretation chosen
3. **Separate ephemeral from persistent context** — Temporal awareness without pollution
4. **Deliverables are specifically scoped** — Predictable trigger behavior
5. **Vertical implementation (Slack first)** — Prove the model before expanding
6. **Preserve user control** — Governance ceilings, not surprise automation

---

## References

- [ADR-031: Platform-Native Deliverable Architecture](../adr/ADR-031-platform-native-deliverables.md)
- [ADR-028: Destination-First Deliverables](../adr/ADR-028-destination-first-deliverables.md)
- [ADR-019: Deliverable Types System](../adr/ADR-019-deliverable-types.md)
- [ADR-030: Context Extraction Methodology](../adr/ADR-030-context-extraction-methodology.md)
- [Integration Strategy Analysis](./integration-strategy.md)
- [Integration-First Onboarding](../design/INTEGRATION_FIRST_ONBOARDING.md)
