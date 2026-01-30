# ADR-016: Work Agents and Artifact Model

> **Status**: Draft
> **Date**: 2025-01-30
> **Depends on**: ADR-009 (Work System), ADR-015 (Unified Context)

---

## Context

ADR-015 Phase 1 proved ambient work flows technically. Testing revealed qualitative issues:

1. **Scattered outputs**: Work produces multiple discrete outputs (Finding, Insight, Recommendation) - feels fragmented vs. Claude Artifacts / ChatGPT Canvas
2. **TP verbosity**: When artifact exists, TP duplicates content in chat instead of referencing it
3. **Progress opacity**: User waits without visibility into what TP is doing

This ADR addresses the **work agents layer** (layer 2) and the **output model**.

---

## Current State Analysis

### Existing Work Agents

| Agent | Purpose | Current Output Model |
|-------|---------|---------------------|
| **ResearchAgent** | Investigation/analysis | Multiple `emit_work_output` calls (finding, insight, recommendation) |
| **ContentAgent** | Content creation | Multiple drafts + recommendations |
| **ReportingAgent** | Structured reports | Section-by-section emissions |

### Current Output Tool

```python
EMIT_WORK_OUTPUT_TOOL = {
    "name": "emit_work_output",
    "input_schema": {
        "properties": {
            "output_type": {"enum": ["finding", "recommendation", "insight", "draft", "report"]},
            "title": {"type": "string"},
            "body": {
                "properties": {
                    "summary": {"type": "string"},
                    "details": {"type": "string"},
                    "evidence": {"type": "array"},
                    "implications": {"type": "array"}
                }
            },
            "confidence": {"type": "number"},
            "source_memory_ids": {"type": "array"}
        }
    }
}
```

**Problem**: This encourages fragmentation. Agents emit 5-10 small pieces instead of one coherent artifact.

---

## Decision

### 1. Artifact-First Output Model

Shift from "emit many outputs" to "build one artifact":

```
┌─────────────────────────────────────────────────────────────────┐
│  CURRENT: Multiple discrete outputs                             │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  emit_work_output("finding", "Finding 1: ...")                  │
│  emit_work_output("finding", "Finding 2: ...")                  │
│  emit_work_output("insight", "Pattern observed...")             │
│  emit_work_output("recommendation", "Suggest...")               │
│  emit_work_output("recommendation", "Also consider...")         │
│                                                                 │
│  → 5 separate database rows, scattered display                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  NEW: Single evolving artifact                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  create_artifact("research_report", {                           │
│    sections: [                                                  │
│      { type: "summary", content: "..." },                       │
│      { type: "findings", items: [...] },                        │
│      { type: "recommendations", items: [...] }                  │
│    ]                                                            │
│  })                                                             │
│                                                                 │
│  → 1 coherent artifact, consolidated display                    │
└─────────────────────────────────────────────────────────────────┘
```

### 2. New Tool: `create_artifact` / `update_artifact`

Replace `emit_work_output` with artifact-oriented tools:

```python
CREATE_ARTIFACT_TOOL = {
    "name": "create_artifact",
    "description": """Create or replace the work artifact.

Each work produces ONE artifact. Call this to set the complete output.
The artifact is what the user sees in the output panel.

Artifact types:
- "research_report": Structured research with findings and recommendations
- "content_draft": Written content (post, article, email, etc.)
- "summary_report": Executive summary or briefing
- "analysis": Data analysis or comparison

The artifact should be COMPLETE when you call this tool.
Include all sections in a single call.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "artifact_type": {
                "type": "string",
                "enum": ["research_report", "content_draft", "summary_report", "analysis"]
            },
            "title": {
                "type": "string",
                "description": "Artifact title (what user sees)"
            },
            "content": {
                "type": "object",
                "description": "Structured artifact content",
                "properties": {
                    "summary": {"type": "string", "description": "Executive summary (1-3 sentences)"},
                    "body": {"type": "string", "description": "Main content (markdown supported)"},
                    "sections": {
                        "type": "array",
                        "description": "Optional structured sections",
                        "items": {
                            "type": "object",
                            "properties": {
                                "heading": {"type": "string"},
                                "content": {"type": "string"}
                            }
                        }
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata (sources, confidence, etc.)"
                    }
                }
            }
        },
        "required": ["artifact_type", "title", "content"]
    }
}
```

### 3. Agent-Specific Artifact Shapes

Each agent type produces a characteristic artifact:

| Agent | Artifact Type | Shape |
|-------|--------------|-------|
| **Research** | `research_report` | Summary + Findings list + Recommendations list |
| **Content** | `content_draft` | Summary + Body (the actual content) + Variants (optional) |
| **Reporting** | `summary_report` | Executive summary + Sections + Appendix |

The agent decides the internal structure. The artifact is ONE thing, displayed as ONE panel.

### 4. TP Response Brevity

When an artifact exists, TP should be brief:

**System prompt addition:**

```
When you create work that produces an artifact:
- Keep your chat response SHORT (1-2 sentences)
- Reference the artifact: "Done - see the research report in the output panel."
- Do NOT duplicate the artifact content in your response
- The artifact IS the deliverable; your message just acknowledges it

Example:
User: "Research AI code assistants"
You: [call create_work...]
You: "I've completed the research. The report is in your output panel with findings on GitHub Copilot, Cursor, and Claude Code."

NOT:
You: "I've completed the research. Here's what I found: [3 paragraphs repeating the artifact]..."
```

### 5. TP Awareness Status (UI)

Progress visibility at the TP awareness level:

```
┌─────────────────────────────────────────────────────────────────┐
│  TP STATUS BAR (persistent, below TopBar or in chat area)       │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Idle state:                                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🟢 Ready • Working in "Client A" project                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Working state:                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🔄 Researching AI code assistants...                     │   │
│  │    └─ Analyzing context ██████░░░░                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Tool use state:                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🔧 Using: create_work (research agent)                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation:**
- SSE events include status updates, not just tool results
- Frontend subscribes to status stream
- Single component displays TP's current awareness state

---

## Implementation Plan

### Phase 2a: Artifact Model (Backend)

1. **New tool**: `create_artifact` replaces `emit_work_output`
2. **Database**: Single `work_artifacts` table (or reuse `work_outputs` with new structure)
3. **Agent updates**: Research/Content/Reporting agents produce one artifact each
4. **Display**: Output panel shows single artifact with internal navigation

### Phase 2b: TP Brevity (Prompt)

1. **System prompt**: Add artifact-aware response guidance
2. **Tool description**: Clarify that artifact IS the deliverable
3. **Testing**: Verify TP keeps chat responses compact

### Phase 2c: TP Status UI (Frontend)

1. **SSE events**: Add `status` event type alongside `tool_use`, `tool_result`, `text`
2. **Status component**: New `TPStatus` component in UI
3. **Integration**: Display below TopBar or inline with chat

---

## Migration Path

### Clean Break (No Dual Approaches)

Pre-launch means no legacy baggage. Replace entirely:

1. **Remove** `emit_work_output` tool from `base.py`
2. **Add** `create_artifact` as the only output mechanism
3. **Update** all three agents (Research, Content, Reporting) in one pass
4. **Update** database schema if needed (single artifact per ticket)
5. **Update** frontend output panel to display artifact structure

**No soft migration**. Dual approaches create downstream ambiguity. If the artifact model is the right direction, commit to it fully.

---

## Open Questions

1. **Artifact versioning**: Should artifacts be versionable/editable after creation?
2. **Multiple artifacts**: What if a task genuinely needs multiple outputs? (Answer: probably shouldn't - one task = one artifact)
3. **Artifact types**: Are the proposed types sufficient? Too rigid? Or should the agent just produce markdown with whatever structure fits?
4. **Status granularity**: How detailed should progress indicators be?

### Deeper Question: Is "Artifact" the Right Framing?

Consider alternatives:

**Option A: Typed Artifacts** (current proposal)
- `research_report`, `content_draft`, `summary_report`, `analysis`
- Pro: Structured, predictable display
- Con: May feel rigid, agents boxed into types

**Option B: Freeform Document**
- Agent produces a single markdown document
- Structure emerges from content, not schema
- Pro: Maximum flexibility, agent decides format
- Con: Less structured display, harder to parse

**Option C: Canvas Model** (like ChatGPT Canvas)
- Work produces a "canvas" - a workspace the user can interact with
- Agent populates it, user can edit/refine
- Pro: Collaborative feel
- Con: More complex, may be over-engineered for MVP

**Leaning toward**: Option A (Typed Artifacts) for MVP, but keep types minimal and allow rich markdown in `body`. The type is a hint for display, not a constraint on content.

---

## Success Criteria

1. Work produces ONE artifact (not 5-10 fragments)
2. TP chat response is brief when artifact exists
3. User sees TP status during work execution
4. Output panel displays coherent, complete artifact
5. Experience feels like Claude Artifacts / ChatGPT Canvas

---

## References

- ADR-009: Async Work System
- ADR-015: Unified Context Model (Phase 2 notes)
- ADR-013: Conversation + Surfaces Architecture
- Claude Artifacts UX
- ChatGPT Canvas UX
