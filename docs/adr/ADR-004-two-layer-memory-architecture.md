# ADR-004: Two-Layer Memory Architecture

**Status:** Implemented
**Date:** 2025-01-29
**Supersedes:** Partially supersedes ADR-003 (extends, doesn't replace)
**Decision Makers:** Kevin Kim

## Context

Analysis of YARNNN's service philosophy revealed a tension:

1. **Brand promise**: "Your AI understands YOUR world" → implies holistic, user-level knowledge
2. **Work model**: "Structured outputs for projects" → requires project-scoped isolation

The current project-only architecture (`blocks` table scoped to `project_id`) cannot fulfill the brand promise. A user starting a new project has zero context - no cold start mitigation from accumulated knowledge.

Industry benchmarks (Mem0, Notion AI, Rewind) show that the leaders explicitly separate "knowing the user" from "knowing the task." This separation must be architectural.

## Decision

Implement a **two-layer memory architecture**:

1. **User Memory** (`user_context` table) - User-scoped, persistent, portable
2. **Project Memory** (`blocks` table) - Project-scoped, task-specific, isolated

### Layer 1: User Memory

**Purpose:** Capture what YARNNN knows about YOU across all projects.

**Categories** (7 total, adapted from Companion AI patterns + audit):

| Category | Description | Examples |
|----------|-------------|----------|
| `preference` | How user likes things done | "Prefers bullet points over prose" |
| `business_fact` | About user's company/domain | "Works in B2B SaaS", "Company is 50 people" |
| `work_pattern` | How user works | "Usually writes reports on Fridays" |
| `communication_style` | Tone and format preferences | "Prefers formal tone for external docs" |
| `goal` | User's objectives | "Trying to raise Series A" |
| `constraint` | Persistent limitations | "Small team, limited engineering resources" |
| `relationship` | People in user's professional orbit | "Works with Alice (designer)", "Mentor is Bob" |

**Characteristics:**
- Scoped to `user_id` (not workspace, not project)
- No expiration for core facts
- Upsert pattern: `(user_id, category, key)` prevents duplicates
- Importance scoring for retrieval prioritization
- Grows from ALL conversations across all projects

### Layer 2: Project Memory

**Purpose:** Capture what's specific to THIS project/deliverable.

**Semantic Types** (6 total, extended from ADR-003 + audit):

| Type | Description | Examples |
|------|-------------|----------|
| `requirement` | Must-have for this project | "Report needs executive summary" |
| `fact` | Project-specific information | "Client is Acme Corp" |
| `guideline` | Rules for this project | "Use their brand voice guide" |
| `insight` | Project-specific conclusions | "Their main concern is cost" |
| `question` | Open questions for this project | "Who is the final approver?" |
| `assumption` | Beliefs to be validated | "Assuming 3-week timeline", "Assuming HTML delivery" |

**Characteristics:**
- Scoped to `project_id`
- Can have expiration (time-bound context)
- Standard block model with semantic_type
- Isolated between projects (Client A context doesn't leak to Client B)

## Schema

### New: `user_context` Table

```sql
CREATE TABLE user_context (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Classification
    category TEXT NOT NULL,  -- preference, business_fact, work_pattern, communication_style, goal, constraint
    key TEXT NOT NULL,       -- Unique identifier within category (for upsert)

    -- Content
    content TEXT NOT NULL,

    -- Scoring
    importance FLOAT DEFAULT 0.5,      -- 0-1 for retrieval priority
    confidence FLOAT DEFAULT 0.8,      -- 0-1 how confident we are in this

    -- Source tracking
    source_type TEXT DEFAULT 'extracted',  -- extracted, explicit, inferred
    source_project_id UUID REFERENCES projects(id) ON DELETE SET NULL,  -- Where it came from (optional)

    -- Lifecycle
    last_referenced_at TIMESTAMPTZ,    -- When last used in context assembly
    reference_count INTEGER DEFAULT 0,  -- How often referenced
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Upsert constraint
    CONSTRAINT unique_user_context UNIQUE (user_id, category, key)
);

CREATE INDEX idx_user_context_user ON user_context(user_id);
CREATE INDEX idx_user_context_category ON user_context(category);
CREATE INDEX idx_user_context_importance ON user_context(importance DESC);
```

### RLS Policy

```sql
ALTER TABLE user_context ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own context"
    ON user_context FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());
```

## Extraction Logic

### Dual-Stream Extraction

When extracting from a conversation, the extraction service must classify each item:

```python
DUAL_EXTRACTION_PROMPT = """Analyze this conversation and extract TWO types of context:

1. USER CONTEXT - Things about the USER that would be true across any project:
   - preference: How they like things done (format, style, presentation)
   - business_fact: About their company/domain (industry, scale, stage)
   - work_pattern: How they work (timing, rhythm, behavior)
   - communication_style: Tone/format preferences (voice, audience-aware)
   - goal: What they're trying to achieve (aspirations, strategy)
   - constraint: Persistent limitations (scarcity, boundaries)
   - relationship: People in their professional orbit (colleagues, mentors)

2. PROJECT CONTEXT - Things specific to THIS task/project:
   - requirement: Must-have for this deliverable
   - fact: Project-specific information
   - guideline: Rules for this project
   - insight: Conclusions about this project
   - question: Open questions/ambiguities
   - assumption: Beliefs to be validated (things taken as true without evidence)

For each item, specify:
- layer: "user" or "project"
- category/type: the specific classification
- key: a unique identifier (for user context deduplication)
- content: the actual information
- importance: 0.0-1.0

Return JSON with two arrays: user_items and project_items.
"""
```

### Taxonomy Design Rationale

The category taxonomy was audited against Companion AI and legacy YARN v3 implementations:

**Why deterministic categories (not flexible tagging):**
- Clean, queryable primary categories for retrieval
- Extraction is more reliable with constrained options
- 7+6 categories cover 90%+ of real-world items
- Can add optional `tags` field later if needed (YAGNI for now)

**Categories added from audit:**
- `relationship` (user): Critical for professional context; from Companion AI
- `assumption` (project): Distinct from facts; represents beliefs to validate

**Categories deferred:**
- `decision`: Handle as `fact` with metadata for now; defer to Phase 3 (block relations)
- `event`: Handle via `deadline_at` metadata on requirements, not a separate category

### Classification Examples

| Extracted Content | Layer | Category/Type | Key |
|-------------------|-------|---------------|-----|
| "Prefers bullet points over prose" | user | preference | format_preference |
| "Works at a B2B SaaS company" | user | business_fact | company_type |
| "Works closely with Alice on design" | user | relationship | colleague_alice |
| "Report is for board meeting Tuesday" | project | requirement | deadline |
| "Needs executive summary" | project | requirement | exec_summary |
| "Target audience is CTOs" | project | fact | audience |
| "Assuming we have 3 weeks" | project | assumption | timeline |
| "Likes to review drafts on Fridays" | user | work_pattern | review_timing |

## Context Assembly

### For ThinkingPartner

ThinkingPartner should receive BOTH layers:

```python
async def assemble_thinking_partner_context(user_id: str, project_id: str | None):
    """Assemble context for ThinkingPartner."""

    # Always include user context
    user_context = await get_user_context(user_id, max_items=20)

    # Include project context if in a project
    project_context = []
    if project_id:
        project_context = await get_project_blocks(project_id, max_items=30)

    return format_combined_context(user_context, project_context)
```

### For Work Agents

Work agents receive primarily project context, with optional user context:

```python
async def assemble_work_agent_context(user_id: str, project_id: str, include_user: bool = True):
    """Assemble context for work agent execution."""

    # Primary: project context
    project_context = await get_project_blocks(project_id, max_items=50)

    # Optional: user preferences for style/format
    user_context = []
    if include_user:
        user_context = await get_user_context(
            user_id,
            categories=['preference', 'communication_style'],
            max_items=10
        )

    return format_combined_context(user_context, project_context)
```

## UX Implications

### Current State
- User must be "in a project" to chat with ThinkingPartner
- New projects start with zero context

### Future State
- User can chat with ThinkingPartner WITHOUT project context (user-level conversation)
- New projects start with user context already available
- ThinkingPartner "knows you" from day one of a new project

### Migration Path

1. **Phase 1** (Now): Add `user_context` table, modify extraction to write to both layers
2. **Phase 2**: Modify ThinkingPartner to read user_context + project blocks
3. **Phase 3**: Add "global chat" (no project required) using only user_context
4. **Phase 4**: Add user context management UI (view/edit what YARNNN knows about you)

## Consequences

### Positive
- Fulfills brand promise: "Your AI understands YOUR world"
- Context compounds across projects
- Reduced cold start on new projects
- ThinkingPartner becomes truly personal
- Portable knowledge that follows the user

### Negative
- More complex extraction (must classify layer)
- Two tables to query for context assembly
- Must handle user context + project context formatting
- Privacy consideration: user context persists even if projects deleted

### Risks
- Over-extraction to user context (everything becomes "about the user")
- Under-extraction to user context (nothing learned about user)
- Classification errors (project fact stored as user fact or vice versa)

### Mitigations
- Tune extraction prompt with examples
- Allow user to move items between layers (future)
- Confidence scoring helps surface uncertain classifications

## Implementation Checklist

- [x] Create `user_context` table with RLS → `docs/database/003_user_context.sql`
- [x] Extend extraction service with dual-stream logic → `api/services/extraction.py`
- [x] Update extraction prompt for layer classification → `DUAL_EXTRACTION_PROMPT`
- [x] Modify ThinkingPartner context assembly → `api/agents/thinking_partner.py`
- [x] Update chat route to pass user_id for extraction → `api/routes/chat.py`
- [x] Add user context retrieval service → `load_user_context_only()`
- [x] Add global chat endpoint → `POST /api/chat`
- [x] Add user context management UI → `web/components/UserContextPanel.tsx`
- [x] Add user context API endpoints → `api/routes/context.py` (list, update, delete)

## References

- [ADR-003: Context & Memory Architecture](ADR-003-context-memory-architecture.md)
- [First Principles Analysis](../analysis/memory-architecture-first-principles.md)
- Companion AI Memory Architecture (three-tier memory, preference extraction)
- Mem0 Multi-Level Memory Hierarchy
