# ADR-025: Claude Code Agentic Alignment

**Status:** In Progress
**Date:** 2026-02-05
**Updated:** 2026-02-05
**Extends:** ADR-010 (Thinking Partner Architecture), ADR-018 (Recurring Deliverables)
**Related:** ADR-019 (Deliverable Types), ADR-023 (Supervisor Desk), ADR-024 (Context Classification)

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

### Progress Summary

**Completed (Validation Phase):**
- ✅ `todo_write` tool added and integrated
- ✅ System prompt updated for concise responses
- ✅ Skills system implemented (8 skills defined)
- ✅ Context scoping integrated (ADR-024)
- ✅ Context-scoped chat history (frontend)
- ✅ Project selector in TPDrawer
- ✅ Todo progress display in TPDrawer

**Remaining work follows a tiered approach based on dependencies.**

---

### Tier 1: Upstream Foundations (Next)

These three capabilities are tightly coupled and form the foundation for downstream work. Plan mode without assumption checking is just a longer todo list. Assumption checking without revision means TP can't course-correct.

#### 1.1 Plan Mode

**What:** Explicit planning phase before complex work begins.

**Why upstream:** Defines how TP approaches any non-trivial request. Affects skill execution patterns, todo structure, and user interaction model.

**Specification:**
```
User: "I need monthly board updates for my investors"

TP enters plan mode:
1. [todo_write] Creates initial plan (marked as "planning")
2. [respond] "Here's my plan: [shows todos]. Ready to proceed?"
3. User confirms OR provides feedback
4. TP exits plan mode, begins execution
```

**Detection heuristics for "complex" requests:**
- Deliverable creation (always plan)
- Multi-entity operations ("update all my projects")
- Ambiguous scope ("help me organize my work")
- Skill invocation (skill defines expected steps)

**Simple requests bypass plan mode:**
- Single navigation ("show my memories")
- Single action with clear target ("pause the weekly report")
- Pure conversation ("what do you think about...")

#### 1.2 Assumption Checking

**What:** TP verifies context matches expectations before major actions.

**Why upstream:** Core discipline that prevents TP from proceeding with wrong information. Essential for plan mode to be trustworthy.

**Specification:**
```markdown
## Assumption Checking (System Prompt Addition)

Before executing each major step in your plan:
1. State what you expect to find
2. Verify with a tool call if needed
3. If reality differs from expectation:
   - STOP execution
   - Update your understanding
   - Revise todos if needed
   - Inform user of the change

Example:
- Plan: "Use PayFlow project context"
- Check: list_projects()
- Result: No PayFlow project exists
- Action: Revise plan, ask user "I don't see a PayFlow project. Should I create one, or use a different project?"
```

**Checkpoints (when to verify):**
- Before creating any entity (deliverable, project, memory)
- Before modifying existing entities
- When plan references specific context (project, deliverable by name)
- After user provides information that changes scope

#### 1.3 Todo Revision

**What:** TP can modify its plan mid-execution based on new information.

**Why upstream:** Without revision, assumption checking is useless—TP would detect problems but couldn't adapt.

**Specification:**
```markdown
## Todo Revision (System Prompt Addition)

Your todo list is a living plan, not a fixed script.

When to revise:
- Assumption check reveals unexpected state
- User provides information that changes scope
- A step fails or becomes unnecessary
- You discover a better approach

How to revise:
- Call todo_write with updated list
- Briefly explain what changed and why
- Continue execution from the appropriate step

Never:
- Silently skip steps without updating todos
- Proceed with outdated plan after discovering issues
- Add steps without removing completed ones (keep list clean)
```

**Example flow:**
```
Original plan:
1. ✓ Parse intent
2. ● Find PayFlow project
3. ○ Gather details
4. ○ Create deliverable

After check reveals no PayFlow:
1. ✓ Parse intent
2. ✓ Check for PayFlow project (not found)
3. ● Clarify with user: create project or use existing?
4. ○ [Depends on user response]
5. ○ Gather details
6. ○ Create deliverable
```

---

### Tier 2: Downstream (Built on Tier 1)

#### 2.1 Full Skill Rollout

**What:** All deliverable types as skills with plan mode integration.

**Dependency:** Skills benefit from plan mode discipline—each becomes a structured workflow that can adapt via assumption checking and revision.

**Deliverable type → Skill mapping:**

| Skill | Deliverable Type | Status |
|-------|------------------|--------|
| `/board-update` | board_update | ✅ Implemented |
| `/status-report` | status_report | ✅ Implemented |
| `/stakeholder-update` | stakeholder_update | ✅ Implemented |
| `/research-brief` | research_brief | ✅ Implemented |
| `/meeting-summary` | meeting_summary | ✅ Implemented |
| `/newsletter-section` | newsletter_section | ✅ Implemented (beta) |
| `/changelog` | changelog | ✅ Implemented (beta) |
| `/one-on-one-prep` | one_on_one_prep | ✅ Implemented (beta) |
| `/client-proposal` | client_proposal | ✅ Implemented (beta) |
| `/performance-review` | performance_review | ✅ Implemented (beta) |

**Post-Tier 1 work:** Update each skill's `system_prompt_addition` to leverage plan mode, assumption checking, and revision patterns.

#### 2.2 Persistent Receipts

**What:** Database storage of skill executions and todo progressions for audit trails.

**Dependency:** Schema emerges from hardened patterns. Once Tier 1 is stable, we know exactly what to persist—the shape of todos at checkpoints, decisions made, revisions triggered.

**Deferred schema (refined after Tier 1):**
```sql
CREATE TABLE skill_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    session_id UUID,
    skill_name TEXT,

    -- Captures the journey, not just the result
    initial_plan JSONB,        -- First todo_write
    final_plan JSONB,          -- Last todo_write
    revisions JSONB[],         -- Each revision with reason
    checkpoints JSONB[],       -- Assumption checks performed

    deliverable_id UUID REFERENCES deliverables(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

---

### Deprioritized / Reconsidered

#### Skill Picker UI

**Original idea:** Visual picker for users to browse and select skills.

**Reconsidered:** TP already routes through natural language → skill detection. User says "board update", TP selects `/board-update`. Explicit slash commands work for power users. Adding a picker creates:
- Extra UI surface to maintain
- Friction for users who just want to describe what they need
- Redundancy with TP's intent recognition

**Decision:** Deprioritize. Revisit only if discoverability becomes a demonstrated problem (users asking "what can you do?" frequently, or failing to find capabilities they need).

---

### Implementation Order

```
Tier 1 (upstream, implement as cohesive unit):
├── 1.1 Plan mode
├── 1.2 Assumption checking
└── 1.3 Todo revision
    ↓
Tier 2 (downstream, benefits from Tier 1):
├── 2.1 Full skill rollout (update skills for new patterns)
└── 2.2 Persistent receipts (schema from stabilized patterns)
```

**Tier 1 is a single deliverable.** The three capabilities are interdependent and should be designed/implemented together.

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

### Resolved

1. ~~**Skill discovery** - How do users learn what skills exist?~~
   **Answer:** Natural language intent recognition + slash commands for power users. Skill picker UI deprioritized—TP handles routing.

2. ~~**Todo UI placement** - In TPBar? Floating panel? Dedicated surface?~~
   **Answer:** Implemented in TPDrawer as inline progress display above messages.

3. ~~**Persistence scope** - Session-only todos vs. persisted receipts?~~
   **Answer:** Session-only for now. Persistent receipts deferred to Tier 2, schema will emerge from Tier 1 patterns.

### Open

4. **Skill customization** - Can users modify skill parameters? Create custom skills?
   *Deferred until core pattern is stable.*

5. **Cross-skill workflows** - Can skills invoke other skills?
   *Not currently needed. Revisit if use case emerges.*

6. **Plan mode UX** - How does user approve/modify a plan?
   - Option A: TP shows plan in respond(), user says "yes" or gives feedback
   - Option B: Structured approval UI (checkbox list, edit capability)
   - *Leaning toward A for simplicity. B adds UI complexity.*

7. **Assumption check frequency** - How aggressive should checking be?
   - Too frequent: Slow, noisy
   - Too sparse: Misses issues
   - *Need to calibrate through testing.*

---

## References

- Claude Code source patterns (TodoWrite, Skills, Plan mode)
- [Claude Agent SDK documentation](https://docs.anthropic.com/en/docs/agents-and-tools/claude-agent-sdk)
- ADR-010: Thinking Partner Architecture
- ADR-019: Deliverable Types System
- ADR-023: Supervisor Desk Architecture
- ADR-024: Context Classification Layer

---

## Appendix B: Tier 1 Implementation Specification

This section provides detailed implementation guidance for the upstream foundations: Plan Mode, Assumption Checking, and Todo Revision.

### System Prompt Additions

The following sections should be added to `SYSTEM_PROMPT_WITH_TOOLS` in `thinking_partner.py`:

```markdown
---

## Plan Mode (ADR-025 Tier 1)

For complex requests, enter **plan mode** before executing.

### When to Plan

**Always plan for:**
- Deliverable creation (any type)
- Multi-entity operations ("update all my...", "organize my...")
- Ambiguous scope requests ("help me with...", "set up...")
- Skill invocations (`/board-update`, `/status-report`, etc.)

**Skip planning for:**
- Single navigation ("show my memories", "list deliverables")
- Single clear action ("pause the weekly report", "rename this to X")
- Pure conversation ("what do you think about...", "explain...")

### Plan Mode Flow

1. **Create plan with todos:**
   ```
   todo_write([
     {content: "Understand request", status: "completed", activeForm: "Understanding request"},
     {content: "Verify context exists", status: "in_progress", activeForm: "Verifying context"},
     {content: "Gather missing details", status: "pending", activeForm: "Gathering details"},
     {content: "Confirm with user", status: "pending", activeForm: "Confirming with user"},
     {content: "Execute action", status: "pending", activeForm: "Executing action"}
   ])
   ```

2. **Share plan briefly:**
   ```
   respond("I'll help you set up a monthly board update. My plan:
   1. Check your project context
   2. Gather recipient details
   3. Confirm the setup
   4. Create the deliverable

   Starting now...")
   ```

3. **Execute with checkpoints** (see Assumption Checking below)

4. **Adapt as needed** (see Todo Revision below)

---

## Assumption Checking (ADR-025 Tier 1)

Before major actions, verify your assumptions match reality.

### Checkpoints (When to Verify)

| Before... | Verify... |
|-----------|-----------|
| Creating a deliverable | Project exists, no duplicate deliverable |
| Using project context | Project exists and has relevant memories |
| Referencing by name | Entity exists with that name |
| Modifying an entity | Entity is in expected state |

### Check Pattern

```
1. State assumption: "I expect PayFlow project exists with board context"
2. Verify: list_projects() or relevant tool
3. Compare: Does reality match expectation?
4. If mismatch → STOP, revise plan, inform user
5. If match → proceed to next step
```

### Example: Assumption Mismatch

**Plan assumes:** "Use PayFlow project context"
**Check:** `list_projects()` returns `[]` (no projects)
**Response:**
```
respond("I was going to use your PayFlow project, but I don't see any projects set up yet.

Would you like me to:
1. Create a PayFlow project first, then set up the board update
2. Create the board update in your Personal context instead")
```
Then: `clarify("How should I proceed?", ["Create PayFlow project first", "Use Personal context"])`

### Verification Tools

Use these tools for assumption checks:
- `list_projects` - Verify project exists
- `list_deliverables` - Check for duplicates, verify deliverable exists
- `list_memories` - Verify context is available
- `get_deliverable` - Check deliverable state before modifying

---

## Todo Revision (ADR-025 Tier 1)

Your plan is a living document. Update it when reality changes.

### When to Revise

| Trigger | Action |
|---------|--------|
| Assumption check fails | Add clarification step, adjust downstream steps |
| User changes scope | Rewrite affected steps |
| Step becomes unnecessary | Remove it |
| New requirement emerges | Add steps |
| Better approach found | Restructure plan |

### Revision Rules

1. **Always call `todo_write`** with the full updated list
2. **Briefly explain** what changed: `respond("Adjusting plan - need to create the project first.")`
3. **Keep completed steps** as historical record
4. **Never silently skip** - if you're not doing a step, remove it
5. **One `in_progress` at a time** - move marker appropriately

### Example: Plan Revision

**Original plan:**
```
1. ✓ Parse intent
2. ● Verify PayFlow context
3. ○ Gather details
4. ○ Confirm setup
5. ○ Create deliverable
```

**After discovering no PayFlow project:**
```
todo_write([
  {content: "Parse intent", status: "completed"},
  {content: "Verify PayFlow context", status: "completed"},  // Mark done even though it "failed"
  {content: "Clarify: create project or use Personal", status: "in_progress"},
  {content: "Create project if needed", status: "pending"},
  {content: "Gather details", status: "pending"},
  {content: "Confirm setup", status: "pending"},
  {content: "Create deliverable", status: "pending"}
])
```

---

## Combined Flow Example

**User:** "I need monthly updates for my board"

```
TP: [todo_write] Create initial plan
    1. ○ Parse intent
    2. ○ Check project context
    3. ○ Gather recipient details
    4. ○ Confirm setup
    5. ○ Create deliverable
    6. ○ Offer first draft

TP: [todo_write] #1 → completed, #2 → in_progress

TP: [respond] "Setting up a Monthly Board Update. Checking your context..."

TP: [list_projects]  // ASSUMPTION CHECK
    → Returns: [{name: "PayFlow", id: "..."}]
    → ✓ Assumption verified: project exists

TP: [todo_write] #2 → completed, #3 → in_progress

TP: [respond] "I see your PayFlow project. Quick questions:
    - Who's the primary recipient?
    - What's your company stage?"

User: "Marcus Webb at Sequoia, Series A"

TP: [todo_write] #3 → completed, #4 → in_progress

TP: [respond] "Got it. I'll create:

    **Monthly Board Update**
    - For: Marcus Webb (Sequoia)
    - Using: PayFlow context
    - Schedule: 1st of each month

    Ready to set this up?"

User: "yes"

TP: [todo_write] #4 → completed, #5 → in_progress

TP: [list_deliverables]  // ASSUMPTION CHECK: no duplicate
    → Returns: [] or list without "Board Update"
    → ✓ No duplicate

TP: [create_deliverable]
    title: "Monthly Board Update"
    type: "board_update"
    frequency: "monthly"
    ...

TP: [todo_write] #5 → completed, #6 → in_progress

TP: [respond] "Done! Monthly Board Update is set up. Want me to generate the first draft?"

TP: [todo_write] #6 → completed (or in_progress if user says yes)
```

**Alternative: Assumption check fails**

```
TP: [list_projects]  // ASSUMPTION CHECK
    → Returns: []
    → ✗ No projects exist!

TP: [todo_write] Revise plan:
    1. ✓ Parse intent
    2. ✓ Check project context (none found)
    3. ● Clarify: create project or use Personal  // NEW
    4. ○ Create project if needed  // NEW
    5. ○ Gather recipient details
    6. ○ Confirm setup
    7. ○ Create deliverable
    8. ○ Offer first draft

TP: [respond] "I don't see any projects set up yet. Should I:
    1. Create a project for your board updates (recommended)
    2. Set this up in your Personal context"

TP: [clarify] "How should I proceed?", ["Create a new project", "Use Personal context"]
```
```

### Implementation Changes

#### 1. System Prompt Updates (`thinking_partner.py`)

Add the three sections above to `SYSTEM_PROMPT_WITH_TOOLS`, after the existing "Task Progress Tracking" section.

**Placement order:**
1. Core Principle: Tools + Conversation (existing)
2. Tools by Category (existing)
3. Response Patterns (existing)
4. Task Progress Tracking (existing)
5. **Plan Mode** (new - Tier 1)
6. **Assumption Checking** (new - Tier 1)
7. **Todo Revision** (new - Tier 1)
8. Work Delegation (existing)
9. Deliverable Creation (existing, may need light updates)
10. Memory Routing (existing)

#### 2. Skill Prompt Updates (`skills.py`)

Update each skill's `system_prompt_addition` to reference plan mode:

```python
"board-update": {
    "system_prompt_addition": """
## Active Skill: Board Update Creation

You are helping create a Monthly Board Update deliverable.

### Plan Mode Active

Follow the plan mode pattern:
1. Create todos for the full workflow
2. Verify project context exists (assumption check)
3. Gather: recipient, company stage
4. Confirm before creating
5. Create deliverable
6. Offer first draft

### Assumption Checks Required
- Before using project context: verify project exists
- Before creating: verify no duplicate deliverable exists

### If Assumptions Fail
- No project: offer to create one or use Personal
- Duplicate exists: offer to update existing or create variant
"""
}
```

#### 3. Frontend: Plan Display Enhancement (optional)

Currently, todos display as a simple list. For plan mode, consider:

- **"Planning..." indicator** when first todos appear
- **"Executing..." indicator** when work begins
- **Revision highlight** - briefly highlight when plan changes

This is polish, not blocking. Current todo display works for Tier 1.

#### 4. Testing Scenarios

| Scenario | Expected Behavior |
|----------|-------------------|
| "Create monthly board update" | Plan mode: 5-6 todos, assumption checks on project |
| "Create board update" (no projects) | Plan revision: add project creation step |
| "Create weekly report" (duplicate exists) | Plan revision: clarify update vs new |
| "Show my memories" | No plan mode, direct navigation |
| "Pause the weekly report" | No plan mode, direct action |

### Migration Notes

- Existing behavior (simple requests) should be unaffected
- Plan mode activates only for qualifying requests
- Skills continue to work; they now benefit from plan discipline
- No database schema changes required
- No frontend changes required (current todo display suffices)

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
