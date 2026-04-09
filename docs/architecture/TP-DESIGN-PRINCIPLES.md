# TP Design Principles

**Status:** Canonical  
**Date:** 2026-04-01  
**Related:** FOUNDATIONS.md (Axiom 1), SERVICE-MODEL.md, ADR-149 (task lifecycle)

---

## Core Principle: TP Judges, We Don't Hardcode

TP is the intelligence layer. It reads context, assesses state, and makes judgment calls. We provide clear context signals and priority guidance — NOT mechanical IF/THEN rules.

**We give TP:**
- Rich context (working memory, WORKSPACE.md, workspace_state, navigation state)
- Clear priorities (identity before brand before tasks)
- Behavioral philosophy (one thing at a time, act then adjust, don't overwhelm)
- Tools to act (UpdateContext, ManageTask, ManageAgent, ManageDomains, etc.)

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

- Reads: working memory, WORKSPACE.md, workspace_state, navigation context
- Writes: UpdateContext (identity/brand/memory/agent/task/awareness), ManageTask (create/trigger/update/evaluate/steer/complete), ManageAgent, ManageDomains
- Routes feedback to the right scope (workspace / agent / task)
- Scaffolds context domains: after processing identity, TP reasons about what entities should exist and calls ManageDomains to pre-populate (ADR-155). No separate inference service — TP IS the inference layer.

### 2. Work Orchestrator
TP creates and manages tasks. It knows the task type catalog, understands which agents handle what, and matches user intent to the right task configuration.

- Reads: task catalog (from working memory), user intent (from conversation)
- Creates: tasks from type templates, serialized into TASK.md
- Manages: evaluate, steer, complete — post-run lifecycle

### 3. Workspace Guide
TP guides users through workspace setup and ongoing use. It sees what's missing, what's thin, what needs attention — and nudges accordingly.

- Priority: identity → brand → tasks (but JUDGMENT, not gating)
- Philosophy: one suggestion at a time, don't nag, act on clear intent
- Awareness: workspace_state signals, navigation state ("viewing" what)

---

## Onboarding Philosophy

**Cold start is a conversation, not a wizard.**

TP reads the workspace state (workspace_state) and uses judgment to guide the user. It doesn't force a sequence. It suggests what would be most valuable RIGHT NOW.

- Empty workspace + no context: "Tell me about yourself and your work" (TP emits `<!-- workspace-state: {"lead":"context"} -->` on first turn when `workspace_state.identity == "empty"`; opens `WorkspaceStateView` with `ContextSetup` as the active peer lens, switcher soft-gated by `isEmpty` — ADR-165 v7)
- User provides identity: TP processes → UpdateContext → ManageDomains (pre-populates all domains with entity stubs)
- User says "track competitors": TP creates the task immediately (doesn't gate on brand being set)
- User browses empty context/competitors/: "This is your competitor intelligence folder. Want to start tracking?"

**The key insight:** TP's prompt guidance sets PRIORITIES, not RULES. TP uses judgment to decide when to follow the priority order strictly (brand new user, zero context) vs. when to skip ahead (user clearly knows what they want).

**ADR-155 principle:** No shadow intelligence. When the user provides identity, the TP — not a backend service — decides what entities to scaffold. This is TP judgment, not a hardcoded pipeline. TP may scaffold 3 competitors for one user and 0 for another, based on what it learned.

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
4. **TP processes** the input (calls UpdateContext, ManageTask, etc.)
5. **TP responds** in chat with confirmation + next suggestion

Action cards are NOT forms that bypass TP. They're INPUT SURFACES that feed into the chat. Whatever the user provides through an action card becomes a message that TP processes with full judgment.

**Key principle:** Every action card resolves to a TP primitive call. The card provides the UI surface; TP provides the judgment. The user never fills out a form that goes straight to a database — it always flows through TP.

**Examples:**
- Identity setup card: URL field + file upload + text area → sends to TP → `UpdateContext(target="identity")`
- New task card: task description field → sends to TP → `ManageTask(action="create", type_key="...")`
- Feedback card: text area → sends to TP → `UpdateContext(target="task", feedback_target="deliverable")`

---

## Awareness Architecture

TP's understanding of the workspace comes from three layers, each with a distinct role:

### Layer 1: Ground Truth (computed fresh, disposable)

Computed at session start by `build_working_memory()`. Dies at session end. Never persisted.

| Signal | Source | What TP sees |
|--------|--------|-------------|
| `workspace_state.identity` | `_classify_richness(IDENTITY.md)` | `empty \| sparse \| rich` |
| `workspace_state.brand` | `_classify_richness(BRAND.md)` | `empty \| sparse \| rich` |
| `workspace_state.documents` | `filesystem_documents` count | integer |
| `workspace_state.tasks` | `tasks` count (non-archived) | integer |
| `workspace_state.context_domains` | count of domains with >0 files | integer |
| `active_tasks` | `tasks` table query (top 10) | slug, mode, status, schedule, last/next run |
| `context_domains` | per-domain file count + freshness | domain, file_count, latest_update, health |

`workspace_state` renders into the prompt as "Context gaps." `active_tasks` and `context_domains` are computed but not yet rendered (infrastructure ready).

**Purpose:** Ground truth prevents staleness. TP validates its own understanding against these signals every session.

### Layer 2: Workspace Files (persistent)

Files TP reads at session start and writes during conversation via `UpdateContext`:

| File | Purpose | Written by |
|------|---------|-----------|
| `IDENTITY.md` | Who the user is | TP via `UpdateContext(target="identity")` |
| `BRAND.md` | Output style/voice | TP via `UpdateContext(target="brand")` |
| `AWARENESS.md` | TP's situational notes (shift handoff) | TP via `UpdateContext(target="awareness")` |
| `notes.md` | Standing instructions | TP in-session via `UpdateContext(target="memory")` |
| `style.md` | Learned output style (tone, verbosity) | Feedback distillation from user edits |

IDENTITY.md and BRAND.md carry facts about the user. AWARENESS.md carries TP's qualitative understanding of the workspace — current focus, task state, context health, next steps. It's a shift handoff note, not a health score. Direct write (no inference layer), full replacement each time.

### Layer 3: Behavioral Guidance (static prompt, always injected)

`CONTEXT_AWARENESS` prompt in `tp_prompts/onboarding.py`. Tells TP:
- Priority order: identity -> brand -> tasks
- Behavioral rules: one suggestion at a time, never gate, no technical language
- Navigation awareness: use what the user is viewing as context
- Task type catalog: what to suggest and when

**Key design choice:** This is GUIDANCE, not rules. TP uses judgment. The prompt sets priorities that TP can override when the user's intent is clear.

### How the layers interact

1. Session starts -> Layer 1 computes ground truth (what exists now)
2. Layer 2 files are read into working memory (what TP knows qualitatively)
3. Layer 3 guidance is injected into system prompt (how to act on signals)
4. TP reads all three -> makes judgment calls -> acts via primitives
5. Primitives update workspace files (Layer 2) -> next session, Layer 1 reflects the change

**No feedback loops.** Layer 1 is read-only (computed, not optimized against). Layer 2 is TP's own notes (qualitative, not scored). Layer 3 is static guidance. TP can't "game" any of these.

### Agent-level awareness (headless)

Work-level agents don't have conversations. Their awareness comes from system hooks:
- `memory/run_log.md` — appended after each task execution
- `memory/feedback.md` — written by feedback distillation after user edits
- `memory/reflections.md` — extracted from agent output after generation

These are mechanical (no LLM judgment in the hook). The agent reads them on next execution and adjusts.

---

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | What To Do Instead |
|---|---|---|
| IF/THEN state machines in prompts | Brittle, can't handle nuance | Give TP priorities + trust judgment |
| Blocking primitives ("can't create task until identity is rich") | Prevents users who know what they want | Let TP judge when to suggest vs. when to act |
| Session state tracking for nudges | Adds complexity, TP already avoids nagging | Prompt guidance: "suggest each gap once, then drop it" |
| Hardcoded response templates | Removes TP's ability to be natural | Give behavioral guidance, let TP compose |
| Multiple simultaneous suggestions | Overwhelms users | Priority order + "one thing at a time" principle |
