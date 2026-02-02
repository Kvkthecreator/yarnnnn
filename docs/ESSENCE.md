# YARNNN Essence v5.1

**Purpose**: Foundation document for fresh implementation
**Status**: Active
**Date**: 2026-01-28
**Updated**: 2026-02-02 (added supervision model)

---

## Core Thesis

YARNNN is a **recurring deliverables platform**. AI produces scheduled work artifacts (reports, updates, briefs) that improve over time through user feedback.

**The value proposition in one sentence:**
> Your recurring deliverables, produced and improving every cycle. Set up once, refine over time, never start from scratch again.

**What makes this different from ChatGPT/Claude directly:**
- Recurring scheduled outputs (not one-off conversations)
- Accumulated context that makes the 10th delivery better than the 1st
- Feedback loop: user edits train the system
- Quality metrics: measurable improvement over time

---

## The Supervision Model

YARNNN embodies a fundamental shift in how users relate to AI-assisted work:

**From**: User as operator (does the work, AI assists)
**To**: User as supervisor (AI does the work, user oversees)

This has specific architectural implications:

| Dimension | First-Class Entity | User Relationship |
|-----------|-------------------|-------------------|
| **Data/Workflow** | Deliverables | Objects to supervise |
| **UI/Interaction** | TP (Thinking Partner) | Method of supervision |

- **Deliverables** = what the user supervises (versions, quality, feedback)
- **TP** = how the user supervises (refinement, delegation, conversation)

Both are first-class in their respective dimensions. Neither is subordinate to the other.

See [Design Principle: Supervision Model](design/DESIGN-PRINCIPLE-supervision-model.md) for full framework.

---

## Domain Model (7 Entities)

```
┌─────────────────────────────────────────────────────────────┐
│                        WORKSPACE                             │
│  (multi-tenancy root - one per user/org)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         PROJECT                              │
│  User's work container. Has context + agents + outputs.     │
│                                                              │
│  Fields: id, name, description, workspace_id, created_at    │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     BLOCKS      │  │   DOCUMENTS     │  │  WORK_TICKETS   │
│                 │  │                 │  │                 │
│ Atomic knowledge│  │ Uploaded files  │  │ Work requests   │
│ units (text,    │  │ (PDF, DOCX)     │  │ with lifecycle  │
│ structured)     │  │ parsed → blocks │  │                 │
│                 │  │                 │  │ pending →       │
│ id, content,    │  │ id, filename,   │  │ running →       │
│ block_type,     │  │ file_url,       │  │ completed       │
│ project_id,     │  │ project_id,     │  │                 │
│ metadata        │  │ parsed_blocks[] │  │ id, task,       │
│                 │  │                 │  │ agent_type,     │
└─────────────────┘  └─────────────────┘  │ project_id      │
        │                                  └─────────────────┘
        │                                          │
        ▼                                          ▼
┌─────────────────┐                      ┌─────────────────┐
│ BLOCK_RELATIONS │                      │  WORK_OUTPUTS   │
│                 │                      │                 │
│ Semantic links  │                      │ Agent products  │
│ between blocks  │                      │ (files, text)   │
│                 │                      │                 │
│ source_id,      │                      │ id, title,      │
│ target_id,      │                      │ output_type,    │
│ relation_type   │                      │ file_url,       │
│                 │                      │ ticket_id       │
└─────────────────┘                      └─────────────────┘
                                                  │
                                                  ▼
                                         ┌─────────────────┐
                                         │ AGENT_SESSIONS  │
                                         │                 │
                                         │ Execution logs  │
                                         │ for provenance  │
                                         │                 │
                                         │ id, agent_type, │
                                         │ ticket_id,      │
                                         │ messages[]      │
                                         └─────────────────┘
```

### Entity Definitions

| Entity | Purpose | Key Fields |
|--------|---------|------------|
| **workspace** | Multi-tenant isolation | id, name, owner_id |
| **project** | User's work container | id, name, workspace_id |
| **block** | Atomic knowledge unit | id, content, block_type, project_id, metadata |
| **document** | Uploaded file reference | id, filename, file_url, project_id |
| **block_relation** | Semantic link | source_id, target_id, relation_type |
| **work_ticket** | Work request lifecycle | id, task, agent_type, status, project_id |
| **work_output** | Agent deliverable | id, title, output_type, file_url, ticket_id |
| **agent_session** | Execution log | id, agent_type, ticket_id, messages |

### Relationships

```
workspace 1──n project
project   1──n block
project   1──n document
project   1──n work_ticket
block     n──n block (via block_relation)
work_ticket 1──n work_output
work_ticket 1──1 agent_session
```

---

## Agent Architecture (4 Types)

### Agent Types

| Agent | Purpose | Input | Output |
|-------|---------|-------|--------|
| **Research** | Investigate topics using context | Query + context blocks | Research summary (markdown) |
| **Content** | Create content from context | Brief + context blocks | Content draft (markdown/doc) |
| **Reporting** | Generate structured reports | Parameters + context | Report file (PDF/PPTX) |
| **Thinking Partner** | Conversational assistant | Chat + optional context | Chat responses |

### Execution Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                     AGENT EXECUTION                          │
└─────────────────────────────────────────────────────────────┘

1. CONTEXT LOADING
   ┌──────────────┐
   │ work_ticket  │ ──→ load project_id
   └──────────────┘           │
                              ▼
                    ┌──────────────────┐
                    │ SELECT * FROM    │
                    │ blocks WHERE     │
                    │ project_id = ?   │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ context_bundle   │
                    │ (blocks + docs)  │
                    └──────────────────┘

2. AGENT EXECUTION
   ┌──────────────────┐
   │ AgentFactory     │
   │ .create(type)    │ ──→ Research | Content | Reporting | TP
   └──────────────────┘
            │
            ▼
   ┌──────────────────┐
   │ agent.execute(   │
   │   task,          │
   │   context_bundle │
   │ )                │
   └──────────────────┘
            │
            ▼
   ┌──────────────────┐
   │ LLM API call     │
   │ (Claude/GPT/     │
   │  Gemini)         │
   └──────────────────┘

3. OUTPUT CAPTURE
   ┌──────────────────┐
   │ agent response   │
   └──────────────────┘
            │
            ▼
   ┌──────────────────┐
   │ work_output      │
   │ .create(         │
   │   ticket_id,     │
   │   content/file   │
   │ )                │
   └──────────────────┘
```

### Agent Interface (Pseudocode)

```python
class BaseAgent:
    async def execute(
        self,
        task: str,
        context: ContextBundle,
        parameters: dict
    ) -> AgentResult:
        """
        1. Build system prompt with context
        2. Call LLM
        3. Parse response
        4. Return structured result
        """
        pass

class ResearchAgent(BaseAgent):
    """Deep investigation using context as source material"""

class ContentAgent(BaseAgent):
    """Content creation using context for voice/facts"""

class ReportingAgent(BaseAgent):
    """Structured report generation (PPTX, PDF)"""

class ThinkingPartnerAgent(BaseAgent):
    """Conversational, maintains chat history"""
```

---

## Data Flow

### Happy Path: Create Report from Context

```
USER ACTION                    SYSTEM RESPONSE
───────────────────────────────────────────────────────────

1. Add context
   "Upload quarterly_data.pdf"  → Parse PDF
                                → Create blocks[]
                                → Store in project

2. Request work
   "Create executive summary"   → Create work_ticket
                                → Status: pending

3. Execute agent
   (automatic or triggered)     → Load context (blocks)
                                → Call ReportingAgent
                                → Generate PPTX
                                → Status: completed

4. Receive output
   "Download report"            → work_output.file_url
                                → Provenance: ticket → session → blocks
```

### API Surface (Minimal)

```
# Context
POST   /api/projects/:id/blocks      # Add block
POST   /api/projects/:id/documents   # Upload document
GET    /api/projects/:id/context     # Get all context

# Work
POST   /api/projects/:id/tickets     # Create work request
GET    /api/projects/:id/tickets     # List tickets
GET    /api/tickets/:id              # Get ticket + outputs

# Agents
POST   /api/tickets/:id/execute      # Run agent (or auto-trigger)

# Chat (Thinking Partner)
POST   /api/projects/:id/chat        # Send message
GET    /api/projects/:id/chat        # Get history
```

---

## Learned Constraints

From building v4, these are non-negotiable:

### 1. Schema Alignment
**Problem**: Frontend sent `work_session_id`, backend expected `work_ticket_id`
**Lesson**: Single source of truth for field names. No aliases.

### 2. Recipe Parameters
**Problem**: Frontend form values weren't passed to backend
**Lesson**: Always pass full parameter objects, not just IDs.

### 3. Progress Tracking
**Problem**: Long-running agents gave no feedback
**Lesson**: Emit progress events (SSE or websocket). Users need to see something happening.

### 4. Output Capture
**Problem**: Agents ran but outputs weren't saved
**Lesson**: Explicit `emit_work_output()` call, not implicit. Make it impossible to forget.

### 5. Context Loading
**Problem**: Agents had no context, produced generic outputs
**Lesson**: Context must load BEFORE agent execution. Never optional.

### 6. Auth Token Flow
**Problem**: User JWT not passed through service-to-service calls
**Lesson**: Extract token once, pass explicitly. Don't rely on request context.

### 7. Error Visibility
**Problem**: 500 errors with no details
**Lesson**: Log full stack traces. Return structured error responses.

### 8. Database Migrations
**Problem**: Migration files existed but weren't applied
**Lesson**: CI/CD must run migrations. Manual = forgotten.

### 9. File Generation
**Problem**: PPTX generation via Skills tool was fragile
**Lesson**: Use proven libraries (python-pptx) directly. Don't abstract too early.

### 10. Session Management
**Problem**: Agent sessions weren't persisted for debugging
**Lesson**: Always save agent_session with full message history.

---

## What NOT to Build (Yet)

These add complexity without current user demand:

| Feature | Why Not Yet |
|---------|-------------|
| **Agent Marketplace** | No users to buy/sell agents |
| **Multi-workspace governance** | No enterprise customers |
| **Complex checkpoint workflows** | Simple approve/reject is enough |
| **Integration tokens** | Users aren't asking for API access |
| **MCP server** | OpenAI Apps integration not priority |
| **Subscription/billing** | Premature until product-market fit |
| **Team collaboration** | Single-user is fine for MVP |
| **Semantic relationship graphs** | Block list is sufficient |
| **P0-P4 pipeline** | Single-pass extraction works |

**Rule**: If no user has asked for it, don't build it.

---

## Tech Stack (Simplified)

### Backend
```
FastAPI (single app)
├── /api/context     # Block/document CRUD
├── /api/work        # Ticket lifecycle
├── /api/agents      # Execution
└── /api/chat        # Thinking Partner

Supabase
├── PostgreSQL (database)
├── Auth (JWT)
├── Storage (file uploads)
└── RLS (row-level security)
```

### Frontend
```
Next.js 14
├── /app
│   ├── /dashboard          # Project list
│   ├── /projects/[id]
│   │   ├── /context        # View/add blocks
│   │   ├── /work           # Tickets + outputs
│   │   └── /chat           # Thinking Partner
│   └── /auth               # Login/signup
└── shadcn/ui components
```

### Infrastructure
```
Single Render service (or Vercel + Railway)
Single Supabase project
No service-to-service calls
No separate BFF layer
```

---

## UI Scope (Supervision Model)

The UI reflects the supervision model: deliverables are visible objects, TP is the interaction method.

### Primary View: Deliverables Dashboard (What User Supervises)

```
┌─────────────────────────────────────────────────────────────┐
│  DELIVERABLES                                    [+ New] 💬 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📋 Weekly Status Report              Due: Tomorrow   │   │
│  │    → Staged for review                               │   │
│  │    Quality: ████████░░ 82% (improving)              │   │
│  │    [Review Now]                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📋 Monthly Investor Update           Due: Feb 15     │   │
│  │    → Next run in 13 days                            │   │
│  │    Quality: ██████░░░░ 65%                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                                            💬 = Floating TP
```

### Review View: Deliverable + TP Refinement (Supervision in Action)

```
┌─────────────────────────────────────────────────────────────┐
│ ← Weekly Status Report - Review                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Draft content displayed - the object being supervised]    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Refine with AI:                        [TP interaction]     │
│ [Shorter] [More detail] [More formal] [More casual]         │
│ ┌────────────────────────────────────────────┐ [Send]       │
│ │ Or tell me what to change...               │              │
│ └────────────────────────────────────────────┘              │
├─────────────────────────────────────────────────────────────┤
│ [Discard]                        [Cancel] [Mark as Done]    │
└─────────────────────────────────────────────────────────────┘
```

### TP Availability

TP manifests in two ways:
1. **Inline refinements** - embedded in deliverable views (chips, custom instructions)
2. **Floating chat** - available via 💬 trigger for conversational interaction

Both are TP; they serve different interaction needs.

---

## Migration Path

### From v4 Codebase

**Keep (extract and adapt):**
- Supabase auth configuration
- Agent SDK adapters (Claude, GPT)
- File parsing logic (PDF → blocks)
- PPTX generation code

**Reference only:**
- Schema patterns (not actual migrations)
- Error handling patterns
- SSE progress streaming

**Abandon:**
- Dual API architecture
- 60+ unused tables
- Scaffolded frontend routes
- MCP infrastructure
- Governance layer

---

## Success Metrics

### MVP is complete when:

1. ✅ User can create recurring deliverable (via wizard or TP)
2. ✅ System produces deliverable versions on schedule
3. ✅ User can review staged versions
4. ✅ User can refine via TP (inline or conversational)
5. ✅ User edits are captured as feedback
6. ✅ User can approve/reject versions
7. ✅ Quality improves over time (edit distance decreases)
8. ✅ User can export approved deliverables

### Core Quality Metric:
- Edit distance between AI draft and user-approved final
- Should decrease over successive versions
- Target: <10% edits by version 4

### Not MVP:
- ❌ Automated delivery (email/Slack send)
- ❌ Team collaboration
- ❌ Multiple workspaces
- ❌ Billing/subscriptions
- ❌ External integrations

---

## Next Steps

1. **Create new repository**: `yarnnn` (clean slate)
2. **Copy this document** as `/docs/ESSENCE.md`
3. **Create minimal schema**: 8 tables, one migration file
4. **Scaffold FastAPI**: Single app, 4 route groups
5. **Scaffold Next.js**: 3 tabs, shadcn/ui
6. **Port auth**: Copy Supabase config directly
7. **Port one agent**: Research agent, end-to-end
8. **Iterate**: Add agents, polish UI

---

*This document is the specification. The old codebase is reference material.*
