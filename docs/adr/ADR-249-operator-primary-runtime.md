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

## Implementation sequence

**Phase 1 (this ADR)**: Documentation hardening — FOUNDATIONS, THESIS, LAYER-MAPPING, NARRATIVE. Vocabulary alignment. No code changes.

**Phase 2**: Strip judgment/reasoning language from YARNNN's prompt. YARNNN stops reasoning about what it *should* do and reads declared substrate to know what to do. Narration posture replaces reasoning posture.

**Phase 3**: Implement Reviewer conversational mode (D7 Mode 3) — route user messages that invoke judgment to the Reviewer's voice rather than YARNNN.

**Phase 4**: YARNNN loop-closes proactively — after each operation cycle, YARNNN narrates what happened in terms of the autonomy posture: "a proposal was evaluated and executed (autonomous)" vs. "a proposal is waiting for your approval (manual)."

---

## Relationship to existing ADRs

| ADR | Relationship |
|-----|-------------|
| ADR-216 | Preserved — YARNNN as orchestration surface. This ADR sharpens: YARNNN is executor + narrator, not co-reasoner. |
| ADR-247 | Preserved — three-party narrative. This ADR clarifies: the primary loop is Operator ↔ System; the user is the supervising principal. |
| ADR-248 | Preserved — periodic Reviewer pulse. This ADR adds context: the pulse is Mode 2 of the Reviewer's presence in the loop. |
| ADR-194 v2 | Preserved — Reviewer substrate. This ADR reframes: Reviewer = operator's judgment function, not separate entity. Substrate unchanged. |
| THESIS | Amended — autonomy definition reframed. Not "structural property of the system" alone but "degree to which user approval is required on operator actions." |
| FOUNDATIONS | Amended — Axiom 2 gains explicit operator-as-primary-runtime framing. New corollary to Axiom 4 on cadence as operational heartbeat. |
