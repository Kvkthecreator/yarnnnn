# Reviewer Occupant

> **Status**: Canonical
> **Date**: 2026-06-04 (split from `reviewer-substrate.md` per ADR-315 D5)
> **Authors**: KVK, Claude
> **Scope**: The **personification** half of the Reviewer canon — the AI agent that *fills* the seat. Occupant classes, the `freddie_agent.py` implementation structure, model selection by trigger, the persona-frame discipline, and how the occupant consumes the published contract. The *seat* (the substrate the occupant reads and writes) is documented in [reviewer-seat-substrate.md](reviewer-seat-substrate.md); the named seam between them is [reviewer-occupant-contract.md](reviewer-occupant-contract.md).
> **Implementation**: `api/agents/freddie_agent.py` (the occupant), `api/agents/occupant_contract.py` (the ABI it consumes), `api/agents/reviewer_agent_sections.py` (persona-frame section machinery).
> **Upstream**: [ADR-315](../adr/ADR-315-reviewer-occupant-contract.md) (seat ≠ occupant — the occupant is carved into a contract-bounded module). [ADR-256](../adr/ADR-256-unified-reviewer-invocation.md) (`invoke_freddie` unified entry point). [agent-composition.md](agent-composition.md) §3.2.1 + §3.2.2 (persona-frame partition + composed-coherence discipline — the singular enforcement home).

> **⚠ ADR-414 banner (2026-07-07):** the occupant module is live as `freddie_agent.py` (the 2026-06-29 full rename); model-by-trigger prose below is superseded by **ADR-402** (one model, Sonnet, all shapes — `services/model_routing.py`). Per [ADR-414](../adr/ADR-414-the-pure-workspace-genesis-system-agent-program-as-hire.md) D2, the occupant's steward constitution becomes kernel constants and the envelope re-carves per altitude (steward subset for Freddie wakes; the judgment load-out loads only for a hired Altitude-3 agent's wakes).

---

## Purpose

This document is the technical canon for the **Reviewer occupant** — the AI agent that fills the independent judgment seat. Per [ADR-315](../adr/ADR-315-reviewer-occupant-contract.md), the occupant is the unit that was carved out of the previously-monolithic `reviewer-substrate.md`: the *seat* stays substrate (no ABC, no abstraction — see [reviewer-seat-substrate.md](reviewer-seat-substrate.md)), while the *occupant* becomes a contract-bounded module.

The boundary is a **data contract over substrate** (`FreddieContext` / `FreddieOutput` TypedDicts), not an OO abstraction over the seat. The contract is published in [reviewer-occupant-contract.md](reviewer-occupant-contract.md) and defined in `api/agents/occupant_contract.py`. This document describes the *occupant that consumes* that contract.

---

## Occupant classes

The seat (per [reviewer-seat-substrate.md](reviewer-seat-substrate.md) `OCCUPANT.md`) is occupant-class-agnostic. Four classes can fill it, all reading and writing the same substrate:

- `human:<user_id>` — the operator themselves, filling the seat via approval UX. No `freddie_agent.py` invocation; the operator renders verdicts by clicking.
- `ai:<model>-<version>` — a YARNNN-internal AI occupant. **This is the occupant `freddie_agent.py` implements.** Today: `ai:freddie-sonnet-v8` (the `FREDDIE_MODEL_IDENTITY` constant in `occupant_contract.py`). **Operator-facing label: "Freddie"** (ADR-381 D1) — the 1st-order substrate steward (Rung 1, ADR-380), the named occupant of the **management seat**. "Freddie" is a relabel-keep-slug (ADR-251 precedent): the `reviewer` slug + `reviewer:` attribution prefix + `/workspace/persona/` seat path are unchanged. The seat keeps its role-name ("the Reviewer seat" / "the management seat"); "Freddie" names who fills it.
- `external:<service>-<identifier>` — an external AI service filling the seat via adapter. **Not built** (ADR-315 D6 names this the trigger for the L3 package carve).
- `impersonated:<admin_user_id>-as-<persona_slug>` — admin alpha-stress-testing mode (ADR-194 v2).

This document focuses on the `ai` occupant; the other classes either bypass the LLM path (human) or are deferred (external / impersonated).

---

## The unified entry point: `invoke_freddie`

Per [ADR-256](../adr/ADR-256-unified-reviewer-invocation.md), the occupant exposes a single entry point:

```
invoke_freddie(trigger, context: FreddieContext) -> FreddieOutput | None
```

- **`trigger`** — `addressed` (operator chat turn) or `reactive` (recurrence-fire or proposal-arrival). The four-mode taxonomy collapsed to two by ADR-263 D2; reflection/heartbeat-shaped verdicts survive as substrate-write directives the Reviewer can emit on any trigger.
- **`context`** — a `FreddieContext` bag assembled by the kernel-side envelope helper (`services/freddie_envelope.py::load_reviewer_governance_envelope`). The occupant reads pre-loaded substrate from the bag and fetches anything else via the `ReadFile` tool.
- **return** — one `FreddieOutput` shape across all triggers; `None` on shape violation (the contract's `_validate_context_shape` guard fails loud rather than waking the Reviewer with an empty message).

`invoke_freddie` runs a bounded tool-use loop. The harness (`services/wake.py` reactive paths, `routes/feed.py` addressed path) imports `invoke_freddie` — the *behavior* — while importing the contract *symbols* (`FreddieContext`, `FreddieOutput`, `FREDDIE_MODEL_IDENTITY`) from `occupant_contract.py`. This is ADR-315 D3: the kernel depends on the contract, never on the occupant implementation.

---

## Model selection by trigger

The occupant selects its model from the trigger shape (constants in `freddie_agent.py`):

| Trigger sub-shape | Model | Rationale |
|---|---|---|
| Proposal-arrival (reactive) | Sonnet (`claude-sonnet-4-6`) | Capital decisions — discrete, high-stakes verdict call. 3-round loop. |
| Recurrence-fire (reactive) | Haiku (`claude-haiku-4-5-...`) | Framework reasoning — longer real-time loop, similar shape to addressed. |
| Addressed (operator chat turn) | Haiku | Conversation reasoning. |

Token usage is attributed to two callers: `reviewer` (Sonnet) and `reviewer-reflection` (Haiku), consolidated by ADR-256.

---

## Persona-frame discipline (the partition)

The occupant assembles a system prompt from two layers:

1. **The operator-authored substrate** — `IDENTITY.md`, `principles.md`, `PRECEDENT.md`, plus the wake envelope's labeled governance headers (MANDATE, AUTONOMY, etc.). The model reads its own message.
2. **The system-authored persona-frame** — `_PERSONA_FRAME_SECTIONS` in `freddie_agent.py`, resolved via `reviewer_agent_sections.py`.

**The partition between these two is enforced at [agent-composition.md](agent-composition.md) §3.2.1 — the singular enforcement home.** That section is canon; this document points at it, it does not duplicate it. The one-line statement (from agent-composition.md §3.2.1 + §4.2): *persona is how to reason; mandate is why we exist; autonomy is how far decisions bind; principles is what the rules of judgment are.*

### The minimal frame (post-collapse)

Post the §3.2.2 collapse, the persona-frame carries **only two irreducible things** (`_compute_minimal_frame`, ~3.5K chars, down from ~36K):

1. **Principal-shift** — corrects the model's trained assistant prior. A model reading `IDENTITY.md` through its assistant prior becomes "a helpful assistant playing the persona" (still asks, defers, enumerates). The shift to installed-judgment is a property of installing judgment over an assistant-trained model — not an operator declaration, so it cannot live in substrate. Per ADR-314 (2026-06-02), the principal-shift **indexes** the operator's intent ("read your governing files; act on what they declare") — it never **asserts** that intent exists. Index-not-assert keeps the frame coherent in both the operating state (MANDATE present) and the standby state (bare kernel, MANDATE absent per ADR-286).
2. **Action-grammar** — the agent↔runtime interface contract (tool-call-IS-action + anti-confabulation). This is the protocol, not data the agent reasons over, so it cannot live in substrate.

Everything else lives elsewhere and is **not** narrated in the frame (the anti-rebloat constraint): rules of judgment → `principles.md`; substrate semantics → `_workspace_guide.md` (ADR-281); governance files → the wake envelope's own labeled headers.

### Composed coherence

Beyond partition (§3.2.1), the assembled frame must pass the **composed-coherence** discipline ([agent-composition.md](agent-composition.md) §3.2.2): read the assembled frame as one document — does it tell a single consistent story about (a) what the Reviewer is, (b) how it acts, (c) where its agency ends, consistent with FOUNDATIONS Axiom 1 §4 + Axiom 2? The directs-not-executes action-grammar is the canonical resolution (the Reviewer directs the System Agent; it does not execute with its own hands). **Any edit to a persona-frame section must run the composed-coherence test in the same commit.**

---

## The Rung-1 harness split (ADR-381 D3)

Today's occupant (Freddie, the Rung-1 substrate steward) operates over **reversible substrate**. Per ADR-380 D3 + ADR-381 D3, the governance harness splits across the activation rungs: **budget + pace are exercised** at Rung 1 (Freddie burns tokens, has a cadence); **mandate + autonomy are carried, not exercised** (degenerate over reversible substrate — no consequential external write for the AUTONOMY ceiling to gate). The envelope pre-loads all of them uniformly (the contract is one shape across rungs); the degeneracy is in *exercise*, not *carriage*. **Canon must not claim "the autonomy harness was validated on Freddie."** The full statement — and why carried-not-exercised is correct, not a bug — is the canonical prose in [reviewer-occupant-contract.md](reviewer-occupant-contract.md) §"The Rung-1 harness split."

## How the occupant consumes the contract

The flow, end to end:

```
load_reviewer_governance_envelope()   →  FreddieContext        [kernel side]
    →  invoke_freddie(trigger, context)  →  FreddieOutput      [occupant side]
        →  reviewer_audit / dispatcher write back to substrate   [kernel side]
```

- The **kernel** assembles a `FreddieContext` from substrate (`freddie_envelope.py`) and hands it to the occupant.
- The **occupant** (`invoke_freddie`) runs its loop, makes tool calls (`ReadFile`, `FireInvocation`, `ProposeAction`, `WriteFile` lock-gated, `ReturnVerdict`, etc. — the `FREDDIE_PRIMITIVES` curated set per ADR-258), and returns a `FreddieOutput`.
- The **kernel** (dispatcher + `reviewer_audit.py`) writes the verdict back to substrate (`judgment_log.md`, `standing_intent.md`, etc.) with `authored_by="reviewer:{FREDDIE_MODEL_IDENTITY}"` attribution (ADR-209 + ADR-288).

The occupant never reaches around the contract to read kernel internals, and the kernel never reaches into the occupant's implementation. The proof that the ABI is decoupled: `occupant_contract.py` imports with `typing` only — no `anthropic`, no `services.*` (ADR-315 D2). See [reviewer-occupant-contract.md](reviewer-occupant-contract.md).

---

## What the occupant is not

- **Not the seat.** The seat is substrate (`/workspace/persona/*`); the occupant is a module (`freddie_agent.py`). Rotating the occupant is a file write to `OCCUPANT.md`, not a code change. See [reviewer-seat-substrate.md](reviewer-seat-substrate.md).
- **Not an ABC or pluggable abstraction.** ADR-194 v2 retracted v1's "Reviewer ABC"; ADR-315 D1 preserved that retraction. The occupant is carved as a *data*-contract-bounded module, not an OO interface over the seat.
- **Not the only possible occupant.** `freddie_agent.py` implements today's `ai:freddie-sonnet-v8`. Human occupants bypass it; external occupants are deferred (ADR-315 D6).
- **Not free to widen autonomy.** The occupant reads `AUTONOMY.md` as a ceiling. `principles.md` may narrow; nothing the occupant does widens delegation beyond the operator's declaration (ADR-217 D4).

---

## L3 deferral (the package carve)

[ADR-315](../adr/ADR-315-reviewer-occupant-contract.md) D6 defers restructuring `api/agents/reviewer_*` into a self-contained `api/agents/reviewer/` package (depending only on the published contract + `services.anthropic`). That is the literally-extractable unit — the form a future `external:<service>` occupant or open-core split would take. **Not built now**: per Derived Principle 7, the package move earns its churn only when a second consumer exists. The published contract (L2) already delivers portability + separate documentation; L3 changes only file *layout*, not the boundary. **Trigger**: productizing an external judgment occupant, or a ratified open-core decision.

---

## Relationship to other canons

- [reviewer-seat-substrate.md](reviewer-seat-substrate.md) — the seat this occupant fills (substrate, attribution contract, calibration).
- [reviewer-occupant-contract.md](reviewer-occupant-contract.md) — the published ABI between seat and occupant.
- [agent-composition.md](agent-composition.md) §3.2.1 + §3.2.2 — the persona-frame partition + composed-coherence discipline (singular enforcement home; this doc points, does not duplicate).
- [ADR-256](../adr/ADR-256-unified-reviewer-invocation.md) — `invoke_freddie` unified entry point.
- [ADR-258](../adr/ADR-258-reviewer-as-personified-chat-mode-operator.md) — `FREDDIE_PRIMITIVES` curated tool set + default write-locks.
- [ADR-315](../adr/ADR-315-reviewer-occupant-contract.md) — seat ≠ occupant; the carve that produced this document.
