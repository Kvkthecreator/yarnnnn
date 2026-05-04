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

## Implementation — Three Layers, Singular Discipline

Each layer is a distinct code commitment. No dual approaches, no backwards-compat shims. Each commit replaces the old behavior entirely. Test gate per layer.

Dependency order is strict: Layer 1 → Layer 2 → Layer 3.

**Why three layers, not four**: Layer 4 (autonomy-aware framing) is folded into Layer 2. The unacknowledged events brief is always autonomy-aware — there is no intermediate state where events surface without autonomy framing. One implementation, not two separate commits.

---

### Layer 1: YARNNN prompt posture — executor/narrator replaces co-reasoner ✅ COMPLETE

**Scope**: `api/agents/prompts/` — four files  
**Status**: Shipped 2026-05-04, commit `1be3e02`. CHANGELOG `[2026.05.04.4]`.

Three co-reasoner archetypes eliminated: proactive suggestion, inference+confirmation ("Sound good?"), advisory guidance. Replaced with executor/narrator posture: "You execute what was declared. You narrate what happened. You do not propose what should happen next."

Files: `base.py`, `chat/workspace.py`, `chat/entity.py`, `chat/onboarding.py`.

---

### Layer 2: Narrative stream integration — loop events surface on session open, autonomy-aware

**Scope**: `api/services/working_memory.py`, `api/routes/chat.py`  
**Risk**: Medium. Changes how the first chat message of a session is assembled.  
**Dependency**: Layer 1 complete.

**The gap**: The scheduler and the chat surface run as separate streams. Scheduled events (signal-evaluation, Reviewer assessment, order execution, reconciliation) write to `session_messages` and appear in the narrative scroll — but when the user opens chat after being away, YARNNN doesn't surface what happened. The user scrolls back or asks. The operation feels silent.

**The fix**: On session open (first user message of a new session), YARNNN assembles an unacknowledged events brief from `session_messages` since the last `role='user'` message. If material events exist, YARNNN opens with a factual brief — framed by autonomy level — before responding to the user's message.

**Autonomy-aware framing** (built in, not a separate layer):
- Manual: "A proposal for MSFT (IH-2) is waiting for your approval." — Queue link surfaced
- Bounded: "IH-2 fired on MSFT. Reviewer approved and executed ($150 at risk). One proposal above ceiling needs your approval."
- Autonomous: "Signal-evaluation ran at 08:05. IH-2 fired on MSFT. Reviewer approved. Order executed at $247.50. No action needed."

**Implementation**:
- `working_memory.py`: new `_get_unacknowledged_loop_events(user_id, client, session_id)` — queries `session_messages` for non-user-role entries since the last `role='user'` message. Returns a structured list: event type, timestamp, autonomy-relevant classification (needs-action / handled / informational).
- `working_memory.py`: `format_compact_index()` gains a "Since you were away" block (conditional, renders only when events exist). Formatted per autonomy level from `workspace_state.autonomy_level`.
- `recent_md` signal: **removed**. It was a pointer to a file the user had to read separately. This block is the single surface for loop events — direct, not indirect.

**Singular implementation**: One function, one compact index block, one autonomy-aware formatter. No parallel paths.

---

### Layer 3: Reviewer natural rhythm — operational cadence wired, not conversational mode

**Scope**: `api/services/reflection_writer.py` (confirm wire), `api/services/back_office/reviewer_reflection.py` (confirm output shape), `api/services/back_office/__init__.py` (trigger confirmation)  
**Risk**: Low. Infrastructure already exists — this layer confirms the wire is complete and the output reaches the narrative correctly.  
**Dependency**: Layer 2 complete (Reviewer's narrative entries must surface in the "Since you were away" block).

**The correct framing** (revised from prior Layer 3 draft):

The Reviewer is not a conversational mode activated by user intent detection. The Reviewer is the Operator's judgment function running at its natural operational rhythm. It speaks at two cadences — both already architected:

**Cadence 1 — Per-proposal verdict** (event-triggered, already implemented):
`ProposeAction` → `on_proposal_created` → `_run_ai_reviewer` → verdict rendered → `write_reviewer_message` writes `role='reviewer'` to `session_messages`. This is mechanical execution of the judgment function. Not the Reviewer's "voice" in the narrative sense — it's the judgment gate operating.

**Cadence 2 — Periodic operational assessment** (scheduled, ADR-248):
`back-office-reviewer-reflection` runs daily after reconciliation. Reads `_performance.md` + `decisions.md` + `calibration.md`. On material findings, `reflection_writer.apply_reflection_writes()` calls `write_reviewer_message` → `role='reviewer'` entry in `session_messages`. This IS the Reviewer's operational voice — the scheduled assessment the Operator produces at their natural rhythm.

**The missing wire**: Cadence 2 is fully implemented in code (ADR-248) but the narrative entry may not surface correctly in the Layer 2 "Since you were away" block because `_get_unacknowledged_loop_events()` (Layer 2) must include `role='reviewer'` events from reflection runs. This must be verified when Layer 2 ships — if reflection-sourced reviewer entries are already captured, Layer 3 is complete at no additional code cost.

**What Layer 3 explicitly does NOT do**:
- No intent detection in `chat.py`
- No new execution path routing user messages to the Reviewer
- No "conversational Reviewer mode" triggered by user message content
- The user can address the Reviewer's persona by name in chat — YARNNN handles it using the Reviewer's substrate (principles, IDENTITY) as context, but YARNNN speaks, not the Reviewer. The Reviewer's voice comes only at its declared rhythm.

**Why**: The Reviewer's independence depends on it not being reactive to every user prompt. If the Reviewer responds conversationally to every "what does Simons think?", it becomes a chatbot persona, not a judgment entity. Its voice carries weight precisely because it speaks on its own schedule, not on demand.

**Implementation**: Verify that `_get_unacknowledged_loop_events()` (Layer 2) queries `session_messages` filtering on `role IN ('reviewer', 'agent', 'system', 'external')` — all non-user narrative roles. If so, Layer 3 is complete when Layer 2 ships. If reflection-sourced reviewer entries are not reaching `session_messages`, trace the `write_reviewer_message` call in `reflection_writer.py` and confirm it writes to the correct session.

---

## Hooks discipline checklist (per commit)

| Rule | Layer 1 | Layer 2 | Layer 3 |
|------|---------|---------|---------|
| Singular impl — delete old, no shims | Remove co-reasoner sections entirely | Remove `recent_md` signal, replace with single block | Verify wire, no parallel path |
| CHANGELOG entry | ✅ Done `[2026.05.04.4]` | Yes — working_memory change | Yes if code change needed |
| ADR docs alongside | ✅ Done | This ADR updated at ship | This ADR updated at verify |
| No backwards compat | ✅ Language removed | Old signal removed | No new path added |

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
