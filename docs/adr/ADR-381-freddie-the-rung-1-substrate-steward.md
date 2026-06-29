# ADR-381 — Freddie: the Rung-1 Substrate Steward (the steward hardening ADR ADR-375 §7 owes)

> **Status**: **Proposed — SKELETON** (2026-06-29). This ADR is **scaffolded, not decided.** It reserves the number, wires the rung vocabulary (ADR-380), and names the decisions it owes as headings — but the substantive hardening discourse (the Freddie rename, the occupant carve, the attribution prefix, the per-rung harness wiring) is **its own session**, not pre-decided in this cascade-hygiene pass. Do NOT read any heading below as ratified; they are the agenda, not the conclusions.
> **Date**: 2026-06-29
> **Authors**: KVK (operator) + Claude (collaborator)
> **Owes-from**: [ADR-375](ADR-375-phase-1-substrate-for-humans-and-external-agents.md) §7 Cut 1 — *"name it Freddie (Frankenstein → the creature we intentionally built and are hardening) and harden it as the de-facto system agent… This is a separate ADR. Not built here."* This is that ADR's placeholder.
> **Builds on**: [the two-order Freddie direction](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md) (the ratified Picture-B: Freddie = the workspace agent / management; judgment pushed out to 2nd-order persona agents), [ADR-380](ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md) (the activation ladder — **Freddie = Rung 1**), [ADR-315](ADR-315-reviewer-occupant-contract.md) (seat≠occupant — Freddie is a *named occupant*, not a new component), [ADR-194](ADR-194-pluggable-reviewer-and-impersonation.md) (the steward seat).
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — naming + hardening the 1st-order substrate steward).

---

## 0. What this skeleton fixes (and what it defers)

**Fixes (vocabulary, settled upstream):**
- Freddie is the **Rung-1 substrate steward** (ADR-380): the 1st-order workspace/system agent — substrate management, derive-and-cite, placement, multi-principal arbitration, persona-agent governance. Reversible substrate-internal mutations. Ships on engineering time.
- Freddie is a **named occupant**, not a new component (ADR-315 seat≠occupant): the rename of the de-facto-hardened Reviewer occupant, the `reviewer` slug preserved as a data-compatibility exception (ADR-251 precedent).
- Freddie **owns the workspace operationally**, not as principal (the operator is the principal) — per the two-order direction.
- The **harness split at Rung 1** (ADR-380 D3): budget/pace are *live and exercised*; mandate/autonomy are *carried, not exercised* (degenerate over reversible substrate — there is no consequential external write to gate). The canon must state this honestly: **autonomy-harness validation does NOT accrue at Rung 1.**

**Defers (the substance — its own discourse, NOT decided here):**
- the operator-facing label decision (literal "Freddie" vs. a working name) and the attribution-prefix decision (`reviewer:` → `freddie:` vs. keep-slug-rename-label);
- the seat-canon generalization ("one judgment seat per workspace" → "one management seat (Freddie) + N judgment seats");
- the exact per-rung harness wiring in `reviewer_envelope.py` / the occupant contract.

---

## 1. Decisions owed (NAMED AS AGENDA — none ratified here)

> Each heading is a question the Freddie hardening session must answer. The bracketed note is the *lean* from prior discourse, recorded as input, not decision.

### D1 — The label + the attribution prefix
*[lean: rename the operator-facing label to "Freddie"; keep the internal `reviewer` slug + `reviewer:` attribution prefix — Singular Implementation + the ADR-251 "System Agent" relabel precedent.]* — **TBD.**

### D2 — Freddie as Rung 1: the substance of "hardening"
*[the converged role per the two-order direction §3 + ADR-380 Rung 1: substrate steward, base-LLM reasoning about the substrate, no operator-authored persona, no capital judgment. "Hardening" = naming the converged role first-class, not adding capability.]* — **TBD.**

### D3 — The harness split (the honesty ADR-380 D3 demands)
*[budget/pace live; mandate/autonomy carried-not-exercised; canon must NOT claim "autonomy harness validated on Freddie." The validation clock runs only at Rung 2.]* — **TBD: how this is stated in the occupant contract + envelope.**

### D4 — The seat-canon generalization
*[ADR-194/315: "one steward seat per workspace" generalizes to "one management seat (Freddie, Rung 1) + N judgment seats (persona agents, Rung 2)." How much of the six-file seat substrate generalizes per seat.]* — **TBD; coordinates with ADR-382 (the persona-agent seat ADR).**

### D5 — Persona-agent governance (the CRUD authority)
*[the two-order direction H1: Freddie is the sole creator/governor of persona agents; the operator's only creation path is the front-end pre-set picker. Freddie sets the "act on behalf" authority per persona agent.]* — **TBD; the boundary with ADR-382.**

---

## 2. What this skeleton does NOT do

- Does not decide any of D1–D5 — they are the agenda for the Freddie hardening session.
- Does not change code, schema, the gate, or the `reviewer` slug.
- Does not build persona-agent seats (ADR-382, Rung 2 — separate).
- Does not promote the rung ladder to an axiom (ADR-380 §6).
- Does not touch the re-founding keystone cascade (orthogonal track).

## 3. Cross-references

- Upstream vocabulary: [ADR-380](ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md) (rungs), [the two-order direction](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md) (Picture B).
- Sibling: [ADR-382](ADR-382-persona-agent-seats-the-rung-2-judgment-layer.md) (the Rung-2 persona-agent seat ADR — name-only stub).
- Seat canon to generalize: `docs/architecture/reviewer-seat-substrate.md` + the occupant docs (ADR-315).
