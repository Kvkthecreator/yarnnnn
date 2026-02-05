# ADR-025: Claude Code Agentic Alignment

**Status:** Proposed
**Date:** 2026-02-05
**Extends:** ADR-010 (Thinking Partner Architecture), ADR-018 (Recurring Deliverables)
**Related:** ADR-019 (Deliverable Types), ADR-023 (Supervisor Desk)

---

## Context

### How We Got Here

While planning the "deliverable roll-up" feature—making TP's deliverable creation process more visible and auditable—we initially explored several reinterpretation approaches:

1. "Thinking Traces" - custom progress tracking
2. "Deliverable Skills" - reimagined workflow system
3. "Full Agentic Loop" - new schema for work sessions

Each involved designing new concepts that paralleled existing, proven patterns. The question emerged:

**Why wouldn't TP just be Claude Code's agentic loop, adapted for YARNNN's domain?**

### The Claude Code Pattern

Claude Code implements a disciplined agentic workflow:

```
User request
    ↓
TodoWrite (plan the work, track progress)
    ↓
Tool execution loop (Read, Edit, Bash, etc.)
    ↓
Check assumptions → revise todos if wrong
    ↓
Mark complete → move to next
    ↓
Skills (/commit, /review-pr) as packaged workflows
```

### What YARNNN's TP Currently Does

```
User request
    ↓
Parse intent (implicit, in system prompt)
    ↓
Maybe clarify()
    ↓
Single tool call (create_deliverable)
    ↓
respond() with confirmation
```

TP has the infrastructure for agentic operation:
- Tool definitions ✓
- Tool execution loop with `max_iterations` ✓
- Streaming with tools ✓
- Context injection ✓

But it lacks the **discipline** of the pattern:
- No explicit task tracking
- No plan/execute mode distinction
- No skills as packaged workflows
- No iterative "check → revise → continue" loop

### The Claude Agent SDK Signal

Anthropic's release of the Claude Agent SDK confirms this pattern as the canonical approach. The SDK is essentially "Claude Code's loop, wired up for developers." This validates:

1. The pattern works at scale
2. It's the direction Anthropic is standardizing on
3. Tools built on this pattern will have ecosystem alignment

---

## Decision

### Wholehearted Commitment, Not Half Measures

We will align TP's architecture with Claude Code's agentic pattern. This is not a partial adoption or reinterpretation—it's a commitment to use the same primitives:

| Claude Code | YARNNN TP |
|-------------|-----------|
| `TodoWrite` | `todo_write` tool for TP |
| Skills (`/commit`, `/review-pr`) | `/board-update`, `/status-report`, `/research-brief` |
| Plan mode | Explicit planning phase before complex work |
| Tool execution loop | Already exists, enhance with discipline |
| Context (codebase) | Context (memories + project + deliverables) |

### Core Principle

**TP becomes YARNNN's instantiation of the Claude Code pattern, specialized for recurring deliverables and supervision workflows.**

The unique aspects YARNNN adds:
- Domain context (memories, projects, deliverable history)
- Supervision UI/UX (review surfaces, approval flows)
- Feedback loop (edit capture, preference learning)
- Scheduling (recurring execution)

But the agentic core is Claude Code's pattern, not a reimagination of it.

---

## Specification

### 1. TodoWrite for TP

Add `todo_write` tool that mirrors Claude Code's behavior:

```python
TODO_WRITE_TOOL = {
    "name": "todo_write",
    "description": """Track and update task progress for multi-step work.

Use this when:
- Setting up a new deliverable (multiple steps involved)
- Executing a complex user request
- Any work requiring 3+ steps

Task states:
- pending: Not yet started
- in_progress: Currently working on (only ONE at a time)
- completed: Finished successfully

Always:
- Create todos at the start of multi-step work
- Update status as you progress
- Mark complete immediately when done (don't batch)
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}
                    },
                    "required": ["content", "status"]
                }
            }
        },
        "required": ["todos"]
    }
}
```

Todos are stored in the session/conversation context, not persisted to database (matching Claude Code).

### 2. Skills as Slash Commands

Deliverable types (ADR-019) become invocable skills:

| Skill | Trigger | Expands To |
|-------|---------|------------|
| `/board-update` | User types or TP recognizes intent | Board update creation workflow |
| `/status-report` | User types or TP recognizes intent | Status report creation workflow |
| `/research-brief` | User types or TP recognizes intent | Research brief creation workflow |
| `/run-deliverable` | User wants to generate now | Trigger pipeline execution |

Skills are prompt expansions + expected tool sequences, not new code paths.

**Skill definition structure:**

```python
SKILLS = {
    "board-update": {
        "trigger_patterns": ["board update", "investor update", "board report"],
        "system_prompt_addition": """
## Skill: Board Update Creation

You are helping the user create a recurring board update deliverable.

Expected workflow:
1. todo_write: Plan the setup steps
2. Gather: company name, stage, recipient, frequency
3. Confirm: State what you'll create
4. Create: create_deliverable with type=board_update
5. Offer: Generate first draft?

Use clarify() for missing required info. Don't guess.
""",
        "deliverable_type": "board_update",
        "required_fields": ["company_name", "recipient_name", "frequency"],
    },
    # ... other skills
}
```

### 3. Plan/Execute Discipline

For complex requests, TP explicitly enters planning mode:

**System prompt addition:**

```markdown
## Plan/Execute Pattern

For simple requests (single clear action): Execute directly.

For complex requests (deliverable setup, multi-step work):
1. PLAN: Use todo_write to outline steps
2. SHARE: Briefly tell user what you'll do
3. EXECUTE: Work through todos, updating status
4. CONFIRM: Summarize what was done

The user should see your progress. This builds trust and enables supervision.
```

### 4. Iterative Check/Revise Loop

TP should verify assumptions and revise approach when needed:

```markdown
## Assumption Checking

Before executing each major step:
- Verify context is what you expected
- If something is missing or different, update todos
- Don't proceed with wrong assumptions

Example:
- Plan says "use PayFlow project context"
- list_projects shows no PayFlow project
- Revise: add step to create project OR clarify with user
```

---

## Implementation Plan

### Validation Phase (Do First)

**Goal:** Test the pattern works before full commitment.

1. **Add `todo_write` tool to TP**
   - Add tool definition to `project_tools.py`
   - Add handler (stores in session context)
   - Update system prompt to use it for multi-step work
   - Test with manual deliverable creation

2. **Implement single skill: `/board-update`**
   - Create skill definition structure
   - Add skill expansion logic
   - Test end-to-end flow
   - Verify todos + skill feel coherent

**Success criteria:**
- TP naturally uses todos for deliverable setup
- Skill invocation feels like Claude Code's `/commit`
- User can see progress through the workflow
- "Receipt" (todo history) is visible/auditable

### Full Rollout (After Validation)

If validation confirms the pattern works:

3. **Port all deliverable types as skills**
   - `/status-report`
   - `/stakeholder-update`
   - `/research-brief`
   - `/meeting-summary`
   - Beta tier skills

4. **Add plan mode for complex requests**
   - Detection logic for "complex" requests
   - Plan display in UI (TodoList component)
   - Edit/approve plan before execution

5. **Enhance tool loop with check/revise**
   - Assumption verification prompts
   - Graceful todo revision
   - Better error recovery

6. **UI integration**
   - Todo progress display in TPBar or surface
   - Skill picker / autocomplete
   - Execution history view ("receipts")

---

## Schema Changes

### Minimal (Validation Phase)

None required. Todos live in session context (memory), matching Claude Code.

### Optional (Full Rollout)

If we want persistent receipts/audit trails:

```sql
-- Optional: Persist skill executions for audit
CREATE TABLE skill_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    skill_name TEXT NOT NULL,
    session_id UUID,
    todos JSONB, -- Final todo state
    tool_calls JSONB, -- Sequence of tools used
    deliverable_id UUID REFERENCES deliverables(id), -- If applicable
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

This is additive and can be deferred.

---

## Consequences

### Positive

1. **Proven pattern** - Claude Code works. We inherit validated UX.

2. **SDK alignment** - TP speaks the same language as Claude Agent SDK. Future interoperability.

3. **Skill ecosystem** - Path to user-created/shared skills. "Here's my investor update skill."

4. **Transparency** - Users see what TP is doing. Supervision model made tangible.

5. **Debugging** - Todo history + tool log = clear audit trail.

6. **Reduced design burden** - We're porting, not inventing.

### Negative

1. **System prompt complexity** - More instructions for TP to follow.

2. **Potential over-engineering** - Simple requests don't need todos. Need good heuristics.

3. **UI work** - Todos need to be displayed somewhere.

### Risks

1. **Pattern mismatch** - Claude Code is for coding; YARNNN is for deliverables. Some adaptation needed.

2. **Performance** - More tool calls = more latency. Monitor.

---

## Alternatives Considered

### A: Custom "Thinking Traces"
Design our own progress tracking system.
**Rejected:** Why invent when proven pattern exists?

### B: "Deliverable Skills" as New Concept
Create skill-like system with different semantics.
**Rejected:** Unnecessary divergence from standard.

### C: Minimal Changes Only
Just improve prompts, no structural changes.
**Rejected:** Doesn't address core opacity problem.

### D: Full Custom Agentic Framework
Build comprehensive agent orchestration from scratch.
**Rejected:** Over-engineering. Claude Code pattern is sufficient.

---

## Open Questions

1. **Skill discovery** - How do users learn what skills exist? Autocomplete? Help menu?

2. **Skill customization** - Can users modify skill parameters? Create custom skills?

3. **Todo UI placement** - In TPBar? Floating panel? Dedicated surface?

4. **Persistence scope** - Session-only todos vs. persisted receipts?

5. **Cross-skill workflows** - Can skills invoke other skills?

---

## References

- Claude Code source patterns (TodoWrite, Skills, Plan mode)
- [Claude Agent SDK documentation](https://docs.anthropic.com/en/docs/agents-and-tools/claude-agent-sdk)
- ADR-010: Thinking Partner Architecture
- ADR-019: Deliverable Types System
- ADR-023: Supervisor Desk Architecture

---

## Appendix: Example Flow with Full Pattern

**User:** "I need to send monthly updates to my board of directors"

**TP with Claude Code alignment:**

```
TP: [todo_write]
    1. ☐ Parse intent (board update, monthly)
    2. ☐ Find or confirm project context
    3. ☐ Gather required details (company, recipient)
    4. ☐ Confirm deliverable setup
    5. ☐ Create deliverable
    6. ☐ Offer first draft generation

TP: [todo_write: #1 → completed, #2 → in_progress]

TP: [list_projects]
    → Returns: [{name: "PayFlow", id: "..."}]

TP: [todo_write: #2 → completed, #3 → in_progress]

TP: [respond]
    "I'll set up a Monthly Board Update using your PayFlow context.

    Quick questions:
    - Who's the primary recipient? (e.g., 'Marcus Webb' or 'the board')
    - What company stage? (seed, Series A, etc.)"

User: "Marcus Webb at Sequoia, we're Series A"

TP: [todo_write: #3 → completed, #4 → in_progress]

TP: [respond]
    "Got it. I'll create:

    **Monthly Board Update**
    - For: Marcus Webb (Sequoia)
    - Company: PayFlow (Series A)
    - Schedule: 1st of each month, 9am
    - Sections: Executive summary, metrics, progress, challenges, asks, outlook

    Ready to set this up?"

User: "yes"

TP: [todo_write: #4 → completed, #5 → in_progress]

TP: [create_deliverable]
    title: "Monthly Board Update"
    type: "board_update"
    frequency: "monthly"
    ...

TP: [todo_write: #5 → completed, #6 → in_progress]

TP: [respond]
    "Done! Your Monthly Board Update is set up.

    ✓ Created deliverable
    ✓ Linked to PayFlow context (8 memories)
    ✓ Scheduled for 1st of each month

    Want me to generate the first draft now?"
```

**The "receipt":** The todo progression + tool calls are the audit trail. User saw each step. They know exactly what happened.

---

## Frontend Integration (ADR-023 Alignment)

The Claude Code pattern requires UI surfaces that display progress, todos, and conversation history. This section specifies how these integrate with the existing Supervisor Desk architecture (ADR-023).

### Design Principle: Preserve What Works

ADR-023's core insights remain valid:
- **One surface at a time** — The supervisor desk model
- **TP-first interaction** — Tool results trigger surface changes
- **Attention queue** — Staged deliverables surface naturally
- **Domain browser escape hatch** — User can navigate directly

We're not replacing ADR-023. We're specifying how the Claude Code pattern **manifests within** its surfaces.

### The Two Modes of TP Interaction

**Mode 1: Ambient TP (Current TPBar)**

For simple, single-turn interactions:
- "What's my next deliverable?"
- "Show me my memories"
- "Pause the weekly report"

TPBar remains as-is:
- Bottom input bar
- Status display for thinking/streaming/clarify
- Brief message history toggle

**Mode 2: Working TP (New: Chat + Todos Panel)**

For multi-step work where TP is actively building something:
- Creating a new deliverable
- Executing a skill (`/board-update`)
- Any operation that triggers `todo_write`

This requires a **richer interface** that shows:
- Full conversation history (not just 3 messages)
- Todo list with live progress
- The "receipt" of what happened

### DeliverableDetailSurface Evolution

When TP is actively working on a deliverable (or creating one), the `deliverable-detail` surface evolves:

**Current Layout:**
```
┌─────────────────────────────────────────────────┐
│ Header (title, schedule, pause/settings)        │
├─────────────────────────────────────────────────┤
│ Status Cards                                    │
│ Run Now Button                                  │
│ Latest Output Preview                           │
│ What It Generates                               │
│ Data Sources                                    │
│ Learned Preferences                             │
│ Version History                                 │
└─────────────────────────────────────────────────┘
          ┌─────────────────────────────────┐
          │ TPBar (input only)              │
          └─────────────────────────────────┘
```

**With Active TP Work:**
```
┌─────────────────────────────────────────────────┐
│ Header (title, schedule, pause/settings)        │
├──────────────────────┬──────────────────────────┤
│ Deliverable Info     │ TP Work Panel            │
│ (collapsed or        │                          │
│  left column)        │ ┌─ Todos ──────────────┐ │
│                      │ │ ✓ Parse intent       │ │
│ • Status Cards       │ │ ✓ Find project       │ │
│ • What It Generates  │ │ ● Gather details     │ │
│ • Data Sources       │ │ ○ Confirm setup      │ │
│ • Version History    │ │ ○ Create deliverable │ │
│                      │ └─────────────────────┘ │
│                      │                          │
│                      │ ┌─ Chat ──────────────┐ │
│                      │ │ TP: I'll help you   │ │
│                      │ │ set up a Monthly... │ │
│                      │ │                     │ │
│                      │ │ You: Marcus Webb... │ │
│                      │ │                     │ │
│                      │ │ TP: Got it. I'll    │ │
│                      │ │ create...           │ │
│                      │ └─────────────────────┘ │
│                      │                          │
│                      │ ┌─────────────────────┐ │
│                      │ │ [input field]       │ │
│                      │ └─────────────────────┘ │
└──────────────────────┴──────────────────────────┘
```

**When to show TP Work Panel:**
- TP has active todos (via `todo_write`)
- User explicitly opened chat (e.g., clicked "Ask TP about this")
- Skill invocation in progress

**When to collapse back to TPBar-only:**
- All todos completed and user dismissed panel
- User navigated away and back
- Session timeout/new session

### New Component: TPWorkPanel

```typescript
interface TPWorkPanelProps {
  // Current todo list (from TP context)
  todos: Todo[];

  // Full message history (not just 3)
  messages: TPMessage[];

  // Whether to show in expanded state
  expanded: boolean;

  // Callback to collapse
  onCollapse: () => void;
}

interface Todo {
  content: string;
  status: 'pending' | 'in_progress' | 'completed';
}
```

**Placement options:**

1. **Side panel on deliverable surface** (shown above) — Best for desktop
2. **Slide-up panel replacing surface content** — Best for mobile
3. **Floating drawer** — Alternative, but less integrated

Recommendation: **Side panel on deliverable-detail, slide-up elsewhere.** The deliverable surface is where most multi-step work happens.

### Skill Invocation UI

Skills can be invoked via:

1. **Direct typing:** `/board-update` in TPBar
2. **Intent recognition:** "I need a board update" → TP recognizes, may confirm
3. **UI affordance:** Skill picker in TPBar or deliverable creation flow

**Skill picker (optional, Phase 2):**
```
┌────────────────────────────────────────────────┐
│ What would you like to create?                 │
│                                                │
│ ┌──────────────┐ ┌──────────────┐             │
│ │ 📊           │ │ 📋           │             │
│ │ Board Update │ │ Status Report│             │
│ └──────────────┘ └──────────────┘             │
│                                                │
│ ┌──────────────┐ ┌──────────────┐             │
│ │ 🔬           │ │ 📝           │             │
│ │ Research     │ │ Meeting      │             │
│ │ Brief        │ │ Summary      │             │
│ └──────────────┘ └──────────────┘             │
│                                                │
│ Or describe what you need...                   │
│ [                                           ]  │
└────────────────────────────────────────────────┘
```

**For validation phase:** Skip skill picker. Just support `/command` syntax and intent recognition in natural language.

### Idle Surface Updates

When on `idle` surface (dashboard), skill invocations open a temporary "working" panel:

```
┌─────────────────────────────────────────────────┐
│ ✓ 4 active · ⏸ 1 paused · Next: Weekly Report  │
├─────────────────────────────────────────────────┤
│                                                 │
│ ┌─ Creating: Board Update ─────────────────┐   │
│ │                                          │   │
│ │ Todos:                                   │   │
│ │ ✓ Parse intent                           │   │
│ │ ● Gathering details...                   │   │
│ │ ○ Confirm setup                          │   │
│ │ ○ Create deliverable                     │   │
│ │                                          │   │
│ │ ────────────────────────────────────────│   │
│ │ TP: What's your company stage?           │   │
│ │                                          │   │
│ │ [Series A] [Series B] [Seed] [Growth]    │   │
│ └──────────────────────────────────────────┘   │
│                                                 │
│ ─── Upcoming Schedule ───                       │
│ ...                                             │
└─────────────────────────────────────────────────┘
```

The panel auto-expands when `todo_write` is called, providing visibility into TP's work without leaving the dashboard.

### State Management Updates

**TPContext additions:**

```typescript
interface TPState {
  messages: TPMessage[];
  isLoading: boolean;
  status: TPStatus;
  pendingClarification: {...} | null;

  // NEW: Claude Code alignment
  todos: Todo[];           // Current todo list
  workPanelExpanded: boolean;  // Whether to show work panel
  activeSkill: string | null;  // e.g., "board-update"
}

interface Todo {
  id: string;
  content: string;
  status: 'pending' | 'in_progress' | 'completed';
  activeForm?: string;  // "Gathering details" vs "Gather details"
}

// New action types
type TPAction =
  | { type: 'SET_TODOS'; todos: Todo[] }
  | { type: 'UPDATE_TODO'; id: string; status: Todo['status'] }
  | { type: 'SET_WORK_PANEL_EXPANDED'; expanded: boolean }
  | { type: 'SET_ACTIVE_SKILL'; skill: string | null }
  | ... // existing actions
```

**Handling `todo_write` tool results:**

When TP calls `todo_write`, the frontend receives the todos via SSE and updates `TPContext.todos`. This triggers the work panel to expand automatically.

### Navigation Preservation

Per ADR-023, surfaces shouldn't require navigation. The TP Work Panel appears **within** the current surface, not as a separate page.

URL behavior:
- `/dashboard?surface=deliverable-detail&did=X` — Always valid
- When TP is working, `?working=true` could be appended for deep-linking (optional)
- Back/forward preserves the surface, panel expansion state is ephemeral

### Implementation Order (Frontend)

**Validation Phase:**

1. **TPWorkPanel component** — Displays todos + chat history
2. **todo_write handler in TPContext** — Parse tool result, update state
3. **Conditional rendering in DeliverableDetailSurface** — Show panel when todos exist
4. **Test with manual todo_write** — Verify UI updates correctly

**Full Rollout:**

5. **Idle surface integration** — Working panel on dashboard
6. **Skill picker** — Optional UI for discoverability
7. **Mobile adaptations** — Slide-up panel behavior
8. **Receipt/history view** — Past skill executions (requires schema)

### Relation to Existing Components

| Existing | Change |
|----------|--------|
| **TPBar** | Remains for ambient interaction. Triggers panel expansion when todos appear. |
| **TPContext** | Extended with `todos`, `workPanelExpanded`, `activeSkill` |
| **DeliverableDetailSurface** | Adds conditional TPWorkPanel rendering |
| **IdleSurface** | Adds conditional working panel overlay |
| **HandoffBanner** | Unchanged — still used for navigation context |
| **SurfaceRouter** | Unchanged — surfaces still route normally |
| **DeskContext** | Unchanged — surface type system preserved |

### Example: Full Flow with Frontend

**User opens dashboard, types:** `/board-update`

```
1. TPBar detects slash command
2. TPContext.setActiveSkill("board-update")
3. TP processes skill, calls todo_write with 5 steps
4. SSE delivers tool_result → TPContext.setTodos(parsed)
5. TPWorkPanel auto-expands on idle surface
6. User sees todo list + TP message asking for details
7. User responds via embedded input
8. TP updates todos → TPContext updates → UI re-renders
9. Eventually: TP calls create_deliverable
10. Tool result includes ui_action → surface changes to deliverable-detail
11. TPWorkPanel remains expanded, showing completion
12. User dismisses panel → back to normal deliverable view
```

---

*This ADR represents a strategic alignment decision. The validation phase will confirm the pattern works for YARNNN's domain before full commitment.*
