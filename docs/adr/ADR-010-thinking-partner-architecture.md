# ADR-010: Thinking Partner as Primary Interface

**Status**: Draft for Discussion
**Date**: 2026-01-30
**Extends**: ADR-007 (Project Authority)
**Related**: ADR-009 (Work Orchestration)

---

## Context

ADR-007 gave Thinking Partner (TP) the ability to manage projects via tools. But TP's role is actually much larger than "chat assistant with some tools."

In practice, TP is:
- The **primary interface** users interact with
- The **orchestrator** that delegates to specialist agents
- The **reviewer** that helps users evaluate work outputs
- The **memory curator** that shapes what the system remembers
- The **proactive partner** that reaches out, not just responds

This ADR expands TP's architectural role to be the central nervous system of YARNNN.

---

## First Principles

### Principle 1: TP is the User's Proxy

Users shouldn't need to learn YARNNN's internal structure. They talk to TP, and TP handles the rest:
- "Research competitors" → TP delegates to Research Agent
- "What did you find?" → TP retrieves and summarizes outputs
- "That looks good" → TP approves on user's behalf
- "Remember this for later" → TP creates memory

**Implication**: TP needs authority over all system operations, acting as user's trusted delegate.

### Principle 2: Conversation is the Universal Interface

Everything should be expressible through conversation:
- Work requests ("help me with X")
- Work review ("show me what you found")
- Memory management ("remember/forget this")
- Preferences ("I prefer morning updates")
- Organization ("move this to project Y")

**Implication**: TP's tool set must be comprehensive, not just project CRUD.

### Principle 3: TP Understands Intent, Not Just Commands

Users speak naturally, not in system commands:
- "I need to prepare for Monday's board meeting"
  → TP infers: needs research + content + maybe a report
- "This is important"
  → TP infers: high importance memory, maybe schedule follow-up

**Implication**: TP must reason about user intent and translate to system operations.

### Principle 4: TP Maintains Continuity

TP isn't stateless Q&A. It maintains:
- Session continuity (within a conversation)
- Work continuity (across sessions—"how's that research going?")
- Relationship continuity (remembers user preferences, patterns)

**Implication**: TP needs access to work state, not just memory context.

### Principle 5: TP Can Act Asynchronously

TP isn't only reactive. It can:
- Follow up on pending work
- Remind about stale items
- Proactively surface relevant context
- Initiate conversations (via push channels)

**Implication**: TP has a "background self" that monitors and initiates.

---

## TP's Expanded Roles

### Role 1: Conversational Interface (Current)

What exists today:
- Chat with user
- Access memory context
- Manage projects (list/create/rename/update)
- Streaming responses with tool use

### Role 2: Work Orchestrator (New)

TP initiates and monitors work:

```
User: "Can you research the AI assistant market?"

TP thinks:
  - This is a research task
  - User is in project "Product Strategy"
  - Should create work intent for Research Agent

TP: "I'll start researching the AI assistant market. This might take a few minutes.
     I'll send you a summary when it's ready, or you can ask me 'how's the research going?'"

[TP calls: create_work_intent(goal="...", agent_type="research", ...)]
```

Tools needed:
- `create_work_intent` - Initiate work
- `get_work_status` - Check on running/pending work
- `get_work_outputs` - Retrieve completed outputs
- `cancel_work` - Stop pending/running work

### Role 3: Work Reviewer (New)

TP helps users evaluate and act on outputs:

```
User: "What did the research find?"

TP:
  [calls get_work_outputs(status="pending_review")]

TP: "Your competitor research found 5 main players in the AI assistant space:
     1. [Summary of finding 1]
     2. [Summary of finding 2]
     ...

     Would you like me to:
     - Approve this and add key points to your project context?
     - Request revisions with specific feedback?
     - Show more detail on any finding?"
```

```
User: "Looks good, approve it"

TP:
  [calls approve_work_output(output_id=..., promote_to_memory=true)]

TP: "Done! I've approved the research and added the key findings to your
     Product Strategy project context."
```

Tools needed:
- `approve_work_output` - Accept output, optionally promote to memory
- `reject_work_output` - Discard output with reason
- `request_revision` - Send feedback for re-work
- `promote_to_memory` - Extract specific content as memory

### Role 4: Memory Curator (Expanded)

Beyond automatic extraction, TP actively manages memory:

```
User: "Actually, that competitor analysis from last week is outdated now"

TP:
  [calls deactivate_memory(memory_id=..., reason="outdated")]

TP: "Got it, I've marked that as outdated. Want me to refresh the research?"
```

```
User: "Remember that our target market is enterprise, not SMB"

TP:
  [calls create_memory(content="Target market is enterprise, not SMB",
                       importance=0.9, scope="user")]

TP: "Noted! I'll keep this in mind across all your projects."
```

Tools needed:
- `create_memory` - Explicit memory creation
- `update_memory` - Modify existing memory
- `deactivate_memory` - Soft-delete with reason
- `search_memories` - Find specific memories
- `move_memory` - Change memory scope (user ↔ project)

### Role 5: Preference Manager (New)

TP helps users configure their experience:

```
User: "I'd prefer getting updates in the morning"

TP:
  [calls update_preferences(notification_time="09:00", timezone="Asia/Singapore")]

TP: "Updated! I'll send you updates around 9am Singapore time."
```

```
User: "Don't email me about small stuff, just important things"

TP:
  [calls update_preferences(email_threshold="high_importance_only")]

TP: "Got it. I'll only email you for high-priority items.
     You can always check in with me here for everything else."
```

Tools needed:
- `get_preferences` - View current settings
- `update_preferences` - Modify settings
- `set_quiet_hours` - Define do-not-disturb times
- `set_delivery_channel` - Email, in-app, digest preferences

### Role 6: Proactive Partner (New)

TP initiates contact, not just responds:

**Work Completion Notification:**
```
[Push/Email initiated by TP]

TP: "Your competitor research is ready! Here's a quick summary:
     - 5 major players identified
     - Key differentiator: [X]
     - Potential opportunity: [Y]

     Reply to discuss, or I'll keep this for when you're ready."
```

**Silence Check-in:**
```
[After 3 days of no interaction]

TP: "Hey! Just checking in. You had some research pending review
     from last week. Want me to summarize it, or is now not a good time?"
```

**Scheduled Digest:**
```
[Weekly digest email]

TP: "Here's your week with YARNNN:

     ✅ Completed: 2 research reports, 1 content draft
     ⏳ Pending review: Competitor analysis
     📅 Upcoming: Weekly market scan (Monday 9am)

     Reply to this email to chat with me about any of these."
```

This requires:
- Background job that "speaks as TP"
- Email/push templates that feel conversational
- TP session that can be resumed from async notification

---

## Tool Taxonomy

### Category 1: Project Management (ADR-007 ✅)
- `list_projects` ✅
- `create_project` ✅
- `rename_project` ✅
- `update_project` ✅
- `archive_project` (future)
- `merge_projects` (future)

### Category 2: Work Orchestration (ADR-009)
- `create_work_intent` - Start new work
- `get_work_status` - Check work state
- `list_pending_work` - What's waiting?
- `get_work_outputs` - Retrieve outputs
- `cancel_work` - Stop work
- `schedule_work` - Set up recurring work

### Category 3: Work Review
- `approve_work_output` - Accept output
- `reject_work_output` - Discard output
- `request_revision` - Ask for changes
- `promote_to_memory` - Extract to context

### Category 4: Memory Management
- `create_memory` - Add explicit memory
- `search_memories` - Find memories
- `update_memory` - Modify memory
- `deactivate_memory` - Soft-delete
- `move_memory` - Change scope
- `get_memory_stats` - Context health

### Category 5: User Preferences
- `get_preferences` - View settings
- `update_preferences` - Change settings
- `set_schedule_preference` - Timing preferences
- `set_notification_channel` - Delivery preferences

### Category 6: Context & Documents
- `list_documents` - View uploaded docs
- `get_document_summary` - Quick overview
- `search_document_content` - Find in docs
- `delete_document` - Remove document

---

## Entry Points

Users reach TP through multiple channels:

### 1. In-App Chat (Primary)
- Real-time conversation
- Full tool access
- Streaming responses
- Session continuity within day

### 2. Project Chat
- Scoped to project context
- Same TP, different context window
- Project memories prioritized

### 3. Global Chat (Dashboard)
- User-level context only
- Cross-project conversations
- "Meta" discussions about organization

### 4. Email Reply
- User replies to TP notification
- Parsed and routed to TP
- Response sent back via email
- Creates/continues session

### 5. Push Notification Response
- User taps notification
- Opens app to relevant context
- Continues conversation

### 6. TP-Initiated (Proactive)
- TP sends first message
- Work completion, reminders, check-ins
- User can respond or ignore

---

## Authority Levels

Not all TP actions are equal. Define authority levels:

### Level 1: Informational (Always Allowed)
- List projects, work, memories
- Search content
- Summarize outputs
- View preferences

### Level 2: Low-Stakes Mutations (Default Allowed)
- Create memories from conversation
- Create projects
- Update project descriptions
- Approve low-confidence outputs (with disclosure)

### Level 3: Medium-Stakes Mutations (Allowed, Transparent)
- Create work intents
- Approve/reject outputs
- Deactivate memories
- Update user preferences

### Level 4: High-Stakes Mutations (Confirm First)
- Delete projects
- Bulk memory operations
- Cancel running work
- Change notification settings significantly

### Level 5: Administrative (User Must Confirm)
- Merge projects
- Export data
- Account-level changes

TP should announce Level 3+ actions:
```
TP: "I'm going to approve this research and add the key findings to your
     project context. Let me know if you'd prefer to review first."

[Waits 3 seconds or for user input before executing]
```

---

## Session Model

### Within-Conversation Continuity
- Messages stored in `session_messages`
- Session scoped to (user, project|null, day)
- History loaded on conversation start
- Tools have access to session context

### Cross-Session Continuity
- Work state persists across sessions
- "How's that research going?" works anytime
- TP queries `work_executions` for status

### Async Continuity
- TP notifications reference session context
- User reply creates/continues session
- Background TP has read access to recent sessions

---

## Proactive TP Architecture

### Background TP Process

```
Cron: Every N minutes
    ↓
Check triggers:
    - Work completed? → Notify user
    - Work failed? → Notify with option to retry
    - Pending review > X days? → Reminder
    - User silent > Y days? → Check-in
    - Scheduled digest time? → Send digest
    ↓
For each trigger:
    Generate TP message (using same LLM)
    Send via appropriate channel (email/push/in-app)
    Log as TP-initiated message
```

### TP Voice Consistency

Proactive messages should sound like TP, not system notifications:

**Bad (system notification):**
```
Subject: Work Output Ready
Body: Your work output "Competitor Analysis" is ready for review.
      Click here to view.
```

**Good (TP voice):**
```
Subject: Your competitor research is ready!
Body: Hey! I finished looking into the AI assistant market.

      Quick highlights:
      - Found 5 major players
      - Biggest opportunity: [X]

      Want to dive deeper? Just reply to this email and we can discuss.
```

---

## TP System Prompt Structure

```markdown
# Thinking Partner System Prompt

You are the user's Thinking Partner in YARNNN - a context-aware AI work platform.

## Your Role

You are the **primary interface** between the user and the YARNNN system. You:
- Converse naturally and help users think through problems
- Delegate work to specialist agents (research, content, reporting)
- Help review and act on work outputs
- Manage the user's context (memories, projects, documents)
- Respect user preferences for communication and timing

## Your Capabilities

You have tools to:
1. **Manage projects**: list, create, rename, update, archive
2. **Orchestrate work**: create work requests, check status, retrieve outputs
3. **Review outputs**: approve, reject, request revisions, promote to memory
4. **Curate memory**: create, search, update, deactivate memories
5. **Manage preferences**: notification timing, delivery channels, quiet hours

## Authority Guidelines

- **Always do**: Informational queries, creating memories from conversation
- **Do with transparency**: Create work, approve outputs, update preferences
- **Confirm first**: Delete projects, bulk operations, significant preference changes

When taking actions, be transparent:
- "I'll start that research for you..."
- "I'm going to approve this and add it to your project context..."
- "Should I delete this project? This will also remove its memories."

## Context You Have

{context}

## Current User Preferences

{preferences}

## Active Work

{active_work_summary}
```

---

## Implementation Phases

### Phase 1: Work Orchestration Tools
- [ ] `create_work_intent` tool
- [ ] `get_work_status` tool
- [ ] `list_pending_work` tool
- [ ] `get_work_outputs` tool
- [ ] `cancel_work` tool

### Phase 2: Work Review Tools
- [ ] `approve_work_output` tool
- [ ] `reject_work_output` tool
- [ ] `request_revision` tool
- [ ] `promote_to_memory` tool

### Phase 3: Memory Management Tools
- [ ] `create_memory` tool (explicit)
- [ ] `search_memories` tool
- [ ] `deactivate_memory` tool
- [ ] `move_memory` tool

### Phase 4: Preference Tools
- [ ] `get_preferences` tool
- [ ] `update_preferences` tool
- [ ] Preference schema definition

### Phase 5: Proactive TP
- [ ] Background job infrastructure
- [ ] Work completion notifications
- [ ] Pending review reminders
- [ ] Weekly digest

### Phase 6: Multi-Channel
- [ ] Email reply parsing
- [ ] Push notification deep links
- [ ] Session continuity across channels

---

## Open Questions

1. **Tool explosion**: 20+ tools might overwhelm the LLM. Should we use tool categories or dynamic tool loading based on conversation context?

2. **Authority confirmation UX**: How does "confirm first" work in streaming? Pause stream and wait for user input?

3. **Proactive frequency**: How often is too often? Should TP learn from user response patterns?

4. **Email reply parsing**: Full NLP or simple intent detection? What if user's reply is ambiguous?

5. **TP personality**: Should TP have configurable personality/tone? Or consistent voice?

6. **Multi-user future**: When teams exist, does each user have their own TP relationship, or is TP shared?

---

## Relationship to ADR-009

ADR-009 (Work Orchestration) defines:
- WorkIntent, WorkExecution, WorkOutput models
- Queue processing architecture
- Scheduling infrastructure
- Delivery preferences

ADR-010 (this document) defines:
- How TP interacts with work orchestration
- TP's tools for work management
- TP's role in review/approval
- Proactive TP patterns

They are complementary:
- ADR-009 = the machinery
- ADR-010 = the interface to the machinery

---

## Service Layer Architecture

### The What vs How Distinction

**Architecture (What)** = Model B: Hierarchical Bounded Contexts
**Behavior (How)** = Model C: Dynamic Intent-Based Routing

This separation means:
- The data model has clear boundaries and ownership
- TP's behavior makes those boundaries feel fluid to users

### Hierarchical Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                          │
│                                                                 │
│  TP lives here by default                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  User Identity & Preferences                             │   │
│  │  - notification settings, timezone, quiet hours          │   │
│  │  - delivery channel preferences                          │   │
│  │  - TP relationship state                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  User-Level Memories (project_id = NULL)                 │   │
│  │  - preferences, facts about the user                     │   │
│  │  - cross-project knowledge                               │   │
│  │  - truly universal context                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  User-Level Documents (project_id = NULL)                │   │
│  │  - general reference materials                           │   │
│  │  - cross-project resources                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Cross-Project Work                                      │   │
│  │  - work that spans multiple projects                     │   │
│  │  - organization-level reports                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   PROJECT A     │  │   PROJECT B     │  │   PROJECT C     │
│                 │  │                 │  │                 │
│ • Memories      │  │ • Memories      │  │ • Memories      │
│ • Documents     │  │ • Documents     │  │ • Documents     │
│ • Work          │  │ • Work          │  │ • Work          │
│ • Outputs       │  │ • Outputs       │  │ • Outputs       │
│                 │  │                 │  │                 │
│ Isolated        │  │ Isolated        │  │ Isolated        │
│ bounded context │  │ bounded context │  │ bounded context │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### TP Operating Levels

TP can operate at different levels, but **always starts at orchestration layer**:

```
User opens YARNNN
    ↓
TP at Orchestration Layer (default home)
    ↓
User says something
    ↓
TP determines appropriate scope:
    │
    ├─→ "What projects do I have?"
    │     → Stay at orchestration layer
    │     → Query across all projects
    │
    ├─→ "Let's work on the API redesign"
    │     → Scope down to Project A
    │     → Load Project A context
    │     → Subsequent messages in project scope
    │
    ├─→ "Remember I prefer bullet points"
    │     → Stay at orchestration layer
    │     → Create user-level memory
    │
    ├─→ "Research competitors for Project B"
    │     → Create work scoped to Project B
    │     → TP can stay at orchestration or scope down
    │
    └─→ "Compare progress across all my projects"
          → Stay at orchestration layer
          → Cross-project query
```

### Context Loading by Level

**Orchestration Layer (no project scope):**
```python
context = {
    "user_memories": memories.where(project_id=NULL),
    "user_documents": documents.where(project_id=NULL),
    "all_projects": projects.list(),
    "active_work": work.where(status in [pending, running]),
    "pending_review": outputs.where(status=pending_review),
}
```

**Project Layer (scoped to project):**
```python
context = {
    "user_memories": memories.where(project_id=NULL),      # Always included
    "project_memories": memories.where(project_id=X),      # Project-specific
    "project_documents": documents.where(project_id=X),
    "project_work": work.where(project_id=X),
    "project_outputs": outputs.where(project_id=X),
}
```

### Scoping Behavior (The "How")

TP dynamically scopes based on conversation, but the architecture remains bounded:

**Explicit Scoping:**
- User clicks into a project → TP scoped to project
- User says "let's talk about Project X" → TP scopes to X
- User says "back to general" → TP returns to orchestration layer

**Implicit Scoping:**
- User asks about specific project content → TP infers scope
- User asks cross-project question → TP stays at orchestration
- New topic emerges → TP may suggest creating project

**Scope Transitions:**
```
TP: "I see you're asking about the API redesign. Want me to switch
     to that project so I have the full context?"

User: "Yes"

TP: [scopes to API Redesign project]
    "Got it, I'm now focused on API Redesign. I can see your
     design docs and the research we did last week."
```

### Document Upload Routing

Documents uploaded at different levels:

**At Orchestration Layer (Dashboard):**
```
User uploads document
    ↓
Document stored with project_id = NULL (user-level)
    ↓
TP: "I've added this to your general documents. Would you like me
     to move it to a specific project, or keep it as a cross-project
     reference?"
```

**Within Project:**
```
User uploads document
    ↓
Document stored with project_id = current_project
    ↓
TP: "Added to [Project Name]. I'll extract the key points and add
     them to your project context."
```

### Work Ownership

Work can be scoped to project or user-level:

**Project-Scoped Work:**
- Research for a specific project
- Content for project deliverables
- Project-specific reports

**User-Scoped Work (Orchestration Level):**
- Cross-project analysis
- Personal productivity reports
- Organization-wide research

```python
WorkIntent {
    user_id: required
    project_id: optional  # NULL = user-level work
    ...
}
```

### Session Architecture Refined

Sessions reflect the hierarchical structure:

```python
ChatSession {
    user_id: required
    project_id: optional      # NULL = orchestration layer session
    session_type: "thinking_partner"
    current_scope: "orchestration" | "project"
    ...
}
```

**Session Continuity Rules:**
- Orchestration-layer sessions are daily (one per day)
- Project sessions are daily per project
- Scope can change within session (tracked in messages)
- History includes scope transitions

### API Implications

**Current:**
- `POST /chat` - Global chat (orchestration layer)
- `POST /projects/{id}/chat` - Project chat

**Refined Understanding:**
- `POST /chat` - TP at orchestration layer, can scope dynamically
- `POST /projects/{id}/chat` - TP pre-scoped to project

Both use the same TP agent, just with different initial context loading.

### Why This Matters

1. **User-level is genuinely universal** - Not a "special project" but a true top layer
2. **Projects are isolated containers** - Clear boundaries for context, work, outputs
3. **TP navigates fluidly** - Users don't think about layers, TP handles routing
4. **Documents have clear homes** - Either user-level or project-level, not ambiguous
5. **Work can span or scope** - Flexibility for different work types
6. **Future-proof for teams** - Workspace layer can sit above user layer

---

## References

- ADR-007: Thinking Partner Project Authority
- ADR-009: Work and Agent Orchestration
- ADR-005: Unified Memory with Embeddings
- chat_companion: Proactive outreach patterns
- yarnnn-app-fullstack: Work supervision patterns
