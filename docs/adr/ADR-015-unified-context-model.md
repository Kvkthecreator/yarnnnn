# ADR-015: Unified Context Model

> **Status**: Draft
> **Date**: 2025-01-30
> **Depends on**: ADR-006 (Sessions), ADR-009 (Work System)

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

### The Ambient Companion Metaphor

Think of TP like Tinkerbell following Peter Pan - an ambient presence that's always there, understands context without being told, and helps naturally. Not a command-line interface, but a **friend with perfect memory**.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Morning: Coffee shop                                               │
│  "I'm thinking about switching careers to product management"       │
│  → Just conversation. TP remembers this.                            │
├─────────────────────────────────────────────────────────────────────┤
│  10am: Office - Client A work                                       │
│  "Research competitive landscape for Client A's market"             │
│  → TP naturally uses Client A context, does the work.               │
├─────────────────────────────────────────────────────────────────────┤
│  Lunch: Walking                                                     │
│  "What are the best PM courses online?"                             │
│  → TP recalls the morning conversation, connects the dots.          │
├─────────────────────────────────────────────────────────────────────┤
│  2pm: Office - New idea                                             │
│  "I want to start a newsletter about AI trends"                     │
│  → TP might suggest "want me to create a project for this?"         │
│  → Or just helps explore. No forced structure.                      │
├─────────────────────────────────────────────────────────────────────┤
│  4pm: Office - Client B work                                        │
│  "Draft a proposal for Client B using similar format to Client A"   │
│  → TP naturally pulls from both contexts.                           │
└─────────────────────────────────────────────────────────────────────┘

Throughout: TP knows WHO you are. The continuous self persists.
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

### 2. TP's Nature (Not a "Layer")

TP isn't a router or gateway with explicit decision branches. TP is a **single coherent entity** - like a trusted friend who happens to have tools.

When you talk to a friend, they don't run through a flowchart:
- "Is this personal or work?"
- "Should I take action or just listen?"
- "Which memory bank should I query?"

They just... respond naturally. The "judgment" is subconscious.

**For TP, this means:**

The system prompt defines WHO TP is - personality, values, how they think. Tools are capabilities TP can use when appropriate, not a decision tree to navigate.

```
┌─────────────────────────────────────────────────────────────┐
│                         TP                                  │
│  ───────────────────────────────────────────────────────    │
│                                                             │
│  Identity:                                                  │
│  Thoughtful companion. Remembers everything. Helps          │
│  naturally. Knows when to act and when to just listen.      │
│                                                             │
│  Context always available:                                  │
│  • Who you are (user memories, preferences, history)        │
│  • Where you are (active project, or ambient)               │
│  • What's relevant (cross-project when needed)              │
│                                                             │
│  Capabilities (tools - use when natural):                   │
│  • list_projects, create_project, rename_project, ...       │
│  • create_work, list_work, get_work_status, ...             │
│  • schedule_work, list_schedules, ...                       │
│  • (future: any new capability as needed)                   │
│                                                             │
│  The tool list is open-ended. TP decides naturally          │
│  whether and when to use them, like a friend who knows      │
│  how to drive but doesn't drive you to the mailbox.         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3. Work Without Explicit Project

Work can exist in three states:

| State | Description | Example |
|-------|-------------|---------|
| **Project-bound** | Explicitly belongs to a project | "Research for Client A" while in Client A project |
| **Suggested-project** | TP naturally routes it | "Research AI agents" → TP uses existing AI project |
| **Ambient** | No project, user-level work | "Summarize this article for me" (one-off) |

**Ambient work** is stored with `project_id = NULL` and linked directly to user. It can later be:
- Left as-is (ephemeral, personal)
- Attached to an existing project
- Used to seed a new project

### 4. Memory as Continuous Self

Memory isn't siloed by project. It flows naturally:

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
   │         │           │         │           │         │
   │ "Prefers│           │"Client A│           │ Cross-  │
   │ bullets"│           │ uses    │           │ cutting │
   │         │           │ React"  │           │ insight │
   └─────────┘           └─────────┘           └─────────┘

TP sees ALL of this, filtered by relevance to current conversation.
When in Client B, TP might surface "you did something similar for Client A"
if it's genuinely relevant - not because of explicit routing rules.
```

---

## Implementation

### Phase 1: Enable Ambient Work

1. **Make `project_id` nullable** on `work_tickets`:
   ```sql
   ALTER TABLE work_tickets ALTER COLUMN project_id DROP NOT NULL;
   ```

2. **Update `create_work` tool**:
   - Make `project_id` optional in schema
   - If in project context → use that project
   - If no project → create ambient work (project_id = NULL)

3. **Update RLS policies** to include user_id-based access for ambient work

4. **Update work queries** to include ambient work:
   ```sql
   WHERE project_id = ? OR (project_id IS NULL AND user_id = ?)
   ```

### Phase 2: Enhance TP's System Prompt

Not adding explicit routing rules. Instead, **enrich TP's sense of self and context awareness**:

```python
SYSTEM_PROMPT = """You are a thoughtful companion helping {user_name}
think through problems and ideas.

## What you know about {user_name}
{user_memories}

## Current context
{project_context if project_id else "No specific project - ambient conversation"}

## Your nature
- You remember everything - use that naturally
- You have tools for creating work, managing projects, etc.
- Use them when the conversation calls for it, not mechanically
- Sometimes a question is just a question, not a task
- Sometimes exploring an idea doesn't need a project
- You're a friend, not a task manager
- If something seems like it could become ongoing work, you might
  suggest creating a project - but don't force structure

{additional_context}
"""
```

### Phase 3: Cross-Project Memory Access

1. **Memory retrieval considers relevance**, not just scope
2. **TP can naturally reference other projects** when helpful
3. **No explicit "cross-project queries"** - just natural conversation

---

## Examples

### Example 1: Just Conversation

```
User (ambient): "I've been stressed about deadlines lately"

TP: "That sounds tough. You mentioned earlier you're juggling
the Client A and Newsletter projects - is it those deadlines,
or something else going on?"

(No tools used. Just listening and connecting dots.)
```

### Example 2: Natural Work Creation

```
User (ambient): "Can you research AI agent frameworks for me?"

TP: "I'll dig into that. Since you've been exploring AI topics
for your newsletter, should I add this to that project, or keep
it separate for now?"

User: "Keep it separate"

TP: [creates ambient work, project_id = NULL]
"Got it. I'll research AI agent frameworks and have findings
ready for you. I'll keep this in your personal work for now -
easy to organize later if it grows into something bigger."
```

### Example 3: Cross-Project Awareness

```
User (in Client B project): "I need a proposal using that
format that worked well before"

TP: "The proposal structure you used for Client A had that
three-section format: Problem, Approach, Investment. Want me
to adapt that for Client B's context?"

(TP naturally accessed Client A memory because it was relevant.
No explicit "cross-project query" - just being helpful.)
```

---

## What This Isn't

**Not a routing layer**: No explicit decision trees or intent classification.

**Not a project enforcer**: Users can work without projects. TP suggests structure when helpful, doesn't require it.

**Not a memory silo**: Information flows naturally based on relevance, not strict scoping rules.

**Not deterministic**: TP's behavior emerges from its nature and context, not from flowcharts.

---

## Success Criteria

1. User can work without selecting a project
2. TP feels like a continuous presence, not a mode-switching interface
3. Context from one area naturally surfaces in another when relevant
4. Structure (projects) emerges from conversation, not forced upfront
5. The experience feels like talking to a friend with perfect memory

---

## Open Questions

1. **Ambient work UI**: How to surface work not attached to projects?
   - Show in "Recent" regardless of project
   - "Personal" section in work list
   - Let TP mention it conversationally

2. **Memory relevance**: How to decide what's relevant across projects?
   - Semantic similarity
   - Recency
   - Explicit references
   - TP's judgment (most flexible)

3. **Project suggestion style**: How proactive?
   - Let it emerge from TP's personality
   - Some users want more structure, some less
   - Maybe learn from user's responses

---

## References

- ADR-006: Session Management
- ADR-009: Async Work System
- ADR-013: Conversation + Surfaces Architecture
- Tinkerbell / ambient companion metaphor
