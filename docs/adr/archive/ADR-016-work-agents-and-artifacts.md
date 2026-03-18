# ADR-016: Layered Agent Architecture and Output Model

> **Status**: Draft
> **Date**: 2025-01-30
> **Depends on**: ADR-009 (Work System), ADR-015 (Unified Context)

---

## Context

ADR-015 Phase 1 proved ambient work flows technically. Testing revealed:
1. Scattered outputs (5-10 fragments vs. one coherent piece)
2. TP verbosity (duplicates content instead of referencing)
3. Progress opacity (no visibility into what's happening)

The root issue: **unclear separation between TP's role and work agents' roles**.

---

## Decision: Layered Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: THINKING PARTNER (TP)                                         │
│  ───────────────────────────────────────────────────────────────────    │
│                                                                         │
│  Role: Orchestration, awareness, communication                          │
│                                                                         │
│  Capabilities:                                                          │
│  - Conversational interface with user                                   │
│  - Judgment: handle directly OR delegate to work agent                  │
│  - Organization: projects, memory, context                              │
│  - Awareness: WHO, WHERE, WHAT, RELEVANT                                │
│                                                                         │
│  Output types (TP's own responses):                                     │
│  - conversation: Direct response to user                                │
│  - delegation: "Research agent is working on this..."                   │
│  - reference: "Done - see the research output" (brief, points to work)  │
│  - organization: "Created project X", "Updated memory"                  │
│                                                                         │
│  Key behavior:                                                          │
│  - When work agent produces output, TP REFERENCES it, doesn't duplicate │
│  - TP communicates status/progress at awareness level                   │
│  - TP is brief when artifacts exist elsewhere                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              │ delegates via create_work
                              │ (when task requires deeper work)
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 2: WORK AGENTS                                                   │
│  ───────────────────────────────────────────────────────────────────    │
│                                                                         │
│  Role: Execute specific work types, produce structured outputs          │
│                                                                         │
│  Each agent has:                                                        │
│  - Defined purpose                                                      │
│  - Own output configuration                                             │
│  - Own system prompt                                                    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  RESEARCH AGENT                                                    │ │
│  │  ─────────────────────────────────────────────────────────────    │ │
│  │  Purpose: Investigate, analyze, synthesize                         │ │
│  │                                                                    │ │
│  │  Output: ONE research document                                     │ │
│  │  - title: What was researched                                      │ │
│  │  - content: Markdown (findings, analysis, recommendations)         │ │
│  │  - metadata: { sources, confidence, scope, depth }                 │ │
│  │                                                                    │ │
│  │  Agent decides structure within content (not predetermined)        │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  CONTENT AGENT                                                     │ │
│  │  ─────────────────────────────────────────────────────────────    │ │
│  │  Purpose: Create, draft, write                                     │ │
│  │                                                                    │ │
│  │  Output: ONE content piece                                         │ │
│  │  - title: What was created                                         │ │
│  │  - content: The actual content (post, article, email, etc.)        │ │
│  │  - metadata: { format, tone, platform, word_count }                │ │
│  │                                                                    │ │
│  │  Agent decides format based on task (linkedin post vs blog, etc.)  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  REPORTING AGENT                                                   │ │
│  │  ─────────────────────────────────────────────────────────────    │ │
│  │  Purpose: Summarize, structure, present                            │ │
│  │                                                                    │ │
│  │  Output: ONE report                                                │ │
│  │  - title: Report title                                             │ │
│  │  - content: Structured report (exec summary, sections, etc.)       │ │
│  │  - metadata: { style, audience, period }                           │ │
│  │                                                                    │ │
│  │  Agent decides structure (executive vs detailed vs summary)        │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## The Handoff: TP → Work Agent → Output

### Flow

```
User: "Research AI code assistants"
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  TP JUDGMENT                                                    │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  "This requires deeper work. Delegate to Research Agent."       │
│                                                                 │
│  TP Response (delegation):                                      │
│  "I'll research AI code assistants for you."                    │
│  [Status: Research agent working...]                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
           │
           │ create_work(agent_type="research", task="...")
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  RESEARCH AGENT EXECUTION                                       │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  - Receives task + context                                      │
│  - Does the work (analysis, synthesis)                          │
│  - Produces ONE output document                                 │
│                                                                 │
│  Output:                                                        │
│  {                                                              │
│    title: "AI Code Assistants Comparison",                      │
│    content: "## Overview\n...\n## Findings\n...",               │
│    metadata: { sources: [...], confidence: 0.85 }               │
│  }                                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
           │
           │ work complete, output saved
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  TP RESPONSE (reference)                                        │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  "Done - I've researched the top AI code assistants.            │
│   See the output panel for the full comparison."                │
│                                                                 │
│  [Output panel opens with the research document]                │
│                                                                 │
│  TP does NOT duplicate the content. It REFERENCES the output.   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### When TP Handles Directly (No Delegation)

```
User: "What's the capital of France?"
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  TP JUDGMENT                                                    │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  "Simple question. Handle directly."                            │
│                                                                 │
│  TP Response (conversation):                                    │
│  "Paris is the capital of France."                              │
│                                                                 │
│  No work agent involved. No artifact created.                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Unified Output Model

### Work Output (from Work Agents)

```python
@dataclass
class WorkOutput:
    """Single output from a work agent execution."""

    # Identity
    ticket_id: UUID           # Which work ticket produced this
    agent_type: str           # "research" | "content" | "reporting"

    # Content (agent-determined structure)
    title: str                # Human-readable title
    content: str              # Markdown body (agent decides structure)

    # Agent-specific metadata
    metadata: dict            # Varies by agent type

    # Timestamps
    created_at: datetime
```

### Metadata by Agent Type

| Agent | Metadata Fields |
|-------|-----------------|
| **Research** | `sources`, `confidence`, `scope`, `depth` |
| **Content** | `format`, `platform`, `tone`, `word_count` |
| **Reporting** | `style`, `audience`, `period`, `sections` |

The `content` field is always markdown. The agent decides its internal structure. The `metadata` provides context for display and future use.

---

## Recurring Work

Recurring work fits the same model:

```
┌─────────────────────────────────────────────────────────────────┐
│  RECURRING WORK (e.g., Weekly Report)                           │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Schedule: Every Monday 9am                                     │
│  Agent: Reporting                                               │
│  Task: "Generate weekly project summary"                        │
│                                                                 │
│  Execution 1 (Jan 6):                                           │
│    → Work Output: "Week of Jan 6 Report" (id: abc123)           │
│                                                                 │
│  Execution 2 (Jan 13):                                          │
│    → Work Output: "Week of Jan 13 Report" (id: def456)          │
│                                                                 │
│  Execution 3 (Jan 20):                                          │
│    → Work Output: "Week of Jan 20 Report" (id: ghi789)          │
│                                                                 │
│  Each execution produces ONE output.                            │
│  Outputs are linked by schedule/template (not versioned within) │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key insight**: Recurring work = same work template executed multiple times. Each execution is independent, produces its own output. "Versioning" is just the history of executions, not in-document versioning.

---

## TP Awareness Status

TP communicates its awareness state to the user:

```
┌─────────────────────────────────────────────────────────────────┐
│  TP STATUS (always visible)                                     │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Idle:                                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🟢 Ready • Dashboard                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  In project:                                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🟢 Ready • Client A project                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Work delegated:                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🔄 Research agent working...                             │   │
│  │    Analyzing AI code assistants                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Work complete:                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ✅ Research complete • View output                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

This is TP's awareness made visible - not feature-level progress, but "what is TP doing right now?"

---

## Implementation: Clean Break

### 1. Remove Old Output Model

- Delete `emit_work_output` tool from `base.py`
- Delete `WorkOutput` with fragmented types (finding, insight, recommendation, etc.)

### 2. Add New Output Model

```python
# In base.py
@dataclass
class WorkOutput:
    title: str
    content: str              # Markdown, structure determined by agent
    metadata: dict = field(default_factory=dict)

# Each agent produces ONE WorkOutput
# Agent's system prompt defines what structure to use in content
```

### 3. Update Each Work Agent

**Research Agent:**
- Remove multi-output emit calls
- Produce single markdown document with findings, analysis, recommendations
- Set metadata: `{ sources, confidence, scope, depth }`

**Content Agent:**
- Remove multi-output emit calls
- Produce single content piece
- Set metadata: `{ format, platform, tone, word_count }`

**Reporting Agent:**
- Remove multi-output emit calls
- Produce single structured report
- Set metadata: `{ style, audience, period }`

### 4. Update TP System Prompt

Add guidance for brevity when work completes:

```
When you delegate work to an agent and it completes:
- Keep your response SHORT (1-2 sentences)
- REFERENCE the output: "Done - see the output panel for the full report."
- Do NOT duplicate the content in your response
- The work output IS the agent; you just acknowledge it

When you handle something directly (no delegation):
- Respond naturally in conversation
- No artifact reference needed
```

### 5. Update Frontend

- Output panel displays single `WorkOutput`
- Render markdown content
- Show metadata as secondary info (sources, format, etc.)
- TP status component shows awareness state

---

## Database Schema

```sql
-- Simplified: one output per ticket
-- (or reuse work_outputs table with cleaner structure)

ALTER TABLE work_outputs
  DROP COLUMN output_type,  -- No more finding/insight/recommendation
  ADD COLUMN metadata JSONB DEFAULT '{}';

-- content column already exists (text/markdown)
-- title column already exists
-- ticket_id links to work_tickets

-- Each ticket has at most ONE output (enforced in code, not schema)
```

---

## Success Criteria

1. **One output per work**: Each work execution produces exactly one output
2. **TP brevity**: TP references outputs, doesn't duplicate content
3. **Agent-determined structure**: Content structure emerges from agent, not schema
4. **TP awareness visible**: User sees TP status (ready, working, complete)
5. **Recurring works**: Same model, multiple executions over time

---

## References

- ADR-009: Async Work System
- ADR-015: Unified Context Model
- ADR-013: Conversation + Surfaces Architecture
- [Claude Artifacts](https://www.anthropic.com/news/artifacts)
- [ChatGPT Canvas](https://openai.com/index/introducing-canvas/)
- [Notion AI Agents](https://skywork.ai/blog/notion-ai-review-2025-features-pricing-workflows/)
