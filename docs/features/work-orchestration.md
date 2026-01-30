# Work Orchestration

> **Status**: ADR-016 drafted, implementation pending
> **ADRs**: ADR-009 (Work System), ADR-015 (Unified Context), ADR-016 (Layered Architecture)

---

## Overview

YARNNN uses a two-layer agent architecture for handling user requests:

1. **Layer 1: Thinking Partner (TP)** - Conversational orchestrator
2. **Layer 2: Work Agents** - Specialized executors (Research, Content, Reporting)

TP judges whether to handle a request directly or delegate to a work agent for deeper work.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  USER                                                           │
│  "Research AI code assistants"                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: THINKING PARTNER (TP)                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Role: Orchestration, awareness, communication                  │
│                                                                 │
│  Judgment options:                                              │
│  1. Handle directly (simple questions, conversation)            │
│  2. Delegate to work agent (research, content, reports)         │
│  3. Organization action (create project, update memory)         │
│                                                                 │
│  Decision: "This needs research. Delegate."                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ create_work(agent_type="research")
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: RESEARCH AGENT                                        │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  - Receives: task + context (user memories + project memories)  │
│  - Executes: Analysis, synthesis, reasoning                     │
│  - Produces: ONE output (markdown document)                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ WorkOutput saved
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TP RESPONSE                                                    │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  "Done - I've researched AI code assistants.                    │
│   See the output panel for the full comparison."                │
│                                                                 │
│  [Output panel opens with research document]                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Work Agents

### Research Agent
- **Purpose**: Investigate, analyze, synthesize
- **Output**: Markdown document (findings, analysis, recommendations)
- **Metadata**: sources, confidence, scope, depth

### Content Agent
- **Purpose**: Create, draft, write content
- **Output**: The content itself (post, article, email, etc.)
- **Metadata**: format, platform, tone, word_count

### Reporting Agent
- **Purpose**: Summarize, structure, present
- **Output**: Structured report
- **Metadata**: style, audience, period

---

## Key Principles

### 1. One Output Per Work
Each work execution produces exactly ONE output. The agent determines the structure within that output.

**Not this:**
```
emit_work_output("finding", "Finding 1...")
emit_work_output("finding", "Finding 2...")
emit_work_output("insight", "Pattern observed...")
emit_work_output("recommendation", "Suggest...")
→ 4+ fragmented pieces
```

**This:**
```
WorkOutput(
  title="AI Code Assistants Analysis",
  content="## Overview\n...\n## Findings\n...\n## Recommendations\n...",
  metadata={sources: [...], confidence: 0.85}
)
→ 1 coherent document
```

### 2. TP References, Doesn't Duplicate
When work completes, TP keeps its response brief and points to the output. It does NOT repeat the content in chat.

### 3. Context Flows Down
User memories and project memories flow from TP to work agents. The agent has full context to do its work.

### 4. Agent Determines Structure
The agent decides how to structure its output based on the task. A research task might need sections; a content task is the content itself.

---

## Ambient Work (ADR-015)

Work can exist without a project:
- **Project-bound**: Explicitly belongs to a project
- **Ambient**: No project, linked to user directly

TP routes intelligently based on context.

---

## Recurring Work

Same model, multiple executions:
- Schedule defines when work runs (e.g., "Every Monday 9am")
- Each execution produces its own output
- Outputs linked by schedule, not versioned within

---

## TP Awareness Status

User sees what TP is doing:

| State | Display |
|-------|---------|
| Ready | 🟢 Ready • Dashboard |
| In project | 🟢 Ready • Client A project |
| Working | 🔄 Research agent working... |
| Complete | ✅ Research complete • View output |

---

## Implementation Status

| Component | Status |
|-----------|--------|
| TP judgment/delegation | ✅ Implemented |
| create_work tool | ✅ Implemented |
| Work agents (Research, Content, Reporting) | ✅ Implemented (old output model) |
| Unified output model (ADR-016) | 🔲 Pending |
| TP brevity guidance | 🔲 Pending |
| TP awareness status UI | 🔲 Pending |
| Error visibility to user | 🔲 Pending |
| Work cancellation | 🔲 Future |
| Timeouts | 🔲 Future |

---

## Related ADRs

- **ADR-009**: Async Work System (original work architecture)
- **ADR-015**: Unified Context Model (ambient work, context hierarchy)
- **ADR-016**: Layered Agent Architecture (current spec)
