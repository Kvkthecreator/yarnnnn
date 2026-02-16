# ADR-061: Two-Path Architecture Consolidation

**Date**: 2026-02-16
**Status**: Proposed
**Supersedes**: ADR-016 (Layered Agent Architecture) - work agent model
**Clarifies**: ADR-045 (Deliverable Orchestration) - execution strategies

---

## Context

### Evolution of Understanding

YARNNN has evolved through multiple agent architecture iterations:

1. **ADR-016** (Jan 2025): Introduced TP + Work Agents (Research, Content, Reporting)
2. **ADR-018** (Feb 2025): Added Recurring Deliverables with pipeline execution
3. **ADR-042** (Feb 2025): Simplified 3-step pipeline to single execution
4. **ADR-045** (Feb 2025): Type-aware execution strategies (platform_bound, cross_platform, research, hybrid)
5. **ADR-060** (Feb 2026): Proposed Conversation Analyst for background pattern detection

### The Clarity

Analysis of the codebase reveals:

**Dead code**: SynthesizerAgent, ReportAgent, ResearcherAgent are never triggered from production paths. Only DeliverableAgent actually produces outputs.

**Actual pattern**: Two distinct execution paths already exist:
1. **Thinking Partner (TP)**: Real-time, conversational, Claude Code-like
2. **Backend Orchestrator**: Async, scheduled, type-driven

ADR-016's "layered agent" model (TP delegates to specialized work agents) was never fully realized. Instead, a simpler pattern emerged organically.

### Claude Code Inspiration

Claude Code succeeds through clear separation:
- **Claude**: Real-time conversational agent (explores, reads, answers, executes)
- **Background systems**: Caching, tool management, context handling

This separation is more powerful than elaborate agent hierarchies.

---

## Decision

### Two-Path Architecture

YARNNN operates through exactly two paths:

```
┌─────────────────────────────────────────────────────────────────┐
│ PATH A: THINKING PARTNER (Real-time)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User ←→ TP                                                     │
│                                                                 │
│  Character: Claude Code-like                                    │
│  - Conversational                                               │
│  - Tool-equipped (primitives: Read, Write, Edit, Search, etc.) │
│  - Low latency                                                  │
│  - Session-scoped                                               │
│                                                                 │
│  Capabilities:                                                  │
│  - Search (internal + web via WebSearch primitive)              │
│  - Read user context (platforms, documents, memories)           │
│  - Answer questions                                             │
│  - Execute platform actions (send Slack, create draft)          │
│  - Remember facts (knowledge_entries)                           │
│  - Create/manage deliverables when explicitly asked             │
│                                                                 │
│  Does NOT:                                                      │
│  - Proactively suggest automations mid-conversation             │
│  - Generate deliverable content (that's Path B)                 │
│  - Run long-running research tasks (hands off to Path B)        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ PATH B: BACKEND ORCHESTRATOR (Async)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Trigger → Orchestrator → Output → Notification                 │
│                                                                 │
│  Character: Scheduled batch processor                           │
│  - Non-conversational                                           │
│  - Type-driven execution                                        │
│  - Latency-tolerant                                             │
│  - User-scoped (not session)                                    │
│                                                                 │
│  Entry points:                                                  │
│  - Cron schedule (unified_scheduler.py every 5 mins)            │
│  - Event triggers (ADR-031)                                     │
│  - Manual trigger (via API)                                     │
│                                                                 │
│  Phases:                                                        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. ANALYSIS PHASE (daily)                                │   │
│  │    - Conversation pattern detection (ADR-060)            │   │
│  │    - Creates suggested deliverables                      │   │
│  │    - No LLM agent - service function with LLM call       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 2. EXECUTION PHASE (per-deliverable schedule)            │   │
│  │    - Freshness check (ADR-049)                           │   │
│  │    - Strategy selection (ADR-045: type_classification)   │   │
│  │    - Context gathering (parallel per platform)           │   │
│  │    - Content generation (single LLM call)                │   │
│  │    - Delivery (if full_auto governance)                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Output:                                                        │
│  - deliverable_versions (staged, approved, delivered)           │
│  - Email notifications                                          │
│  - Platform delivery (Slack, Gmail, Notion)                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Path Boundary

The boundary between paths is clear:

| Action | Path | Rationale |
|--------|------|-----------|
| "Summarize #engineering channel" | A (TP) | One-time request, immediate response |
| "Set up weekly #engineering digest" | A→B | TP creates deliverable, orchestrator executes |
| Generate weekly #engineering digest | B | Scheduled, async, no conversation |
| "What happened in #engineering this week?" (3x) | A, then B | TP answers; orchestrator detects pattern |
| Detect recurring user patterns | B (Analysis) | Background, daily, non-blocking |

### Type-Driven Execution (ADR-045)

The orchestrator selects execution strategy based on `type_classification.binding`:

```python
# From deliverable type config
type_classification = {
    "binding": "platform_bound",      # Strategy: single platform fetch
    "primary_platform": "slack",      # Platform focus
    "temporal_pattern": "digest",     # Temporal nature
}
```

| Binding | Strategy | Description |
|---------|----------|-------------|
| `platform_bound` | PlatformBoundStrategy | Single platform, platform-specific synthesis |
| `cross_platform` | CrossPlatformStrategy | Parallel fetch, cross-platform synthesis |
| `research` | ResearchStrategy | Web search via Anthropic native tool |
| `hybrid` | HybridStrategy | Web + platform in parallel |

### Multi-Turn and Complex Work

Complex or multi-turn work is handled by **execution strategies**, not by spawning multiple agents:

**Single-turn (normal):**
```
Trigger → Strategy.gather_context() → generate_draft() → Version
```

**Multi-turn (research-heavy):**
```
Trigger → ResearchStrategy.gather_context()
              │
              ├─ web_search (Anthropic native, multi-search)
              ├─ platform grounding (parallel)
              └─ user memories
          → generate_draft() → Version
```

**Parallel complexity:**
```
Trigger → HybridStrategy.gather_context()
              │
              └─ asyncio.gather(
                   do_web_research(),     # Multiple searches
                   do_platform_fetch()    # Parallel platforms
                 )
          → generate_draft() → Version
```

The key insight: **complexity is in the strategy, not in agent proliferation**. One DeliverableAgent with type-aware context gathering handles all cases.

### Conversation Analysis (ADR-060)

Conversation analysis is NOT a separate agent. It's a service function in the orchestrator's analysis phase:

```python
# In unified_scheduler.py (daily cron)
async def run_analysis_phase(supabase, user_id):
    """
    Detect patterns in recent conversations.
    Creates suggested deliverables with confidence scores.
    """
    # Get recent sessions
    sessions = await get_recent_sessions(supabase, user_id, days=7)

    # Get existing deliverables (avoid duplicates)
    existing = await get_user_deliverables(supabase, user_id)

    # Single LLM call with structured output
    suggestions = await analyze_conversation_patterns(
        sessions=sessions,
        existing_deliverables=existing,
        user_knowledge=await get_user_knowledge(supabase, user_id),
    )

    # Create suggested deliverables (status: "suggested")
    for suggestion in suggestions:
        if suggestion.confidence >= 0.50:
            await create_suggested_deliverable(supabase, user_id, suggestion)
```

This is simpler than a full "ConversationAnalystAgent" with its own prompt, tools, and lifecycle.

---

## Dead Code Cleanup

The following should be marked for removal or significant simplification:

| File | Status | Reason |
|------|--------|--------|
| `api/agents/synthesizer.py` | Dead | Never triggered; DeliverableAgent handles synthesis |
| `api/agents/report.py` | Dead | Never triggered; deliverable types cover reports |
| `api/agents/researcher.py` | Partial | Only `research_topic()` used by ResearchStrategy |
| `api/agents/factory.py` | Simplify | Only DeliverableAgent instantiation needed |

Keep:
- `api/agents/thinking_partner.py` - Path A
- `api/agents/deliverable.py` - Path B content generation
- `api/agents/base.py` - Shared infrastructure

---

## Implementation

### Phase 1: Documentation (This ADR)
- [x] Document Two-Path Architecture
- [x] Clarify path boundaries
- [x] Note dead code

### Phase 2: Analysis Phase Addition
- [ ] Add `analyze_conversation_patterns()` service function
- [ ] Integrate into `unified_scheduler.py` (daily trigger)
- [ ] Use ADR-060 schema (suggested status, analyst_metadata)

### Phase 3: Dead Code Cleanup (Future)
- [ ] Remove SynthesizerAgent (or merge into DeliverableAgent)
- [ ] Remove ReportAgent
- [ ] Simplify ResearcherAgent to pure function
- [ ] Update factory.py

---

## Naming Clarification

The `unified_scheduler.py` IS the orchestrator. No rename needed - it already:
- Runs on cron schedule
- Processes deliverables (execution phase)
- Processes work tickets
- Processes digests

Adding analysis phase extends its role naturally.

---

## TP Prompt Updates

TP's role is clarified (not changed):

```python
# In tp_prompts/behaviors.py

WORK_BOUNDARY = """
## Work Boundary

You are a conversational assistant (Path A), NOT a batch processor (Path B).

**DO:**
- Answer questions using Search, Read, Execute primitives
- Execute one-time platform actions
- Create deliverables when user explicitly asks
- Remember facts about user

**DON'T:**
- Generate recurring deliverable content (orchestrator does that)
- Suggest automations mid-conversation (background analysis does that)
- Run long research tasks (use Execute for one-off, deliverable for recurring)

If user says "set up a weekly digest", create the deliverable config.
The orchestrator will generate content on schedule.
"""
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Agent code reduction | 40% fewer agent files |
| Execution path clarity | 2 paths, documented |
| Conversation analysis precision | >70% suggestion acceptance |
| TP response latency | <3s (unchanged) |
| Orchestrator run time | <60s per cycle |

---

## Related

- **ADR-016**: Work Agents (superseded - work agent model not realized)
- **ADR-042**: Simplified Execution (aligned - single flow)
- **ADR-045**: Execution Strategies (clarified - strategies not agents)
- **ADR-060**: Background Conversation Analyst (integrated - analysis phase)
- **ADR-049**: Context Freshness (unchanged - freshness checks remain)

---

## Appendix: Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ PATH B: Detailed Execution Flow                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Render Cron (*/5 * * * *)                                      │
│           │                                                     │
│           ▼                                                     │
│  unified_scheduler.run_unified_scheduler()                      │
│           │                                                     │
│           ├──────────────────────────────────────────────┐      │
│           │                                              │      │
│           ▼                                              ▼      │
│  ┌─────────────────┐                          ┌─────────────────┐
│  │ Analysis Phase  │ (daily, minute < 5)      │ Execution Phase │
│  │                 │                          │                 │
│  │ For each user:  │                          │ For due items:  │
│  │  - get_sessions │                          │  - deliverables │
│  │  - analyze_patterns                        │  - work_tickets │
│  │  - create_suggested                        │  - digests      │
│  │                 │                          │  - imports      │
│  └─────────────────┘                          └────────┬────────┘
│                                                        │        │
│                                                        ▼        │
│                                          ┌─────────────────────┐│
│                                          │ process_deliverable ││
│                                          │                     ││
│                                          │ 1. freshness_check  ││
│                                          │ 2. get_strategy     ││
│                                          │ 3. gather_context   ││
│                                          │ 4. generate_draft   ││
│                                          │ 5. stage_version    ││
│                                          │ 6. [deliver if auto]││
│                                          │ 7. send_email       ││
│                                          └─────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
