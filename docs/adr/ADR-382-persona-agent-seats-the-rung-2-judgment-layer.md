# ADR-382 — Persona-Agent Seats: the Rung-2 Judgment Layer (name-only placeholder)

> **Status**: **Proposed — NAME-ONLY PLACEHOLDER** (2026-06-29). This ADR **reserves the number and frames the concept; it decides nothing.** Lifecycle, creation surface, and trust model are an entire discourse of their own — explicitly deferred (ADR-375 §7 Cut 2: *"its own discourse — different lifecycle, creation surface, trust model. Explicitly out of scope."*). Do NOT build against this; it exists so the concept has a stable home and the rung vocabulary has a Rung-2 anchor.
> **Date**: 2026-06-29
> **Authors**: KVK (operator) + Claude (collaborator)
> **Owes-from**: [ADR-375](ADR-375-phase-1-substrate-for-humans-and-external-agents.md) §7 Cut 2 (user-authored independent agent seats) + [ADR-216](ADR-216-orchestration-surface-vs-judgment-persona.md) (the original "user-authored domain Agents").
> **Builds on**: [the two-order Freddie direction](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md) (persona agents = the 2nd-order judgment labor Freddie creates + governs), [ADR-380](ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md) (**persona agents = Rung 2** — consequential external action, deferred from the launch build, gated by an exogenous track-record clock).
> **Sibling**: [ADR-381](ADR-381-freddie-the-rung-1-substrate-steward.md) (Freddie = Rung 1; the management seat that creates + governs these Rung-2 seats).
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — the 2nd-order judgment seat).

---

## 1. The concept (framed, not decided)

A **persona-agent seat** is a 2nd-order internal agent the operator authors (via the YARNNN front-end pre-set picker — the two-order direction H1) and **Freddie creates + governs**. Each holds an operator-authored persona, a bounded mandate, standing intent, and — when Freddie sets the authority — the power to **act on the operator's behalf** (consequential external action). These are the trader, the author, the domain characters. They are **Rung 2** (ADR-380): consequential, irreversible, deferred from the launch build, validated by an exogenous multi-quarter track-record clock.

What a persona agent is NOT:
- **Not Freddie** (Rung 1, one systemic management seat — ADR-381).
- **Not an external agent** (a *principal on the outside*, ADR-373 — an external caller with a grant, no workspace-resident standing intent).
- The line: a persona agent is an *internal seat that reasons from workspace-resident standing intent Freddie created*; an external agent *brings its own intent from outside* (the substrate-residency-of-intent line, per the two-order direction).

## 2. What this placeholder DEFERS (the whole discourse)

Every substantive question is its own session — named so they stop contaminating the Rung-0/1 launch work, NOT answered here:

1. **Lifecycle & creation surface** — the front-end pre-set picker → Freddie instantiates + governs. The minimal "create a persona agent" act. **TBD.**
2. **Trust & authority model** — propose-only vs. accountable-action; how Freddie sets/revokes "act on behalf"; the autonomy grant per agent. *[lean: graduated propose → witness → earn-autonomy, per ADR-380's open vision discussion — but the vision boundary is itself UNDECIDED (ADR-380 §5).]* **TBD.**
3. **Accountability** — DP24/DP30 (stewardship + the standing obligation) relocate to the persona agent (the two-order direction §5); how. **TBD.**
4. **Seat substrate** — how much of the ADR-315 seat≠occupant six-file substrate generalizes per persona agent (coordinates with ADR-381 D4). **TBD.**
5. **The Rung-2 validation clock** — how track-record accrues + what "earned autonomy" requires (ADR-380 D4). **TBD.**

## 3. What this placeholder does NOT do

- Decides nothing — it reserves the number and frames the concept.
- Builds no seat, no lifecycle, no creation surface, no schema.
- Does not close ADR-380 §5's open vision boundary (which governs whether Rung 2 is the *vision*, not just deferred from the *build*).
- Does not touch code or the re-founding keystone cascade.
