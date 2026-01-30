# ADR-015: Unified Context Model

> **Status**: Phase 1 Complete, Iterating
> **Date**: 2025-01-30
> **Depends on**: ADR-006 (Sessions), ADR-009 (Work System)
> **Phase 1 Completed**: 2025-01-30 (ambient work functional)

---

## Context

Current architecture treats projects as primary containers:
- Work must belong to a project
- Chat is either "global" or "project-scoped"
- Memory is siloed per project

This creates friction:
- User asks "research X" without selecting a project → blocked
- Context learned in one project doesn't flow to related work
- The user's continuous "self" is fragmented

---

## The Core Model: TP Follows the User

The key insight: **TP follows the user through their world**, not the other way around.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER'S WORLD                                 │
│                                                                     │
│    User moves through contexts throughout their day:                │
│                                                                     │
│    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐        │
│    │ Personal│───▶│Client A │───▶│ Personal│───▶│Client B │        │
│    │ morning │    │  work   │    │  lunch  │    │  work   │        │
│    └─────────┘    └─────────┘    └─────────┘    └─────────┘        │
│                                                                     │
│    The user is the constant. Contexts are locations they visit.     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ TP follows
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                            TP                                       │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  AWARENESS (what TP knows at any moment):                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ • WHO: User identity, preferences, history (always present)  │   │
│  │ • WHERE: Current context (project, ambient, personal)        │   │
│  │ • WHAT: Conversation content, user's apparent intent         │   │
│  │ • RELEVANT: Cross-context memories when applicable           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  CAPABILITIES (tools - the action space):                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Work:         create_work, list_work, get_work_status, ...   │   │
│  │ Organization: create_project, rename_project, list_projects  │   │
│  │ Scheduling:   schedule_work, list_schedules, update_schedule │   │
│  │ (extensible): any new tool added expands what TP can do      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ORCHESTRATION (TP's judgment):                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Given awareness + capabilities, TP decides:                  │   │
│  │ • Which tools to use (or none)                               │   │
│  │ • What context to apply                                      │   │
│  │ • How to respond                                             │   │
│  │                                                              │   │
│  │ This is NOT a flowchart. It's judgment informed by context.  │   │
│  │ The tools define the action space; TP navigates it.          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Decision

### 1. Context Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                      USER (self)                            │
│  ───────────────────────────────────────────────────────    │
│  • Identity: name, role, communication style                │
│  • Preferences: formats, verbosity, working hours           │
│  • Personal: life context, goals, interests                 │
│  • Cross-cutting: things relevant across all projects       │
└─────────────────────────────┬───────────────────────────────┘
                              │ always available
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AMBIENT SPACE                            │
│  ───────────────────────────────────────────────────────    │
│  • Default interaction mode (no project selected)           │
│  • Personal conversations, exploration, planning            │
│  • Ad-hoc work that doesn't need a project                  │
│  • Staging area for potential projects                      │
└─────────────────────────────┬───────────────────────────────┘
                              │ when relevant
                              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Project A   │  │  Project B   │  │  Project C   │
│  ──────────  │  │  ──────────  │  │  ──────────  │
│  • Memories  │  │  • Memories  │  │  • Memories  │
│  • Work      │  │  • Work      │  │  • Work      │
│  • Sessions  │  │  • Sessions  │  │  • Sessions  │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 2. TP's Orchestration

TP makes decisions based on awareness and capabilities. The tools ARE the possible actions.

**Awareness** informs the decision:
- User's current context (project or ambient)
- User's history and preferences
- Conversation content and apparent intent
- Relevant memories from any scope

**Capabilities** define the action space:
- Each tool is something TP *can* do
- TP decides *whether* and *when* to use them
- No tool is mandatory; conversation alone is valid
- New tools expand what TP can do

**Orchestration** is the judgment:
- Not a fixed flowchart or decision tree
- Context-dependent reasoning
- "Given what I know and what I can do, what should I do?"

```
Example orchestration:

User (ambient): "Research AI agent frameworks"

TP's awareness:
- WHERE: Ambient (no project selected)
- WHO: User has been exploring AI topics
- WHAT: Research request (work-like)
- RELEVANT: User has "AI Newsletter" project

TP's capabilities include:
- create_work (can do research)
- list_projects (can check existing projects)
- create_project (can make new project)

TP's judgment:
→ This is work, use create_work
→ Related to existing project, mention it
→ Don't force project assignment, offer choice

TP: "I'll research AI agent frameworks. This seems related
to your AI Newsletter project - should I add it there, or
keep it as standalone work?"
```

### 3. Work Without Explicit Project

Work can exist in three states:

| State | Description | Example |
|-------|-------------|---------|
| **Project-bound** | Explicitly belongs to a project | "Research for Client A" while in Client A project |
| **Routed** | TP assigns based on context | "Research AI agents" → TP uses existing AI project |
| **Ambient** | No project, user-level work | "Summarize this article for me" (one-off) |

**Ambient work** is stored with `project_id = NULL` and linked directly to user.

### 4. Memory Flows with the User

Memory isn't siloed. It flows based on relevance:

```
                    ┌─────────────────────┐
                    │   User's Mind       │
                    │   (unified memory)  │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
   ┌─────────┐           ┌─────────┐           ┌─────────┐
   │ Scope:  │           │ Scope:  │           │ Scope:  │
   │ user    │           │ project │           │ shared  │
   └─────────┘           └─────────┘           └─────────┘

TP sees all memory, filtered by relevance to current context.
Cross-project access happens naturally when relevant.
```

---

## Implementation

### Phase 1: Enable Ambient Work

1. **Make `project_id` nullable** on `work_tickets`:
   ```sql
   ALTER TABLE work_tickets ALTER COLUMN project_id DROP NOT NULL;
   ```

2. **Update `create_work` tool schema**:
   - Make `project_id` optional
   - Add guidance in description about when to use/omit

3. **Update RLS policies** for user_id-based access on ambient work

4. **Update work queries**:
   ```sql
   WHERE project_id = ? OR (project_id IS NULL AND user_id = ?)
   ```

### Phase 2: Enhance TP's Awareness

Update system prompt to provide richer context:

```python
SYSTEM_PROMPT = """You are a thoughtful assistant helping the user...

## About the User
{user_memories}

## Current Context
{context_description}
- Active project: {project_name or "None (ambient)"}
- Recent topics: {recent_conversation_themes}

## Your Capabilities
You have tools for work, organization, and scheduling.
Use them when appropriate based on what the user needs.
Not every conversation needs a tool - sometimes just talking is right.

{tool_specific_context}
"""
```

### Phase 3: Cross-Context Memory

1. Memory retrieval considers relevance across all scopes
2. TP can reference other projects when genuinely helpful
3. No explicit "cross-project mode" - just natural awareness

---

## Testing & Iteration

The framework is correct. Quality comes from iterative testing:

### Test Scenarios

| Scenario | What to observe |
|----------|-----------------|
| Work request (no project) | Does TP handle gracefully? Route intelligently? |
| Personal conversation | Does TP engage without forcing tools? |
| Cross-project reference | Does TP connect relevant context? |
| Ambiguous request | Does TP's judgment feel right? |
| Project suggestion | Does TP offer structure without forcing it? |

### Iteration Loop

```
1. Run scenario with real user or test prompt
2. Observe TP's orchestration decisions
3. Identify gaps in awareness or judgment
4. Adjust:
   - System prompt (TP's nature/guidance)
   - Tool descriptions (action guidance)
   - Context provided (awareness inputs)
5. Re-test same scenario
6. Repeat
```

### Quality Signals

- **Good**: TP uses right tool for context, offers without forcing
- **Bad**: TP forces structure, misses relevant context, wrong tool
- **Adjust**: Prompt wording, context richness, tool descriptions

---

## Success Criteria

1. User can work without selecting a project first
2. TP routes work intelligently based on context
3. Cross-project context surfaces when relevant
4. Structure emerges from conversation, not forced upfront
5. TP's orchestration feels helpful, not mechanical

---

## Open Questions

1. **Ambient work UI**: How to surface work not attached to projects?
2. **Memory relevance**: Semantic similarity vs. recency vs. explicit reference?
3. **Orchestration tuning**: How to adjust TP's judgment style per user?

---

## Phase 2: Qualitative Iteration (Next)

Phase 1 proved the technical flow works. Now we need to refine the *quality* of the experience.

### Observation 1: Output Model - Scattered vs. Consolidated

**Current behavior**: Work produces multiple discrete outputs (Finding, Insight, Recommendation, etc.)

**Problem**: This feels deterministic and fragmented compared to:
- **Claude Artifacts**: Single, evolving document
- **ChatGPT Canvas**: Unified workspace that gets refined

**Question**: Should outputs be:
- A single "artifact" that the agent builds/refines?
- Or multiple pieces that get consolidated on display?
- Or defined by the work agent itself (not predetermined)?

**Hypothesis**: The output *structure* should emerge from the work agent's judgment, not be hardcoded. A research task might produce one comprehensive report. A content task might produce drafts. The current multi-output model may be over-engineered.

**Consideration**: This may be a "work agents" (layer 2) concern, not TP orchestration. Work agents haven't been deeply defined yet.

### Observation 2: TP Response Verbosity with Tool Use

**Current behavior**: When work completes and the drawer opens, TP also writes a lengthy elaboration in chat.

**Problem**: Redundant. The artifact/output IS the deliverable. The chat message should:
- Acknowledge the work is done
- Reference the artifact (brief)
- Not duplicate the content

**Compare to Claude Code**: When Claude Code runs a tool or shows output, the message is compact. Progress and results appear in dedicated UI, not prose.

**Direction**:
```
Current:  "Great! The research has been completed. Here's what I found:
          [3 paragraphs of summary duplicating the output panel]"

Better:   "Done - I've researched the top 3 AI code assistants.
          See the output panel for the full comparison."

Or even:  [Tool indicator: Research complete ✓] + artifact reference
```

### Observation 3: Progress Visibility

**Current behavior**: User sends message → waits → result appears

**Compare to Claude Code**: Shows todos, progress indicators, what's being done

**Question**: Should TP show:
- "Researching..." indicator
- Progress steps (like a todo list)
- Streaming partial results

**Consideration**: This is UX/frontend, not orchestration. But the SSE events may need richer progress signals.

### Next Steps for Phase 2

1. **Define work agents** (ADR-016?): What are research/content/reporting agents actually doing? What's their output model?
2. **Output consolidation**: Move toward single artifact per work, not multiple discrete outputs
3. **TP response brevity**: Adjust system prompt to be compact when artifacts exist
4. **Progress UI**: Consider inline progress indicators during work execution

---

## References

- ADR-006: Session Management
- ADR-009: Async Work System
- ADR-013: Conversation + Surfaces Architecture
