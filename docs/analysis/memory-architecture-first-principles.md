# First Principles Analysis: YARNNN Memory Architecture

**Date:** 2025-01-29
**Purpose:** Derive north star architecture from service philosophy + industry benchmarks

---

## Part 1: YARNNN Service Philosophy Audit

### Core Identity Claims

| Claim | Evidence | Implications for Architecture |
|-------|----------|------------------------------|
| "Context-aware AI work platform" | Landing, ESSENCE | Context is central, not optional |
| "Your AI understands your world" | Landing hero | Suggests holistic understanding, not task-scoped |
| "Context that compounds, not conversations that vanish" | About page | Persistence + growth over time |
| "Accumulated knowledge" | Throughout | Additive model, not per-project silos |
| "Agents read from your context" | ESSENCE | Agents consume unified context |
| "Work outputs, not chat responses" | Core principle | Execution is project-scoped, memory isn't |
| "Provenance & trust" | Core principle | Traceability requires knowing where knowledge came from |
| "Utility-first, not engagement" | ADR-002 | Professional tool, not companion/relationship |

### The Hidden Tension in Current Claims

YARNNN's brand promises TWO things that may conflict:

1. **"Your AI understands YOUR world"** → User-centric, holistic
2. **"Structured outputs for THIS project"** → Project-centric, scoped

The question: Does "your world" mean:
- (A) Everything about you across all work? (User-centric)
- (B) Everything about this specific project? (Project-centric)

**Reading the brand language carefully:**

> "Stop re-explaining your business to AI"

This suggests user-level knowledge ("your business") not project-level ("this task").

> "Context that compounds"

Compounding implies cross-pollination and accumulation, not siloed growth.

> "Agents read your entire context before executing"

Currently project-scoped, but the word "your" is ambiguous.

---

## Part 2: Industry Benchmark Analysis

### Pattern 1: Notion AI - Workspace as Context Boundary

**Model:** Document-scoped by default, workspace-wide via agents
**Strength:** Clear boundaries, good for team collaboration
**Weakness:** Cold start on new workspaces; context doesn't follow user

**Key Insight:** Notion treats the workspace as the "world" - context belongs to the space, not the person.

### Pattern 2: Mem0 - Explicit Memory Layer Separation

**Model:** Multi-level hierarchy (User → Session → Agent → Project)
**Strength:** Portable personalization; "who you are" travels with you
**Weakness:** Complexity; requires explicit memory management

**Key Insight:** Mem0 explicitly separates "knowing the user" from "knowing the task" - this is architectural, not accidental.

### Pattern 3: Rewind/Limitless - Ambient Personal Memory

**Model:** Capture everything about the user; query across time
**Strength:** Zero cold start; context compounds passively
**Weakness:** No project/task scoping; hard to share or collaborate

**Key Insight:** Personal memory that follows the individual, regardless of tool or project.

### Pattern 4: Granola - Meeting-Centric Context

**Model:** Ambient capture scoped to conversations; expanding to team
**Strength:** Context naturally grows from participation
**Weakness:** Limited to meeting content; transitioning model

**Key Insight:** Started personal, now adding team/project layer - recognizing the tension.

---

## Part 3: Synthesis - The Core Tension

All four tools (and YARNNN) face the same fundamental question:

**What is the natural boundary for AI context?**

| Boundary | Pro | Con |
|----------|-----|-----|
| **User** | Portable, compounds across everything, truly "knows you" | Privacy concerns, may pollute unrelated work |
| **Project** | Clean isolation, good for discrete deliverables | Cold start each time, loses cross-project insights |
| **Workspace** | Team-friendly, shared context | Context belongs to space, not person |
| **Time** | Natural accumulation | No topical scoping |

**The insight from Mem0 is crucial:** These aren't mutually exclusive. You can have BOTH:
- User-level memory (who you are, how you work, your business context)
- Project-level memory (what this specific work needs)

---

## Part 4: First Principles Derivation

### Principle 1: "Your World" Is User-Level

YARNNN's promise is "your AI understands YOUR world."

- "Your world" = your business, your domain, your preferences, your patterns
- This is fundamentally **user-scoped**, not project-scoped
- The ThinkingPartner should know YOU across all projects

**Implication:** User-level memory is required to fulfill the brand promise.

### Principle 2: Work Outputs Are Project-Level

YARNNN produces "work outputs" - reports, research, content.

- These are deliverables for specific purposes
- They need project-specific context (requirements, constraints, audience)
- They need isolation (a report for Client A shouldn't leak into Client B)

**Implication:** Project-level context is required for work execution.

### Principle 3: Context Should Compound, Not Silo

"Context that compounds" is a core differentiator.

- If every project starts from zero, context doesn't compound
- If insights from Project A can inform Project B, context compounds
- The user's accumulated knowledge should grow across projects

**Implication:** Some context must flow across projects (user-level), some must stay scoped (project-level).

### Principle 4: ThinkingPartner ≠ Work Agents

Reading ESSENCE.md and the agent architecture:

- **ThinkingPartner** = Conversational, exploratory, helps you think
- **Work Agents** = Execution-focused, produce deliverables

These have different context needs:
- ThinkingPartner should know YOU holistically
- Work Agents should know THIS PROJECT specifically

**Implication:** Different agents may need different context scopes.

### Principle 5: Utility-First Means Professional Memory

ADR-002 explicitly rejects "relationship-building patterns."

- YARNNN isn't trying to be your friend (Companion AI model)
- It's trying to be professionally useful
- Professional context = your business, domain expertise, work patterns

**Implication:** User memory should be "professional persona" not "whole life" (unlike Rewind).

---

## Part 5: The North Star Architecture

Based on first principles, YARNNN should have:

### Two-Layer Memory Model

```
┌─────────────────────────────────────────────────────────────┐
│                    USER MEMORY (user-scoped)                │
│  ─────────────────────────────────────────────────────────  │
│  What YARNNN knows about YOU:                               │
│  • Your business/domain context                             │
│  • Your work preferences and patterns                       │
│  • Your communication style                                 │
│  • Cross-project insights and learnings                     │
│  • Your goals and constraints                               │
│                                                             │
│  Access: ThinkingPartner (always), Work Agents (optionally) │
│  Grows from: All conversations, all projects, explicit input│
└─────────────────────────────────────────────────────────────┘
                              │
                              │ (user context flows down)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              PROJECT MEMORY (project-scoped)                │
│  ─────────────────────────────────────────────────────────  │
│  What's specific to THIS PROJECT:                           │
│  • Project requirements and constraints                     │
│  • Deliverable specifications                               │
│  • Source documents and research                            │
│  • Client/audience details                                  │
│  • Project-specific decisions                               │
│                                                             │
│  Access: Work Agents (primary), ThinkingPartner (in-project)│
│  Grows from: Project chat, project imports, project docs    │
└─────────────────────────────────────────────────────────────┘
```

### How This Resolves The Tension

| Question | Answer |
|----------|--------|
| Does TP know me across projects? | Yes - reads user memory |
| Are project deliverables isolated? | Yes - work agents read project memory |
| Does context compound? | Yes - user memory grows from all projects |
| Is there cold start for new projects? | Partially - user memory provides baseline |
| Can I share project-specific context? | Yes - project memory stays scoped |

### What This Means for Current Implementation

**Current state:** Everything is project-scoped (blocks belong to projects)

**Proposed addition:**
1. Add `user_context` table (user-scoped memory)
2. ThinkingPartner reads: user_context + current project blocks
3. Work agents read: current project blocks (optionally user_context)
4. Extraction writes to: user_context (personal insights) + blocks (project-specific)

### The UX Implication

**Current:** User must be "in a project" to chat with TP

**Proposed:** User can chat with TP without project context (user-level conversation), OR in a project context (user + project memory)

This matches the brand promise: "Your AI understands your world" - even before you start a project.

---

## Part 6: Decision Framework

### Option A: Stay Project-Centric (Current)
- Simpler architecture
- Cleaner data isolation
- **But:** Doesn't fulfill "your world" promise; cold start every project

### Option B: Add User Memory Layer (Proposed)
- Fulfills brand promise
- Context compounds across projects
- ThinkingPartner becomes truly personal
- **But:** More complexity; must decide what goes where

### Option C: User-Only (Companion AI Model)
- Maximum context compounding
- True personal AI
- **But:** Loses project isolation; hard to produce discrete deliverables

### Recommendation: Option B

The brand promise requires user-level memory. The work output model requires project isolation. **Option B is the only architecture that satisfies both constraints.**

---

## Part 7: Implementation Considerations

### What Goes in User Memory?
- Facts about the user's business/domain
- Work preferences and patterns (discovered from behavior)
- Communication style preferences
- Cross-project learnings and insights
- Explicitly stated goals and constraints

### What Goes in Project Memory?
- Project-specific requirements
- Client/audience details for this project
- Source documents uploaded to this project
- Decisions made within this project
- Task-specific context

### How Does Extraction Decide?
When extracting from a conversation, classify each item:
- "User likes bullet points over prose" → **user_context**
- "This report needs executive summary" → **project blocks**
- "User's business is B2B SaaS" → **user_context**
- "Target audience is CTOs" → **project blocks** (could be project-specific)

### Migration Path
1. Add `user_context` table
2. Modify ThinkingPartner to read user_context + project blocks
3. Modify extraction to route appropriately
4. Eventually: Allow TP to work without project context (user-level chat)

---

## Conclusion

**The North Star:** YARNNN should know the user holistically while producing project-scoped work outputs.

This requires a **two-layer memory architecture**:
- User Memory: Portable, compounding, professional persona
- Project Memory: Isolated, deliverable-focused, task-specific

This architecture is the only way to fulfill both "your AI understands your world" AND "structured outputs for your projects."

The key insight from Mem0's architecture applies: **separation of "knowing the user" from "knowing the task" must be explicit and architectural, not accidental.**
