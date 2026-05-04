# ADR-249: Operator as Primary Runtime Entity — Autonomy as User Approval Degree

> **Status**: Proposed
> **Date**: 2026-05-04
> **Authors**: KVK, Claude
> **Amends**: THESIS.md (autonomy definition + operator framing), FOUNDATIONS.md (Axiom 2 operator loop, Axiom 3 autonomy corollary), LAYER-MAPPING.md (operator above the system/judgment split)
> **Preserves**: All existing code, substrate paths, primitive registry, Reviewer architecture
> **Dimensional classification**: **Identity** (Axiom 2) primary — clarifies who the primary runtime entity is; **Trigger** (Axiom 4) secondary — cadence of operator ↔ system loop; **Purpose** (Axiom 3) tertiary — autonomy mode as purpose-delegation degree

---

## Context

### What prior ADRs got partially right

ADR-216 reclassified YARNNN as an orchestration surface, not a judgment-bearing Agent. ADR-247 ratified the three-party narrative model (operator / YARNNN / Reviewer). ADR-248 added the periodic Reviewer pulse.

These are correct and preserved. What they didn't articulate clearly is the **runtime relationship** — who is the primary entity in the ongoing operation, and what does autonomy mode actually govern.

### The gap

The prior framing treated the operation as: "user drives YARNNN, which dispatches work, which produces proposals, which the Reviewer judges." The user was implicitly the primary runtime entity — the one whose presence keeps the operation moving.

This is wrong. The operation runs whether the user is present or not. The user's presence is not the condition for the loop to continue.

---

## Decisions

### D1: The Operator is the primary runtime entity

The **Operator** is the entity that acts on behalf of the user's declared goals. It holds the judgment seat (Reviewer), authors the mandate, declares the principles, and exercises judgment on proposed actions. The Operator is always present in the operation — through substrate (MANDATE.md, principles.md, IDENTITY.md, `_operator_profile.md`) when the user is absent, and through real-time presence when the user is engaged.

The Operator is not a separate software entity from the user. The user IS the operator. What "operator" names is the user's role in the system: the principal whose declared intent drives everything.

The primary runtime conversation is **Operator ↔ System (YARNNN)**:
- The operator declares intent and judgment framework through substrate
- The system executes declared work and narrates what happened
- This loop runs continuously at operational cadence, independent of the user's real-time presence
- The user can cut into this conversation at any moment from the chat surface

### D2: YARNNN is the system — executor and narrator, not co-reasoner

YARNNN's role is precisely bounded:
- Executes declared work (dispatches invocations, routes primitives)
- Narrates what happened (every invocation emits a narrative entry)
- Surfaces what requires the user's attention (proposals above ceiling, drift detected, anomalies)

YARNNN does not hold judgment about what *should* happen. It executes what was declared. The operator's substrate IS the intelligence. YARNNN reads it and acts on it — it does not augment it with its own reasoning about the operation's direction.

This is the Claude Code model applied consistently: CLAUDE.md is the operator's declared rules; Claude Code reads and executes without forming its own opinions about the project.

### D3: The Reviewer is the Operator's judgment function, not a separate entity

The Reviewer seat is the operator acting in judgment posture. When the human user is present and engaged, they occupy the Reviewer seat directly — clicking Approve/Reject is the user exercising judgment. When the AI occupies the seat (ADR-194 v2 Phase 3), it is instantiating the operator's pre-declared judgment framework from principles.md and IDENTITY.md.

The Reviewer is not an independent third party in the sense of a different principal. It is the operator's judgment, expressed either in real-time (human) or through substrate (AI). The independence comes from the architectural separation of the production path (analyst evaluating signals) from the judgment path (Reviewer evaluating proposals) — not from different principals.

**What this preserves**: the Reviewer seat, substrate paths, `reviewer_agent.py`, `review_proposal_dispatch.py`, all ADR-194 v2 architecture. None of this changes. Only the vocabulary and framing changes — the Reviewer is explicitly named as the operator's judgment function, not a separate entity.

### D4: Autonomy mode = degree to which user approval is required on Operator actions

Autonomy mode does NOT govern:
- Whether the operator is present (the operator is always present through substrate)
- Whether the loop runs (the loop always runs at operational cadence)
- Whether the user can intervene (the user can always cut in at any moment)

Autonomy mode DOES govern:
- **Whether the user's explicit approval is required** before an operator-initiated action executes

The three modes, precisely defined:

| Mode | What it means |
|------|---------------|
| **Manual** | Every operator action that has external consequence surfaces to the user for explicit approval before executing. The operator proposes; the user confirms. |
| **Bounded** | Operator actions within declared limits (ceiling_cents, never_auto) execute without user approval. Actions above the ceiling surface for user confirmation. |
| **Autonomous** | Operator actions execute per the declared judgment framework without requiring user confirmation. The user sees outcomes in the narrative. |

In all three modes: the user can always cut into the chat, override a decision, change the mandate, or pause autonomy. The mode controls the **default continuation** — whether the system pauses and waits for the user or proceeds and narrates.

### D5: Cadence of the Operator ↔ System loop = operational heartbeat

The frequency at which the operator ↔ system loop cycles is the operational heartbeat. This is declared through recurrence YAML (track-universe 3x/day, signal-evaluation 08:05, reconciliation nightly). The cadence is not determined by the user's session activity — it's determined by what the operation requires.

The cadence has direct cost implications: each loop cycle consumes tokens. The frequency of invocations × the depth of context per invocation = the operational cost. This is why recurrence cadence is a first-class concern declared in substrate, not an implementation detail.

### D6: User can always cut in — the chat input is unconditional

The user's ability to enter the conversation is not governed by autonomy mode. At any moment, the user can:
- Type in the chat input to address YARNNN (system matters)
- Type to invoke the Reviewer's voice (judgment matters)
- Approve or reject proposals in the Queue
- Change the autonomy chip to pause or escalate
- Modify MANDATE.md, principles.md, AUTONOMY.md through chat

This is the fundamental property of the chat surface: it is always an entry point into the operator ↔ system conversation. The user never has to "wait their turn."

### D7: The Reviewer speaks in three modes — all within the operator ↔ system loop

The Reviewer's presence in the loop takes three shapes:

1. **Verdict mode** (reactive, per-proposal): triggered by ProposeAction. Renders approve/reject/defer. This is already implemented.

2. **Reflection mode** (periodic, pattern-aware): triggered by heartbeat after ≥5 decisions. Notices drift, can write pause marker to AUTONOMY.md. ADR-248 implements this.

3. **Conversational mode** (addressed, on-demand): triggered when the user addresses the Reviewer's judgment directly in chat ("what does Simons think about holding this position?"). Routes to the Reviewer's voice rather than YARNNN's. **Not yet implemented — this is the missing wire for true back-and-forth.**

Mode 3 is what makes the operator ↔ system loop feel like a genuine conversation rather than a log of automated events. It is the mechanism by which the user can invoke the operator's judgment posture on demand.

---

## What this ADR does NOT change

- All existing code, substrate paths, primitive registry
- Reviewer architecture (ADR-194 v2, reviewer_agent.py, review_proposal_dispatch.py)
- The Reviewer seat concept, IDENTITY.md, principles.md, decisions.md
- AUTONOMY.md schema and `should_auto_execute_verdict()` logic
- The three-party narrative model (ADR-247)
- Any database schema

---

## Implementation — Four Layers, Singular Discipline

Each layer is a distinct code commitment. No dual approaches, no backwards-compat shims. Each commit replaces the old behavior entirely. Test gate per layer.

Dependency order is strict: Layer 1 → Layer 2 → Layer 3 → Layer 4.

---

### Layer 1: YARNNN prompt posture — executor/narrator replaces co-reasoner

**Scope**: `api/agents/prompts/` — four files  
**Risk**: Low. Prompt-only. No schema, route, or primitive changes.  
**CHANGELOG entry**: Required per CLAUDE.md rule 7.

The co-reasoner character in YARNNN's current prompts violates D2. Three archetypes to eliminate:

1. **Proactive suggestion** — YARNNN offering changes the operator didn't request ("consider asking", "propose", "want me to")
2. **Inference + confirmation** — YARNNN inferring intent then asking for validation ("Sound good?")  
3. **Advisory guidance** — YARNNN reasoning about what the operation *should* do ("seems recurring", "fastest way")

**File-level changes** (from audit, 2026-05-04):

`base.py`:
- Lines 6, 25: Rewrite "help the user think through" → "read declared substrate and act"
- Line 52: REMOVE "Proactiveness balance" section — co-reasoner framing

`chat/workspace.py`:
- Lines 56-84: REWRITE "Explore Before Asking" → "Search Before Acting" — inference+confirmation removed, declaration-gate added
- Lines 375-379: REWRITE recurrence suggestion guidance → declaration-only creation gate
- Line 394: REMOVE "consider asking about scheduling" — unsolicited advisory
- Lines 413-414: REWRITE platform awareness proposal → reactive-only

`chat/entity.py`:
- Lines 148-158: REWRITE "Before suggesting a rerun" → surface output metadata, act when operator declares intent

`chat/onboarding.py`:
- Lines 143-149: REWRITE mandate elicitation — remove example suggestions, accept operator framing verbatim
- Lines 252-264: REWRITE proactive upload offer → "You uploaded X. Should I read it?" (declarative, not suggestive)
- Lines 389-393: REWRITE daily-update opt-in — remove proactive suggestion, create only on explicit request
- Lines 415-420: REMOVE "Behaviors" section — explicit suggestion framing

**What replaces the removed language**: Nothing lengthy. The posture is expressed in one sentence added to the preamble of each chat profile: *"You execute what was declared. You narrate what happened. You do not propose what should happen next."*

---

### Layer 2: Narrative stream integration — scheduler events surface in chat

**Scope**: `api/routes/chat.py`, `api/services/working_memory.py`  
**Risk**: Medium. Changes how the first chat message of a session is assembled.  
**Dependency**: Layer 1 must be complete — YARNNN needs executor/narrator posture before narrating loop events.

**The gap**: The scheduler and the chat surface are two separate streams. Events from the scheduled loop (signal-evaluation ran, Reviewer approved, order executed) live in `session_messages` with `role='reviewer'` or `role='agent'`. They appear in the narrative scroll. But when the user opens chat after being away, YARNNN doesn't proactively surface what happened — the user has to scroll back or ask.

**The fix**: On session open (first user message of a new session), YARNNN assembles an "unacknowledged events" brief from `session_messages` since the last `role='user'` message. If material events exist (proposals created, verdicts rendered, orders executed, patterns flagged), YARNNN opens with a factual brief before responding to the user's message.

**Autonomy-mode-aware framing**:
- Manual: "A proposal for MSFT (IH-2) is waiting for your approval."
- Bounded: "IH-2 fired on MSFT. Reviewer approved and executed ($150 at risk). One proposal above ceiling is in Queue."
- Autonomous: "Signal-evaluation ran at 08:05. IH-2 fired on MSFT. Reviewer approved. Order executed at $247.50. No action needed."

**Implementation**: A new `_get_unacknowledged_loop_events()` function in `working_memory.py` that queries `session_messages` for material non-user events since last user message. Result injected into the compact index as a "Loop events since your last session" block (conditional, only when events exist). YARNNN reads this from the compact index on the first turn and surfaces it in its response.

**Singular implementation**: This replaces the current `recent_md` signal (which exists but requires the user to ask). `recent_md` signal is removed; this new block is the single surface for loop events.

---

### Layer 3: Reviewer conversational mode

**Scope**: `api/routes/chat.py` (routing), `api/agents/reviewer_agent.py` (new conversational method), `api/services/primitives/` (no changes)  
**Risk**: Medium-high. New execution path in the chat route.  
**Dependency**: Layer 1 (YARNNN must have executor posture before Reviewer can have distinct voice).

**The gap (D7 Mode 3)**: When the user addresses the Reviewer's judgment in chat ("what does Simons think about holding this position?" / "should I adjust the ceiling?" / "is the win rate good enough?"), YARNNN currently answers. The Reviewer's voice is never invoked conversationally. The back-and-forth between user and operator's judgment function doesn't exist.

**Intent detection**: A lightweight classifier in `chat.py` before dispatching to `YarnnnAgent`. Reads the user message for judgment-invocation signals:
- Reviewer name mentioned ("what does Simons think", "what would Buffett say")
- Judgment-framed question about an active operation ("should I", "is this within risk", "does this match the mandate")
- Direct address to principles ("given my principles, should I")

When triggered: route to `reviewer_agent.respond_conversationally(user_message, workspace_substrate)` — a new method in `reviewer_agent.py` that reads IDENTITY.md + principles.md + `_performance.md` + recent decisions and responds in the Reviewer persona's voice. Response written to `session_messages` with `role='reviewer'` so it renders as ReviewerCard in the narrative.

When not triggered: normal YARNNN dispatch (unchanged).

**Singular implementation**: One routing decision point. No fallback path. If the classifier is uncertain, route to YARNNN (default). Reviewer conversational mode only fires on confident signal.

---

### Layer 4: Autonomy-mode-aware loop closure

**Scope**: `api/routes/chat.py`, `api/services/working_memory.py`  
**Risk**: Low. Additive to Layer 2.  
**Dependency**: Layers 1, 2, 3 complete.

**The gap**: After the loop runs (invocations fire, proposals are created/evaluated/executed), the user's next chat turn sees the loop events (Layer 2). But the framing of those events isn't autonomy-mode-aware. "A proposal was created" reads the same whether the user is in manual mode (needs to act) or autonomous mode (already handled).

**The fix**: The unacknowledged events brief (Layer 2) is post-processed through the autonomy level from `workspace_state.autonomy_level`. The same underlying events are framed differently:

- Manual: "needs your action" framing — surface Queue link, make the required action explicit
- Bounded: "handled within ceiling / needs your action above ceiling" framing — split events by threshold
- Autonomous: "handled, no action needed" framing — summary only, no Queue prompt

**Implementation**: A small formatting function `_frame_loop_events_for_autonomy(events, autonomy_level)` in `working_memory.py`. Called by the compact index when assembling the loop events block.

---

## Hooks discipline checklist (per commit)

| Rule | Layer 1 | Layer 2 | Layer 3 | Layer 4 |
|------|---------|---------|---------|---------|
| Singular impl — delete old, no shims | Remove co-reasoner sections, don't leave comments | Remove `recent_md` signal, replace | Single routing point, no fallback path | Single format function, no parallel |
| CHANGELOG entry | Yes — prompt change per rule 7 | Yes — working_memory change | Yes — new execution path | Yes — formatting change |
| ADR docs alongside | This ADR updated each phase | This ADR updated | This ADR updated | This ADR updated |
| No backwards compat | Language removed, not commented | Old signal removed | No old path preserved | Old framing removed |

---

## Relationship to existing ADRs

| ADR | Relationship |
|-----|-------------|
| ADR-216 | Preserved — YARNNN as orchestration surface. This ADR sharpens: YARNNN is executor + narrator, not co-reasoner. Layer 1 implements. |
| ADR-247 | Preserved — three-party narrative. This ADR clarifies: primary loop is Operator ↔ System; user is supervising principal. Layer 2 implements. |
| ADR-248 | Preserved — periodic Reviewer pulse. Mode 2 of Reviewer presence. Layer 3 adds Mode 3. |
| ADR-194 v2 | Preserved — Reviewer substrate. Layer 3 adds conversational method without touching substrate. |
| THESIS | Amended — autonomy + operator loop framing. Phase 1 complete. |
| FOUNDATIONS | Amended — Derived Principle 17. Phase 1 complete. |
| LAYER-MAPPING | Amended — Operator above the split. Phase 1 complete. |
