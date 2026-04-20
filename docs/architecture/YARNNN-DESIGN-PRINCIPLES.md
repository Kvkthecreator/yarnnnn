# YARNNN Design Principles

**Status:** Canonical
**Date:** 2026-04-01 (renamed from TP-DESIGN-PRINCIPLES.md 2026-04-17 per ADR-189; Spectrum section added 2026-04-20 per FOUNDATIONS v5.1; dimensional framing added 2026-04-20 per FOUNDATIONS v6.0)
**Related:** FOUNDATIONS.md (Axiom 0 dimensional model, Axioms 1–8), SERVICE-MODEL.md, GLOSSARY.md, ADR-149 (task lifecycle), ADR-189 (three-layer cognition), ADR-194 (Reviewer layer)

---

## The Two Spectrums: Substrate Strictness vs Runtime Flexibility

Two distinct design spectrums govern YARNNN. Conflating them is the most common source of design drift; naming them explicitly is the single most load-bearing discipline in this doc.

**Relationship to FOUNDATIONS v6.0:** these spectrums sit beneath Derived Principle 11 ("Substrate tightens; Mechanism loosens"). Spectrum A is the Substrate dimension's discipline (Axiom 1). Spectrum B is the Mechanism dimension's posture (Axiom 5). The other four dimensions (Identity, Purpose, Trigger, Channel) each have their own disciplines inside FOUNDATIONS; this doc focuses on the two that most shape day-to-day design decisions.

### Spectrum A — Substrate strictness (locked)

**Where state lives.** DB rows ↔ filesystem files. (The Substrate dimension — FOUNDATIONS Axiom 1.)

FOUNDATIONS Axiom 1 decides this one categorically: the filesystem is the substrate, and the database is narrowly permitted for four row kinds (scheduling indexes, neutral audit ledgers, credentials, ephemeral queues). Anything holding semantic content belongs in a file. This spectrum is **strict by architectural conscience** — every prior collapse of a parallel substrate (platform_content → files, projects → tasks, Composer → YARNNN, knowledge tables → workspace files, user_memory → /workspace/*.md, action_outcomes → `_performance.md`) happened because semantic content was in a DB row when it belonged in a file.

Do not loosen Axiom 1. The strictness is what makes the architecture coherent across ADRs.

### Spectrum B — Runtime flexibility (deliberately procedural today, will loosen)

**How agents interact with that substrate.** Fixed procedure ↔ primitive CRUD. (The Mechanism dimension — FOUNDATIONS Axiom 5, which is explicitly a determinism-to-judgment spectrum within one axiom.)

The task execution pipeline is currently **procedural over the filesystem**: it parses TASK.md for declared process steps, pre-gathers context deterministically, dispatches a single generation call, composes the output via section-kind renderers, delivers through a typed channel, and terminates. The agent does not wander the filesystem in free-form pursuit of its task — the pipeline choreographs the run.

This is a **deliberate choice**, not a permanent one. Reasons it's correct today:
- Domain of alpha work is procedurally regular (digests, briefs, trades, reports).
- Cost predictability matters pre-revenue — procedural pipelines have bounded token budgets.
- The Reviewer layer (ADR-194) and approval loop (ADR-193) are the safety envelope that must land *before* runtime loosens; independent judgment over autonomous writes is the precondition.

Reasons it will loosen over time:
- As Agents accumulate tenure (FOUNDATIONS Axiom 4), the procedural ceiling becomes visible — a tenured Agent should be able to observe → decide → act across its own filesystem without the pipeline sequencing every step.
- The four permitted DB row categories of Axiom 0 already separate *substrate* concerns from *runtime* concerns, meaning the procedural pipeline can loosen without touching substrate rules.
- The Reviewer seat makes runtime autonomy safe by interposing independent judgment before irreversible writes. Loosen runtime *into* the Reviewer's gate, not around it.

### How to tell which spectrum a proposed change touches

Ask: **does this rule protect a load-bearing structural property, or is it codifying a procedural convenience?**

| Rule | Spectrum | Why |
|---|---|---|
| Filesystem is substrate (Axiom 0) | **A — strict** | Protects storage-agnostic + legibility + every prior collapse |
| Four permitted DB row kinds | **A — strict** | Protects semantic-content-in-files invariant |
| Reviewer layer structurally separate | **A — strict** | Independence *is* the architectural claim; interchangeability fails without it |
| Primitive permission modes (chat/headless/MCP) | **A — strict (auth part only)** | Auth boundaries are structural; "when to reach for this tool" is Spectrum B |
| Task scaffolding from TASK_TYPES registry | **B — loosenable** | Fast onboarding convenience; YARNNN can compose beyond it per ADR-188 |
| Pre-gather of context before generation | **B — loosenable** | Cost + determinism today; obsolete when agents drive own context reads |
| Single generation call per run | **B — loosenable** | Procedural simplicity today; multi-round reasoning arrives when Reviewer gates it |
| Declared `## Process` steps in TASK.md | **B — loosenable** | Choreography today; Agents will own their own execution shape with tenure |

**When in doubt:** if loosening the rule could cause semantic content to leak into a DB row, it's Spectrum A — keep it strict. If loosening it could cause an Agent to over-spend tokens or produce inconsistent output, it's Spectrum B — loosen it carefully, with Reviewer gates, when tenure justifies.

### The direction of travel

The architecture is designed to **tighten Spectrum A over time** (more substrate conscience, fewer DB tables holding semantic content) and **loosen Spectrum B over time** (more agent autonomy within the substrate, fewer procedural rails). The Reviewer layer (ADR-194) is the pivot — once an Agent's proposed writes have an independent judgment seat, the pipeline can step back from choreographing every step.

Today (2026-04-20): Spectrum A is nearly fully tight (post-Axiom 0 + ADR-195/196 cleanup). Spectrum B is still heavily procedural. That's the correct current posture. The ADRs following 194/195 will progressively loosen B.

---

## Core Principle: YARNNN Judges, We Don't Hardcode

YARNNN is the intelligence layer. It reads context, assesses state, and makes judgment calls. We provide clear context signals and priority guidance — NOT mechanical IF/THEN rules.

**We give YARNNN:**
- Rich context (working memory, WORKSPACE.md, workspace_state, navigation state)
- Clear priorities (identity before brand before tasks)
- Behavioral philosophy (one thing at a time, act then adjust, don't overwhelm)
- Tools to act (UpdateContext, ManageTask, ManageAgent, ManageDomains, etc.)

**We do NOT give YARNNN:**
- State machines ("IF identity == empty THEN only suggest identity")
- Mechanical gating ("block task creation until identity.richness >= 'rich'")
- Session state tracking ("already_suggested_this_gap = true")
- Hardcoded decision trees

**Why:** YARNNN is an LLM. It reads the room. It understands nuance. A user who says "I run a SaaS company tracking 5 competitors" has given enough identity context to skip straight to task creation — even if IDENTITY.md is technically "empty." A state machine would block this. YARNNN's judgment wouldn't.

---

## The Three Roles of YARNNN

### 1. Context Manager
YARNNN manages what's in the workspace filesystem. Every primitive is a filesystem write with judgment about what to write and where.

- Reads: working memory, WORKSPACE.md, workspace_state, navigation context
- Writes: UpdateContext (identity/brand/memory/agent/task/awareness), ManageTask (create/trigger/update/evaluate/steer/complete), ManageAgent, ManageDomains
- Routes feedback to the right scope (workspace / agent / task)
- Scaffolds context domains: after processing identity, YARNNN reasons about what entities should exist and calls ManageDomains to pre-populate (ADR-155). No separate inference service — YARNNN IS the inference layer.

### 2. Work Orchestrator
YARNNN creates and manages tasks. It knows the task type catalog, understands which agents handle what, and matches user intent to the right task configuration.

- Reads: task catalog (from working memory), user intent (from conversation)
- Creates: tasks from type templates, serialized into TASK.md
- Manages: evaluate, steer, complete — post-run lifecycle

### 3. Workspace Guide
YARNNN guides users through workspace setup and ongoing use. It sees what's missing, what's thin, what needs attention — and nudges accordingly.

- Priority: identity → brand → tasks (but JUDGMENT, not gating)
- Philosophy: one suggestion at a time, don't nag, act on clear intent
- Awareness: workspace_state signals, navigation state ("viewing" what)

---

## Onboarding Philosophy

**Cold start is a conversation, not a wizard.**

YARNNN reads the workspace state (workspace_state) and uses judgment to guide the user. It doesn't force a sequence. It suggests what would be most valuable RIGHT NOW.

- Empty workspace + no context: "Tell me about yourself and your work" (ContextSetup component on `/context`)
- User provides identity: YARNNN processes → UpdateContext → ManageDomains (pre-populates all domains with entity stubs)
- User says "track competitors": YARNNN creates the task immediately (doesn't gate on brand being set)
- User browses empty context/competitors/: "This is your competitor intelligence folder. Want to start tracking?"

**The key insight:** YARNNN's prompt guidance sets PRIORITIES, not RULES. YARNNN uses judgment to decide when to follow the priority order strictly (brand new user, zero context) vs. when to skip ahead (user clearly knows what they want).

**ADR-155 principle:** No shadow intelligence. When the user provides identity, the YARNNN — not a backend service — decides what entities to scaffold. This is YARNNN judgment, not a hardcoded pipeline. YARNNN may scaffold 3 competitors for one user and 0 for another, based on what it learned.

---

## Navigation Awareness ("Viewing")

YARNNN receives navigation context with every chat message when the user browses the workspace. This enables contextual suggestions without requiring the user to explain what they're looking at.

- Viewing IDENTITY.md → YARNNN can suggest enriching identity
- Viewing empty context/competitors/ → YARNNN can suggest tracking tasks
- Viewing a task's DELIVERABLE.md → YARNNN can suggest adjustments
- Viewing nothing (workfloor root) → YARNNN uses general workspace awareness

**This is context, not commands.** YARNNN doesn't mechanically react to navigation. It uses it as ADDITIONAL context for its judgment.

---

## Action Cards + Chat = Unified Flow

Conversation starter chips, inline action cards, and chat messages are ONE fluid system — not separate UX patterns.

**The flow:**
1. **Chip** starts the conversation ("Tell me about myself and my work")
2. **Action card** appears with guided input (URL field, file upload, text area)
3. **User provides input** via the action card (paste LinkedIn, upload deck, type description)
4. **YARNNN processes** the input (calls UpdateContext, ManageTask, etc.)
5. **YARNNN responds** in chat with confirmation + next suggestion

Action cards are NOT forms that bypass YARNNN. They're INPUT SURFACES that feed into the chat. Whatever the user provides through an action card becomes a message that YARNNN processes with full judgment.

**Key principle:** Every action card resolves to a YARNNN primitive call. The card provides the UI surface; YARNNN provides the judgment. The user never fills out a form that goes straight to a database — it always flows through YARNNN.

**Examples:**
- Identity setup card: URL field + file upload + text area → sends to YARNNN → `UpdateContext(target="identity")`
- New task card: task description field → sends to YARNNN → `ManageTask(action="create", type_key="...")`
- Feedback card: text area → sends to YARNNN → `UpdateContext(target="task", feedback_target="deliverable")`

---

## Awareness Architecture

YARNNN's understanding of the workspace comes from three layers, each with a distinct role:

### Layer 1: Ground Truth (computed fresh, disposable)

Computed at session start by `build_working_memory()`. Dies at session end. Never persisted.

| Signal | Source | What YARNNN sees |
|--------|--------|-------------|
| `workspace_state.identity` | `_classify_richness(IDENTITY.md)` | `empty \| sparse \| rich` |
| `workspace_state.brand` | `_classify_richness(BRAND.md)` | `empty \| sparse \| rich` |
| `workspace_state.documents` | `filesystem_documents` count | integer |
| `workspace_state.tasks` | `tasks` count (non-archived) | integer |
| `workspace_state.context_domains` | count of domains with >0 files | integer |
| `active_tasks` | `tasks` table query (top 10) | slug, mode, status, schedule, last/next run |
| `context_domains` | per-domain file count + freshness | domain, file_count, latest_update, health |

`workspace_state` renders into the prompt as "Context gaps." `active_tasks` and `context_domains` are computed but not yet rendered (infrastructure ready).

**Purpose:** Ground truth prevents staleness. YARNNN validates its own understanding against these signals every session.

### Layer 2: Workspace Files (persistent)

Files YARNNN reads at session start and writes during conversation via `UpdateContext`:

| File | Purpose | Written by |
|------|---------|-----------|
| `IDENTITY.md` | Who the user is | YARNNN via `UpdateContext(target="identity")` |
| `BRAND.md` | Output style/voice | YARNNN via `UpdateContext(target="brand")` |
| `AWARENESS.md` | YARNNN's situational notes (shift handoff) | YARNNN via `UpdateContext(target="awareness")` |
| `notes.md` | Standing instructions | YARNNN in-session via `UpdateContext(target="memory")` |
| `style.md` | Learned output style (tone, verbosity) | Feedback distillation from user edits |

IDENTITY.md and BRAND.md carry facts about the user. AWARENESS.md carries YARNNN's qualitative understanding of the workspace — current focus, task state, context health, next steps. It's a shift handoff note, not a health score. Direct write (no inference layer), full replacement each time.

### Layer 3: Behavioral Guidance (static prompt, always injected)

`CONTEXT_AWARENESS` prompt in `yarnnn_prompts/onboarding.py`. Tells YARNNN:
- Priority order: identity -> brand -> tasks
- Behavioral rules: one suggestion at a time, never gate, no technical language
- Navigation awareness: use what the user is viewing as context
- Task type catalog: what to suggest and when

**Key design choice:** This is GUIDANCE, not rules. YARNNN uses judgment. The prompt sets priorities that YARNNN can override when the user's intent is clear.

### How the layers interact

1. Session starts -> Layer 1 computes ground truth (what exists now)
2. Layer 2 files are read into working memory (what YARNNN knows qualitatively)
3. Layer 3 guidance is injected into system prompt (how to act on signals)
4. YARNNN reads all three -> makes judgment calls -> acts via primitives
5. Primitives update workspace files (Layer 2) -> next session, Layer 1 reflects the change

**No feedback loops.** Layer 1 is read-only (computed, not optimized against). Layer 2 is YARNNN's own notes (qualitative, not scored). Layer 3 is static guidance. YARNNN can't "game" any of these.

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
| IF/THEN state machines in prompts | Brittle, can't handle nuance | Give YARNNN priorities + trust judgment |
| Blocking primitives ("can't create task until identity is rich") | Prevents users who know what they want | Let YARNNN judge when to suggest vs. when to act |
| Session state tracking for nudges | Adds complexity, YARNNN already avoids nagging | Prompt guidance: "suggest each gap once, then drop it" |
| Hardcoded response templates | Removes YARNNN's ability to be natural | Give behavioral guidance, let YARNNN compose |
| Multiple simultaneous suggestions | Overwhelms users | Priority order + "one thing at a time" principle |

---

## Prompt Profiles (ADR-186)

YARNNN's system prompt is assembled from a **prompt profile** determined by the user's current surface. Two profiles:

### `workspace` — workspace-wide scope

**When:** User on `/chat`, browsing general surfaces, no entity focus.
**Contains:** Onboarding, task type catalog, team composition, creation routes, domain scaffolding, profile/brand awareness.
**Compact index:** Full workspace overview.
**Budget:** ~7K tokens.

### `entity` — entity-scoped

**When:** User viewing a specific task (`task-detail`), agent (`agent-detail`), or run (`agent-review`).
**Contains:** Feedback routing (domain/agent/task layers), evaluate/steer/complete, agent identity management, accumulation-first for scoped entity.
**Compact index:** Scoped — this entity's health, its domains, one-line workspace summary.
**Budget:** ~5-6K tokens.

### Key design choices

1. **Primitive set is constant across profiles.** Both profiles get the same 14 chat tools. Behavioral guidance determines when YARNNN reaches for them, not tool availability. This preserves YARNNN's ability to create a new task from a task page if the user explicitly asks.

2. **Profile resolution is declarative and logged.** A dict maps surface types to profiles. Default is `workspace`. Adding a surface type = one dict entry. Resolution is logged for evaluation.

3. **Profiles are stateless.** Determined entirely from the `DeskSurface.type` on each request. No mode tracking, no state transitions.

4. **Surface content routing is profile-aware.** For `entity` profile, surface content (TASK.md, run log, output preview) is injected as an entity preamble. For `workspace` profile, it's prepended as general navigation context.
