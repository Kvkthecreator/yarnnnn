# YARNNN Essence v6.0

**Purpose**: Foundation document for fresh implementation
**Status**: Active
**Date**: 2026-01-28
**Updated**: 2026-02-23 (repositioned: context-powered autonomous AI)

---

## Core Thesis

YARNNN is an **autonomous AI system that works on your behalf** — powered by accumulated context from your real work platforms.

It connects to your tools (Slack, Gmail, Notion, Calendar), accumulates understanding of your work world over time, and uses that context to act autonomously: producing deliverables, surfacing signals, and operating as a thinking partner that already knows your world.

**The value proposition in one sentence:**
> AI that works autonomously on your behalf — and gets smarter the longer you use it, because it accumulates context from your actual work.

**What makes this different from every other AI tool:**
- **Autonomous output**: Produces work (reports, digests, briefs) on schedule without prompting
- **Persistent context**: Syncs continuously with your platforms — Slack, Gmail, Notion, Calendar
- **Accumulated intelligence**: Every sync cycle, every edit, every interaction deepens the system's understanding
- **Compounding moat**: 90 days of accumulated context is irreplaceable — the system becomes more valuable with tenure

**The insight**: Most AI tools are stateless — they forget everything between sessions. The few that persist data don't act on it autonomously. YARNNN does both: it accumulates context AND uses it to work independently. The accumulated context is what makes the autonomy meaningful rather than generic.

**The ClawdBot connection**: The demand signal that validated this thesis was ClawdBot/OpenClaw — millions of users demonstrated appetite for AI that persists and knows them. YARNNN is the professional evolution: persistence → understanding → autonomous work.

---

## The Three Pillars of Autonomy

YARNNN's autonomous capability rests on three pillars, each architecturally distinct:

### 1. Thinking Partner (TP) — The Intelligent Interface
An AI agent with real-time access to your synced platform context. Not a chatbot — a Claude Code-like agent with primitive-based tool use (Search, FetchPlatformContent, CrossPlatformQuery), sub-agent delegation, and web search. The TP already knows your work world before you say a word.

### 2. Deliverables — Autonomous Output
Scheduled, recurring work artifacts (reports, digests, briefs) produced without user prompting. Deliverables can be user-configured, analyst-suggested, or signal-emergent (triggered automatically when patterns are detected). Each version improves through a feedback loop where user edits become training data.

### 3. Context Accumulation — The Moat
Continuous platform sync (Slack, Gmail, Notion, Calendar) feeds a unified content layer (`platform_content`) with retention-based accumulation. Content that proves significant is retained indefinitely. Memory extraction distills patterns from conversations, feedback, and activity. The four-layer model (Memory → Activity → Context → Work) creates a compounding intelligence loop.

**The relationship between these pillars:**
- Context accumulation ENABLES meaningful autonomy (without context, autonomous output is generic)
- Deliverables are the primary expression of autonomy (push-based, scheduled, improving)
- TP is how the user supervises and steers the autonomous system
- Each pillar reinforces the others: more deliverable runs → more learning → better context → smarter TP → better deliverables

## The Supervision Model

YARNNN embodies a fundamental shift in how users relate to AI-assisted work:

**From**: User as operator (does the work, AI assists)
**To**: User as supervisor (AI does the work, user oversees)

| Dimension | First-Class Entity | User Relationship |
|-----------|-------------------|-------------------|
| **Data/Workflow** | Deliverables | Objects to supervise |
| **UI/Interaction** | TP (Thinking Partner) | Method of supervision |

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

## UI Scope (Review-First Supervision)

**Reference:** [ADR-021: Review-First Supervision UX](adr/ADR-021-review-first-supervision-ux.md)

The UI embodies two axioms from the supervision model:

| Axiom | Entity | UI Implication |
|-------|--------|----------------|
| **Data first-class** | Deliverables | Content is always visible, not hidden behind navigation |
| **Interaction first-class** | TP (Thinking Partner) | TP is present on every screen, not requiring navigation |

### The Review-First Principle

**When something needs attention, user lands directly on it.**

This inverts the traditional dashboard-first pattern:
- Traditional: Login → Dashboard → Find item → Click → Review
- YARNNN: Login → Review (the thing that needs attention)

### Primary View: Review (Supervision in Action)

```
┌─────────────────────────────────────────────────────────────┐
│ Weekly Status Report - Review                    [1 of 2] → │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Hi Sarah,                                                  │
│                                                             │
│  Here's the weekly update for Project Alpha...              │
│  [Full draft content - THE OBJECT BEING SUPERVISED]         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Refine with TP:                      [TP ALWAYS PRESENT]    │
│ [Shorter] [More detail] [More formal] [Custom...]           │
├─────────────────────────────────────────────────────────────┤
│ [Discard]                        [Skip] [Mark as Done]      │
└─────────────────────────────────────────────────────────────┘
```

When no items need review → Dashboard view (secondary).

### Secondary View: Dashboard (Nothing to Review)

```
┌─────────────────────────────────────────────────────────────┐
│  All caught up! Next deliverable in 3 days.                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Upcoming:                                                  │
│  • Weekly Status Report — Monday 9am                        │
│  • Monthly Investor Update — Feb 15                         │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 💬 Ask TP: "Create a new deliverable" / "Run now"      │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### TP Presence Rule

**TP must be visible and interactive on every screen.**

| Screen | TP Manifestation |
|--------|------------------|
| Review | Inline refinement chips + custom instruction input |
| Dashboard | Embedded input for questions/commands |
| Detail | Contextual chat for this deliverable |
| Browse | Global TP for cross-deliverable questions |

No screen should require navigation to access TP interaction.

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

1. ✅ User connects at least one platform (Slack, Gmail, Notion, Calendar)
2. ✅ Platform sync accumulates context continuously
3. ✅ TP agent has real-time access to synced context via primitives
4. ✅ User can create recurring deliverables (via wizard or TP)
5. ✅ System produces deliverable versions on schedule, autonomously
6. ✅ User can review, refine (via TP), and approve/reject versions
7. ✅ User edits are captured as feedback → memory extraction
8. ✅ Quality improves over time (edit distance decreases)
9. ✅ Context accumulation is visible to user (retention badges, quality trends)

### Core Quality Metrics:
- **Edit distance**: Between AI draft and user-approved final — should decrease over successive versions. Target: <10% edits by version 4.
- **Context depth**: Volume of retained platform_content records — should grow monotonically with tenure.
- **Autonomy ratio**: Proportion of deliverables approved without edits — should increase over time.

### Not MVP:
- ❌ Automated delivery (email/Slack send)
- ❌ Team collaboration
- ❌ Multiple workspaces
- ❌ Billing/subscriptions

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
