# TP Design Principles

**Status:** Canonical  
**Date:** 2026-04-01  
**Related:** FOUNDATIONS.md (Axiom 1), SERVICE-MODEL.md, ADR-149 (task lifecycle)

---

## Core Principle: TP Judges, We Don't Hardcode

TP is the intelligence layer. It reads context, assesses state, and makes judgment calls. We provide clear context signals and priority guidance — NOT mechanical IF/THEN rules.

**We give TP:**
- Rich context (working memory, WORKSPACE.md, context_readiness, navigation state)
- Clear priorities (identity before brand before tasks)
- Behavioral philosophy (one thing at a time, act then adjust, don't overwhelm)
- Tools to act (UpdateContext, CreateTask, ManageTask, etc.)

**We do NOT give TP:**
- State machines ("IF identity == empty THEN only suggest identity")
- Mechanical gating ("block task creation until identity.richness >= 'rich'")
- Session state tracking ("already_suggested_this_gap = true")
- Hardcoded decision trees

**Why:** TP is an LLM. It reads the room. It understands nuance. A user who says "I run a SaaS company tracking 5 competitors" has given enough identity context to skip straight to task creation — even if IDENTITY.md is technically "empty." A state machine would block this. TP's judgment wouldn't.

---

## The Three Roles of TP

### 1. Context Manager
TP manages what's in the workspace filesystem. Every primitive is a filesystem write with judgment about what to write and where.

- Reads: working memory, WORKSPACE.md, context_readiness, navigation context
- Writes: UpdateContext (identity/brand/memory/agent/task), CreateTask, ManageTask
- Routes feedback to the right scope (workspace / agent / task)

### 2. Work Orchestrator
TP creates and manages tasks. It knows the task type catalog, understands which agents handle what, and matches user intent to the right task configuration.

- Reads: task catalog (from working memory), user intent (from conversation)
- Creates: tasks from type templates, serialized into TASK.md
- Manages: evaluate, steer, complete — post-run lifecycle

### 3. Workspace Guide
TP guides users through workspace setup and ongoing use. It sees what's missing, what's thin, what needs attention — and nudges accordingly.

- Priority: identity → brand → tasks (but JUDGMENT, not gating)
- Philosophy: one suggestion at a time, don't nag, act on clear intent
- Awareness: context_readiness signals, navigation state ("viewing" what)

---

## Onboarding Philosophy

**Cold start is a conversation, not a wizard.**

TP reads the workspace state (context_readiness) and uses judgment to guide the user. It doesn't force a sequence. It suggests what would be most valuable RIGHT NOW.

- Empty workspace + no context: "Tell me about yourself and your work"
- User provides identity: "Got it. Want to set up how outputs look, or jump straight to tracking something?"
- User says "track competitors": TP creates the task immediately (doesn't gate on brand being set)
- User browses empty context/competitors/: "This is your competitor intelligence folder. Want to start tracking?"

**The key insight:** TP's prompt guidance sets PRIORITIES, not RULES. TP uses judgment to decide when to follow the priority order strictly (brand new user, zero context) vs. when to skip ahead (user clearly knows what they want).

---

## Navigation Awareness ("Viewing")

TP receives navigation context with every chat message when the user browses the workspace. This enables contextual suggestions without requiring the user to explain what they're looking at.

- Viewing IDENTITY.md → TP can suggest enriching identity
- Viewing empty context/competitors/ → TP can suggest tracking tasks
- Viewing a task's DELIVERABLE.md → TP can suggest adjustments
- Viewing nothing (workfloor root) → TP uses general workspace awareness

**This is context, not commands.** TP doesn't mechanically react to navigation. It uses it as ADDITIONAL context for its judgment.

---

## Action Cards + Chat = Unified Flow

Conversation starter chips, inline action cards, and chat messages are ONE fluid system — not separate UX patterns.

**The flow:**
1. **Chip** starts the conversation ("Tell me about myself and my work")
2. **Action card** appears with guided input (URL field, file upload, text area)
3. **User provides input** via the action card (paste LinkedIn, upload deck, type description)
4. **TP processes** the input (calls UpdateContext, CreateTask, etc.)
5. **TP responds** in chat with confirmation + next suggestion

Action cards are NOT forms that bypass TP. They're INPUT SURFACES that feed into the chat. Whatever the user provides through an action card becomes a message that TP processes with full judgment.

**Key principle:** Every action card resolves to a TP primitive call. The card provides the UI surface; TP provides the judgment. The user never fills out a form that goes straight to a database — it always flows through TP.

**Examples:**
- Identity setup card: URL field + file upload + text area → sends to TP → `UpdateContext(target="identity")`
- New task card: task description field → sends to TP → `CreateTask(type_key="...")`
- Feedback card: text area → sends to TP → `UpdateContext(target="task", feedback_target="deliverable")`

---

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | What To Do Instead |
|---|---|---|
| IF/THEN state machines in prompts | Brittle, can't handle nuance | Give TP priorities + trust judgment |
| Blocking primitives ("can't create task until identity is rich") | Prevents users who know what they want | Let TP judge when to suggest vs. when to act |
| Session state tracking for nudges | Adds complexity, TP already avoids nagging | Prompt guidance: "suggest each gap once, then drop it" |
| Hardcoded response templates | Removes TP's ability to be natural | Give behavioral guidance, let TP compose |
| Multiple simultaneous suggestions | Overwhelms users | Priority order + "one thing at a time" principle |
