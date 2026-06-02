# ADR-314: Substrate-Conditional Posture — The Frame Indexes Intent, It Does Not Assert It

**Status**: **Proposed**
**Date**: 2026-06-02
**Deciders**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing; agent behavior IS the system)

> **Evidence base**: receipt-backed audit this session (2026-06-02) of `api/agents/reviewer_agent.py::_compute_minimal_frame` against the standby state. Builds directly on [ADR-306](ADR-306-persona-frame-collapse.md) (persona-frame collapse), the [ablation audit](../evaluations/2026-05-29-persona-frame-collapse-ablation.md), FOUNDATIONS Derived Principle 22 (anti-rebloat), and the ratified [bare-kernel product floor](../architecture/bare-kernel-product-floor-2026-06-01.md) (Direction A).

---

## Context

A bare-kernel workspace (no program activated) has the kernel-universal floor only. Per ADR-286 single-writer, the governance files MANDATE / IDENTITY / AUTONOMY / principles are **absent** — they are bundle-owned, forked only at program activation (`programs.py::fork_reference_workspace`). The operator-facing chat IS the Reviewer's addressed turn (`feed.py::_dispatch_reviewer_turn` → `invoke_reviewer`); there is no separate orchestration LLM (`YarnnnAgent` dead-coded since ADR-257, swept in `1272c92`).

The recurring question — *"can a bare kernel become an operating workspace through conversation?"* — was already settled by the **bare-kernel product floor memo (Direction A, ratified 2026-06-01)**: **program-activation is the product floor.** The bundle-fork forks a pre-authored constitution (MANDATE, IDENTITY, principles, AUTONOMY, recurrences) that the operator inherits and then refines. There is no interactive constitution-elicitation flow, and there will not be one — that machinery was deliberately deleted, not lost.

This ADR does **not** reopen that decision. It closes the **one residual incoherence** the floor decision left in the agent's prompt envelope.

### The bug, visible within the frame itself

`_compute_minimal_frame` (the entire system-authored prompt layer post-ADR-306, ~3.5K chars) contains this sequence:

> **Line 434**: "*This prompt does not restate them — it tells you only who you are and how you act.*"
> **Line 437–438**: "*The operator already told you what to do: it is in your MANDATE.md and your standing_intent.md. Read them and act. You do not ask the operator what to do; you decide and direct.*"

Line 437 **restates a substrate claim** three lines after the frame promises not to. And the restated claim — *"the operator already told you what to do"* — is:

- **True** when the envelope carries a MANDATE (operating state). The agent directs.
- **False** when MANDATE is absent (standby state). The operator has *not* told the agent what to do; the constitution-creation event (activation) hasn't happened.

So in the standby state the frame asserts a falsehood and pairs it with "you do not ask… you decide and direct" — instructing the agent to direct toward an intent that doesn't exist. The empty-substrate fallbacks already present in the envelope (`_(empty — reason as a neutral skeptical judgment seat)_`, line 722; `_(empty — no declared framework)_`, line 728; MANDATE header omitted when absent) keep the agent from hard-paralyzing — but the *posture prose contradicts the empty-state reality*, which is exactly the class of self-contradiction ADR-306 was created to eliminate.

### Why this is a bug-against-canon, not a new design

This is not a missing feature requiring new architecture. It is a **violation of FOUNDATIONS Derived Principle 22** (the anti-rebloat constraint, ratified by ADR-306):

> *The frame narrates no fundamental and re-teaches no substrate file… every proposed addition to the frame must answer "is this correcting the model's prior, or defining the runtime interface?" — if neither, it belongs in substrate or code.*

And of the ablation's own **"substrate-authoritative index"** principle (ablation line 37):

> *Your governance lives in the substrate files pre-loaded in your message; they are authoritative; this prompt does not restate them — read them. The envelope already labels each; trust the labels.*

Line 437 fails both: "the operator already told you what to do: it is in your MANDATE.md" is a *restatement of substrate content*, not an *index pointer to it*. The implementation leaked past the discipline its own ADR ratified. The fix is to bring line 437 into compliance with ADR-306 D5 — **index, don't assert.**

## Decision

### D1 — Opt out of interactive `/init`; bundle-fork is the sole constitution-creation event.

YARNNN ships the kernel-program-bundle architecture (ADR-222/223/226). The bundle-fork **is** YARNNN's `/init` analog: it produces an editable, pre-authored constitution the operator inherits and refines. YARNNN does **not** build a Claude-Code-style interactive `/init` elicitation flow (ask → explore → gap-fill → write). Doing so would (a) re-introduce the conversational-onboarding machinery Direction A deliberately deleted, (b) duplicate what activation already does, and (c) require resurrecting an orchestration LLM, partially un-doing ADR-257. This ratifies, at the agent-behavior layer, what the bare-kernel product floor memo ratified at the product layer.

### D2 — The frame indexes intent; it does not assert intent exists.

The minimal frame's principal-shift (ADR-306 D1) is preserved — it is the one thing that genuinely fights the assistant prior. But it carries **only** the prior-correction, stated as an *index* to substrate, never as an *assertion of substrate content*. The corrected shape:

> You are the operator's installed judgment, acting on their behalf while they are away — NOT an assistant awaiting instruction. Your governing files (IDENTITY, principles, MANDATE, AUTONOMY, PRECEDENT, pace, preferences) are pre-loaded in the message below under labeled headers. They are authoritative; read them there and act on what they declare. This prompt does not restate them.
>
> You decide and direct from what your governing files declare — you do not ask the operator what to do. When a header is present, act on its content. When a header is absent or empty, reason honestly about that absence rather than inventing intent: an absent MANDATE means the operation's primary intent has not yet been declared (the operator establishes it by activating a program); judge from what *is* present.

The phrase *"the operator already told you what to do"* is deleted. It was a substrate assertion. What survives is the prior-correction ("you are installed judgment, not an assistant") + the index ("read your governing files; act on what they declare"). This is true in **both** states without a branch:

- **Operating state** (MANDATE present): "act on what they declare" → directs toward declared intent. Identical behavior to today.
- **Standby state** (MANDATE absent): "act on what they declare" over an empty governance set → the agent reasons honestly about the absence, never told a falsehood, never instructed to direct toward nonexistent intent.

**This is subtractive and D5-compliant** — no posture-branch keyed on `activation_state`, no substrate-conditional logic in the frame (which *would* be rebloat). One frame, two coherent behaviors, because the frame stops claiming a constitution exists and lets the agent read whether one does.

### D3 — The standby↔operating posture invariant is canon.

The system commits to this invariant, recorded in SERVICE-MODEL.md:

> **The agent's posture is read from substrate presence, never asserted by the frame.** The same persona-bearing judgment seat is coherent whether its constitution is forked (operating) or absent (standby). The frame corrects the model's assistant prior and defines the runtime interface; *what to do* comes from the envelope's substrate headers, which the agent reads — present headers direct behavior, absent headers are reasoned about honestly. There is no separate onboarding agent, no posture-branch, and no `/init`; the bundle-fork is the constitution-creation event (Direction A).

### D4 — Inference primitives: NOT deletion candidates (receipt-corrected).

> **Correction (2026-06-02, same session)**: an earlier draft of this ADR proposed deleting `InferContext` + `InferWorkspace` as vestigial "no live caller" cleanup. A precise call-site audit *before* executing the deletion found that claim **false for `InferContext`** and **insufficient for `InferWorkspace`**. The deletion was NOT executed. The corrected finding:
>
> - **`InferContext` is LIVE.** It is invoked by the MCP `remember_this` tool — `api/services/mcp_composition.py::route_remember_this` calls `execute_primitive(auth, "InferContext", {"target": target, "text": stamped_text})` for `target ∈ {identity, brand}`. This is the ADR-310 / ADR-169 judged-hub path (foreign-LLM identity/brand contributions). Deleting it breaks a live, recently-shipped surface. The original "no live caller" grep checked `routes/feed.py` / `routes/memory.py` / `mcp_server/server.py` but missed `mcp_composition.py`, the actual dispatcher. **`InferContext` stays.**
> - **`InferWorkspace` is invocation-dead but canon-ratified.** No `execute_primitive(…, "InferWorkspace", …)` call exists (the string hits are the registry dispatch-map entry, the tool definition, prose/comments, and the `feed.py` decisions-summary *display filter* — none an invocation). But ADR-235 D1.a ratified it as the first-act scaffold primitive, and three gates assert its existence (`test_recent_commits.py`, `test_adr235`, `test_adr307`). Deleting it is therefore **not hygiene — it is a primitive-surface amendment to ADR-235**, which warrants its own decision, not a follow-on bullet here.
>
> **Net: this ADR deletes no primitives.** Any future removal of the invocation-dead `InferWorkspace` lands in a dedicated ADR that amends ADR-235, weighing whether the first-act-scaffold capability is still wanted at all under Direction A (where bundle-fork, not a scaffold primitive, is the constitution-creation event). The Claude-Code observation that "infer is `Read → reason → Write`, not a primitive" remains a valid *future* simplification thesis — but it is a separate decision, not a consequence of the posture fix, and it must reckon with `InferContext`'s live MCP role.

## What this supersedes / amends / preserves

- **Preserves** ADR-306 (persona-frame collapse) entirely — this ADR *enforces* D5 where the implementation leaked, it does not reopen the collapse. The frame stays minimal (D1 principal-shift + D2 action-grammar); D2-of-this-ADR is a *correction within* the principal-shift, not an addition.
- **Preserves** FOUNDATIONS Derived Principle 22 (anti-rebloat) — the fix is subtractive; no substrate-conditional branch is added to the frame.
- **Preserves** the bare-kernel product floor (Direction A) + ADR-257 (no orchestration LLM) + ADR-286 (single-writer governance) — D1 ratifies them at the agent-behavior layer.
- **Preserves** ADR-194 v2 Reviewer substrate, the seat structure, the occupant model, the `_is_path_locked_for_reviewer` lock-set (MANDATE confirmed write-reachable + AUTONOMY-gated; the refine-after-fork lifecycle is mechanically supported, attributed per ADR-209, revertible).
- **Amends** SERVICE-MODEL.md — adds the standby↔operating posture invariant (D3) to the Execution Flow / Reviewer section.
- **Does not touch the primitive surface** — D4 (receipt-corrected) deletes nothing; `InferContext` is live via MCP, `InferWorkspace` removal is a future ADR-235 amendment.

## Risk + revert

The frame change is one section edit, separable, revertible to the line-437 state (working, deployed) if re-validation shows regression. The load-bearing risk is *operating-state behavior regression* — that the corrected prose makes the agent less decisive when MANDATE *is* present. Mitigated by the structure of D2: in the operating state, "act on what they declare" over a present MANDATE is behaviorally identical to "the operator already told you what to do" — the directive force is preserved; only the false-on-empty assertion is removed. Validation runs against an operating workspace (alpha-trader) to confirm decisiveness is unchanged, and against a bare-kernel workspace to confirm the standby coherence.

## Implementation

- **Phase A** (this ADR): record the decision.
- **Phase B**: `reviewer_agent.py::_compute_minimal_frame` — delete the "operator already told you what to do" assertion; rewrite the principal-shift to the D2 index-not-assert shape. `CHANGELOG` entry. Single-section edit.
- **Phase C**: SERVICE-MODEL.md — add the standby↔operating posture invariant (D3).
- ~~**Phase D**: delete `InferContext` + `InferWorkspace`~~ — **NOT executed** (D4 receipt-correction). `InferContext` is live via MCP `remember_this`; `InferWorkspace` is invocation-dead but ADR-235-ratified. Any removal is a future ADR amending ADR-235, not a follow-on here.

Refs: ADR-306, ADR-281, ADR-257, ADR-286, ADR-226, FOUNDATIONS Derived Principle 22, `docs/architecture/bare-kernel-product-floor-2026-06-01.md`, `docs/evaluations/2026-05-29-persona-frame-collapse-ablation.md`.
